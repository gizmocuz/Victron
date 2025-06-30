#!/usr/bin/python3

"""
@Author: PA1DVB
@Date: 24 June 2025
@Version: 1.01

Special thanks to esphome-jk-bms,
I found 80% of the fields by reverse engineering and the others from here

needed libraries
pip3 install requests paho-mqtt

"""

from mqtt_helper import MQTTHelper

import json
import time
import requests
import serial
import struct
import signal
from struct import unpack_from

poll_interval = 10

debug = False

influx_host = "http://172.16.0.201:8086"
influx_token = "oU9XL0uckHKyzxWuKbEamWJTb2yNIJNI4cNuPCWdNhxqOy3oiUbltsBrScW1ox8xnxIRjBJL9WHIDioG_aUHiQ=="
influx_bucket = "domoticz_home"
influx_org = "DVBControl"

influx_url = f'{influx_host}/api/v2/write?org={influx_org}&bucket={influx_bucket}&precision=s'
influx_headers = {
  'Authorization': f'Token {influx_token}',
  'Content-type': 'text/plain'
}

#MQTT Settings
broker_ip                = "192.168.0.90"
broker_port              = 1883
broker_username          = "domoticz"
broker_password          = "123domoticz"
broker_public_base_topic = "jk_pack_1/status"

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

def crc16mod(data: bytes, len: int, poly: hex = 0xA001) -> bytes:
    crc = 0xFFFF
    for b2 in range(len):
        byte = data[b2]
        crc ^= byte
        for _ in range(8):
            crc = ((crc >> 1) ^ poly
                   if (crc & 0x0001)
                   else crc >> 1)

    return crc.to_bytes(2, byteorder='little')
    
def get16(data: bytes, offset: int) -> int:
    return (data[offset + 1] * 256) + data[offset]
 
def get32(data: bytes, offset: int) -> int:
    return (data[offset + 3] << 24) + (data[offset + 2] << 16) + (data[offset + 1] << 8) + data[offset]

def get32i(data: bytes, offset: int):
    # Combine the bytes into a 32-bit integer (little-endian)
    int_value = (data[offset + 0] << 0) | \
                (data[offset + 1] << 8) | \
                (data[offset + 2] << 16) | \
                (data[offset + 3] << 24)
    
    # Convert to signed int32 if necessary
    if int_value >= 2**31:
        int_value -= 2**32

    return int_value

def get32if(data: bytes, offset: int):
    # Combine the bytes into a 32-bit integer (little-endian)
    int_value = (data[offset + 0] << 0) | \
                (data[offset + 1] << 8) | \
                (data[offset + 2] << 16) | \
                (data[offset + 3] << 24)
    
    # Convert to signed int32 if necessary
    if int_value >= 2**31:
        int_value -= 2**32

    # Convert the int32 value to float
    float_value = float(int_value)
    return float_value
    
def get32_float(data: bytes, offset: int) -> float:
    # Combine the bytes into a uint32_t, assuming little-endian format
    uint_value = (data[offset + 0] << 0) | \
                 (data[offset + 1] << 8) | \
                 (data[offset + 2] << 16) | \
                 (data[offset + 3] << 24)
    
    # Convert the combined value to float
    float_value = float(uint_value)
    return float_value

def get16_float(data: bytes, offset: int) -> float:
    # Combine the bytes into an int16_t
    int_value = (data[offset + 0] << 0) | \
                (data[offset + 1] << 8)

    # Convert the combined value to float
    float_value = float(int_value)
    return float_value

def check_bit(byte, n):
    # Ensure that the index is within range (0-7)
    n = n % 8

    # Right shift the byte by 'n' positions and then mask with 1
    bit_value = (byte >> n) & 1
    
    return bit_value == 1

def convert_seconds(total_seconds):
    # Calculate the number of days
    days = total_seconds // (24 * 3600)
    
    remaining_seconds = total_seconds % (24 * 3600)
    hours = remaining_seconds // 3600
    remaining_seconds %= 3600
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    
    return days, hours, minutes, seconds

