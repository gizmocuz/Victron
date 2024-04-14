return {
	on = {
		timer = {
			'every minute'
		},
	    devices = {
			'Battery Mode'
		}		
	},
	logging = {
		level = domoticz.LOG_INFO,
		marker = 'batt_solar_charge',
	},
	execute = function(dz, timer)
		local batt_mode = dz.devices('Battery Mode')
		local car_charging = dz.devices('Laadpaal Charging').active

        if (batt_mode.state == 'Solar Charge') and (car_charging == false) then
    
    		local batt_soc = dz.devices('Battery SOC').percentage
            local max_soc_level = dz.variables('max_soc_level').value
    
            if (batt_soc < max_soc_level) then
        	    local batt_sp = dz.devices('ESS Setpoint')
        	    local batt_sp_value = batt_sp.setPoint
        	    local idle_rate = dz.variables('IdleRate').value
        		local charge_rate = dz.variables('ChargeRate').value

            	local new_setpoint = batt_sp_value

                local current_usage = dz.devices('Grid L3 Watt').actualWatt
                
        		if (current_usage > 5000) then
            		print('>>> Grid Usage to High! (' .. current_usage .. ' Watt), switching to IDLE value')
            		new_setpoint = idle_rate
        		else
            	    grid_power = dz.devices('Elektra Meter').usage - dz.devices('Elektra Meter').usageDelivered
                	print('grid value: ' ..grid_power)
                	if (grid_power > 0) then
                	    grid_power = 0
                	end
    
            	    new_setpoint = batt_sp_value - (grid_power/2)
        
                    --we always make sure to have atleast the idle rate value
                    if (new_setpoint < idle_rate) then
                        new_setpoint = idle_rate
                    elseif (new_setpoint > charge_rate) then
                        new_setpoint = charge_rate
                    end
                end
            	
                if ((new_setpoint < 0) and (batt_soc >=max_soc_level)) or ((new_setpoint > 0) and (batt_soc <= min_soc_level)) then
                    --Also handled in batt_control script
                     new_setpoint = idle_rate
                end
            	
            	if (new_setpoint ~= batt_sp_value) then
                    diff_sp = math.abs(new_setpoint - batt_sp_value)
                    if (diff_sp > 50) or ( new_setpoint == idle_rate) then
                    	print('old_setpoint: ' ..batt_sp_value)
                    	print('new_setpoint: ' ..new_setpoint)
                        batt_sp.cancelQueuedCommands()
            		    batt_sp.updateSetPoint(new_setpoint)
            		end
        		end
            else
                --we are ready
                if (batt_sp_value ~= idle_rate.value) then
                    batt_sp.cancelQueuedCommands()
                    batt_sp.updateSetPoint(idle_rate.value)
                end
    	    end
    	end
	end
}
