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
from mqtt_helper import MQTTClient

import json
import time
import math
import signal
import sys
import requests
import logging
from datetime import datetime

poll_interval = 30 #same as defined in the Enphase hardware setup in Domoticz

#Domoticz Settings
enphase_idx = 10298
domoticz_url              = str("http://192.168.0.90:8080/json.htm?type=command&param=getdevices&rid=") + str(enphase_idx)

#MQTT Settings
broker_ip                = "192.168.0.90"
broker_port              = 2883
broker_username          = "domoticz"
broker_password          = "123domoticz"
broker_public_base_topic = "enphase/envoy-s/meters"

broker_reconnect_interval = 30

have_data = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    #format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = False

def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) for graceful shutdown."""
    global shutdown_flag
    logger.info("\nReceived SIGINT, initiating graceful shutdown...")
    shutdown_flag = True

def on_connect_callback(client, userdata, flags, rc):
    """Callback when connected to MQTT broker."""
    if rc == 0:
        logger.info("✓ Connected successfully!")
    else:
        logger.error(f"✗ Connection failed with return code: {rc}")

def on_disconnect_callback(client, userdata, rc):
    """Callback when disconnected from MQTT broker."""
    if rc == 0:
        logger.info("✓ Disconnected gracefully")
    else:
        logger.warning(f"⚠ Unexpected disconnect (return code: {rc})")

def on_message_callback(client, userdata, message):
    """Callback when a message is received."""
    topic = message.topic
    payload = message.payload.decode('utf-8')
    logger.info(f"📨 Received message on '{topic}': {payload}")

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
        power = abs(math.ceil(float(result[0]['Usage'].split(' ')[0])))
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

def main():
    global shutdown_flag
    
    # Register signal handler for SIGINT
    signal.signal(signal.SIGINT, signal_handler)

    # Create MQTT client
    logger.info("Enphase2MQTT (c) 2024-2025 PA1DVB")
    mqtt_client = MQTTClient(
        broker=broker_ip, 
        port=broker_port, 
        client_id="Enphase2MQTT",
        reconnect_interval=broker_reconnect_interval
    )
    
    mqtt_client.set_auth(broker_username, broker_password)

    # Register callbacks
    mqtt_client.on_connect(on_connect_callback)
    mqtt_client.on_disconnect(on_disconnect_callback)
    mqtt_client.on_message(on_message_callback)

    # Connect to broker
    connection_result = mqtt_client.connect()
    
    if connection_result:
        logger.info("Successfully connected to MQTT Broker!")
    else:
        logger.warning("Initial MQTT connection failed - will retry in background")
        logger.info(f"Auto-reconnect will attempt every {broker_reconnect_interval} seconds")

    # Give it a moment to connect
    time.sleep(1)
    
    """
    # Subscribe to topics
    logger.info("Subscribing to topics...")
    mqtt_client.subscribe("test/topic1", qos=0)
    mqtt_client.subscribe("test/topic2", qos=1)
    mqtt_client.subscribe("test/#", qos=0)  # Wildcard subscription
    
    # Wait a bit for subscriptions to complete
    time.sleep(0.5)
    """

    ltime = int(time.time())
    sec_counter = poll_interval - 2

    while not shutdown_flag:
        # Process MQTT network events (includes auto-reconnect logic)
        mqtt_client.loop(timeout=1.0)        

        atime = int(time.time())
        if ltime == atime:
            continue
        ltime = atime
        sec_counter += 1
        if sec_counter % poll_interval == 0:
            if mqtt_client.is_connected():
                get_enphase_details()
        if sec_counter % 10 == 0:
            if mqtt_client.is_connected():
                if have_data == True:
                    ojson['pv']['last_update'] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
                    mqtt_client.publish(broker_public_base_topic, json.dumps(ojson))

        # Small sleep to prevent CPU spinning
        time.sleep(1)

    # Graceful shutdown
    logger.info("Shutting down...")
    mqtt_client.disconnect()
    
    # Give time for disconnect to complete
    time.sleep(1)
    
    logger.info("Goodbye!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
