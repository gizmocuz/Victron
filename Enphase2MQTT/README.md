# Domoticz Enphase to MQTT

This project is created to publish the actual delivery and kWh counter of the Enphase Meter to MQTT
It is currently used for [Venus-OS, dbus-mqtt-pv](https://github.com/mr-manuel/venus-os_dbus-mqtt-pv)

## Configuration
Configuration is done by editing the python file.
Required information: MQTT Broker, Domoticz URL + idx of Enphase kWh Production sensor

### This python plugin can run in the background as a service.
Let's assume this script is installed in /home/dietpi/enphase2mqtt.py

    sudo nano /etc/systemd/system/enphase2mqtt.service
*file contents:*

    [Unit]
    Description=Domoticz Enphase 2 MQTT
    Wants=network-online.target
    After=network.target network-online.target
    [Service]
    Type=simple
    Restart=always
    ExecStart=/usr/bin/python3 /home/dietpi/enphase2mqtt.py
    [Install]
    WantedBy=multi-user.target

*issue:*

    sudo systemctl daemon-reload
    sudo systemctl enable enphase2mqtt.service
    sudo systemctl start enphase2mqtt.service

