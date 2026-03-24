import requests
import obspython as obs
import os

from dotenv import load_dotenv

from types import SimpleNamespace
from ctypes import *
from ctypes.util import find_library


load_dotenv()
TOPIC_ID = os.getenv("TOPIC_ID")

# API call to ntfy for push notificaiton
def send_notification(): 
    print("Making request")
    requests.post(f"https://ntfy.sh/{TOPIC_ID}",
        data="!!Luna is Barking!!".encode(encoding='utf-8'))


### OS Setup
obsffi = CDLL(find_library("obs"))#Linux/Mac
# obsffi = CDLL("obs")#windows
print("Script library found!") 






