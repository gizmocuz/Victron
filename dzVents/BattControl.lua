return {
	logging = { level = domoticz.LOG_NORMAL, marker = "batt_control" },
	on = {
		devices = {
		    'Battery Mode', 'Battery State', 'Battery SOC', 'ESS Setpoint', 'ESS Charge State', 'Laadpaal Charging' },
		--timer = { 'every hour' } 
	},
	execute = function(dz, dev)
        local min_soc_level = dz.variables('batt_min_soc_level').value
        local max_soc_level = dz.variables('batt_max_soc_level').value

		local batt_sp = dz.devices('ESS Setpoint')
		local batt_sp_value = batt_sp.setPoint
		local batt_mode = dz.devices('Battery Mode')
		local batt_state = dz.devices('Battery State')

		local idle_rate = dz.variables('batt_idle_rate').value
		local charge_rate = dz.variables('batt_charge_rate').value
		local discharge_rate = dz.variables('batt_discharge_rate').value
		
		local batt_soc = dz.devices('Battery SOC').percentage
		local car_charging = dz.devices('Laadpaal Charging').active
		--if dev.isDevice then
		--	dz.log("called by "..dev.name)
		--end
		
        if dev.name == 'Laadpaal Charging' then
            --is the car charging? If yes, switch to Idle mode
            if (car_charging) then
                --is yes, disable charge/discharge, so switch to idle mode
                if (batt_state.state ~= 'Off') or (batt_state.state ~= 'Idle') then
                    -- store previous batt_sp
                    dz.log('Car is charging... switching to Idle mode')
                    batt_sp.cancelQueuedCommands()
                    batt_sp.updateSetPoint(idle_rate)    
    			end
    		else
    		        --restore previous state?
    		end
		elseif dev.name == 'Battery Mode' then
			-- handle Battery Mode changes: Charge, Discharge
			-- Balance has a separate script (BattBalance) and Manual needs nothing
			dz.globalData.shouldGridBalance = false

			if (batt_mode.state == 'Off') then
                batt_sp.cancelQueuedCommands()
                batt_sp.updateSetPoint(0)
			elseif (batt_mode.state == 'Idle') or (batt_mode.state == 'Manual') then 
                batt_sp.cancelQueuedCommands()
		        batt_sp.updateSetPoint(idle_rate)    
		    elseif (batt_mode.state == 'IQ Smart Mode') or (batt_mode.state == 'Grid Balance') or (batt_mode.state == 'Solar Charge') then
		        --start at IDLE rate. Giz: Should this be done or handled in their scripts? (balance/iqmode)
                batt_sp.cancelQueuedCommands()
                batt_sp.updateSetPoint(idle_rate)
		    elseif (batt_mode.state == 'Charge') then
		        if (car_charging) then
	                dz.log('Car is charging! Not switching to Charge mode!')
		        else
    		        if (batt_soc < max_soc_level) then
                        dz.log('Battery Mode: Charge')
                        batt_sp.cancelQueuedCommands()
                        batt_sp.updateSetPoint(charge_rate)
                    end
                end
		    elseif (batt_mode.state == 'Disharge') then
		        if (car_charging) then
	                dz.log('Car is charging! Not switching to Discharge mode!')
		        else
    		        if (batt_soc > min_soc_level) then
                        dz.log('Battery Mode: Discharge')
                        batt_sp.cancelQueuedCommands()
                        batt_sp.updateSetPoint(discharge_rate)
                    end
                end
			end
        elseif dev.name == 'ESS Setpoint' then
            if (batt_sp_value == 0) and (batt_state.state ~= 'Off') then
                batt_state.switchSelector('Off')
	        elseif (batt_sp_value == idle_rate) and (batt_state.state ~= 'Idle') then
	            batt_state.switchSelector('Idle')
	        elseif (batt_sp_value > 0) and (batt_state.state ~= 'Charging') then
	            batt_state.switchSelector('Charging')
	        elseif (batt_sp_value < 0) and (batt_state.state ~= 'Discharging') then
	            batt_state.switchSelector('Discharging')
	        end
		elseif dev.name == 'ESS Charge State' and dev.text == 'Float' and batt_state.state == 'Charging' then 
			-- Batt finished absorpsion and has entered float state so charge is done
			dz.log("MP2 entered Float state so let's switch to idle state")
			if (batt_sp_value ~= idle_rate) then
                batt_sp.cancelQueuedCommands()
	            batt_sp.updateSetPoint(idle_rate)
	        end
        elseif dev.name == 'Battery SOC' then
            if (batt_mode.state ~= 'Idle') then
                if (batt_soc <= min_soc_level) or (batt_soc > max_soc_level) then
        			dz.log("SOC target reached, switching to idle mode")
        			if (batt_sp_value ~= idle_rate) then
                        batt_sp.cancelQueuedCommands()
    	                batt_sp.updateSetPoint(idle_rate)
    	            end
    	        end
    	    end
	   end
	end
}
