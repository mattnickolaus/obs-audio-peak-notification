import requests
import obspython as obs
import os

from dotenv import load_dotenv

from types import SimpleNamespace
from ctypes import *
from ctypes.util import find_library


#################### Ntfy Request #########################

load_dotenv()
TOPIC_ID = os.getenv("TOPIC_ID")

# API call to ntfy for push notificaiton
def send_notification(): 
    print("Making request")
    requests.post(f"https://ntfy.sh/{TOPIC_ID}",
        data="!!Luna is Barking!!".encode(encoding='utf-8'))

###########################################################

### OS Setup ###
# obsffi = CDLL(find_library("obs"))#Linux/Mac
obsffi = CDLL("obs")#windows
print("Script library found!") 


### Global Namespace ###
G = SimpleNamespace()
stop_loop = False

def wrap(funcname, restype, argtypes):
    """Simplify wrapping ctypes functions in obsffi"""
    func = getattr(obsffi, funcname)
    func.restype = restype
    func.argtypes = argtypes
    globals()["g_" + funcname] = func

class Source(Structure):
    pass

class Volmeter(Structure):
    pass

volmeter_callback_t = CFUNCTYPE(
    None, c_void_p, POINTER(c_float), POINTER(c_float), POINTER(c_float)
)
wrap("obs_get_source_by_name", POINTER(Source), argtypes=[c_char_p])
wrap("obs_source_release", None, argtypes=[POINTER(Source)])
wrap("obs_volmeter_create", POINTER(Volmeter), argtypes=[c_int])
wrap("obs_volmeter_destroy", None, argtypes=[POINTER(Volmeter)])
wrap(
    "obs_volmeter_add_callback",
    None,
    argtypes=[POINTER(Volmeter), volmeter_callback_t, c_void_p],
)
wrap(
    "obs_volmeter_remove_callback",
    None,
    argtypes=[POINTER(Volmeter), volmeter_callback_t, c_void_p],
)
wrap(
    "obs_volmeter_attach_source",
    c_bool,
    argtypes=[POINTER(Volmeter), POINTER(Source)],
)

@volmeter_callback_t
def volmeter_callback(data, mag, peak, input):
    G.noise = float(peak[0])

### Callback Monitoring ### 
def clip_volume_monitoring(volume):
    if float(volume) >= 0:
        print(f"Audio Value: {volume}")
        print("!---------- clipped ----------!")
        send_notification()


### Global Variables ###

source_name = ""
device_name = ""
OBS_FADER_LOG = 2
G.lock = False
G.start_delay = 3
G.duration = 0
G.noise = 999
G.tick = 10
G.tick_mili = G.tick * 0.001
G.interval_sec = 0.025
G.tick_acc = 0
G.source_name = "GH5"
G.volmeter = "not yet initialized volmeter instance"
G.callback = clip_volume_monitoring


### Event Loop ### 
def event_loop():
    """wait n seconds, then execute callback with db volume level within interval"""
    if G.duration > G.start_delay:
        if not G.lock:
            print("setting volmeter")
            source = g_obs_get_source_by_name(G.source_name.encode("utf-8"))
            G.volmeter = g_obs_volmeter_create(OBS_FADER_LOG)
            g_obs_volmeter_add_callback(G.volmeter, volmeter_callback, None)
            if g_obs_volmeter_attach_source(G.volmeter, source):
                g_obs_source_release(source)
                G.lock = True
                print("Attached to source")
                return
        G.tick_acc += G.tick_mili
        if G.tick_acc > G.interval_sec:
            G.callback(G.noise)
            G.tick_acc = 0
    else:
        G.duration += G.tick_mili


def script_unload():
    g_obs_volmeter_remove_callback(G.volmeter, volmeter_callback, None)
    g_obs_volmeter_destroy(G.volmeter)
    print("Removed volmeter & volmeter_callback")


obs.timer_add(event_loop, G.tick)
