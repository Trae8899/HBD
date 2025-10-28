"""Console presentation helpers for the solver results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def _format_block(title: str, lines: list[str]) -> str:
    divider = "=" * len(title)
    return "\n".join([title, divider, *lines])


def render_console_view(
    case_path: Path,
    merged_case: Mapping[str, Any],
    result: Mapping[str, Any],
    show_calcs: bool = False,
) -> None:
    """Print a structured console view of inputs and outputs."""
    ambient = merged_case.get("ambient", {})
    gas_turbine = merged_case.get("gas_turbine", {})
    hrsg = merged_case.get("hrsg", {})
    steam_turbine = merged_case.get("steam_turbine", {})

    input_lines = [
        f"Ambient: T={ambient.get('Ta_C', 'N/A')} °C, RH={ambient.get('RH_pct', 'N/A')} %, P={ambient.get('P_bar', 'N/A')} bar",
        f"Gas Turbine: ISO Power={gas_turbine.get('ISO_power_MW', 'N/A')} MW, Exhaust T={gas_turbine.get('ISO_exhaust_temp_C', 'N/A')} °C",
        f"HRSG HP/IP/LP pressures: {hrsg.get('hp', {}).get('pressure_bar', 'N/A')} / {hrsg.get('ip', {}).get('pressure_bar', 'N/A')} / {hrsg.get('lp', {}).get('pressure_bar', 'N/A')} bar",
        f"Steam Turbine Efficiencies: HP={steam_turbine.get('isentropic_eff_hp', 'N/A')}, IP={steam_turbine.get('isentropic_eff_ip', 'N/A')}, LP={steam_turbine.get('isentropic_eff_lp', 'N/A')}",
    ]

    print(_format_block(f"Input Case: {case_path.name}", input_lines))

    summary = result.get("summary", {})
    gt_block = result.get("gt_block", {})
    hrsg_block = result.get("hrsg_block", {})
    st_block = result.get("st_block", {})
    condenser_block = result.get("condenser_block", {})
    mass_balance = result.get("mass_energy_balance", {})

    summary_lines = [
        f"GT Power: {summary.get('GT_power_MW', 0):.1f} MW",
        f"ST Power: {summary.get('ST_power_MW', 0):.1f} MW",
        f"Net Power: {summary.get('NET_power_MW', 0):.1f} MW",
        f"Net Eff (LHV): {summary.get('NET_eff_LHV_pct', 0):.1f} %",
        f"Closure Error: {mass_balance.get('closure_error_pct', 0):.2f} %",
    ]
    print()
    print(_format_block("Plant Summary", summary_lines))

    gt_lines = [
        f"Fuel Heat Input: {gt_block.get('fuel_heat_input_MW_LHV', 0):.1f} MW",
        f"Electric Power: {gt_block.get('electric_power_MW', 0):.1f} MW",
        f"Exhaust: {gt_block.get('exhaust', {}).get('temp_C', 0):.1f} °C / {gt_block.get('exhaust', {}).get('flow_kg_s', 0):.1f} kg/s",
    ]
    print()
    print(_format_block("Gas Turbine Block", gt_lines))

    hrsg_lines = [
        f"HP: {hrsg_block.get('hp', {}).get('steam_flow_kg_s', 0):.1f} kg/s @ {hrsg_block.get('hp', {}).get('steam_P_bar', 0):.1f} bar",
        f"IP: {hrsg_block.get('ip', {}).get('steam_flow_kg_s', 0):.1f} kg/s @ {hrsg_block.get('ip', {}).get('steam_P_bar', 0):.1f} bar",
        f"LP: {hrsg_block.get('lp', {}).get('steam_flow_kg_s', 0):.1f} kg/s @ {hrsg_block.get('lp', {}).get('steam_P_bar', 0):.1f} bar",
        f"Stack Temp: {hrsg_block.get('stack_temp_C', 0):.1f} °C",
    ]
    print()
    print(_format_block("HRSG Block", hrsg_lines))

    st_lines = [
        f"HP Section Power: {st_block.get('hp_section', {}).get('power_MW', 0):.1f} MW",
        f"IP Section Power: {st_block.get('ip_section', {}).get('power_MW', 0):.1f} MW",
        f"LP Section Power: {st_block.get('lp_section', {}).get('power_MW', 0):.1f} MW",
        f"ST Electric Power: {st_block.get('electric_power_MW', 0):.1f} MW",
    ]
    print()
    print(_format_block("Steam Turbine Block", st_lines))

    condenser_lines = [
        f"Cooling Water In/Out: {condenser_block.get('cw_inlet_C', 0):.1f} / {condenser_block.get('cw_outlet_C', 0):.1f} °C",
        f"Heat Rejected: {condenser_block.get('heat_rejected_MW', 0):.1f} MW",
        f"LP Exhaust Vacuum: {st_block.get('lp_section', {}).get('exhaust_kPa_abs', 0):.1f} kPa abs",
    ]
    print()
    print(_format_block("Condenser Loop", condenser_lines))

    if show_calcs:
        print()
        print(_format_block("Calculation Trace", ["Details stored in calculation log." ]))


def export_calculation_log(trace: Mapping[str, Any], output_path: Path) -> Path:
    """Persist the detailed calculation trace to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
