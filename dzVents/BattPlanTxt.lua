--
-- put the charge and discharge times in a text variable
--
return {
	active = true,
	on = { variables = { 'ChargeToday', 'DischargeToday', 'ChargeTomorrow', 'DischargeTomorrow' } },

	execute = function(dz, dev)
		local cn = dz.variables('ChargeToday').value
		local dn = dz.variables('DischargeToday').value
		local ct = dz.variables('ChargeTomorrow').value
		local dt = dz.variables('DischargeTomorrow').value
		dz.devices('Battery Plan').updateText('Charge TD: '..cn..'\nDischarge TD: '..dn..'\nCharge TM: '..ct..'\nDischarge TM: '..dt)
	end
}

