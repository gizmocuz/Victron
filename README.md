# Victron battery helpers
Scripts/Tools to control one or multiple battery systems in combination with [Victron](https://www.victronenergy.com) and [Domoticz](https://domoticz.com) hardware.

[Github project home](https://github.com/gizmocuz/Victron)

## Projects
Zigbee2MQTT integrates well with (almost) every home automation solution because it uses MQTT. However the following integrations are worth mentioning:

### [Basengreen BMS to Influx](https://github.com/gizmocuz/Victron/tree/main/Basengreen%20BMS%20to%20Influx)
- This project is created to publish all parameters from a BasenGreen BMS to InfluxDB You can use these values with Grafana to build a monitoring dashboard.

### [Enphase2MQTT](https://github.com/gizmocuz/Victron/tree/main/Enphase2MQTT)
- This project is created to publish the actual delivery and kWh counter of the Enphase Meter to MQTT
It is currently used for [Venus-OS, dbus-mqtt-pv](https://github.com/mr-manuel/venus-os_dbus-mqtt-pv)

## Support & help
If you need assistance or want to discuss, please check the [opened issues](https://github.com/gizmocuz/Victron/issues).
Feel free to help with Pull Requests when you were able to fix/improve things or add new projects.
