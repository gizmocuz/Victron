return {
	active = true,
	logging = { level = domoticz.LOG_NORMAL, marker = "batt_plan_txt" },
	on = {
		devices = {
		    'BattTest' },
		timer = {
		    'at 00:02',
		    'at 14:02'
        } 
	},
	execute = function(dz, item)
        local today = dz.utils.fromJSON(dz.variables('charge_scheme_today').value)
        local tomorrow = dz.utils.fromJSON(dz.variables('charge_scheme_tomorrow').value)

        local d_today = os.date('%Y-%m-%d')
        local d_tomorrow = os.date('%Y-%m-%d', os.time()+24*60*60)

        if (today["status"] ~= true) then
            dz.log('Invalid Today Scheme! (status)')
            do return end
        end
        if (d_today ~= today["datum"]) then
             dz.log('Invalid Today Scheme! (datum)')
             do return end
        end

        local today_str = ""
        local tomorrow_str = ""

        local last_state = "idle"
        
        for th, v in pairs(today["data"]) do
            if (v.hour_type ~= last_state) then
                if (v.hour_type ~= "idle") then
                    if (today_str ~= "") then
                        today_str = today_str .. "\n"
                    end
                    today_str = today_str .. string.format("TD: %02d:00 %s", v.iHour, v.hour_type)
                else
                    today_str = today_str .. string.format(" -> %02d:00 (%.2f%%)", v.iHour, v.battery_capacity_percentage)
                end
                last_state = v.hour_type
            end
        end
        
        last_state = "idle"
        if (tomorrow["status"] == true) then
            if (d_tomorrow == tomorrow["datum"]) then
                for th, v in pairs(tomorrow["data"]) do
                    if (v.hour_type ~= last_state) then
                        if (v.hour_type ~= "idle") then
                            if (today_str ~= "") then
                                today_str = today_str .. "\n"
                            end
                            today_str = today_str .. string.format("TM: %02d:00 %s", v.iHour, v.hour_type)
                        else
                            today_str = today_str .. string.format(" -> %02d:00 (%.2f%%)", v.iHour, v.battery_capacity_percentage)
                        end
                        last_state = v.hour_type
                    end
                end
            end
        end

        local final_str = today_str;
        if (tomorrow_str ~= "") then
            final_str = final_str .. "\n"
            final_str = final_str .. tomorrow_str
        end

		dz.devices('Battery Plan').updateText(final_str)
        
	end
}

