"""Ambient condition correction calculations."""

from __future__ import annotations

from typing import Any, Mapping

from ..utils.physical_props import humid_air_props


ISO_REFERENCE_TEMP_C = 15.0


def apply_site_corrections(ambient: Mapping[str, Any], corr_coeff: Mapping[str, float]) -> dict[str, float]:
    """Compute correction factors for gas turbine performance based on site ambient conditions."""
    site_temp = float(ambient.get("Ta_C", ISO_REFERENCE_TEMP_C))
    delta_temp = site_temp - float(corr_coeff.get("reference_temp_C", ISO_REFERENCE_TEMP_C))

    power_pct_per_K = float(corr_coeff.get("dPower_pct_per_K", 0.0))
    flow_pct_per_K = float(corr_coeff.get("dFlow_pct_per_K", 0.0))
    exhaust_delta_per_K = float(corr_coeff.get("dExhT_K_per_K", 0.0))

    power_correction_pct = power_pct_per_K * delta_temp
    flow_correction_pct = flow_pct_per_K * delta_temp
    exhaust_delta_C = exhaust_delta_per_K * delta_temp

    humid_air = humid_air_props(site_temp, float(ambient.get("RH_pct", 60.0)), float(ambient.get("P_bar", 1.013)))

    return {
        "site_temperature_C": site_temp,
        "delta_T_K": delta_temp,
        "power_correction_pct": power_correction_pct,
        "flow_correction_pct": flow_correction_pct,
        "exhaust_temp_delta_C": exhaust_delta_C,
        "power_multiplier": 1.0 + power_correction_pct / 100.0,
        "flow_multiplier": 1.0 + flow_correction_pct / 100.0,
        "humid_air": humid_air,
    }
