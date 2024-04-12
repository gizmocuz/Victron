disabled at the moment
--
-- adjust the ESS setpoint for Charge/Discharge modes, if the grid power is too high/low
-- recalculate every minute to achieve max grid usage
-- assumes a 3 phase setup to prevent single phase overload
--
return {
	active = true,
	logging = { level = domoticz.LOG_NORMAL, marker = "POWCONTROL" },
	on = {
		timer = { 'every minute' },
		devices = { 'Battery Mode', 'Battery SOC' },
	},
	data = {
	    adjusted = { initial = 0 }
	},

	execute = function(dz, dev)
        local min_soc_level = 20 --maybe use two variables for them
        local max_soc_level = 90
        
        local tot_inverters = 1 -- set to 3 when using 3 inverters
        local max_grid_usage = 5500

		local grid_usage = dz.devices('Actual Usage (L1 + L2 + L3)').actualWatt
		local grid_delivery = dz.devices('Actual Delivery (L1 + L2 + L3)').actualWatt
		local charge_rate = dz.variables('ChargeRate').value
		local discharge_rate = dz.variables('DischargeRate').value

		local ess_sp = dz.devices('ESS Setpoint')
		local state = dz.devices('Battery Mode').state

		if (dev.isDevice) then
			if (dev.name == 'Battery Mode' and (dev.state == 'Charge' or dev.state == 'Discharge')) then
				-- we just started a (dis)charge cycle so reset the adjusted flag
				dz.data.adjusted = 0
				print('Power control: set adjusted to 0 as per Batt Mode')
			else -- SOC
				if (dev.name == 'Battery SOC' and dev.percentage > max_soc_level and state == 'Charge' and dz.data.adjusted ~= 0) then
					-- we are at the end of a charge cycle so power will be managed externally. Let's not interfere
					dz.data.adjusted = 0
					print('Power control: set adjusted to 0 as we reached ' .. max_soc_level .. '% SOC')
				end
			end
		elseif (state == 'Charge') then
			if (grid_usage > max_grid_usage) then 
				-- charging but power too high, let's reduce our setpoint
				dz.data.adjusted = 1
				pow_diff=grid_usage-max_grid_usage
				print('Reducing charge power to not overload the grid: '..grid_usage..' so '..pow_diff*tot_inverters)
				sp = ess_sp.setPoint - pow_diff*tot_inverters
				--sp = ess_sp.setPoint - 1000
				if (sp < 0) then
					-- dz.data.adjusted = 0
					sp = 300
				end
				ess_sp.updateSetPoint(sp)
			else -- check if we can increase power
				if (grid_usage < 4900 and dz.data.adjusted == 1 and ess_sp.setPoint < charge_rate) then
					pow_diff=5200-grid_usage
					sp = math.min(ess_sp.setPoint + pow_diff*tot_inverters,charge_rate)
					print('Increase adjusted charge power to maximise the grid: ' .. grid_usage ..' to '..sp)
					ess_sp.updateSetPoint(sp)
				else
					print('Grid load within acceptable parameters ' .. grid_usage)
				end
			end
		elseif (state == 'Discharge') then
			if (grid_delivery > max_grid_usage) then 
				-- discharging but power too high, let's reduce our setpoint
				dz.data.adjusted = 1
				pow_diff=grid_delivery-max_grid_usage
				print('Reducing discharge power to not overload the grid: '.. grid_delivery ..'  so '..pow_diff*tot_inverters)
				sp = ess_sp.setPoint + pow_diff*tot_inverters
				if (sp > 0) then
					dz.data.adjusted = 0
					sp = 60
				end
				ess_sp.updateSetPoint(sp)
			else -- check if we can increase return power
				if (grid_delivery < 4900 and dz.data.adjusted == 1 and ess_sp.setPoint > discharge_rate) then
					pow_diff=5200-grid_delivery
					sp = math.max(ess_sp.setPoint - pow_diff*tot_inverters,discharge_rate)
					print('Adjust discharge power to maximise the grid: ' .. grid_delivery ..' to '..sp)
					-- sp = ess_sp.setPoint - 500
					ess_sp.updateSetPoint(sp)
				else
					print('Grid discharge within acceptable parameters ' .. grid_delivery)
				end
			end
		end
	end
}
