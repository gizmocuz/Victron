-- Version: 2.1 (2026-03-22)
--
-- cutover day data for batt schedule just before midnight so the new day can check again
-- 
return {
    on = { timer = { 'at 23:58', }, },
    logging = {
        -- level = domoticz.LOG_INFO,
        marker = 'batt_schedule_cutover',
    },
    execute = function(dz, item)
        -- save tomorrow's scheme in today's variable
    	dz.variables('charge_scheme_today').set(dz.variables('charge_scheme_tomorrow').value)
    	-- Clear tomorrow's scheme so it will be re-fetched for the new day
	    local edata = {
            status = false
        }
    	dz.variables('charge_scheme_tomorrow').set(dz.utils.toJSON(edata))
    end
}

