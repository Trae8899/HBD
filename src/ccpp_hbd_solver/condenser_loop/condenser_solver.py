"""Condenser and feedwater loop closure."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from ..utils.unit_helpers import kpa_to_bar

CP_WATER_KJ_PER_KG_K = 4.186
LATENT_CONDENSATION_KJ_PER_KG = 2250.0


def solve_condenser_loop(context: Mapping[str, Any]) -> Tuple[dict[str, Any], dict[str, Any]]:
    """Close the condenser heat balance and return loop conditions."""
    st_block = context.get("steam_turbine", {})
    gt_block = context.get("gt_block", {})
    condenser_spec = context.get("condenser", {})

    lp_section = st_block.get("lp_section", {})
    lp_flow = float(lp_section.get("flow_kg_s", 0.0))
    lp_inlet_temp = float(lp_section.get("inlet_T_C", 0.0))

    cw_inlet = float(condenser_spec.get("cw_inlet_C", 20.0))
    condenser_pressure_bar = kpa_to_bar(float(condenser_spec.get("vacuum_kPa_abs", 8.0)))

    condensing_temp = max(25.0, 100.0 + 40.0 * (condenser_pressure_bar - 0.1))
    sensible_drop = max(lp_inlet_temp - condensing_temp, 0.0)

    gt_power = float(gt_block.get("electric_power_MW", 0.0))
    st_power = float(st_block.get("electric_power_MW", 0.0))
    fuel_heat_input = float(gt_block.get("fuel_heat_input_MW_LHV", 0.0))

    thermal_balance_mw = max(fuel_heat_input - (gt_power + st_power), 0.0)

    latent_component_kj_per_s = lp_flow * LATENT_CONDENSATION_KJ_PER_KG
    sensible_component_kj_per_s = lp_flow * CP_WATER_KJ_PER_KG_K * sensible_drop
    baseline_heat_kj_per_s = latent_component_kj_per_s + sensible_component_kj_per_s
    baseline_heat_mw = baseline_heat_kj_per_s / 1000.0

    heat_rejected_mw = max(thermal_balance_mw, baseline_heat_mw)
    heat_rejected_kj_per_s = heat_rejected_mw * 1000.0

    cw_mass_flow = max(lp_flow * 60.0, 1.0)
    cw_delta_temp = heat_rejected_kj_per_s / (cw_mass_flow * CP_WATER_KJ_PER_KG_K)
    cw_outlet = cw_inlet + cw_delta_temp

    result = {
        "cw_inlet_C": cw_inlet,
        "cw_outlet_C": cw_outlet,
        "heat_rejected_MW": heat_rejected_mw,
        "condensing_temp_C": condensing_temp,
        "lp_flow_kg_s": lp_flow,
    }

    trace = {
        "lp_flow_kg_s": lp_flow,
        "lp_inlet_temp_C": lp_inlet_temp,
        "condensing_temp_C": condensing_temp,
        "latent_heat_kJ_per_kg": LATENT_CONDENSATION_KJ_PER_KG,
        "sensible_drop_C": sensible_drop,
        "fuel_heat_input_MW": fuel_heat_input,
        "electric_power_MW": gt_power + st_power,
        "cw_mass_flow_kg_s": cw_mass_flow,
        "cw_delta_T_C": cw_delta_temp,
        "heat_rejected_MW": heat_rejected_mw,
    }

    return result, trace
