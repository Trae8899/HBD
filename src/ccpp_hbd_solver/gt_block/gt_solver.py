"""Gas turbine block solver."""

from __future__ import annotations

from typing import Any, Mapping, Tuple


def solve_gt_block(inputs: Mapping[str, Any]) -> Tuple[dict[str, Any], dict[str, Any]]:
    """Derive gas turbine output, fuel heat input, and exhaust conditions."""
    gas_turbine = inputs.get("gas_turbine", {})
    corrections = inputs.get("corrections", {})

    iso_power = float(gas_turbine.get("ISO_power_MW", 0.0))
    iso_heat_rate = float(gas_turbine.get("ISO_heat_rate_kJ_per_kWh", 0.0))
    iso_exhaust_temp = float(gas_turbine.get("ISO_exhaust_temp_C", 0.0))
    iso_exhaust_flow = float(gas_turbine.get("ISO_exhaust_flow_kg_s", 0.0))
    fuel_lhv = gas_turbine.get("fuel_LHV_kJ_per_kg")
    fuel_lhv_value = float(fuel_lhv) if fuel_lhv is not None else None

    power_multiplier = float(corrections.get("power_multiplier", 1.0))
    flow_multiplier = float(corrections.get("flow_multiplier", 1.0))
    exhaust_temp_delta = float(corrections.get("exhaust_temp_delta_C", 0.0))

    electric_power = iso_power * power_multiplier
    exhaust_flow = iso_exhaust_flow * flow_multiplier
    exhaust_temp = iso_exhaust_temp + exhaust_temp_delta

    # Convert ISO heat rate (kJ/kWh) to MW thermal based on actual power output.
    fuel_heat_input_mw = (iso_heat_rate * electric_power) / 3600.0
    fuel_flow = (fuel_heat_input_mw * 1000.0 / fuel_lhv_value) if fuel_lhv_value else None

    result = {
        "fuel_heat_input_MW_LHV": fuel_heat_input_mw,
        "fuel_LHV_kJ_per_kg": fuel_lhv_value,
        "fuel_flow_kg_s": fuel_flow,
        "electric_power_MW": electric_power,
        "exhaust": {
            "temp_C": exhaust_temp,
            "flow_kg_s": exhaust_flow,
        },
        "correction_summary": {
            "power_multiplier": power_multiplier,
            "flow_multiplier": flow_multiplier,
            "temperature_offset_C": exhaust_temp_delta,
        },
    }

    trace = {
        "iso_power_MW": iso_power,
        "iso_heat_rate_kJ_per_kWh": iso_heat_rate,
        "iso_exhaust_temp_C": iso_exhaust_temp,
        "iso_exhaust_flow_kg_s": iso_exhaust_flow,
        "power_multiplier": power_multiplier,
        "flow_multiplier": flow_multiplier,
        "exhaust_temp_delta_C": exhaust_temp_delta,
        "fuel_heat_input_calculation": {
            "heat_rate_kJ_per_kWh": iso_heat_rate,
            "electric_power_MW": electric_power,
            "fuel_heat_input_MW_LHV": fuel_heat_input_mw,
            "fuel_LHV_kJ_per_kg": fuel_lhv_value,
            "fuel_flow_kg_s": fuel_flow,
        },
    }

    return result, trace
