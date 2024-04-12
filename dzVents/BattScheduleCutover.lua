--
-- cutover day data for batt schedule just before midnight so the new day can check again
-- 
return {
    on = { timer = { 'at 23:58', }, },
    logging = { level = domoticz.LOG_NORMAL, marker = 'BATTCUTOVER', },
    execute = function(dz, item)

-- save tomorrow's schedule in today's variable
	dz.variables('ChargeToday').set(dz.variables('ChargeTomorrow').value)
	dz.variables('DischargeToday').set(dz.variables('DischargeTomorrow').value)
	dz.variables('today_soc_target').set(dz.variables('tomorrow_soc_target').value)
	dz.variables('today_charge_kwh').set(dz.variables('tomorrow_charge_kwh').value)
	dz.variables('today_discharge_kwh').set(dz.variables('tomorrow_discharge_kwh').value)
-- set tomorrow's variables to a value that does not trigger (hour middle)
	dz.variables('ChargeTomorrow').set('00.30')
	dz.variables('DischargeTomorrow').set('00:30')
    end
}

