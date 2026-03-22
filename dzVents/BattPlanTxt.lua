-- Version: 2.1 (2026-03-22)
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
        local now = os.time()
        local d_today = os.date('%Y-%m-%d', now)
        local d_tomorrow = os.date('%Y-%m-%d', now + 24*60*60)
        local today_str = ""
        local tomorrow_str = ""
        -- Local Functions go here =============
        local function makePlan(data, dStr)
            local day_str = ""
            local last_state = ""
            local prev_v = nil
            for th, v in ipairs(data) do
                if (v.hour_type ~= last_state) then
                    local hhmm = string.match(v.datum, "%d%d:%d%d")
                    if (last_state ~= "") then
                        -- Finish current line using the last item of the finished block
                        day_str = day_str .. string.format(" -> %s (%.2f%%)", hhmm, prev_v.battery_capacity_percentage) .. "\n"
                    end
                    if (v.hour_type ~= "idle") then
                        day_str = day_str .. dStr .. string.format(": %s %s", hhmm, v.hour_type)
                        last_state = v.hour_type
                    else
                        last_state = "";
                    end
                end
                prev_v = v
            end
            -- Close the final block if one is still open
            if (last_state ~= "") and (prev_v ~= nil) then
                local hhmm = string.match(prev_v.datum, "%d%d:%d%d")
                day_str = day_str .. string.format(" -> %s (%.2f%%)", hhmm, prev_v.battery_capacity_percentage)
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
            local hour = tonumber(os.date("%H", now))
            if hour >= 15 then
                tomorrow_str = '<font color="red">No Tomorrow data !?</font>'
            else
                tomorrow_str = '<font color="purple">Tomorrow not known yet...</font>'
            end
        end
        local final_str = today_str;
        if (tomorrow_str ~= "") then
            if (final_str ~= "") then
                final_str = final_str
            end
            final_str = final_str .. tomorrow_str
        end
		dz.devices('Battery Plan').updateText(final_str)
	end
}

