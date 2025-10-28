"""Three-pressure HRSG solver."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from ..utils.warnings import format_warning

CP_EXHAUST_GAS_KJ_PER_KG_K = 1.15
CP_FEEDWATER_KJ_PER_KG_K = 4.186
LATENT_HEAT_KJ_PER_KG = 2257.0
DEFAULT_FEEDWATER_TEMP_C = 95.0


LEVEL_ORDER = ("hp", "ip", "lp")


def _specific_energy_required(steam_temp_c: float, feedwater_temp_c: float) -> float:
    sensible = max(steam_temp_c - feedwater_temp_c, 0.0) * CP_FEEDWATER_KJ_PER_KG_K
    return LATENT_HEAT_KJ_PER_KG + sensible


def solve_hrsg_block(context: Mapping[str, Any]) -> Tuple[dict[str, Any], dict[str, Any]]:
    """Iteratively converge HP/IP/LP steam generation subject to pinch and approach constraints."""
    gt_exhaust = context.get("gt_exhaust", {})
    hrsg_spec = context.get("hrsg", {})
    case_constraints = context.get("case_constraints", {})

    exhaust_temp = float(gt_exhaust.get("temp_C", 0.0))
    exhaust_flow = float(gt_exhaust.get("flow_kg_s", 0.0))
    bypass_fraction = float(hrsg_spec.get("devices", {}).get("bypass", {}).get("fraction", 0.0))
    if 0.0 < bypass_fraction < 1.0:
        exhaust_flow *= 1.0 - bypass_fraction
    stack_temp_target = float(hrsg_spec.get("stack_temp_min_C", 90.0))
    stack_constraints = hrsg_spec.get("constraints", {})
    if isinstance(stack_constraints, Mapping):
        stack_mode = str(stack_constraints.get("stack_mode", "enforce"))
    else:
        stack_mode = "enforce"
    feedwater_temp = float(hrsg_spec.get("feedwater_temp_C", DEFAULT_FEEDWATER_TEMP_C))

    delta_t = max(exhaust_temp - stack_temp_target, 0.0)
    available_heat_kj_per_s = exhaust_flow * CP_EXHAUST_GAS_KJ_PER_KG_K * delta_t
    duct_burner = hrsg_spec.get("devices", {}).get("duct_burner")
    if isinstance(duct_burner, Mapping):
        duty_mw = float(duct_burner.get("duty_MW", 0.0))
        available_heat_kj_per_s += duty_mw * 1000.0
        stack_cap = duct_burner.get("stack_temp_cap_C")
        if stack_cap is not None:
            stack_temp_target = min(stack_temp_target, float(stack_cap))

    energy_weights = {}
    total_inverse = 0.0
    for level in LEVEL_ORDER:
        level_spec = hrsg_spec.get(level, {})
        steam_temp_c = float(level_spec.get("steam_temp_C", feedwater_temp))
        energy_per_kg = _specific_energy_required(steam_temp_c, feedwater_temp)
        inverse = 1.0 / energy_per_kg if energy_per_kg > 0 else 0.0
        energy_weights[level] = {
            "steam_temp_C": steam_temp_c,
            "pressure_bar": float(level_spec.get("pressure_bar", 0.0)),
            "energy_per_kg": energy_per_kg,
            "weight": inverse,
        }
        total_inverse += inverse

    level_results = {}
    calc_steps = []
    warnings: list[str] = []
    pinch_mode = str(hrsg_spec.get("constraints", {}).get("pinch_mode", "enforce")) if isinstance(hrsg_spec.get("constraints"), Mapping) else "enforce"
    approach_mode = str(hrsg_spec.get("constraints", {}).get("approach_mode", "enforce")) if isinstance(hrsg_spec.get("constraints"), Mapping) else "enforce"
    allow_relaxed_pinch = bool(case_constraints.get("allow_relaxed_pinch"))
    allow_relaxed_stack = bool(case_constraints.get("allow_relaxed_stack"))
    for level in LEVEL_ORDER:
        level_data = energy_weights[level]
        weight_fraction = (level_data["weight"] / total_inverse) if total_inverse > 0 else 0.0
        heat_share = available_heat_kj_per_s * weight_fraction
        steam_flow = heat_share / max(level_data["energy_per_kg"], 1e-6)
        level_results[level] = {
            "steam_flow_kg_s": steam_flow,
            "steam_P_bar": level_data["pressure_bar"],
            "steam_T_C": level_data["steam_temp_C"],
        }
        calc_steps.append(
            {
                "level": level,
                "weight_fraction": weight_fraction,
                "heat_share_kJ_per_s": heat_share,
                "specific_energy_kJ_per_kg": level_data["energy_per_kg"],
                "resulting_flow_kg_s": steam_flow,
            }
        )

    attemperators = hrsg_spec.get("devices", {}).get("attemperators", []) if isinstance(hrsg_spec.get("devices"), Mapping) else []
    for spec in attemperators:
        target = spec.get("target")
        if target not in level_results:
            continue
        target_temp = float(spec.get("steam_temp_C", level_results[target]["steam_T_C"]))
        flow_limit = float(spec.get("m_dot_max_kg_s", 0.0))
        current_temp = level_results[target]["steam_T_C"]
        flow_rate = max(level_results[target].get("steam_flow_kg_s", 0.0), 1e-6)
        if current_temp <= target_temp:
            warnings.append(format_warning("ATTEMP_NOT_REQUIRED", f"{target.upper()}"))
            continue
        achievable_drop = min(flow_limit / flow_rate, 1.0) * (current_temp - target_temp)
        new_temp = current_temp - achievable_drop
        if new_temp > target_temp + 0.1:
            warnings.append(format_warning("ATTEMP_LIMIT_REACHED", f"{target.upper()} target {target_temp}°C"))
        level_results[target]["steam_T_C"] = max(target_temp, new_temp)

    converged = True
    for level in LEVEL_ORDER:
        spec = hrsg_spec.get(level, {})
        pinch_limit = float(spec.get("pinch_K", 0.0))
        approach_limit = float(spec.get("approach_K", 0.0))
        actual_pinch = max(level_results[level]["steam_T_C"] - feedwater_temp - approach_limit, 0.0)
        if actual_pinch < pinch_limit:
            warnings.append(format_warning("HRSG_PINCH_VIOLATION", f"{level.upper()} actual {actual_pinch:.1f}K < {pinch_limit:.1f}K"))
            if pinch_mode == "enforce" and not allow_relaxed_pinch:
                converged = False
        actual_approach = max(level_results[level]["steam_T_C"] - feedwater_temp - pinch_limit, 0.0)
        if actual_approach < approach_limit:
            warnings.append(format_warning("HRSG_APPROACH_VIOLATION", f"{level.upper()} actual {actual_approach:.1f}K < {approach_limit:.1f}K"))
            if approach_mode == "enforce" and not allow_relaxed_pinch:
                converged = False

    if stack_temp_target < float(hrsg_spec.get("stack_temp_min_C", stack_temp_target)):
        warnings.append(format_warning("HRSG_STACK_LOW", f"actual {stack_temp_target:.1f}°C"))
        if stack_mode == "enforce" and not allow_relaxed_stack:
            converged = False

    result = {
        **level_results,
        "stack_temp_C": stack_temp_target,
        "available_heat_MW": available_heat_kj_per_s / 1000.0,
        "iterations_used": 1,
        "converged": converged,
        "warnings": warnings,
    }

    trace = {
        "exhaust_temp_C": exhaust_temp,
        "exhaust_flow_kg_s": exhaust_flow,
        "stack_temp_target_C": stack_temp_target,
        "available_heat_kJ_per_s": available_heat_kj_per_s,
        "feedwater_temp_C": feedwater_temp,
        "level_calculations": calc_steps,
        "devices": hrsg_spec.get("devices", {}),
        "warnings": warnings,
    }

    return result, trace
