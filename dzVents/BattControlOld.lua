--
-- script that controls the battery based on
--   set timers in ChargeToday and DischargeToday
--   SOC changes (adjust if need be)
--   ESS mode(Bulk, Absorption and float)
--   Battery Mode changes (Charge, Discharge, Idle)
--   Laadpaal Charging change
--
return {
	active = true,
	logging = { level = domoticz.LOG_NORMAL, marker = "BATTCONTROL" },
	on = {
		devices = { 'ESS Setpoint' , 'BattTest', 'Battery SOC', 'ESS Charge State', 'Battery Mode', 'Laadpaal Charging' },
		timer = { 'every hour' } 
	},
	execute = function(dz, dev)

        local min_soc_level = dz.variables('min_soc_level').value
        local max_soc_level = dz.variables('max_soc_level').value

		local batt_sp = dz.devices('ESS Setpoint')
		local batt_sp_value = batt_sp.setPoint
		local batt_mode = dz.devices('Battery Mode')

		local charge_rate = dz.variables('ChargeRate').value
		local discharge_rate = dz.variables('DischargeRate').value
		local idle_rate = dz.variables('IdleRate')
		
		local ChargeToday = dz.variables('ChargeToday').value
		local DischargeToday = dz.variables('DischargeToday').value
		local soc_target = dz.variables('today_soc_target').value
		local charge_kwh = dz.variables('today_charge_kwh').value
		local batt_kwh = dz.variables('batt_kwh').value
		local batt_soc = dz.devices('Battery SOC').percentage
		local car_charging = dz.devices('Laadpaal Charging').active
		--if dev.isDevice then
		--	print("called by "..dev.name)
		--end
		
		if (dev.isTimer or dev.name == 'BattTest') then 
		    if (batt_mode.state ~= 'Off') and (batt_mode.state ~= 'Manual') and (car_charging == false) then
    			-- check every hour if we need to charge/discharge the batt according to the schedule in the variables
    			hr = os.date('%H')
    			timestr = hr..':00'
    
    			--print('Comparing ' ..timestr.. ' with CT '..ChargeToday.. ' and DT '..DischargeToday)
    			if timestr == ChargeToday then
    				batt_mode.switchSelector('Charge')
    			elseif timestr == DischargeToday then
    				batt_mode.switchSelector('Discharge')
    			end
    		end
	    elseif dev.name == 'Battery SOC' then
            if (batt_mode.state == 'Discharge') or (batt_mode.state == 'Manual') or (batt_mode.state == 'Balance') then
			    -- when going below min_soc_level stop discharging
			    if (batt_soc <= min_soc_level) then
			        print('Battery at SOC lowest allowed percentage (' .. min_soc_level .. '%), stopping discharge')
			        batt_mode.switchSelector('Idle')
				end
            elseif (batt_mode.state == 'Charge') then
				if ((soc_target == 0) or (soc_target > max_soc_level)) then
				    soc_target = max_soc_level
				end
			    if (batt_soc > soc_target) then
        			--  when charging and reaching soc target, stop
				    print('Battery at SOC target (' .. soc_target .. '%), stopping charge')
				    batt_mode.switchSelector('Idle')
				end
            elseif ((batt_mode.state == 'Manual') or (batt_mode.state == 'Balance')) then
    			if (batt_soc > max_soc_level) then
    			    --this will prevent absorption/float mode!!
    			    
			        --print('Battery at SOC maximum allowed percentage (' .. max_soc_level .. '%), stopping charge')
                    --batt_sp.cancelQueuedCommands()
                    --batt_sp.updateSetPoint(0)
				end
			end
        elseif dev.name == 'Laadpaal Charging' then
            --is the car charging?
            if (car_charging) then
                --is yes, disable charge/discharge, so switch to idle mode
                if (batt_mode.state == 'Discharge') or (batt_mode.state == 'Charge') then
                    -- store previous batt_mode state and bat_sp
                    print('Car is charging... switching to idle mode')
		            batt_mode.switchSelector('Idle')
                else
                    if (batt_sp.state == 'Balance') or (batt_mode.state == 'Manual') then
                        if ((batt_sp_value < 0) or (batt_sp_value > idle_rate.value)) then
                            print('Car is charging... setting SP to idle_rate')
                            batt_sp.cancelQueuedCommands()
                            batt_sp.updateSetPoint(idle_rate.value)
                        end
                    end
    			end
    		else
    		        --restore previous state?
    		end
		elseif dev.name == 'ESS Charge State' and dev.text == 'Float' and batt_mode.state == 'Charge' then 
			-- Batt finished absorpsion and has entered float state so charge is done
			print("MP2 entered Float state so let's switch to idle state")
			batt_mode.switchSelector('Idle')
		elseif dev.name == 'Battery Mode' then
			-- handle Battery Mode changes: Charge, Discharge
			-- Balance has a separate script (BattBalance) and Manual needs nothing
			if (batt_mode.state == 'Charge') then 
				-- Mode Charge switched on
				if ((soc_target == 0) or (soc_target > max_soc_level)) then
				    soc_target = max_soc_level
				end
				if (batt_soc < soc_target) then
					-- start the charging because the batt_soc is lower than the soc_target, or not set yet
					print('Charge setting ESS Setpoint to: ' .. charge_rate_normal)
    				batt_sp.cancelQueuedCommands()
					batt_sp.updateSetPoint(charge_rate)
					local new_batt_kwh = ((batt_soc/100) * batt_kwh) + ((soc_target - batt_soc) / 100) * charge_kwh
					print('Recalculated batt_kwh to: '..new_batt_kwh)
					dz.variables('batt_kwh').set(tonumber(string.format("%.4f", new_batt_kwh)))
				else -- the batt_soc is already above the soc_target so nothing to do
					print('Charge command ignored. Battery threshold already reached')
					batt_mode.switchSelector('Idle')
				end
			elseif (batt_mode.state == 'Discharge') then 
				-- Mode Discharge switched on
				if (batt_soc > min_soc_level) then
					print('Discharge setting ESS Setpoint to: '..discharge_rate_normal)
    				batt_sp.cancelQueuedCommands()
					batt_sp.updateSetPoint(discharge_rate)
				else
					print('SOC already at minimum threshold (' .. min_soc_level .. '%) so ignore Discharge command')
					batt_mode.switchSelector('Idle')
				end
		    elseif (batt_mode.state == 'Idle') then
                batt_sp.cancelQueuedCommands()
                batt_sp.updateSetPoint(idle_rate.value)
			end
		end
	end
}
