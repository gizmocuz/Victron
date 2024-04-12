disabled at the moment
--
-- set the ESS setpoint according to the energy needs of the house
-- when battery is in Balance mode
-- and more than 250W difference
--
return {
	active = true,
	logging = { level = domoticz.LOG_NORMAL, marker = "BATTBALANCE" },
	on = {
		devices = { 'Battery Mode', 'Elektra Meter' },
		--timer = { 'Every minute' } 
	},
	execute = function(dz, dev)

		local bms = dz.devices('Battery Mode').state
		local car_charging = dz.devices('Laadpaal Charging').active


		if ((bms == 'Balance') and (car_charging == false)) then
			power=dz.devices('Elektra Meter').usage - dz.devices('Elektra Meter').usageDelivered
			if (math.abs(power) > 250) then 
				-- check if we need to adjust power
				--print('Power is '..power)
				local bm = dz.devices('Battery Mode')
				local ess_sp = dz.devices('ESS Setpoint')
				local sp = dz.devices('ESS Setpoint').setPoint
				local bat_sp = dz.devices('ESS Setpoint')
				local batt_soc = dz.devices('Battery SOC').percentage

				if power > 0 then
					new_sp = -power
					print('ESS Setpoint needs adjusting, power: '..power..' from: '..sp..' to '..new_sp)
					ess_sp.updateSetPoint(new_sp)
					if (batt_soc <= 10) then -- stop compensating if we are approaching the last 10% SOC
						bm.switchSelector('Idle')
					end
				else
					new_sp = -power
					print('ESS Setpoint needs adjusting, power: '..power..' from: '..sp..' to '..new_sp)
					ess_sp.updateSetPoint(new_sp)
				end
			end
		end
	end
}
