--
-- cutover day data for batt schedule just before midnight so the new day can check again
-- 
return {
    on = { timer = { 'at 23:58', }, },
    logging = { level = domoticz.LOG_NORMAL, marker = 'batt_schedule_cutover', },
    execute = function(dz, item)
        -- save tomorrow's scheme in today's variable
    	dz.variables('charge_scheme_today').set(dz.variables('charge_scheme_tomorrow').value)
    	
    	-- flag tomorrow schema false
	    my_table = {}
	    local edata = {
            status = false
        }
    	dz.variables('charge_scheme_tomorrow').set(dz.utils.toJSON(edata))
    end
}

