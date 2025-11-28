return {
	active = true,
	logging = {
	    --level = domoticz.LOG_INFO,
	    marker = "batt_plan_txt"
    },
	on = {
		devices = {
            'BattTest'
        },
        variables = {
            'charge_scheme_today',
            'charge_scheme_tomorrow'
        },
		timer = {
		    'at 00:02',
		    'at 01:02',
		    'at 14:02',
		    'at 15:02'
        } 
	},
	execute = function(dz, item)
        local today = dz.utils.fromJSON(dz.variables('charge_scheme_today').value)
        local tomorrow = dz.utils.fromJSON(dz.variables('charge_scheme_tomorrow').value)

        local d_today = os.date('%Y-%m-%d')
        local d_tomorrow = os.date('%Y-%m-%d', os.time()+24*60*60)

        local today_str = ""
        local tomorrow_str = ""

        -- Local Functions go here =============
        local function makePlan(data, dStr)
            local day_str = ""
            local last_state = ""
            for th, v in pairs(data) do
                if (v.hour_type ~= last_state) then
                    local hhmm = string.match(v.datum, "%d%d:%d%d")
                    if (last_state ~= "") then
                        -- Finish current line
                        day_str = day_str .. string.format(" -> %s (%.2f%%)", hhmm, v.battery_capacity_percentage) .. "\n"
                    end
                    if (v.hour_type ~= "idle") then
                        day_str = day_str .. dStr .. string.format(": %s %s", hhmm, v.hour_type)
                        last_state = v.hour_type
                    else
                        last_state = "";
                    end
                end
            end
            if (day_str == "") then
                if (dStr == "TD") then
                    day_str = '<font color="purple">Today no charge day...</font>'
                else
                    day_str = '<font color="purple">Tomorrow no charge day...</font>'
                end
            end
            return day_str
        end

        if (today["status"] == true) then
            if (d_today == today["datum"]) then
                today_str = makePlan(today["data"], "TD")
            else
                today_str = string.format('<font color="red">Today has wrong data !?</font>, %s, %s', d_today, today["datum"])
                --today_str = '<font color="red">Today has wrong data !?</font>' .. d_today .. ', ' .. today["datum"]
            end
        else
            today_str = '<font color="red">No Today data !?</font>'
        end

        if (tomorrow["status"] == true) then
            if (d_tomorrow == tomorrow["datum"]) then
                tomorrow_str = makePlan(tomorrow["data"], "TM")
            else
                tomorrow_str = '<font color="red">Tomorrow has wrong data !?</font>'
            end
        else
            -- Only alert when time is later than 3 PM (15:00)
            local hour = tonumber(os.date("%H"))
            if hour >= 15 then
                tomorrow_str = '<font color="red">No Tomorrow data !?</font>'
            end
        end

        local final_str = today_str;
        if (tomorrow_str ~= "") then
            if (final_str ~= "") then
                final_str = final_str .. "\n"
            end
            final_str = final_str .. tomorrow_str
        end

		dz.devices('Battery Plan').updateText(final_str)
	end
}