def print_byte_array(byte_array):
    for i in range(0, len(byte_array), 16):
        hex_bytes = ' '.join('{:02x}'.format(b) for b in byte_array[i:i+16])
        print("{:08d}".format(i) + f': {hex_bytes}')    

def print_byte_array_len(byte_array, offset, len):
    for i in range(0, len, 16):
        hex_bytes = ' '.join('{:02x}'.format(b) for b in byte_array[i+offset:i+offset+16])
        print("{:08d}".format(i) + f': {hex_bytes}')    

def readJKBMS(bms_serial, pack_id):
    voltages=[0]*17
    resistances=[0]*17
    temps=[0]*6
    
    highest_voltage = 0
    lowest_voltage = 100

    array = bytearray(11)
    array[0] = pack_id #//
    array[1] = 0x10 #Function code
    array[2] = 0x16 #Start Adress high
    array[3] = 0x20 #Start Adress low
    array[4] = 0    #numer of registers high
    array[5] = 1    #number of registers low
    array[6] = 2    #data length
    array[7] = 0    #data
    array[8] = 0    #data

    crc16 = crc16mod(array,9)
    array[9] = crc16[0]
    array[10] = crc16[1]

    #print_byte_array(array)

    bms_serial.write(array)
    time.sleep(0.350)
    bytesToRead = bms_serial.in_waiting
    if bytesToRead == 0:
        print("Nothing received from BMS!")
        return
    array2 = bytearray(bms_serial.read(bytesToRead))

    #print('len: ', len(array2))
    if debug == True:
        print_byte_array(array2)
    #return

    if (array2[0] != 0x55):
        print("Invalid data received!")
        return
    if (array2[1] != 0xAA):
        print("Invalid data received!")
        return

    FrameHeader_1 = array2[2]
    FrameHeader_2 = array2[3]

    if (FrameHeader_1 != 0xEB):
        print("Invalid Frame Header 1!")
        return
    if (FrameHeader_2 != 0x90):
        print("Invalid data received!")
        return

    pid = array2[4]
    if (pid != pack_id):
        print("Invalid data received! (pack_id mismatch)")
        return

    cmd = array2[5]
    #print('FrameType/Cmd:', cmd)
    if ((cmd != 0x00) & (cmd != 0x05)):
        print("Invalid data received! (cmd mismatch)")
        return

    tot_cells = 16

    for i in range(1, tot_cells + 1):
        voltage = float(get16(array2, 2 * (i - 1) + 6)) / 1000.0
        voltages[i] = voltage
        if voltage > highest_voltage:
            highest_voltage = voltage
        elif voltage < lowest_voltage:
            lowest_voltage = voltage

        if debug == True:
            print("cell_" + str(i) + "=" + "{:.3f}".format(voltage) + " V")

    #voltage_diff = highest_voltage - lowest_voltage

    if debug == True:
        print('highest_diff: ' + "{:.3f}".format(highest_voltage) + " V")
        print('lowest_diff: ' + "{:.3f}".format(lowest_voltage) + " V")
        #print('voltage_diff: ' + "{:.3f}".format(voltage_diff) + " V")

    # next are 16 values with 0x00 0x00
    #for i in range(1, tot_cells + 1):
    #    something = float(get16(array2, 2 * (i - 1) + 6 + 32)) / 1000.0
    #    print('something: ', something)

    offset = 70
    # 2x 0xFF
    # 2x 0x00
    '''
    // 54    4   0xFF 0xFF 0x00 0x00    Enabled cells bitmask
    //           0x0F 0x00 0x00 0x00    4 cells enabled
    //           0xFF 0x00 0x00 0x00    8 cells enabled
    //           0xFF 0x0F 0x00 0x00    12 cells enabled
    //           0xFF 0x1F 0x00 0x00    13 cells enabled
    //           0xFF 0xFF 0x00 0x00    16 cells enabled
    //           0xFF 0xFF 0xFF 0x00    24 cells enabled
    //           0xFF 0xFF 0xFF 0xFF    32 cells enabled
    '''
    offset += 4
    
    cell_average_voltage = float(get16(array2, offset)) * 0.001
    offset += 2
    if debug == True:
        print('cell_average_voltage: ', cell_average_voltage)

    cell_delta_voltage = float(get16(array2, offset)) * 0.001
    offset += 2
    if debug == True:
        print('cell_delta_voltage: ', cell_delta_voltage)

    cell_number_max_voltage = array2[offset] + 1;
    cell_number_min_voltage = array2[offset + 1] + 1;
    offset += 2
    if debug == True:
        print('cell_number_max_voltage: ', cell_number_max_voltage) #klopt dit wel?
        print('cell_number_min_voltage: ', cell_number_min_voltage)


    for i in range(1, tot_cells + 1):
        #resistance = get16(array2, offset + (2 * (i - 1)))
        resistance = float(get16(array2, offset + (2 * (i - 1)))) / 1000.0
        resistances[i] = resistance
        if debug == True:
            print("cell_" + str(i) + "_resistance=" + "{:.3f}".format(resistance) + " Ohm")

    offset += 32

    # next are 16 values with 0x00 0x00
    #for i in range(1, tot_cells + 1):
    #    something = get16(array2, offset + (2 * (i - 1)))
    #    print('something: ', something)
        
    offset += 32
        
    temp_power_tube = float(get16(array2, offset)) / 10.0
    offset += 2
    if debug == True:
        print('temp powertube: ', temp_power_tube)


    '''
    0x00, 0x00, 0x00, 0x00 # Wire resistance warning bitmask (each bit indicates a warning per cell / wire)
    '''
    offset += 4

    battery_voltage = get32_float(array2, offset) / 1000.0
    offset += 4
    if debug == True:
        print("battery_voltage=" + "{:.2f}".format(battery_voltage) + " V")
    
    #v_avg_cell = battery_voltage / float(tot_cells)
    #if debug == True:
        #print("v_avg_cell=" + "{:.3f}".format(v_avg_cell) + " V")

    #print_byte_array_len(array2, offset, 8)

    power = get32if(array2, offset) / 1000.0
    offset += 4
    if debug == True:
        print("power=" + "{:.3f}".format(power) + " W")

    current = float(get32if(array2, offset)) / 1000.0
    offset += 4
    if debug == True:
        print("current=" + "{:.3f}".format(current) + " A")
        #print("current2=" + "{:.3f}".format(current2) + " A")
        
    if current < 0:
        power = -power
    #or power = battery_voltage * current

    Charging_Status = 0
    Discharge_Status = 0

    if current != 0:
        Charging_Status = 1 if (current > 0) else 0
        Discharge_Status = 1 if (current < 0) else 0

    temps[1] = get16_float(array2, offset) / 10.0
    offset += 2
    if debug == True:
        print('temp_1: ', temps[1])
    
    temps[2] = float(get16(array2, offset)) / 10.0
    offset += 2
    if debug == True:
        print('temp_2: ', temps[2])
    

    '''
    //  # Bit 0     Wire resistance                              0000 0000 0000 0001         0x0001 
    //  # Bit 1     MOS OTP                                      0000 0000 0000 0010         0x0002
    //  # Bit 2     Cell quantity                                0000 0000 0000 0100         0x0004
    //  # Bit 3     Current sensor error                         0000 0000 0000 1000         0x0008
    //  # Bit 4     Cell OVP                                     0000 0000 0001 0000         0x0010
    //  # Bit 5     Battery OVP                                  0000 0000 0010 0000         0x0020
    //  # Bit 6     Charge OCP                                   0000 0000 0100 0000         0x0040
    //  # Bit 7     Charge SCP                                   0000 0000 1000 0000         0x0080
    //  # Bit 8     Charge OTP                                   0000 0001 0000 0000         0x0100
    //  # Bit 9     Charge UTP                                   0000 0010 0000 0000         0x0200
    //  # Bit 10    CPU Aux comm error                           0000 0100 0000 0000         0x0400
    //  # Bit 11    Cell UVP                                     0000 1000 0000 0000         0x0800
    //  # Bit 12    Batt UVP                                     0001 0000 0000 0000         0x1000
    //  # Bit 13    Discharge OCP                                0010 0000 0000 0000         0x2000
    //  # Bit 14    Discharge SCP                                0100 0000 0000 0000         0x4000
    //  # Bit 15    Charge MOS                                   1000 0000 0000 0000         0x8000
    //  # Bit 16    Discharge MOS                           0001 0000 0000 0000 0000        0x10000
    //  # Bit 17    GPS Disconneted                         0010 0000 0000 0000 0000        0x20000
    //  # Bit 18    Modify PWD. in time                     0100 0000 0000 0000 0000        0x40000
    //  # Bit 19    Discharge On Failed                     1000 0000 0000 0000 0000        0x80000
    //  # Bit 20    Battery Over Temp Alarm            0001 0000 0000 0000 0000 0000       0x100000
    //  # Bit 21    Temperature sensor anomaly         0010 0000 0000 0000 0000 0000       0x200000
    //  # Bit 22    PLCModule anomaly                  0100 0000 0000 0000 0000 0000       0x400000
    //  # Bit 23    Reserved                           1000 0000 0000 0000 0000 0000       0x800000
    '''
    
    alarm32 = get32(array2, offset)
    if debug == True:
        print('alarm32: ', alarm32)
    offset += 4
    
    # fuses
    alarm_bits = unpack_from("<I", array2, 166)[0]
    
    Wire_resistance = 1 if (alarm_bits & 0x0001) != 0 else 0
    MOS_OTP = 1 if (alarm_bits & 0x0002) != 0 else 0
    Cell_quantity = 1 if (alarm_bits & 0x0004) != 0 else 0
    Current_sensor_error = 1 if (alarm_bits & 0x0008) != 0 else 0
    Cell_OVP = 1 if (alarm_bits & 0x0010) != 0 else 0
    Battery_OVP = 1 if (alarm_bits & 0x0020) != 0 else 0
    Charge_OCP = 1 if (alarm_bits & 0x0040) != 0 else 0
    Charge_SCP = 1 if (alarm_bits & 0x0080) != 0 else 0
    Charge_OTP = 1 if (alarm_bits & 0x0100) != 0 else 0
    Charge_UTP = 1 if (alarm_bits & 0x0200) != 0 else 0
    CPU_Aux_comm_error = 1 if (alarm_bits & 0x0400) != 0 else 0
    Cell_UVP = 1 if (alarm_bits & 0x0800) != 0 else 0
    Batt_UVP = 1 if (alarm_bits & 0x1000) != 0 else 0
    Discharge_OCP = 1 if (alarm_bits & 0x2000) != 0 else 0
    Discharge_SCP = 1 if (alarm_bits & 0x4000) != 0 else 0
    Charge_MOS = 1 if (alarm_bits & 0x8000) != 0 else 0
    Discharge_MOS = 1 if (alarm_bits & 0x10000) != 0 else 0
    GPS_Disconneted = 1 if (alarm_bits & 0x20000) != 0 else 0
    Modify_PWD_in_time = 1 if (alarm_bits & 0x40000) != 0 else 0
    Discharge_On_Failed = 1 if (alarm_bits & 0x80000) != 0 else 0
    Battery_Over_Temp_Alarm = 1 if (alarm_bits & 0x100000) != 0 else 0
    Temperature_sensor_anomaly = 1 if (alarm_bits & 0x200000) != 0 else 0
    PLCModule_anomaly = 1 if (alarm_bits & 0x400000) != 0 else 0

    balance_current = get16_float(array2, offset) / 1000.0
    offset += 2
    if debug == True:
        print(f'balance_current: {balance_current} A')

    balance_action = array2[offset]
    offset += 1
    '''
    0x00: Off
    0x01: Charging balancer
    0x02: Discharging balancer    
    if 1 or 2 then on, else off
    '''
    if debug == True:
        print(f'balance_action: {balance_action}')

    Balance_Status = 1 if (balance_action != 0) else 0        
  
    SOC =  array2[offset]
    offset += 1
    if debug == True:
        print("SOC=" + "{:.2f}".format(SOC) + " %")
    '''
    SOC_TEST = unpack_from("<B", array2, 173)[0]
    print("SOC_TEST=" + "{:.2f}".format(SOC_TEST) + " %")
    '''

    battery_capacity_remaining = float(get32(array2, offset)) / 1000.0
    offset += 4
    if debug == True:
        print("battery_capacity_remaining=" + "{:.3f}".format(battery_capacity_remaining) + " Ah")

    battery_capacity_total = float(get32(array2, offset)) / 1000.0
    offset += 4
    if debug == True:
        print("battery_capacity_total=" + "{:.3f}".format(battery_capacity_total) + " Ah")

    total_w = (51.2 * battery_capacity_total)
    total_kw = total_w / 1000.0
    if debug == True:
        print('total_kw: ' + '{:.1f}'.format(total_kw));

    total_kw_remaining = (total_w / 100.0) * SOC

    remain_charge_time = 0;
    remain_discharge_time = 0;

    cycles = get32(array2, offset)
    offset += 4
    if debug == True:
        print('cycles = ', cycles)

    cycle_capacity = float(get32(array2, offset)) / 1000.0
    offset += 4
    if debug == True:
        print("cycle_capacity=" + "{:.3f}".format(cycle_capacity) + " Ah")

    SOH = array2[offset]
    offset += 1
    if debug == True:
        print('SOH = ', SOH)
    
    precharging_binary_sensor = check_bit(array2[offset],0)
    if debug == True:
        print('precharging_binary_sensor=', precharging_binary_sensor);
    offset += 1
    
    user_alarm = get16(array2, offset)
    offset += 2
    if debug == True:
        print('user_alarm=', user_alarm);

    total_runtime_in_seconds = get32(array2, offset)
    offset += 4
    if debug == True:
        days, hours, minutes, seconds = convert_seconds(total_runtime_in_seconds)
        print(f'total_runtime: {days} days, {hours} hours, {minutes} minutes, and {seconds} seconds')
        
    charging_mosfet_enabled = check_bit(array2[offset],0)
    discharging_mosfet_enabled = check_bit(array2[offset+1],0)
    offset += 2
    if debug == True:
        print('charging_mosfet_enabled=', charging_mosfet_enabled)
        print('discharging_mosfet_enabled=', discharging_mosfet_enabled)

    #for i in range(1, 152):
    #    something = get16(array2, (2 * (i - 1)))
    #    print('Offset: ' + " " * (3-len(str((2*(i-1))))) + str((2*(i-1))) + ', something: ' + " " * (5-len(str(something))) + str(something) + ' - {:04x}'.format(something))
        
    offset = 254
    temps[3] = float(get16(array2, offset)) / 10.0
    offset += 2
    if debug == True:
        print('temp_3: ', temps[3])
    temps[4] = float(get16(array2, offset)) / 10.0
    offset += 2
    if debug == True:
        print('temp_4: ', temps[4])
    temps[5] = float(get16(array2, offset)) / 10.0
    offset += 2
    if debug == True:
        print('temp_5: ', temps[5])

    #offset = 266
    #detail_logs_count = get16(array2, offset)
    #print('detail_logs_count: ', detail_logs_count)

    #offset = 270
    #time_enter_sleep = get32(array2, offset)
    #print('time_enter_sleep: ', time_enter_sleep)

    offset = 296
    power_on_times = get16(array2, offset)
    if debug == True:
        print('power_on_times: ', power_on_times)
        
    # bits
    bal = unpack_from("<B", array2, 172)[0]
    charge = unpack_from("<B", array2, 198)[0]
    discharge = unpack_from("<B", array2, 199)[0]
    
    Charging_Enabled = 1 if charge != 0 else 0
    Discharge_Enabled = 1 if discharge != 0 else 0
    Balance_Enabled = 1 if bal != 0 else 0

    bd = {
        "voltage_cell01": voltages[1],
        "voltage_cell02": voltages[2],
        "voltage_cell03": voltages[3],
        "voltage_cell04": voltages[4],
        "voltage_cell05": voltages[5],
        "voltage_cell06": voltages[6],
        "voltage_cell07": voltages[7],
        "voltage_cell08": voltages[8],
        "voltage_cell09": voltages[9],
        "voltage_cell10": voltages[10],
        "voltage_cell11": voltages[11],
        "voltage_cell12": voltages[12],
        "voltage_cell13": voltages[13],
        "voltage_cell14": voltages[14],
        "voltage_cell15": voltages[15],
        "voltage_cell16": voltages[16],
        "highest_voltage": highest_voltage,
        "lowest_voltage": lowest_voltage,
        "voltage_diff": cell_delta_voltage,
        "battery_voltage": battery_voltage,
        "v_avg_cell": cell_average_voltage,
        "battery_current": current,
        "battery_power": power,
        "battery_kw": total_kw_remaining,
        "balance_current": balance_current,
        "balance_action": balance_action,
        "soh": SOH,
        "soc": SOC,
        "cycle_count": cycles,
        "cycle_capacity": cycle_capacity,
        "power_on_times": power_on_times,
        "battery_t1": temps[1],
        "battery_t2": temps[2],
        "battery_t3": temps[3],
        "battery_t4": temps[4],
        "battery_t5": temps[5],
        "power_tube_temp": temp_power_tube,
        "remain_batt_cap": battery_capacity_remaining,
        "remain_charge_time": remain_charge_time,
        "remain_discharge_time": remain_discharge_time,
        "alarm32": alarm32,
        "Wire_resistance": Wire_resistance,
        "MOS_OTP": MOS_OTP,
        "Cell_quantity": Cell_quantity,
        "Current_sensor_error": Current_sensor_error,
        "Cell_OVP": Cell_OVP,
        "Battery_OVP": Battery_OVP,
        "Charge_OCP": Charge_OCP,
        "Charge_SCP": Charge_SCP,
        "Charge_OTP": Charge_OTP,
        "Charge_UTP": Charge_UTP,
        "CPU_Aux_comm_error": CPU_Aux_comm_error,
        "Cell_UVP": Cell_UVP,
        "Batt_UVP": Batt_UVP,
        "Discharge_OCP": Discharge_OCP,
        "Discharge_SCP": Discharge_SCP,
        "Charge_MOS": Charge_MOS,
        "Discharge_MOS": Discharge_MOS,
        "GPS_Disconneted": GPS_Disconneted,
        "Modify_PWD_in_time": Modify_PWD_in_time,
        "Discharge_On_Failed": Discharge_On_Failed,
        "Battery_Over_Temp_Alarm": Battery_Over_Temp_Alarm,
        "Temperature_sensor_anomaly":Temperature_sensor_anomaly,
        "PLCModule_anomaly": PLCModule_anomaly,
        "Charging_Status": Charging_Status,
        "Discharge_Status": Discharge_Status,
        "Balance_Status": Balance_Status
    }
    return bd

