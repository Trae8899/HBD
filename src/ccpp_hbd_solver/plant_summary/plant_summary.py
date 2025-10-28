"""Aggregate plant summary metrics."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from ..utils.warnings import format_warning


def summarize_plant(blocks: Mapping[str, Any], metadata: Mapping[str, Any]) -> Tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Compose plant-wide metrics, convergence status, and metadata."""
    gt_block = blocks.get("gt_block", {})
    st_block = blocks.get("st_block", {})
    condenser_block = blocks.get("condenser_block", {})
    hrsg_block = blocks.get("hrsg_block", {})

    fuel_heat_input = float(gt_block.get("fuel_heat_input_MW_LHV", 0.0))
    gt_power = float(gt_block.get("electric_power_MW", 0.0))
    st_power = float(st_block.get("electric_power_MW", 0.0))
    aux_load = float(metadata.get("bop", {}).get("aux_load_MW", 0.0))
    condenser_heat = float(condenser_block.get("heat_rejected_MW", 0.0))

    net_power = gt_power + st_power - aux_load
    net_eff_pct = (net_power / fuel_heat_input * 100.0) if fuel_heat_input else 0.0

    expected_heat_out = gt_power + st_power + condenser_heat
    closure_error_pct = (
        abs(fuel_heat_input - expected_heat_out) / fuel_heat_input * 100.0 if fuel_heat_input else 0.0
    )
    convergence_ok = closure_error_pct <= 0.3 and bool(hrsg_block.get("converged", True))

    summary = {
        "GT_power_MW": gt_power,
        "ST_power_MW": st_power,
        "AUX_load_MW": aux_load,
        "NET_power_MW": net_power,
        "NET_eff_LHV_pct": net_eff_pct,
    }

    mass_balance = {
        "closure_error_pct": closure_error_pct,
        "converged": convergence_ok,
        "iterations_used": int(hrsg_block.get("iterations_used", 1)),
    }

    meta_defaults = metadata.get("meta", {})
    meta = {
        "input_case": meta_defaults.get("input_case"),
        "timestamp_utc": meta_defaults.get("timestamp_utc"),
        "solver_commit": meta_defaults.get("solver_commit"),
    }

    warnings = []
    if closure_error_pct > 0.5:
        warnings.append(format_warning("CLOSURE_GT_0P5", f"{closure_error_pct:.3f}%"))
    elif closure_error_pct > 0.3:
        warnings.append(format_warning("CLOSURE_NEAR_LIMIT", f"{closure_error_pct:.3f}%"))
    if not bool(hrsg_block.get("converged", True)):
        warnings.append(format_warning("HRSG_PINCH_VIOLATION", "See HRSG warnings"))

    trace = {
        "meta": meta,
        "balance": {
            "fuel_heat_input_MW": fuel_heat_input,
            "gt_power_MW": gt_power,
            "st_power_MW": st_power,
            "condenser_heat_MW": condenser_heat,
            "expected_heat_out_MW": expected_heat_out,
            "closure_error_pct": closure_error_pct,
        },
        "warnings": warnings,
    }

    return summary, mass_balance, trace
