-- Version: 2.1 (2026-03-22)
local idx_grid_meter = 1768
return {
	on = {
		timer = {
			'every minute'
			--'30 seconds'
		},
	    devices = {
			'Battery Mode',
			'Elektra Meter'
		}		
	},
	logging = {
		-- level = domoticz.LOG_INFO,
		marker = 'batt_solar_and_balance',
	},
	data =
    {
        GridPowerHistory = { history = true, maxMinutes = 1 },
	    first_counterToday = { initial = 0 },
	    first_counterDeliveredToday = { initial = 0 },
	    bHaveFirstValue = { initial = 0 },
	    last_max_adjusted = { initial = 0 },
	    last_setpoint = { initial = 0 },
    },
	execute = function(dz, dev)
	    local counterToday = dz.devices(idx_grid_meter).usage1 + dz.devices(idx_grid_meter).usage2
	    local counterDeliveredToday = dz.devices(idx_grid_meter).return1 + dz.devices(idx_grid_meter).return2
		local batt_soc = dz.devices('Battery SOC').percentage
        local max_soc_level = dz.variables('batt_max_soc_level').value
	    if (dev.name == 'Elektra Meter') then
            if (dz.data.bHaveFirstValue == 0) then
                dz.log('---------------------------------------', dz.LOG_INFO)
                dz.log('First Meter Value!', dz.LOG_INFO)
                dz.data.bHaveFirstValue = 1
                dz.data.first_counterToday = counterToday
                dz.data.first_counterDeliveredToday = counterDeliveredToday
                dz.log('counterToday = ' .. counterToday, dz.LOG_INFO)
                dz.log('counterDeliveredToday = ' .. counterDeliveredToday, dz.LOG_INFO)
            end
        elseif ( (dev.isTimer) or (dev.name == 'Battery Mode') ) then
    		local batt_mode = dz.devices('Battery Mode').state
	        if (dev.name == 'Battery Mode') and (batt_mode == 'Grid Balance') then
	           dz.globalData.shouldGridBalance = false
	           dz.log('Grid Balance mode active (flag cleared, mode drives balance directly)', dz.LOG_INFO)
            end
        	local bIsSolarChargeMode = (batt_mode == 'Solar Charge')
            if (bIsSolarChargeMode) and (batt_soc >= max_soc_level) then
            	dz.log('We aleady have reached max soc')
            	do return end
            end
    		local car_charging = dz.devices('Laadpaal Charging').active
            if (car_charging == true) then
            	do return end
            end
    	    local batt_sp = dz.devices('ESS Setpoint')
    	    local batt_sp_value = batt_sp.setPoint
            local min_soc_level = dz.variables('batt_min_soc_level').value
    	    local idle_rate = dz.variables('batt_idle_rate').value
    	    local batt_efficiency = dz.variables('batt_efficiency').value
    	    local solar_produced_watt = math.abs(dz.devices('Solar Produced').actualWatt)
    	    --dz.log('solar_produced_watt = ' .. solar_produced_watt .. ' Watt', dz.LOG_INFO)
            if (dz.data.bHaveFirstValue ~= 0) then
        	    local last_counterToday = dz.devices(idx_grid_meter).usage1 + dz.devices(idx_grid_meter).usage2
        	    local last_counterDeliveredToday = dz.devices(idx_grid_meter).return1 + dz.devices(idx_grid_meter).return2
        	    local used = last_counterToday - dz.data.first_counterToday
        	    local deliv = last_counterDeliveredToday - dz.data.first_counterDeliveredToday
        	    local usage = used - deliv
                local grid_power = usage * 60
    		    local bDoBalance =  (batt_mode == 'Solar Charge') or (batt_mode == 'Grid Balance') or (dz.globalData.shouldGridBalance == true)
    		    --local bIsIQModeEnabled = (batt_mode == 'IQ Smart Mode') or (batt_mode == 'IQ Smart Mode + Balance')
    		    if (bDoBalance == true) then
                    dz.log('---------------------------------------', dz.LOG_INFO)
                    dz.log('used today = ' .. used .. ' Watt', dz.LOG_INFO)
                    dz.log('deliv today = ' .. deliv .. ' Watt', dz.LOG_INFO)
                    dz.log('usage = ' .. usage .. ' Watt', dz.LOG_INFO)
                    dz.log('grid_power = ' .. grid_power .. ' Watt', dz.LOG_INFO)
    		    end
        		if (bDoBalance == true) then
                	local new_setpoint = batt_sp_value
                	if (dz.data.last_setpoint ~= -1) then
                	    -- work with the uncompensated setpoint
                	    new_setpoint = dz.data.last_setpoint
                	end
        			local max_grid_usage = dz.variables('batt_max_grid_usage').value
            		local current_usage_L1 = dz.devices('Grid L1 Watt').actualWatt
            		local current_usage_L2 = dz.devices('Grid L2 Watt').actualWatt
            		local current_usage_L3 = dz.devices('Grid L3 Watt').actualWatt
            		if (current_usage_L1 > max_grid_usage) or (current_usage_L1 < -max_grid_usage) or
            		   (current_usage_L2 > max_grid_usage) or (current_usage_L2 < -max_grid_usage) or
            		   (current_usage_L3 > max_grid_usage) or (current_usage_L3 < -max_grid_usage) then
                		dz.log('>>> Grid Usage too high! (L1/L2/L3: ' .. current_usage_L1 .. '/' .. current_usage_L2 .. '/' .. current_usage_L3 .. ' Watt), switching to IDLE rate')
                		new_setpoint = idle_rate
            		else
            		    new_setpoint = math.floor(new_setpoint - grid_power + 0.5)
            		    --local eff_grid_power = grid_power
            		    --if (batt_mode == 'Grid Balance') or (batt_mode == 'IQ Smart Mode + Balance') then
            		        --only compensate in Grid Balance mode
            		        --eff_grid_power = grid_power / (batt_efficiency / 100)
                            --dz.log('eff_grid_power = ' .. eff_grid_power .. ' Watt', dz.LOG_INFO)
            		    --end
                	    --new_setpoint = math.floor(new_setpoint - eff_grid_power + 0.5)
                	    if (bIsSolarChargeMode) then
                            if (new_setpoint < idle_rate) then
                                new_setpoint = idle_rate
                	        end
                	    else
                    		local discharge_rate = dz.variables('batt_discharge_rate').value
                    		--if (bIsIQModeEnabled == true) then
                    		--    -- when in IQ Mode, but grid balancing, never discharge more then our current solar producing wattage
                    		--    discharge_rate = solar_produced_watt
                    		--end
                            if (new_setpoint < discharge_rate) then
                                new_setpoint = discharge_rate
                                if (batt_sp_value <= discharge_rate) then
                                    local current_time = os.time()
                                    if (dz.data.last_max_adjusted ~= 0) then
                                        local timediff = current_time - dz.data.last_max_adjusted
                                        --dz.log("timediff: " .. timediff)
                                        if (timediff >= 900) then
                                            -- it could be we are stuck on the bottom... lift us up
                                            -- otherwise we have a very high load for half an 15 minutes!
                                            new_setpoint = math.floor(0 - grid_power + 0.5)
                                            dz.data.last_max_adjusted = 0
                                        end
                                    else
                                        dz.data.last_max_adjusted = os.time()
                                    end
                                end
                            end
                	    end
                		local charge_rate = dz.variables('batt_max_charge_rate').value -- batt_charge_rate').value
                        if (new_setpoint > charge_rate) then
                            new_setpoint = charge_rate
                        end
                        if ((new_setpoint < 0) and (batt_soc <= min_soc_level)) or ((new_setpoint > 0) and (batt_soc > max_soc_level)) then
                            --Also handled in batt_control script
                             new_setpoint = idle_rate
                        end
                        dz.log('old_setpoint = ' .. batt_sp_value .. ' Watt', dz.LOG_INFO)
                        dz.log('new_setpoint = ' .. new_setpoint .. ' Watt', dz.LOG_INFO)
                	end
                	if (new_setpoint ~= batt_sp_value) then
                        diff_sp = math.abs(new_setpoint - batt_sp_value)
                        if (diff_sp > 50) or ( new_setpoint == idle_rate) then
                        	dz.log('old_setpoint: ' .. batt_sp_value)
                        	dz.log('new_setpoint: ' .. new_setpoint)
                        	-- compensate final setpoint with charge efficiency
                        	local inverter_efficiency = dz.helpers.get_inverter_efficiency(dz, new_setpoint)
                        	--dz.log('inverter_efficiency = ' .. inverter_efficiency .. ' %', dz.LOG_INFO)
                        	--local eff_setpoint = math.floor(new_setpoint + ((1 - (inverter_efficiency / 100)) * new_setpoint) + 0.5)
                        	-- dz.log('batt_efficiency = ' .. batt_efficiency .. ' %', dz.LOG_INFO)
                            local eff_setpoint = math.floor(new_setpoint + ((1 - (batt_efficiency / 100)) * new_setpoint) + 0.5)
                            dz.log('eff_setpoint = ' .. eff_setpoint .. ' Watt', dz.LOG_INFO)
                            batt_sp.cancelQueuedCommands()
                		    batt_sp.updateSetPoint(eff_setpoint)
                		end
                	end
                	-- store uncompensated new setpoint
                	dz.data.last_setpoint = new_setpoint
                end
                dz.data.bHaveFirstValue = 1
                dz.data.first_counterToday = last_counterToday
                dz.data.first_counterDeliveredToday = last_counterDeliveredToday
                if (bDoBalance == true) then
                    dz.log('counterToday = ' .. counterToday, dz.LOG_INFO)
                    dz.log('counterDeliveredToday = ' .. counterDeliveredToday, dz.LOG_INFO)
                end
            end
        end
	end
}