def sendJKBMS(bms_serial, pack_id, data):
    timestamp = int(time.time())
    payload = '';
    
    #voltages
    payload += f'jk,pack={pack_id},cell=1,type=voltage value={data["voltage_cell01"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=2,type=voltage value={data["voltage_cell02"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=3,type=voltage value={data["voltage_cell03"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=4,type=voltage value={data["voltage_cell04"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=5,type=voltage value={data["voltage_cell05"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=6,type=voltage value={data["voltage_cell06"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=7,type=voltage value={data["voltage_cell07"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=8,type=voltage value={data["voltage_cell08"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=9,type=voltage value={data["voltage_cell09"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=10,type=voltage value={data["voltage_cell10"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=11,type=voltage value={data["voltage_cell11"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=12,type=voltage value={data["voltage_cell12"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=13,type=voltage value={data["voltage_cell13"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=14,type=voltage value={data["voltage_cell14"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=15,type=voltage value={data["voltage_cell15"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},cell=16,type=voltage value={data["voltage_cell16"]} {timestamp}\n'

    #min/max/diff
    payload += f'jk,pack={pack_id},type=lowest_voltage value={data["lowest_voltage"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=highest_voltage value={data["highest_voltage"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=voltage_diff value={data["voltage_diff"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=v_avg_cell value={data["v_avg_cell"]} {timestamp}\n'
 
    #temps
    payload += f'jk,pack={pack_id},temp=1,type=temperate value={data["battery_t1"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},temp=2,type=temperate value={data["battery_t2"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},temp=3,type=temperate value={data["battery_t3"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},temp=4,type=temperate value={data["battery_t4"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},temp=5,type=temperate value={data["battery_t5"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},temp=powertube,type=temperate value={data["power_tube_temp"]} {timestamp}\n'

    #others
    payload += f'jk,pack={pack_id},type=battery_voltage value={data["battery_voltage"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=battery_current value={data["battery_current"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=battery_power value={data["battery_power"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=battery_kw value={data["battery_kw"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=balance_current value={data["balance_current"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=balance_action value={data["balance_action"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=soh value={data["soh"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=soc value={data["soc"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=cycle_count value={data["cycle_count"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=power_on_times value={data["power_on_times"]} {timestamp}\n'
    
    payload += f'jk,pack={pack_id},type=remain_batt_cap value={data["remain_batt_cap"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=remain_charge_time value={data["remain_charge_time"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=remain_discharge_time value={data["remain_discharge_time"]} {timestamp}\n'
    
    payload += f'jk,pack={pack_id},type=alarm32 value={data["alarm32"]} {timestamp}\n'
    
    
    #alarms
    payload += f'jk,pack={pack_id},type=alarm,id=Wire_resistance value={data["Wire_resistance"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=MOS_OTP value={data["MOS_OTP"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Cell_quantity value={data["Cell_quantity"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Current_sensor_error value={data["Current_sensor_error"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Cell_OVP value={data["Cell_OVP"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Battery_OVP value={data["Battery_OVP"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Charge_OCP value={data["Charge_OCP"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Charge_SCP value={data["Charge_SCP"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Charge_OTP value={data["Charge_OTP"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Charge_UTP value={data["Charge_UTP"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=CPU_Aux_comm_error value={data["CPU_Aux_comm_error"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Cell_UVP value={data["Cell_UVP"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Batt_UVP value={data["Batt_UVP"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Discharge_OCP value={data["Discharge_OCP"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Discharge_SCP value={data["Discharge_SCP"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Charge_MOS value={data["Charge_MOS"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Discharge_MOS value={data["Discharge_MOS"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=GPS_Disconneted value={data["GPS_Disconneted"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Modify_PWD_in_time value={data["Modify_PWD_in_time"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Discharge_On_Failed value={data["Discharge_On_Failed"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Battery_Over_Temp_Alarm value={data["Battery_Over_Temp_Alarm"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Temperature_sensor_anomaly value={data["Temperature_sensor_anomaly"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=PLCModule_anomaly value={data["PLCModule_anomaly"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Charging_Status value={data["Charging_Status"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Discharge_Status value={data["Discharge_Status"]} {timestamp}\n'
    payload += f'jk,pack={pack_id},type=alarm,id=Balance_Status value={data["Balance_Status"]} {timestamp}\n'

    #print(payload)

    response = requests.request("POST", influx_url, headers=influx_headers, data=payload)
    if response.status_code >= 400:
        print("response: Code: " + str(response.status_code) + ", Text: " + response.text)

try:
    bms_serial = serial.Serial('/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_B001J8TE-if00-port0')
    bms_serial.baudrate = 115200 #19200
    bms_serial.bytesize = 8
    bms_serial.parity = serial.PARITY_NONE
    bms_serial.stopbits = 1
    bms_serial.exclusive = True
    bms_serial.timeout  = 0.3
except:
    print("BMS not found.")
    exit(1)

mqtt = MQTTHelper()
mqtt.on_message = handle_mqtt_message
mqtt.on_connect = handle_mqtt_connect
mqtt.broker_ip = broker_ip
mqtt.broker_port = broker_port
mqtt.broker_username = broker_username
mqtt.broker_password = broker_password
mqtt.client_id = 'jk_bms'

handler = SIGINT_handler()
signal.signal(signal.SIGINT, handler.signal_handler)

pack_id = 2

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
            data = readJKBMS(bms_serial, pack_id)
            if data == None:
                print('Read bms failed')
                exit(1)
            sendJKBMS(bms_serial, pack_id, data)
            publish_value(json.dumps(data))
            if debug == True:
                print('Done testing ;)')
                exit(1)


