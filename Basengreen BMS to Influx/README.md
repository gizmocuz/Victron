


# Basengreen BMS to InfluxDB

This project is created to publish all parameters from a BasenGreen BMS to InfluxDB
You can use these values with Grafana to build a monitoring dashboard

## Configuration
Configuration is done by editing the python file.
Required information: BMS serial port, InfluxDB parameters

### Example
![screenshot_1](images/screenshot1)
![screenshot_2](images/screenshot2)

### This python plugin can run in the background as a service.
Let's assume this script is installed in /home/dietpi/basen_bms.py

    sudo nano /etc/systemd/system/basenbms.service
*file contents:*

    [Unit]
    Description=Basengreen BMS 2 InfluxDB
    Wants=network-online.target
    After=network.target network-online.target
    [Service]
    Type=simple
    Restart=always
    ExecStart=/usr/bin/python3 /home/dietpi/basen_bms.py
    [Install]
    WantedBy=multi-user.target

*issue:*

    sudo systemctl daemon-reload

    sudo systemctl enable basenbms.service

    sudo systemctl start basenbms.service
