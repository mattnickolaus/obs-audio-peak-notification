import obspython as S  # studio
from types import SimpleNamespace
from ctypes import *
from ctypes.util import find_library
import serial
import serial.tools.list_ports

###############
#OS Setup
###############
obsffi = CDLL("obs")#windows
#obsffi = CDLL(find_library("obs"))#Linux/Mac
print("Script OK!")

###############
#Serial Devices Search
###############
print('Checking Com Ports.......')
ports = serial.tools.list_ports.comports(include_links=False)
ser = ""
for port in ports :
    print('Found port: '+ port.device+ " !")

###############
#Create Global Namespace
###############
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

###############
#Serial Output
###############
def output_to_file(volume):
    vol = str(volume)
    if(vol == "-inf"):
        volume = -999
    
    if float(volume) >= -0.09:
        ser.write((str((1))+"\n\0").encode())
        return 0

    ser.write((str((volume))+"\n\0").encode())
    return 0
    
    

    #with open("c:/current_db_volume_of_source_status.txt", "w", encoding="utf-8") as f:
    #        f.write(vol)
              
    #        ser.write((str(int(vol)) + "\r\n").encode())
            
            #if float(vol) >= 0:
            #    print("!---------------clip------------------!")

###############
#Python Global Variables
###############
        
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
G.source_name = source_name
G.volmeter = "not yet initialized volmeter instance"
G.callback = output_to_file

###############
#Update Audio Device Selection
###############
def update_source():
    
    global interval
    global source_name
    #print(source_name)    

    if source_name is not None:
        G.source_name = source_name
        #G.source_name = S.obs_data_get_string(source,"name")
        #print(G.source_name)

        S.timer_add(event_loop, G.tick)
        global stop_loop
        stop_loop = False

###############
#Button Call / Initiate Run Sequence
###############
def refresh_pressed(props, prop):
    global ser
    print("Starting Output")
    ser = serial.Serial(device_name)
    if ser.isOpen():
        ser.close()

    ser = serial.Serial(device_name, 9600, timeout=1)
    ser.flushInput()
    ser.flushOutput()
    print('Connecting to: ' + ser.name)
    
    update_source()

###############
#Settings Menu Description
###############
def script_description():
    return "Volume DB to Com Port Output as Text String Click Refresh Script to Change/Search Com Ports or if any errors .\n\n John Leger, upgradeQ & Various"

###############
#Global Variable Update
###############
def script_update(settings):
    global source_name
    global device_name

    interval    = S.obs_data_get_int(settings, "interval")
    source_name = S.obs_data_get_string(settings, "source")
    device_name = S.obs_data_get_string(settings, "device")
    

def script_defaults(settings):
    S.obs_data_set_default_int(settings, "interval", 30)

###############
#Settings Layout and Functions
###############
def script_properties():
    props = S.obs_properties_create()

    p = S.obs_properties_add_list(props, "source", "Audio Source", S.OBS_COMBO_TYPE_EDITABLE, S.OBS_COMBO_FORMAT_STRING)
    sources = S.obs_enum_sources()
    portlist = ""
    if sources is not None:
        for source in sources:
            source_id = S.obs_source_get_unversioned_id(source)
            #print(source_id)
            if source_id == "asio_input_capture" or source_id == "wasapi_input_capture" or source_id == "wasapi_output_capture":
                name = S.obs_source_get_name(source)
                
                S.obs_property_list_add_string(p, name, name)

        S.source_list_release(sources)
    
    com = S.obs_properties_add_list(props, "device", "COM PORT", S.OBS_COMBO_TYPE_EDITABLE, S.OBS_COMBO_FORMAT_STRING)
    ports = serial.tools.list_ports.comports(include_links=False)
    for port in ports :
        port.device
        
        S.obs_property_list_add_string(com,port.device,port.device)
    S.obs_properties_add_button(props, "button", "Connect", refresh_pressed)
    S.obs_properties_add_button(props, "button2", "Stop", script_unload_button)
    return props


###############
#Main Loop runs after Connect Button Is Pressed
###############
def event_loop():
    """wait n seconds, then execute callback with db volume level within interval"""
    if stop_loop == True:
        return 
    if G.duration > G.start_delay:
        if not G.lock:
            print("Setting up Meter Instance")
            source = g_obs_get_source_by_name(G.source_name.encode("utf-8"))
            G.volmeter = g_obs_volmeter_create(OBS_FADER_LOG)
            g_obs_volmeter_add_callback(G.volmeter, volmeter_callback, None)
            if g_obs_volmeter_attach_source(G.volmeter, source):
                g_obs_source_release(source)
                G.lock = True
                print("Attached to source:" + G.source_name + "!")
                return
        G.tick_acc += G.tick_mili
        if G.tick_acc > G.interval_sec:
            G.callback(G.noise)
            G.tick_acc = 0
    else:
        G.duration += G.tick_mili

###############
#Restart / Kill Script
###############
def script_unload():
    global stop_loop
    stop_loop = True
    g_obs_volmeter_remove_callback(G.volmeter, volmeter_callback, None)
    g_obs_volmeter_destroy(G.volmeter)
    if ser.isOpen():
        ser.flushInput()
        ser.flushOutput()
        ser.close()
    print("Removed volmeter & volmeter_callback")

def script_unload_button(pad,pad2):
    global stop_loop
    stop_loop = True
    g_obs_volmeter_remove_callback(G.volmeter, volmeter_callback, None)
    g_obs_volmeter_destroy(G.volmeter)
    if ser.isOpen():
        ser.flushInput()
        ser.flushOutput()
        ser.close()
    print("Removed volmeter & volmeter_callback")


