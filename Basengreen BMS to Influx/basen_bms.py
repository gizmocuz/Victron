#!/usr/bin/python3

"""
@Author: PA1DVB
@Date: 20 December 2023
@Version: 1.03

needed libraries
pip3 install requests pyserial

"""

import json
import time
import requests
import serial

sleepTime = 10

influx_host = "http://192.168.0.90:8086"
influx_token = "oU9XLverylongbase64token=="
influx_bucket = "domoticz_home"
influx_org = "Domoticz"

influx_url = f'{influx_host}/api/v2/write?org={influx_org}&bucket={influx_bucket}&precision=s'
influx_headers = {
  'Authorization': f'Token {influx_token}',
  'Content-type': 'text/plain'
}

debug = False

try:
    bms = serial.Serial('/dev/ttyUSB0')
    bms.baudrate = 9600 #19200
    bms.bytesize = 8
    bms.parity = serial.PARITY_NONE
    bms.stopbits = 1
    bms.exclusive = True
    bms.timeout  = 0.3
    #You could add more BMS devices here and poll them below (bms = serial.Serial('/dev/ttyUSB1')
    #Best to use /dev/serial/by-id devices instead of /dev/ttyUSBx as the might not be consistant after reboot
except:
    print("BMS not found.")
    exit(1)

def check(buf, len):
    b = 0
    num = 0
    for b2 in range(len):
        b ^= buf[b2]
        num += buf[b2]
    return (b ^ num) & 255

