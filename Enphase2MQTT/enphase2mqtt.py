"""
#Domoticz Enphase->MQTT
@Author: PA1DVB
@Date: 10 April 2024
@Version: 1.02

needed libraries
pip3 install requests paho-mqtt

History
1.02 - Sending data every 10 seconds
"""
from helpers import *
from mqtt_helper import MQTTHelper

import json
import time
import signal
import sys
import requests

poll_interval = 60 #same as defined in the Enphase hardware setup in Domoticz

#Domoticz Settings
enphase_idx = 10298
domoticz_url              = str("http://192.168.0.90:8080/json.htm?type=command&param=getdevices&rid=") + str(enphase_idx)

#MQTT Settings
broker_ip                = "192.168.0.90"
broker_port              = 1883
broker_username          = "domoticz"
broker_password          = "123domoticz"
broker_public_base_topic = "enphase/envoy-s/meters"

have_data = False

def handle_mqtt_connect(client):
    print("Connected to MQTT broker!")
    #client.subscribe("zigbee2mqtt/#")

    
def handle_mqtt_message(client, message):
    #print("received from queue", msg)
    try:
        decoded_message = ""#str(message.payload.decode("utf-8"))
        print(f"topic: {message.topic}, payload: ...{decoded_message}")
        #jmsg = json.loads(decoded_message)
        #print(f"received: {jmsg}")
    except ValueError as e:
        return False

class SIGINT_handler():
    def __init__(self):
        self.SIGINT = False

    def signal_handler(self, signal, frame):
        print('Going to stop...')
        self.SIGINT = True

def publish_value(value):
    mqtt.publish(broker_public_base_topic, value)

def get_enphase_details():
    global ojson
    global have_data
    power = -1
    total_kwh = -1
    last_update = ""

    try:
        r = requests.get(domoticz_url)
        ijson = r.json()
        result = ijson.get('result')
        #print(result)
        power = abs(float(result[0]['Usage'].split(' ')[0]))
        total_kwh = float(result[0]['Data'].split(' ')[0])
        last_update = result[0]['LastUpdate']
    except Exception as ex:
        print(f"Get Domoticz Enphase data  Exception: {ex}")
        have_data = False
        return
    
    if power != -1:
        ojson = {
          "pv": {
            "last_update": last_update,
            "power": power,
            "energy_forward": total_kwh,
            "L1": {
                "power": power,
                "energy_forward": total_kwh
            }
          }
        }
        
        have_data = True

mqtt = MQTTHelper()
mqtt.on_message = handle_mqtt_message
mqtt.on_connect = handle_mqtt_connect
mqtt.broker_ip = broker_ip
mqtt.broker_port = broker_port
mqtt.broker_username = broker_username
mqtt.broker_password = broker_password


handler = SIGINT_handler()
signal.signal(signal.SIGINT, handler.signal_handler)

ltime = int(time.time())
sec_counter = poll_interval - 2

while True:
    time.sleep(0.2)

    if handler.SIGINT:
        break
    mqtt.loop()
    
    atime = int(time.time())
    if ltime == atime:
        continue
    ltime = atime
    sec_counter += 1
    if sec_counter % poll_interval == 0:
        if mqtt.isConnected():
            get_enphase_details()
    if sec_counter % 10 == 0:
        if mqtt.isConnected():
            if have_data == True:
                publish_value(json.dumps(ojson))

mqtt.close()

print("done...")
