"""SVG diagram generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

BLOCK_POSITIONS = {
    "GT": (40, 80),
    "HRSG": (240, 60),
    "ST": (520, 80),
    "COND": (720, 80),
}

BLOCK_SIZE = (140, 120)


def _rect(x: int, y: int, label: str) -> str:
    width, height = BLOCK_SIZE
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" ry="12" '
        f'style="fill:#f4f4f4;stroke:#2d3a4a;stroke-width:2" />\n'
        f'<text x="{x + width / 2}" y="{y + 24}" text-anchor="middle" '
        f'style="font-size:16px;font-family:Arial;fill:#2d3a4a">{label}</text>\n'
    )


def _arrow(x1: int, y1: int, x2: int, y2: int, label: str) -> str:
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'style="stroke:#1f78b4;stroke-width:3;marker-end:url(#arrowhead)" />\n'
        f'<text x="{(x1 + x2) / 2}" y="{y1 - 10}" text-anchor="middle" '
        f'style="font-size:12px;font-family:Arial;fill:#1f78b4">{label}</text>\n'
    )


def export_flow_diagram(result: Mapping[str, Any], output_path: Path) -> Path:
    """Render a block diagram of the CCPP heat balance."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gt = result.get("gt_block", {})
    hrsg = result.get("hrsg_block", {})
    st = result.get("st_block", {})
    condenser = result.get("condenser_block", {})

    svg_parts = [
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"900\" height=\"260\">",
        "<defs><marker id=\"arrowhead\" markerWidth=\"10\" markerHeight=\"7\" refX=\"10\" refY=\"3.5\" orient=\"auto\">",
        "<polygon points=\"0 0, 10 3.5, 0 7\" style=\"fill:#1f78b4\" /></marker></defs>",
    ]

    svg_parts.append(_rect(*BLOCK_POSITIONS["GT"], "Gas Turbine"))
    svg_parts.append(_rect(*BLOCK_POSITIONS["HRSG"], "3P HRSG"))
    svg_parts.append(_rect(*BLOCK_POSITIONS["ST"], "Steam Turbine"))
    svg_parts.append(_rect(*BLOCK_POSITIONS["COND"], "Condenser"))

    gt_arrow_label = f"{gt.get('electric_power_MW', 0):.1f} MW"\
        f" / {gt.get('exhaust', {}).get('flow_kg_s', 0):.0f} kg/s"
    svg_parts.append(_arrow(180, 140, 240, 140, gt_arrow_label))

    hrsg_label = (
        f"HP {hrsg.get('hp', {}).get('steam_flow_kg_s', 0):.1f} kg/s\n"
        f"IP {hrsg.get('ip', {}).get('steam_flow_kg_s', 0):.1f} kg/s\n"
        f"LP {hrsg.get('lp', {}).get('steam_flow_kg_s', 0):.1f} kg/s"
    )
    svg_parts.append(
        f'<text x="{BLOCK_POSITIONS["HRSG"][0] + 70}" y="{BLOCK_POSITIONS["HRSG"][1] + 70}" '
        f'text-anchor="middle" style="font-size:12px;font-family:Arial;fill:#2d3a4a;white-space:pre">{hrsg_label}</text>\n'
    )

    st_arrow_label = f"{st.get('electric_power_MW', 0):.1f} MW"
    svg_parts.append(_arrow(380, 140, 520, 140, st_arrow_label))

    condenser_label = (
        f"CW out {condenser.get('cw_outlet_C', 0):.1f}°C\n"
        f"Heat {condenser.get('heat_rejected_MW', 0):.1f} MW"
    )
    svg_parts.append(
        f'<text x="{BLOCK_POSITIONS["COND"][0] + 70}" y="{BLOCK_POSITIONS["COND"][1] + 70}" '
        f'text-anchor="middle" style="font-size:12px;font-family:Arial;fill:#2d3a4a;white-space:pre">{condenser_label}</text>\n'
    )
    svg_parts.append(_arrow(660, 140, 720, 140, f"{st.get('lp_section', {}).get('flow_kg_s', 0):.1f} kg/s"))

    summary = result.get("summary", {})
    summary_text = (
        f"Net Power: {summary.get('NET_power_MW', 0):.1f} MW\n"
        f"Net Eff.: {summary.get('NET_eff_LHV_pct', 0):.1f}%"
    )
    svg_parts.append(
        f'<text x="450" y="30" text-anchor="middle" '
        f'style="font-size:14px;font-family:Arial;fill:#2d3a4a;white-space:pre">{summary_text}</text>'
    )

    svg_parts.append("</svg>")

    output_path.write_text("".join(svg_parts), encoding="utf-8")
    return output_path