def readBMS(bms, pack_id):
    voltages=[0]*17
    temps=[0]*7
    
    highest_voltage = 0
    lowest_voltage = 100

    array = bytearray(6)
    array[0] = 126
    array[1] = pack_id #//addr 
    array[2] = 1 #analogue info
    array[3] = 0
    array[4] = check(array, 4)
    array[5] = 13
    bms.write(array)
    time.sleep(0.350)
    bytesToRead = bms.in_waiting
    if bytesToRead == 0:
        print("Nothing received from BMS!")
        return
    array2 = bytearray(bms.read(bytesToRead))
    if (array[2] != array2[2]):
        print("Invalid data received!")
        return
    if (array2[bytesToRead - 1] != 13):
        print("Invalid data received!")
        return
    if (array2[bytesToRead - 2] != check(array2, bytesToRead - 2)):
        print("Invalid data received! (CRC error)")
        return
    #print("Recieved: " + bytes(array2).hex())
    
    #decode
    tot_cells = array2[5] #16
    if debug == True:
        print("tot_cells: " + str(tot_cells))
    
    for i in range(1, tot_cells + 1):
        voltage = (float(array2[2 * (i - 1) + 7]) + (int(array2[2 * (i - 1) + 6]) & 31) * 256) / 1000.0
        voltages[i] = voltage
        
        if voltage > highest_voltage:
            highest_voltage = voltage
        elif voltage < lowest_voltage:
            lowest_voltage = voltage
        
        if debug == True:
            print("cell_" + str(i) + "=" + "{:.3f}".format(voltage) + " V")
        if (array2[2 * (i - 1) + 6] & 128) == 128:
            if debug == True:
                print("No data for this cell? Yellow")
        #self.data_cell[i] = voltage

    voltage_diff = highest_voltage - lowest_voltage

    num5 = int(array2[19 + 2 * tot_cells])
    if num5 != 5 and num5 != 6:
        num5 = 5
    temp_count = num5;
    if debug == True:
        print("temp_count: " + str(temp_count))
    
    num6 = (int(array2[17 + 2 * tot_cells]) + int(array2[16 + 2 * tot_cells]) * 256) / 100.0
    
    cell_ah = num6
    if debug == True:
        print("cell_ah=" + "{:.3f}".format(cell_ah) + " Ah")

    num7 = (int(array2[13 + 2 * tot_cells]) + int(array2[12 + 2 * tot_cells]) * 256) / 100.0
    num6 = num6 * num7 / 100.0
    
    remain_batt_cap = num6
    if debug == True:
        print("remain_batt_cap=" + "{:.3f}".format(remain_batt_cap) + " Ah")
    
    num8 = (30000 - ((int)(array2[9 + 2 * tot_cells]) + (int)(array2[8 + 2 * tot_cells]) * 256)) / 100.0
    
    bIsTPBD16S48V300 = False
    
    #if "TP-BD16S48V300" in this.textBox3.Text:
    if bIsTPBD16S48V300 == True:
        num8 = (50000 - ((int)(array2[89 + 2 * tot_cells + 2 * num5]) + (int)(array2[88 + 2 * tot_cells + 2 * num5]) * 256 + (int)(array2[87 + 2 * tot_cells + 2 * num5]) * 256 * 256 + (int)(array2[86 + 2 * tot_cells + 2 * num5]) * 256 * 256 * 256)) / 100.0
    num7 = ((int)(array2[17 + 2 * tot_cells]) + (int)(array2[16 + 2 * tot_cells]) * 256) / 100.0
    num7 -= num6

    if num8 > 0.0:
        num8 = num7 / num8

    remain_charge_time = num8
    if debug == True:
        print("remain_charge_time=" + "{:.3f}".format(remain_charge_time) + " h")

    num7 = (float)(int(array2[13 + 2 * tot_cells]) + int(array2[12 + 2 * tot_cells]) * 256) / 100.0
    num7 = (float)(int(array2[17 + 2 * tot_cells]) + int(array2[16 + 2 * tot_cells]) * 256) / 100.0 * num7 / 100.0
    num8 = (float)(30000 - (int(array2[9 + 2 * tot_cells]) + int(array2[8 + 2 * tot_cells]) * 256)) / 100.0

    if bIsTPBD16S48V300 == True:
        num8 = (double)(50000 - (int(array2[89 + 2 * tot_cells + 2 * num5]) + int(array2[88 + 2 * tot_cells + 2 * num5]) * 256 + int(array2[87 + 2 * tot_cells + 2 * num5]) * 256 * 256 + int(array2[86 + 2 * tot_cells + 2 * num5]) * 256 * 256 * 256 * 256))
        num8 /= 100.0;
    if (num8 == 0.0):
        num8 = 0.0
    else:
        num8 = num7 / num8
    
    remain_discharge_time = 0
    if (num8 == 0.0 or num8 > 0.0):
        remain_discharge_time = 0
    elif (num8 < 0.0):
        num8 = -1.0 * num8
        remain_discharge_time = num8
    if debug == True:
        print("remain_discharge_time=" + "{:.3f}".format(remain_discharge_time) + " h")
   
    #temperatures
    for i in range(1, temp_count + 1):
        temperature = (array2[21 + 2 * tot_cells + (i - 1) * 2] - 50)
        temps[i] = temperature
        if debug == True:
            print("Temp_" + str(i) + "=" + str(temperature))
   
    num8 = (float)(30000 - (int(array2[9 + 2 * tot_cells]) + int(array2[8 + 2 * tot_cells]) * 256)) / 100.0
    if bIsTPBD16S48V300 == True:
        num8 = (float)(50000 - (int(array2[89 + 2 * tot_cells + 2 * num5]) + int(array2[88 + 2 * tot_cells + 2 * num5]) * 256 + int(array2[87 + 2 * tot_cells + 2 * num5]) * 256 * 256 + int(array2[86 + 2 * tot_cells + 2 * num5]) * 256 * 256 * 256 * 256))
        num8 /= 100.0

    current = num8
    if debug == True:
        print("current=" + "{:.2f}".format(current) + " A")
    
    num8 = (float)(int(array2[43 + 2 * tot_cells + 2 * num5]) + int(array2[42 + 2 * tot_cells + 2 * num5]) * 256) / 100.0
    SOH = num8 #state of health
    
    if debug == True:
        print("SOH=" + "{:.2f}".format(SOH) + " %")

    num8 = (float)(int(array2[13 + 2 * tot_cells]) + int(array2[12 + 2 * tot_cells]) * 256) / 100.0
    if (num8 > 100.0):
        num8 = 100.0;
    SOC = num8
    
    if debug == True:
        print("SOC=" + "{:.2f}".format(SOC) + " %")

    num10 = int(array2[35 + 2 * tot_cells + 2 * num5]) + int(array2[34 + 2 * tot_cells + 2 * num5]) * 256
    cycles = num10
    if debug == True:
        print("cycles=" + str(cycles))

    num11 = (float)(int(array2[39 + 2 * tot_cells + 2 * num5]) + int(array2[38 + 2 * tot_cells + 2 * num5]) * 256) / 100.0
    battery_voltage = num11
    if debug == True:
        print("battery_voltage=" + "{:.2f}".format(battery_voltage) + " V")
    num12 = num11 / float(tot_cells)
    v_avg_cell = num12
    if debug == True:
        print("v_avg_cell=" + "{:.2f}".format(v_avg_cell) + " V")

    flogbuff=[0]*12

    #statussus
    for i in range(80, 90):
        flogbuff[i - 80] = array2[22 + 2 * tot_cells + 2 * num5 + i - 80];
    flogbuff[11] = array2[46 + 2 * tot_cells + 2 * num5];
    flogbuff[10] = array2[47 + 2 * tot_cells + 2 * num5];

    Cell_VOL_Low_Fault = (flogbuff[0] & 8) != 0
    VOL_Line_Break = (flogbuff[0] & 16) != 0
    Charge_MOS_Fault = (flogbuff[0] & 32) != 0
    DISC_MOS_Fault = (flogbuff[0] & 64) != 0
    VOL_Sensor_Fault = (flogbuff[0] & 128) != 0
    NTC_Disconnection = (flogbuff[1] & 1) != 0
    ADC_MOD_Fault = (flogbuff[1] & 2) != 0
    Reverse_Battery = (flogbuff[1] & 4) != 0
    Hot_Failure = (flogbuff[1] & 8) != 0
    Battery_Locked = (flogbuff[1] & 16) != 0
    DISC_OV_TEMP_Protection = (flogbuff[2] & 1) != 0
    DISC_UN_TEMP_Protection = (flogbuff[2] & 2) != 0
    Startup_Failed = (flogbuff[2] & 8) != 0
    b536_COM_Timeout = (flogbuff[2] & 64) != 0
    Charging_Status = (flogbuff[3] & 1) != 0
    Discharge_Status = (flogbuff[3] & 2) != 0
    Short_Circuit_Protection = (flogbuff[3] & 4) != 0
    OV_CUR_Protection = (flogbuff[3] & 8) != 0
    CHG_OV_TEMP_Protection = (flogbuff[3] & 64) != 0
    CHG_UN_TEMP_Protection = (flogbuff[3] & 128) != 0
    Ambient_Low_TEMP_Protection = (flogbuff[4] & 1) != 0
    ENV_High_TEMP_Protection = (flogbuff[4] & 2) != 0
    Manual_CHG_MOS_Open = (flogbuff[5] & 1) != 0
    Manual_CHG_MOS_Off = (flogbuff[5] & 2) != 0
    Manual_DISC_MOS_Open = (flogbuff[5] & 4) != 0
    Manual_DISC_MOS_Off = (flogbuff[5] & 8) != 0
    Heating_pad = (flogbuff[5] & 16) != 0
    MOSFET_OV_TEMP_Protection = (flogbuff[5] & 32) != 0
    MOSFET_LO_TEMP_Protection = (flogbuff[5] & 64) != 0
    CHG_Open_TEMP_Too_Low = (flogbuff[5] & 128) != 0
    SOC_Low_Alarm2 = (flogbuff[7] & 1) != 0
    Vibration_Alarm = (flogbuff[7] & 2) != 0
    Gap_power_make_up_waite = (flogbuff[7] & 4) != 0
    Fire_fighting_Alarm = (flogbuff[7] & 8) != 0
    NTC_short_circuit = (flogbuff[7] & 32) != 0
    AMB_Over_TEMP_Alarm = (flogbuff[8] & 1) != 0
    AMB_Low_TEMP_Alarm = (flogbuff[8] & 2) != 0
    MOS_Over_TEMP_Alarm = (flogbuff[8] & 4) != 0
    SOC_Low_Alarm = (flogbuff[8] & 8) != 0
    Vol_DIF_Alarm = (flogbuff[8] & 16) != 0
    BAT_DISC_Over_TEMP_Alarm = (flogbuff[8] & 32) != 0
    BAT_DISC_Low_TEMP_Alarm = (flogbuff[8] & 64) != 0
    Cell_Over_VOL_Alarm = (flogbuff[9] & 1) != 0
    Cell_Low_VOL_Alarm = (flogbuff[9] & 2) != 0
    Pack_Over_VOL_Alarm = (flogbuff[9] & 4) != 0
    Pack_Low_VOL_Alarm = (flogbuff[9] & 8) != 0
    CHG_Over_CUR_Alarm = (flogbuff[9] & 16) != 0
    DISC_Over_CURR_Alarm = (flogbuff[9] & 32) != 0
    BAT_CHG_Over_TEMP_Alarm = (flogbuff[9] & 64) != 0
    BAT_CHG_Low_TEMP_Alarm = (flogbuff[9] & 128) != 0 
    Cell_Over_Prot = (flogbuff[10] & 1) != 0
    Pack_Over_Prot = (flogbuff[10] & 2) != 0
    Cell_Under_Prot = (flogbuff[10] & 4) != 0
    Pack_Under_Prot = (flogbuff[10] & 8) != 0
    Full_Cha_Prot = (flogbuff[11] & 32) != 0

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
        "voltage_diff": voltage_diff,
        "cell_ah": cell_ah,
        "battery_voltage": battery_voltage,
        "v_avg_cell": v_avg_cell,
        "battery_current": current,
        "battery_power": round(current * battery_voltage, 3),
        "soh": SOH,
        "soc": SOC,
        "cycle_count": cycles,
        "battery_t1": temps[1],
        "battery_t2": temps[2],
        "battery_t3": temps[3],
        "battery_t4": temps[4],
        "battery_t5": temps[5],
        "battery_t6": temps[6],
        "remain_batt_cap": remain_batt_cap,
        "remain_charge_time": remain_charge_time,
        "remain_discharge_time": remain_discharge_time,
        "Cell_VOL_Low_Fault": Cell_VOL_Low_Fault,
        "VOL_Line_Break": VOL_Line_Break,
        "Charge_MOS_Fault": Charge_MOS_Fault,
        "DISC_MOS_Fault": DISC_MOS_Fault,
        "VOL_Sensor_Fault": VOL_Sensor_Fault,
        "NTC_Disconnection": NTC_Disconnection,
        "ADC_MOD_Fault": ADC_MOD_Fault,
        "Reverse_Battery": Reverse_Battery,
        "Hot_Failure": Hot_Failure,
        "Battery_Locked": Battery_Locked,
        "DISC_OV_TEMP_Protection": DISC_OV_TEMP_Protection,
        "DISC_UN_TEMP_Protection": DISC_UN_TEMP_Protection,
        "Startup_Failed": Startup_Failed,
        "b536_COM_Timeout": b536_COM_Timeout,
        "Charging_Status": Charging_Status,
        "Discharge_Status": Discharge_Status,
        "Short_Circuit_Protection": Short_Circuit_Protection,
        "OV_CUR_Protection": OV_CUR_Protection,
        "CHG_OV_TEMP_Protection": CHG_OV_TEMP_Protection,
        "CHG_UN_TEMP_Protection": CHG_UN_TEMP_Protection,
        "Ambient_Low_TEMP_Protection": Ambient_Low_TEMP_Protection,
        "ENV_High_TEMP_Protection": ENV_High_TEMP_Protection,
        "Manual_CHG_MOS_Off": Manual_CHG_MOS_Off,
        "Manual_DISC_MOS_Open": Manual_DISC_MOS_Open,
        "Manual_DISC_MOS_Off": Manual_DISC_MOS_Off,
        "Heating_pad": Heating_pad,
        "MOSFET_OV_TEMP_Protection": MOSFET_OV_TEMP_Protection,
        "MOSFET_LO_TEMP_Protection": MOSFET_LO_TEMP_Protection,
        "CHG_Open_TEMP_Too_Low": CHG_Open_TEMP_Too_Low,
        "SOC_Low_Alarm2": SOC_Low_Alarm2,
        "Vibration_Alarm": Vibration_Alarm,
        "Gap_power_make_up_waite": Gap_power_make_up_waite,
        "Fire_fighting_Alarm": Fire_fighting_Alarm,
        "NTC_short_circuit": NTC_short_circuit,
        "AMB_Over_TEMP_Alarm": AMB_Over_TEMP_Alarm,
        "AMB_Low_TEMP_Alarm": AMB_Low_TEMP_Alarm,
        "MOS_Over_TEMP_Alarm": MOS_Over_TEMP_Alarm,
        "SOC_Low_Alarm": SOC_Low_Alarm,
        "Vol_DIF_Alarm": Vol_DIF_Alarm,
        "BAT_DISC_Over_TEMP_Alarm": BAT_DISC_Over_TEMP_Alarm,
        "BAT_DISC_Low_TEMP_Alarm": BAT_DISC_Low_TEMP_Alarm,
        "Cell_Over_VOL_Alarm": Cell_Over_VOL_Alarm,
        "Cell_Low_VOL_Alarm": Cell_Low_VOL_Alarm,
        "Pack_Over_VOL_Alarm": Pack_Over_VOL_Alarm,
        "Pack_Low_VOL_Alarm": Pack_Low_VOL_Alarm,
        "CHG_Over_CUR_Alarm": CHG_Over_CUR_Alarm,
        "DISC_Over_CURR_Alarm": DISC_Over_CURR_Alarm,
        "BAT_CHG_Over_TEMP_Alarm": BAT_CHG_Over_TEMP_Alarm,
        "BAT_CHG_Low_TEMP_Alarm": BAT_CHG_Low_TEMP_Alarm,
        "Cell_Over_Prot": Cell_Over_Prot,
        "Pack_Over_Prot": Pack_Over_Prot,
        "Cell_Under_Prot": Cell_Under_Prot,
        "Pack_Under_Prot": Pack_Under_Prot,
        "Full_Cha_Prot": Full_Cha_Prot
    }
    return bd

