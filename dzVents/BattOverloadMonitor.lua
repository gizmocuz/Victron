--
-- adjust the ESS Setpoint when dischargen when the phase power is too high
-- recalculate every minute to achieve max phase usage
--
return {
	active = true,
	logging = { level = domoticz.LOG_NORMAL, marker = "batt_power_monitor" },
	on = {
		timer = { 'every minute' },
		devices = { 'Battery Mode', 'Battery SOC' },
	},
	data = {
	    adjusted = { initial = 0 },
	    org_setpoint_value = { initial = 0 }
	},

	execute = function(dz, dev)

		local max_usage = dz.variables('batt_max_grid_usage').value
        local current_usage = dz.devices('Grid L3 Watt').actualWatt

	    local batt_sp = dz.devices('ESS Setpoint')
	    local batt_sp_value = batt_sp.setPoint

		local batt_mode = dz.devices('Battery Mode')
		local batt_state = dz.devices('Battery State')
		
	    local idle_rate = dz.variables('batt_idle_rate').value

		if (dev.isDevice) then
			if (dev.name == 'Battery Mode') then
				-- we changed the battery mode, so reset the adjusted flag
				dz.data.adjusted = 0
				print('Power control: New battery mode, resetting any adjustments')
			end
	    elseif (batt_state.state == 'Discharging') then
			if (current_usage > max_usage) and (dz.data.adjusted == 0) then 
				-- charging but power too high, let's reduce our setpoint
				print('Stopping discharging to not overload the grid: Current Usage: ' .. current_usage)
				dz.data.adjusted = 1
				dz.data.org_setpoint_value = batt_sp_value;
                batt_sp.cancelQueuedCommands()
    		    batt_sp.updateSetPoint(idle_rate)
			elseif (dz.data.adjusted == 1) then
		        --we adjusted our setpoint previously, let's see if we can restore it again
			    if (current_usage + math.abs(dz.data.org_setpoint_value) < max_usage - 600) then
    				print('Restoring Battery Setpoint caused by previous overload...')
                    batt_sp.cancelQueuedCommands()
        		    batt_sp.updateSetPoint(dz.data.org_setpoint_value)
        		    dz.data.adjusted = 0
        		else
        		    --still not good!
        		    print('Grid Overload! Current Usage: ' .. current_usage)
        		end
			end
	    elseif (batt_state.state == 'Charging') then
			if (current_usage < -max_usage) and (dz.data.adjusted == 0) then 
				-- charging but power too high, let's reduce our setpoint
				print('Stopping discharging to not underload the grid: Current Usage: ' .. current_usage)
				dz.data.adjusted = 1
				dz.data.org_setpoint_value = batt_sp_value;
                batt_sp.cancelQueuedCommands()
    		    batt_sp.updateSetPoint(idle_rate)
			elseif (dz.data.adjusted == 1) then
		        --we adjusted our setpoint previously, let's see if we can restore it again
			    if (current_usage - math.abs(dz.data.org_setpoint_value) > -max_usage + 600) then
    				print('Restoring Battery Setpoint caused by previous overload...')
                    batt_sp.cancelQueuedCommands()
        		    batt_sp.updateSetPoint(dz.data.org_setpoint_value)
        		    dz.data.adjusted = 0
        		else
        		    --still not good!
        		    print('Grid Underload! Current Usage: ' .. current_usage)
        		end
			end
		end
	end
}