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
	    had_charge_block_today = { initial = false },
	    last_hour_type = { initial = "" },
    },
	execute = function(dz, dev)
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

        local IQMode = "Unknown?!"

        hour_type = tHour.hour_type

        --dz.log(tHour.hour_price)

        local bBalanceAllDay = (batt_mode.state == 'IQ Smart Mode + Balance')
        local new_setpoint = idle_rate
        
        local set_charge_rate = charge_rate
        
        if (bBalanceAllDay) and (hour_type == "charge") then
            set_charge_rate = charge_rate -- - (tHour.forecast / 2)
            if (set_charge_rate < 50) then
                -- we have enough solar, let's continue balancing
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
            dz.data.had_charge_block_today = true
            if (dz.data.last_hour_type ~= "charge") then
                dz.log("Starting 'Charge' block")
            end
            IQMode = "Charge"
        elseif (hour_type == "discharge") then
            new_setpoint = discharge_rate
            dz.data.had_charge_block_today = false
            if (dz.data.last_hour_type ~= "discharge") then
                dz.log("Starting 'Discharge' block")
            end
            IQMode = "Discharge"
        elseif (hour_type == "idle") then

    	    local bAllowGridBalance = dz.variables('batt_allow_balance').value ~= 0
            local batt_solar_min = dz.variables('batt_solar_min').value --minimum solar value to enable balancing
            local bCouldBalance = (batt_solar_min ~= 0) and (tHour.forecast > batt_solar_min)
    
            local bDoBalance = bBalanceAllDay
            -- and (dz.data.had_charge_block_today == true)  (WINTER MODE!?)
            --if (bAllowGridBalance == true) and (bCouldBalance == true) and (batt_soc < max_soc_level) then
            --    -- there is so much sun that we could grid balance
            --    bDoBalance = true
            --end
            
            if (bDoBalance == true) then
                if (dz.globalData.shouldGridBalance == false) then
                    dz.globalData.shouldGridBalance = true --this will cause our BattSolarAndBalance script to balance
                    new_setpoint = idle_rate
                else
                    new_setpoint = batt_sp_value
                end
                dz.log("Starting 'Balance' block (solar forecast = " .. tHour.forecast .. ")")
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
        do return end
        
        if (new_setpoint ~= batt_sp_value) then
            dz.log("Setting setpoint to " .. new_setpoint .. "(" .. hour_type .. ")")
            batt_sp.cancelQueuedCommands()
		    batt_sp.updateSetPoint(new_setpoint)
        end
	end
}
