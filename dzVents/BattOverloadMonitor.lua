--
-- adjust the ESS Setpoint when charging/dischargen when the phase power is too high
-- should be atleast 1 minute OK before we return to our previous value

return {
	logging = { level = domoticz.LOG_NORMAL, marker = "batt_power_monitor" },
	on = {
		timer = { 'every minute' },
		devices = { 'Battery Mode', 'Battery SOC', 'Grid L3 Watt' },
	},
	data = {
	    adjusted = { initial = 0 },
	    org_setpoint_value = { initial = 0 },
	    adjusted_time =  { initial = 0 }
	},

	execute = function(dz, dev)
		local max_usage = dz.variables('batt_max_grid_usage').value
        local current_usage = dz.devices('Grid L3 Watt').actualWatt

	    local batt_sp = dz.devices('ESS Setpoint')
	    local batt_sp_value = batt_sp.setPoint

		local batt_mode = dz.devices('Battery Mode')
		local batt_state = dz.devices('Battery State')
		
	    local idle_rate = dz.variables('batt_idle_rate').value

		if (dev.isDevice) and (dev.name == 'Battery Mode') then
			-- we changed the battery mode, so reset the adjusted flag
			dz.data.adjusted = 0
			dz.log('Power control: New battery mode, resetting any adjustments')
		else
            local have_overload = false    
            if (batt_state.state == 'Charging') then
			    if (current_usage > max_usage) then 
			        have_overload = true
			    end
            elseif (batt_state.state == 'Discharging') then
			    if (current_usage < -max_usage) then 
			        have_overload = true
			    end
            end
	        
	        if (have_overload == true) then
				if (dz.data.adjusted == 0) then
    				dz.data.adjusted = 1
    				dz.data.org_setpoint_value = batt_sp_value;
				    dz.log('Stopping discharging to not overload the grid: Current Usage: ' .. current_usage)
				end
				dz.data.adjusted_time = os.time()
				if (batt_sp_value ~= idle_rate) then
                    batt_sp.cancelQueuedCommands()
    		        batt_sp.updateSetPoint(idle_rate)
    		    end
    		elseif (dz.data.adjusted == 1) then
                local current_time = os.time()
                local timediff = current_time - dz.data.adjusted_time
                if (timediff > 1*60) then --we should be atleast be okey for 1 minute
    				dz.log('Restoring Battery Setpoint caused by previous overload...')
                    batt_sp.cancelQueuedCommands()
        		    batt_sp.updateSetPoint(dz.data.org_setpoint_value)
        		    dz.data.adjusted = 0
            	end
	        end
        end		    
	end
}