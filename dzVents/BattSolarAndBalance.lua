return {
	on = {
		timer = {
			'every minute'
		},
	    devices = {
			'Battery Mode',
			'Elektra Meter'
		}		
	},
	logging = {
		level = domoticz.LOG_INFO,
		marker = 'batt_solar_and_balance',
	},
	data =
    {
        GridPowerHistory = { history = true, maxMinutes = 5 },
    },
	execute = function(dz, dev)
	    if (dev.name == 'Elektra Meter') then
	        power = dz.devices('Elektra Meter').usage - dz.devices('Elektra Meter').usageDelivered
	        dz.data.GridPowerHistory.add(power)
	    elseif ( (dev.isTimer) or (dev.name == 'Battery Mode') ) then
    		local batt_mode = dz.devices('Battery Mode')
    		if (batt_mode.state == 'Solar Charge') or (batt_mode.state == 'Grid Balance') then
        		local car_charging = dz.devices('Laadpaal Charging').active
                if (car_charging == true) then
                	do return end
                end

        		local batt_soc = dz.devices('Battery SOC').percentage
        	    local batt_sp = dz.devices('ESS Setpoint')
        	    local batt_sp_value = batt_sp.setPoint
                local min_soc_level = dz.variables('batt_min_soc_level').value
                local max_soc_level = dz.variables('batt_max_soc_level').value
        	    local idle_rate = dz.variables('batt_idle_rate').value
    
            	local new_setpoint = batt_sp_value
            	
            	local bIsSolarChargeMode = (batt_mode.state == 'Solar Charge')
                if (bIsSolarChargeMode) and (batt_soc >= max_soc_level) then
                	dz.log('we aleady have reached max soc')
                	do return end
                end
    
        		local charge_rate = dz.variables('batt_charge_rate').value
        		local discharge_rate = dz.variables('batt_discharge_rate').value
    
        		local current_usage = dz.devices('Grid L3 Watt').actualWatt
    			local max_grid_usage = dz.variables('batt_max_grid_usage').value
    
        		if (current_usage > max_grid_usage) or (current_usage < -max_grid_usage) then
            		dz.log('>>> Grid Usage to High! (' .. current_usage .. ' Watt), switching to IDLE rate')
            		new_setpoint = idle_rate
        		else
            	    grid_power = dz.data.GridPowerHistory.avg()

            	    --new_setpoint = batt_sp_value - (grid_power/2) --not sure if still need to do this as we are already averaging!
            	    new_setpoint = math.floor(batt_sp_value - grid_power + 0.5)
            	    
            	    if (bIsSolarChargeMode) then
                        if (new_setpoint < idle_rate) then
                            new_setpoint = idle_rate
            	        end
            	    else
                        if (new_setpoint < discharge_rate) then
                            new_setpoint = discharge_rate
                        end
            	    end
                    if (new_setpoint > charge_rate) then
                        new_setpoint = charge_rate
                    end
    
                    if ((new_setpoint < 0) and (batt_soc <=min_soc_level)) or ((new_setpoint > 0) and (batt_soc >= max_soc_level)) then
                        --Also handled in batt_control script
                         new_setpoint = idle_rate
                    end
                end
    
            	if (new_setpoint ~= batt_sp_value) then
                    diff_sp = math.abs(new_setpoint - batt_sp_value)
                    if (diff_sp > 50) or ( new_setpoint == idle_rate) then
                	    dz.log('grid value: ' .. grid_power)
                    	dz.log('old_setpoint: ' .. batt_sp_value)
                    	dz.log('new_setpoint: ' .. new_setpoint)
                        batt_sp.cancelQueuedCommands()
            		    batt_sp.updateSetPoint(new_setpoint)
            		end
            	end
        	end
        end
	end
}
