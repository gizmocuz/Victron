import paho.mqtt.client as mqtt
import json
import time
from queue import Queue

class MQTTHelper():
    client = None
    q = None
    on_connect = None
    on_disconnect = None
    on_message = None
    verbose = False
    broker_ip = "127.0.0.1"
    broker_port = 1883
    broker_username = ""
    broker_password = ""
    
    need_Reconnect = True
    last_retry_time = time.time() - 20
    
    def __init__(self):
        self.q = Queue()
        
    def isConnected(self):
        if self.client is None:
            return False
        return self.client.connected_flag
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        if rc==0:
            client.connected_flag=True
            client.disconnect_flag=False
            print("connected OK")
            if self.on_connect:
                self.on_connect(client)
        else:
            print("Bad connection Returned code= ",rc)

    def on_mqtt_disconnect(self, client, userdata, rc):
        if rc != 0:
            print("MQTT-Broker disconnected, reason: "  +str(rc))
            self.last_retry_time = time.time()
        client.connected_flag=False
        client.disconnect_flag=True
        if self.on_disconnect:
            self.on_disconnect(client)
        
    def on_mqtt_message(self, client, userdata, message):
        client.q.put(message)
        
    def connect_to_mqtt(self):
        mqtt.Client.connected_flag=False
        mqtt.Client.disconnect_flag=False
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "enphase2mqtt")
        client.on_connect=self.on_mqtt_connect
        client.on_disconnect=self.on_mqtt_disconnect
        client.on_message = self.on_mqtt_message
        client.q = self.q
        client.loop_start()
        if self.broker_username != "":
            client.username_pw_set(self.broker_username, self.broker_password)
    
        print(f"Connecting to MQTT-Broker: {self.broker_ip}:{self.broker_port}")
        
        try:
            client.connect(self.broker_ip, self.broker_port)
            #client.loop_forever()
            wait_counter = 0
            while not client.connected_flag: #wait in loop
                #print(".", end="")
                time.sleep(0.5)
                wait_counter+=1
                if wait_counter == 10:
                    print("could not connect to MQTT broker, will retry again soon...")
                    return None
            return client
        except Exception as ex:
            print(f"Exception: {ex}")
            return None

    def close(self):
        if self.client is not None:
            self.client.loop_stop()    #Stop loop 
            self.client.disconnect() # disconnect

    def publish(self, topic, payload, qos=0, retain=False):
        if self.client is not None:
            self.client.publish(topic, payload, qos, retain);
        else:
            print("publish error: Not connected!")

    def loop(self):
        if self.client is None:
            now  = time.time()
            tdiff = int(now - self.last_retry_time)
            if tdiff > 10:
                self.client = self.connect_to_mqtt()
                self.last_retry_time = time.time()
                if self.client is None:
                    return
        else:
            if self.client.disconnect_flag == True:
                self.client = None #force reconnect
                return
        while not self.q.empty():
            message = self.q.get()
            if message is None:
                continue
            if self.on_message:
                self.on_message(self.client, message)

