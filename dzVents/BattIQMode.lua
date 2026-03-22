-- Version: 2.1 (2026-03-22)
return {
	logging = {
	    -- level = domoticz.LOG_INFO,
	    marker = "batt_iq_mode"
    },
	on = {
		devices = {
		    'Battery Mode',
		    'BattTest'
		},
		timer = { 'every 15 minutes' } 
	},
	data =
    {
	    last_hour_type = { initial = "" },
    },
	execute = function(dz, dev)
--	    dz.log('script called!')
		local car_charging = dz.devices('Laadpaal Charging').active
        if (car_charging == true) then
            -- maybe we want to provide some juice from our battery here?
            do return end
        end

        local batt_mode = dz.devices('Battery Mode')

        if (batt_mode.state ~= 'IQ Smart Mode') and (batt_mode.state ~= 'IQ Smart Mode + Balance') then
            do return end
        end

        dz.globalData.shouldGridBalance = false

        local min_soc_level = dz.variables('batt_min_soc_level').value
        local max_soc_level = dz.variables('batt_max_soc_level').value
        local min_soc_night_level = dz.variables('batt_min_soc_night').value

        
		local idle_rate = dz.variables('batt_idle_rate').value
        local charge_rate = dz.variables('batt_charge_rate').value
        local discharge_rate = dz.variables('batt_discharge_rate').value
        
        -- When true: during IQ Smart Mode + Balance, reduce charge rate by half the solar
        -- forecast and switch to balance mode if the remaining charge rate drops below 50W.
        -- Useful in summer when solar can cover the house load during cheap-price hours.
        local use_solar_adjusted_charge = false
        
        local batt_soc = dz.devices('Battery SOC').percentage
	    local batt_sp = dz.devices('ESS Setpoint')
	    local batt_sp_value = batt_sp.setPoint

        local charge_scheme = dz.variables('charge_scheme_today').value
        
        local today = os.date('%Y-%m-%d')

        local jtable = dz.utils.fromJSON(charge_scheme)

        if (jtable["status"] ~= true) then
            dz.log('Invalid Scheme! (status)')
            do return end
        end
        
        if (today ~= jtable["datum"]) then
             dz.log('Invalid Scheme! (datum)')
             do return end
        end

        local table_length = #jtable["data"]
        if (table_length ~= 24) and (table_length ~= 96) then
             dz.log('Invalid Scheme! (number of items)')
             do return end
        end
        
        local isQuarter = (table_length == 96)

        local act_hour = tonumber(os.date('%H'))
        local act_minute = tonumber(os.date('%M'))
        if (isQuarter == true) then
            act_minute = math.floor(act_minute / 15) * 15
        else
            act_minute = 0
        end
        
        local act_time_str = string.format("%02d:%02d", act_hour, act_minute)
        dz.log('act_time_str: ' .. act_time_str)

        local tHour = nil
        local hour_type = "idle"

        local size = 0
        for th, v in pairs(jtable["data"]) do
            local hhmm = string.match(v.datum, "%d%d:%d%d")
            if (hhmm  == act_time_str) then
              tHour = v
            end
            size = size + 1
        end
        
        if (tHour == nil) then
             dz.log('Invalid Scheme! (act hour not found!?)')
             do return end
        end

        --dz.log('tHour: ' .. tostring(tHour))


        local IQMode = "Unknown?!"

        hour_type = tHour.hour_type

        --dz.log(tHour.hour_price)

        local bBalanceAllDay = (batt_mode.state == 'IQ Smart Mode + Balance')
        local new_setpoint = idle_rate
        
        local set_charge_rate = charge_rate
        
        if (bBalanceAllDay) and (hour_type == "charge") and (use_solar_adjusted_charge) then
            set_charge_rate = charge_rate - (tHour.forecast / 2)
            if (set_charge_rate < 50) then
                -- solar covers the load, balance instead of force-charging
                hour_type = "idle"
            end
        elseif (bBalanceAllDay) and (hour_type == "discharge") then
            if (batt_soc <= min_soc_night_level) then
                -- keep some reserve for the evening/night
                hour_type = "idle"
            end
        end

        if (hour_type == "charge") then
            new_setpoint = set_charge_rate --charge_rate
            if (dz.data.last_hour_type ~= "charge") then
                dz.log("Starting 'Charge' block")
            end
            IQMode = "Charge"
        elseif (hour_type == "discharge") then
            new_setpoint = discharge_rate
            if (dz.data.last_hour_type ~= "discharge") then
                dz.log("Starting 'Discharge' block")
            end
            IQMode = "Discharge"
        elseif (hour_type == "idle") then
            local bDoBalance = bBalanceAllDay

            if (bDoBalance == true) then
                dz.globalData.shouldGridBalance = true
                if (dz.data.last_hour_type ~= "idle") then
                    new_setpoint = idle_rate
                    dz.log("Starting 'Balance' block (solar forecast = " .. tHour.forecast .. ")")
                else
                    new_setpoint = batt_sp_value
                    dz.log("Continuing 'Balance' block (solar forecast = " .. tHour.forecast .. ")")
                end
                IQMode = "Balance"
            else
                new_setpoint = idle_rate
                if (dz.data.last_hour_type ~= "idle") then
                    dz.log("Starting 'Idle' block")
                end
                IQMode = "Idle"
            end
        end
        dz.data.last_hour_type = hour_type

        dz.log("action: " .. hour_type .. ", SP=" .. new_setpoint)
        --do return end
        
        dz.devices('IQ Mode').updateText(IQMode)

        if ((new_setpoint < 0) and (batt_soc <=min_soc_level)) or ((new_setpoint > 0) and (batt_soc >= max_soc_level)) then
            --nothing to do, soc min or max reached
            dz.log("nothing to do, soc min or max reached")
            do return end
        end

        if (new_setpoint ~= batt_sp_value) then
            dz.log("Setting setpoint to " .. new_setpoint .. "(" .. hour_type .. ")")
            batt_sp.cancelQueuedCommands()
		    batt_sp.updateSetPoint(new_setpoint)
        end
	end
}

