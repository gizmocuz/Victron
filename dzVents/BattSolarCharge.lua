return {
	on = {
		timer = {
			'every minute'
		},
	    --devices = {
		--	'Elektra Meter'
		--}		
	},
	logging = {
		level = domoticz.LOG_INFO,
		marker = 'batt_solar_charge',
	},
	execute = function(dz, timer)
		local batt_mode = dz.devices('Battery Mode')
		local car_charging = dz.devices('Laadpaal Charging').active
		local batt_soc = dz.devices('Battery SOC').percentage
        local max_soc_level = dz.variables('max_soc_level').value

        if (batt_mode.state == 'Solar Charge') and (car_charging == false) then
            if (batt_soc < max_soc_level) then
        	    local batt_sp = dz.devices('ESS Setpoint')
        	    local batt_sp_value = batt_sp.setPoint
        	    local idle_rate = dz.variables('IdleRate').value
                
        	    grid_power = dz.devices('Elektra Meter').usage - dz.devices('Elektra Meter').usageDelivered

            	if (grid_power > 0) then
            	    grid_power = 0
            	end
            	
            	local new_setpoint = batt_sp_value + ((-grid_power - batt_sp_value) / 2)
        
                --we always make sure to have atleast the idle rate value
                if (new_setpoint < idle_rate) then
                    new_setpoint = idle_rate
                end
            	
            	print('Grid value: ' ..grid_power)
            	print('new_setpoint: ' ..new_setpoint)
            	
            	if (new_setpoint ~= batt_sp_value) then
                    batt_sp.cancelQueuedCommands()
        		    batt_sp.updateSetPoint(new_setpoint)
        		end
            else
                --we are ready
                batt_sp.cancelQueuedCommands()
                batt_sp.updateSetPoint(idle_rate.value)
    	    end
    	end
	end
}
