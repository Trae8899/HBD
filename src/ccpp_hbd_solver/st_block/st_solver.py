"""Steam turbine block solver."""

from __future__ import annotations

import math
from typing import Any, Mapping, Tuple

from ..utils.unit_helpers import kpa_to_bar

CP_STEAM_KJ_PER_KG_K = 2.08
MIN_DELTA_T_C = 5.0


def _approx_saturation_temp(pressure_bar: float) -> float:
    if pressure_bar <= 0:
        return 25.0
    return 100.0 + 45.0 * math.log10(max(pressure_bar, 0.05))


def _section_delta_h(steam_temp_c: float, exhaust_temp_c: float, efficiency: float) -> float:
    delta_t = max(steam_temp_c - exhaust_temp_c, MIN_DELTA_T_C)
    delta_h_iso = CP_STEAM_KJ_PER_KG_K * delta_t
    return delta_h_iso * max(min(efficiency, 1.0), 0.0)


def solve_steam_turbine(context: Mapping[str, Any]) -> Tuple[dict[str, Any], dict[str, Any]]:
    """Compute HP/IP/LP section expansion work and aggregate electric power."""
    hrsg = context.get("hrsg", {})
    steam_turbine_spec = context.get("steam_turbine", {})
    condenser_spec = context.get("condenser", {})

    eff_hp = float(steam_turbine_spec.get("isentropic_eff_hp", 0.88))
    eff_ip = float(steam_turbine_spec.get("isentropic_eff_ip", eff_hp))
    eff_lp = float(steam_turbine_spec.get("isentropic_eff_lp", eff_ip))
    mech_eff = float(steam_turbine_spec.get("mech_elec_eff", 0.985))

    hp_flow = float(hrsg.get("hp", {}).get("steam_flow_kg_s", 0.0))
    ip_flow = float(hrsg.get("ip", {}).get("steam_flow_kg_s", 0.0))
    lp_flow = float(hrsg.get("lp", {}).get("steam_flow_kg_s", 0.0))

    hp_inlet_temp = float(hrsg.get("hp", {}).get("steam_T_C", 0.0))
    ip_inlet_temp = float(hrsg.get("ip", {}).get("steam_T_C", 0.0))
    lp_inlet_temp = float(hrsg.get("lp", {}).get("steam_T_C", 0.0))

    ip_pressure = float(hrsg.get("ip", {}).get("steam_P_bar", 0.0))
    lp_pressure = float(hrsg.get("lp", {}).get("steam_P_bar", 0.0))
    condenser_pressure_bar = kpa_to_bar(float(condenser_spec.get("vacuum_kPa_abs", 8.0)))

    hp_exhaust_temp = _approx_saturation_temp(max(ip_pressure, 1.0))
    ip_exhaust_temp = _approx_saturation_temp(max(lp_pressure, 0.5))
    lp_exhaust_temp = _approx_saturation_temp(max(condenser_pressure_bar, 0.1))

    hp_delta_h = _section_delta_h(hp_inlet_temp, hp_exhaust_temp, eff_hp)
    ip_delta_h = _section_delta_h(ip_inlet_temp, ip_exhaust_temp, eff_ip)
    lp_delta_h = _section_delta_h(lp_inlet_temp, lp_exhaust_temp, eff_lp)

    hp_power = hp_flow * hp_delta_h / 1000.0
    ip_power = ip_flow * ip_delta_h / 1000.0
    lp_power = lp_flow * lp_delta_h / 1000.0

    gross_mech_power = hp_power + ip_power + lp_power
    electric_power = gross_mech_power * mech_eff

    sections = {
        "hp_section": {
            "inlet_P_bar": float(hrsg.get("hp", {}).get("steam_P_bar", 0.0)),
            "inlet_T_C": hp_inlet_temp,
            "exhaust_P_bar": ip_pressure,
            "power_MW": hp_power * mech_eff,
            "flow_kg_s": hp_flow,
        },
        "ip_section": {
            "inlet_P_bar": ip_pressure,
            "inlet_T_C": ip_inlet_temp,
            "exhaust_P_bar": lp_pressure,
            "power_MW": ip_power * mech_eff,
            "flow_kg_s": ip_flow,
        },
        "lp_section": {
            "inlet_P_bar": lp_pressure,
            "inlet_T_C": lp_inlet_temp,
            "exhaust_kPa_abs": float(condenser_spec.get("vacuum_kPa_abs", 8.0)),
            "power_MW": lp_power * mech_eff,
            "flow_kg_s": lp_flow,
        },
    }

    result = {
        **sections,
        "gross_mech_power_MW": gross_mech_power,
        "electric_power_MW": electric_power,
        "mech_elec_eff": mech_eff,
    }

    trace = {
        "hp": {
            "inlet_temp_C": hp_inlet_temp,
            "exhaust_temp_C": hp_exhaust_temp,
            "delta_h_kJ_per_kg": hp_delta_h,
            "flow_kg_s": hp_flow,
            "power_MW_before_generator": hp_power,
        },
        "ip": {
            "inlet_temp_C": ip_inlet_temp,
            "exhaust_temp_C": ip_exhaust_temp,
            "delta_h_kJ_per_kg": ip_delta_h,
            "flow_kg_s": ip_flow,
            "power_MW_before_generator": ip_power,
        },
        "lp": {
            "inlet_temp_C": lp_inlet_temp,
            "exhaust_temp_C": lp_exhaust_temp,
            "delta_h_kJ_per_kg": lp_delta_h,
            "flow_kg_s": lp_flow,
            "power_MW_before_generator": lp_power,
        },
        "mech_efficiency": mech_eff,
        "electric_power_MW": electric_power,
    }

    return result, trace
