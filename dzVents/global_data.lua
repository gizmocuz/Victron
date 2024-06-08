-- this scripts holds all the globally persistent variables and helper functions
-- see the documentation in the wiki
-- NOTE:
-- THERE CAN BE ONLY ONE global_data SCRIPT in your Domoticz install.

return {
	-- global persistent data
	data = {
        shouldGridBalance = { initial = false }
	},

	-- global helper functions (and it needs to be called 'helpers' and nothing else)
	helpers = {
		return_plus_123 = function(domoticz, orgvalue)
			return orgvalue + 123
		end,
		something_else = function(domoticz)
			return 1
		end
	}
}
