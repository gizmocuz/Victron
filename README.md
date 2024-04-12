
# Victron battery helpers
Scripts/Tools to control one or multiple battery systems in combination with [Victron](https://www.victronenergy.com) and [Domoticz](https://domoticz.com) hardware.

This is a **work in progress**!

Maybe ideas and discussions are made with another Domoticz user (Herman/Heggink) and we're trying to make the ultimate scripts that will work for both systems (1 phase and 3 phase)

[Github project home](https://github.com/gizmocuz/Victron)
[Heggink Github project home](https://github.com/heggink/domoticz-victron)

## Projects
Zigbee2MQTT integrates well with (almost) every home automation solution because it uses MQTT. However the following integrations are worth mentioning:

### [Basengreen BMS to Influx](https://github.com/gizmocuz/Victron/tree/main/Basengreen%20BMS%20to%20Influx)
- This project is created to publish all parameters from a BasenGreen BMS to InfluxDB You can use these values with Grafana to build a monitoring dashboard.

### [Enphase2MQTT](https://github.com/gizmocuz/Victron/tree/main/Enphase2MQTT)
- This project is created to publish the actual delivery and kWh counter of the Enphase Meter to MQTT
It is currently used for [Venus-OS, dbus-mqtt-pv](https://github.com/mr-manuel/venus-os_dbus-mqtt-pv)

### [dzVents Scripts](https://github.com/gizmocuz/Victron/tree/main/dzVents)
- At the moment I am rewriting most scripts and am changing the logic.
It is not recommended yet to use these scripts yet but are here for review and discussion.

### [Grafana](https://github.com/gizmocuz/Victron/tree/main/Grafana)
- My Grafana Dashboard

### [Victron Node Red](https://github.com/gizmocuz/Victron/tree/main/Victron%20Node%20Red)
- Node Red flow running on the Cerbo CX. This also creates most of the devices via MQTT Auto Discovery

## Support & help
If you need assistance or want to discuss, please check the [opened issues](https://github.com/gizmocuz/Victron/issues).
Feel free to help with Pull Requests when you were able to fix/improve things or add new projects.