def sendBMS(bms, pack_id):
    timestamp = int(time.time())
    payload = '';
    
    #voltages
    payload += f'basengreen,pack={pack_id},cell=1,type=voltage value={data["voltage_cell01"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=2,type=voltage value={data["voltage_cell02"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=3,type=voltage value={data["voltage_cell03"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=4,type=voltage value={data["voltage_cell04"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=5,type=voltage value={data["voltage_cell05"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=6,type=voltage value={data["voltage_cell06"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=7,type=voltage value={data["voltage_cell07"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=8,type=voltage value={data["voltage_cell08"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=9,type=voltage value={data["voltage_cell09"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=10,type=voltage value={data["voltage_cell10"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=11,type=voltage value={data["voltage_cell11"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=12,type=voltage value={data["voltage_cell12"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=13,type=voltage value={data["voltage_cell13"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=14,type=voltage value={data["voltage_cell14"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=15,type=voltage value={data["voltage_cell15"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},cell=16,type=voltage value={data["voltage_cell16"]} {timestamp}\n'

    #min/max/diff
    payload += f'basengreen,pack={pack_id},type=lowest_voltage value={data["lowest_voltage"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},type=highest_voltage value={data["highest_voltage"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},type=voltage_diff value={data["voltage_diff"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},type=v_avg_cell value={data["v_avg_cell"]} {timestamp}\n'
 
    #temps
    payload += f'basengreen,pack={pack_id},temp=1,type=temperate value={data["battery_t1"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},temp=2,type=temperate value={data["battery_t2"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},temp=3,type=temperate value={data["battery_t3"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},temp=4,type=temperate value={data["battery_t4"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},temp=5,type=temperate value={data["battery_t5"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},temp=6,type=temperate value={data["battery_t6"]} {timestamp}\n'

    #others
    payload += f'basengreen,pack={pack_id},type=battery_voltage value={data["battery_voltage"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},type=battery_current value={data["battery_current"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},type=battery_power value={data["battery_power"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},type=soh value={data["soh"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},type=soc value={data["soc"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},type=cycle_count value={data["cycle_count"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},type=remain_batt_cap value={data["remain_batt_cap"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},type=remain_charge_time value={data["remain_charge_time"]} {timestamp}\n'
    payload += f'basengreen,pack={pack_id},type=remain_discharge_time value={data["remain_discharge_time"]} {timestamp}'
    
    #print(payload)

    response = requests.request("POST", influx_url, headers=influx_headers, data=payload)
    if response.status_code >= 400:
        print("response: " + response.text)

while True:
    pack_id = 1
    data = readBMS(bms, pack_id)
    if data == None:
        print('Read bms failed')
        exit(1)
    sendBMS(bms, pack_id)

    time.sleep(sleepTime)
