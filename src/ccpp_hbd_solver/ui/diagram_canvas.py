"""Interactive diagram canvas with inline editing hotspots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import tkinter as tk
from tkinter import messagebox, ttk

from .theme import COLORS, FONTS

PathTuple = Sequence[str]
ValueGetter = Callable[[PathTuple], Any]
ValueSetter = Callable[[PathTuple, float], None]
ChangeCallback = Callable[[PathTuple, float], None]


@dataclass(frozen=True)
class HotspotSpec:
    """Definition for a clickable hotspot on the diagram."""

    path: tuple[str, ...]
    label_en: str
    label_ko: str
    unit: str
    bbox: tuple[int, int, int, int]
    value_pos: tuple[int, int]
    min_value: float
    max_value: float
    step: float = 1.0
    decimals: int = 1


HOTSPOTS: tuple[HotspotSpec, ...] = (
    HotspotSpec(
        path=("ambient", "Ta_C"),
        label_en="Ambient T",
        label_ko="건구 온도",
        unit="°C",
        bbox=(20, 20, 200, 80),
        value_pos=(28, 58),
        min_value=-20.0,
        max_value=55.0,
        step=0.5,
        decimals=1,
    ),
    HotspotSpec(
        path=("ambient", "RH_pct"),
        label_en="Relative Humidity",
        label_ko="상대습도",
        unit="%",
        bbox=(220, 20, 400, 80),
        value_pos=(228, 58),
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("ambient", "P_bar"),
        label_en="Ambient Pressure",
        label_ko="대기압",
        unit="bar abs",
        bbox=(420, 20, 600, 80),
        value_pos=(428, 58),
        min_value=0.8,
        max_value=1.1,
        step=0.01,
        decimals=3,
    ),
    HotspotSpec(
        path=("gas_turbine", "ISO_power_MW"),
        label_en="GT ISO Power",
        label_ko="ISO 정격",
        unit="MW",
        bbox=(20, 120, 180, 180),
        value_pos=(28, 158),
        min_value=50.0,
        max_value=600.0,
        step=1.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("gas_turbine", "ISO_heat_rate_kJ_per_kWh"),
        label_en="ISO Heat Rate",
        label_ko="ISO 열소비율",
        unit="kJ/kWh",
        bbox=(20, 190, 180, 250),
        value_pos=(28, 228),
        min_value=8000.0,
        max_value=12000.0,
        step=10.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("gas_turbine", "fuel_LHV_kJ_per_kg"),
        label_en="Fuel LHV",
        label_ko="연료 LHV",
        unit="kJ/kg",
        bbox=(20, 260, 180, 320),
        value_pos=(28, 298),
        min_value=38000.0,
        max_value=52000.0,
        step=50.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("gas_turbine", "ISO_exhaust_temp_C"),
        label_en="ISO Exhaust T",
        label_ko="ISO 배기온도",
        unit="°C",
        bbox=(20, 330, 180, 390),
        value_pos=(28, 368),
        min_value=450.0,
        max_value=700.0,
        step=1.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("gas_turbine", "ISO_exhaust_flow_kg_s"),
        label_en="ISO Exhaust Flow",
        label_ko="ISO 배기유량",
        unit="kg/s",
        bbox=(200, 120, 360, 180),
        value_pos=(208, 158),
        min_value=200.0,
        max_value=900.0,
        step=5.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("gas_turbine", "corr_coeff", "dPower_pct_per_K"),
        label_en="ΔPower",
        label_ko="전력 변화율",
        unit="%/K",
        bbox=(200, 190, 360, 250),
        value_pos=(208, 228),
        min_value=-1.0,
        max_value=0.0,
        step=0.01,
        decimals=2,
    ),
    HotspotSpec(
        path=("gas_turbine", "corr_coeff", "dFlow_pct_per_K"),
        label_en="ΔFlow",
        label_ko="유량 변화율",
        unit="%/K",
        bbox=(200, 260, 360, 320),
        value_pos=(208, 298),
        min_value=0.0,
        max_value=1.0,
        step=0.01,
        decimals=2,
    ),
    HotspotSpec(
        path=("gas_turbine", "corr_coeff", "dExhT_K_per_K"),
        label_en="ΔExhaust T",
        label_ko="배기온 변화",
        unit="K/K",
        bbox=(200, 330, 360, 390),
        value_pos=(208, 368),
        min_value=0.0,
        max_value=2.0,
        step=0.05,
        decimals=2,
    ),
    HotspotSpec(
        path=("hrsg", "hp", "pressure_bar"),
        label_en="HP Pressure",
        label_ko="HP 압력",
        unit="bar abs",
        bbox=(380, 120, 540, 170),
        value_pos=(388, 152),
        min_value=60.0,
        max_value=160.0,
        step=1.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("hrsg", "hp", "steam_temp_C"),
        label_en="HP Steam T",
        label_ko="HP 증기온",
        unit="°C",
        bbox=(380, 176, 540, 226),
        value_pos=(388, 208),
        min_value=450.0,
        max_value=600.0,
        step=1.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("hrsg", "hp", "pinch_K"),
        label_en="HP Pinch",
        label_ko="HP 핀치",
        unit="K",
        bbox=(380, 232, 540, 282),
        value_pos=(388, 264),
        min_value=5.0,
        max_value=20.0,
        step=0.5,
        decimals=1,
    ),
    HotspotSpec(
        path=("hrsg", "hp", "approach_K"),
        label_en="HP Approach",
        label_ko="HP 어프로치",
        unit="K",
        bbox=(380, 288, 540, 338),
        value_pos=(388, 320),
        min_value=3.0,
        max_value=15.0,
        step=0.5,
        decimals=1,
    ),
    HotspotSpec(
        path=("hrsg", "ip", "pressure_bar"),
        label_en="IP Pressure",
        label_ko="IP 압력",
        unit="bar abs",
        bbox=(560, 120, 720, 170),
        value_pos=(568, 152),
        min_value=15.0,
        max_value=60.0,
        step=1.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("hrsg", "ip", "steam_temp_C"),
        label_en="IP Steam T",
        label_ko="IP 증기온",
        unit="°C",
        bbox=(560, 176, 720, 226),
        value_pos=(568, 208),
        min_value=400.0,
        max_value=600.0,
        step=1.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("hrsg", "ip", "pinch_K"),
        label_en="IP Pinch",
        label_ko="IP 핀치",
        unit="K",
        bbox=(560, 232, 720, 282),
        value_pos=(568, 264),
        min_value=8.0,
        max_value=20.0,
        step=0.5,
        decimals=1,
    ),
    HotspotSpec(
        path=("hrsg", "ip", "approach_K"),
        label_en="IP Approach",
        label_ko="IP 어프로치",
        unit="K",
        bbox=(560, 288, 720, 338),
        value_pos=(568, 320),
        min_value=4.0,
        max_value=15.0,
        step=0.5,
        decimals=1,
    ),
    HotspotSpec(
        path=("hrsg", "lp", "pressure_bar"),
        label_en="LP Pressure",
        label_ko="LP 압력",
        unit="bar abs",
        bbox=(740, 120, 900, 170),
        value_pos=(748, 152),
        min_value=1.0,
        max_value=15.0,
        step=0.5,
        decimals=1,
    ),
    HotspotSpec(
        path=("hrsg", "lp", "steam_temp_C"),
        label_en="LP Steam T",
        label_ko="LP 증기온",
        unit="°C",
        bbox=(740, 176, 900, 226),
        value_pos=(748, 208),
        min_value=150.0,
        max_value=350.0,
        step=1.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("hrsg", "lp", "pinch_K"),
        label_en="LP Pinch",
        label_ko="LP 핀치",
        unit="K",
        bbox=(740, 232, 900, 282),
        value_pos=(748, 264),
        min_value=10.0,
        max_value=25.0,
        step=0.5,
        decimals=1,
    ),
    HotspotSpec(
        path=("hrsg", "lp", "approach_K"),
        label_en="LP Approach",
        label_ko="LP 어프로치",
        unit="K",
        bbox=(740, 288, 900, 338),
        value_pos=(748, 320),
        min_value=5.0,
        max_value=15.0,
        step=0.5,
        decimals=1,
    ),
    HotspotSpec(
        path=("hrsg", "stack_temp_min_C"),
        label_en="Stack Min T",
        label_ko="스택 최소온",
        unit="°C",
        bbox=(920, 200, 1080, 260),
        value_pos=(928, 238),
        min_value=70.0,
        max_value=130.0,
        step=1.0,
        decimals=0,
    ),
    HotspotSpec(
        path=("steam_turbine", "isentropic_eff_hp"),
        label_en="HP η",
        label_ko="HP 효율",
        unit="η",
        bbox=(380, 360, 480, 410),
        value_pos=(388, 392),
        min_value=0.75,
        max_value=0.92,
        step=0.005,
        decimals=3,
    ),
    HotspotSpec(
        path=("steam_turbine", "isentropic_eff_ip"),
        label_en="IP η",
        label_ko="IP 효율",
        unit="η",
        bbox=(490, 360, 590, 410),
        value_pos=(498, 392),
        min_value=0.75,
        max_value=0.92,
        step=0.005,
        decimals=3,
    ),
    HotspotSpec(
        path=("steam_turbine", "isentropic_eff_lp"),
        label_en="LP η",
        label_ko="LP 효율",
        unit="η",
        bbox=(600, 360, 700, 410),
        value_pos=(608, 392),
        min_value=0.75,
        max_value=0.90,
        step=0.005,
        decimals=3,
    ),
    HotspotSpec(
        path=("steam_turbine", "mech_elec_eff"),
        label_en="Mech/Gen η",
        label_ko="기전 효율",
        unit="η",
        bbox=(710, 360, 840, 410),
        value_pos=(718, 392),
        min_value=0.95,
        max_value=0.995,
        step=0.001,
        decimals=3,
    ),
    HotspotSpec(
        path=("condenser", "vacuum_kPa_abs"),
        label_en="Condenser Vacuum",
        label_ko="복수기 진공",
        unit="kPa abs",
        bbox=(900, 320, 1080, 370),
        value_pos=(908, 352),
        min_value=4.0,
        max_value=15.0,
        step=0.1,
        decimals=2,
    ),
    HotspotSpec(
        path=("condenser", "cw_inlet_C"),
        label_en="CW Inlet",
        label_ko="냉각수 입구",
        unit="°C",
        bbox=(900, 372, 1080, 422),
        value_pos=(908, 404),
        min_value=5.0,
        max_value=35.0,
        step=0.5,
        decimals=1,
    ),
    HotspotSpec(
        path=("bop", "aux_load_MW"),
        label_en="Aux Load",
        label_ko="보조부하",
        unit="MW",
        bbox=(900, 120, 1080, 170),
        value_pos=(908, 152),
        min_value=0.0,
        max_value=50.0,
        step=0.5,
        decimals=1,
    ),
)


class DiagramCanvas(tk.Canvas):
    """Canvas widget that renders the plant schematic and supports inline editing."""

    def __init__(
        self,
        master: tk.Widget,
        *,
        get_value: ValueGetter,
        set_value: ValueSetter,
        on_change: ChangeCallback,
        width: int = 1100,
        height: int = 460,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            background=COLORS["canvas_bg"],
            highlightthickness=0,
        )
        self._get_value = get_value
        self._set_value = set_value
        self._on_change = on_change
        self._hotspot_items: dict[HotspotSpec, dict[str, int]] = {}
        self._value_labels: dict[HotspotSpec, int] = {}
        self._editor: ttk.Spinbox | None = None
        self._overlay_items: list[int] = []
        self._node_shapes: dict[str, int] = {}
        self._default_fills: dict[str, str] = {}

        self._draw_static_elements()
        self._create_hotspots()
        self.update_case_values()

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def _draw_static_elements(self) -> None:
        """Draw fixed diagram blocks and connecting lines."""

        # Process flow arrows
        self.create_line(140, 170, 200, 170, arrow=tk.LAST, fill=COLORS["block_outline"], width=3)
        self.create_line(300, 170, 360, 170, arrow=tk.LAST, fill=COLORS["block_outline"], width=3)
        self.create_line(460, 170, 520, 170, arrow=tk.LAST, fill=COLORS["block_outline"], width=3)
        self.create_line(520, 260, 680, 300, arrow=tk.LAST, fill=COLORS["block_outline"], width=3)

        # Major equipment blocks
        self._node_shapes["gt"] = self.create_rectangle(
            80,
            130,
            200,
            210,
            fill=COLORS["gt_fill"],
            outline=COLORS["block_outline"],
            width=2,
        )
        self._node_shapes["hrsg"] = self.create_rectangle(
            220,
            90,
            320,
            310,
            fill=COLORS["hrsg_fill"],
            outline=COLORS["block_outline"],
            width=2,
        )
        self._node_shapes["st_hp"] = self.create_rectangle(
            360,
            110,
            460,
            160,
            fill=COLORS["st_fill"],
            outline=COLORS["block_outline"],
            width=2,
        )
        self._node_shapes["st_ip"] = self.create_rectangle(
            360,
            180,
            460,
            230,
            fill=COLORS["st_fill"],
            outline=COLORS["block_outline"],
            width=2,
        )
        self._node_shapes["st_lp"] = self.create_rectangle(
            360,
            250,
            460,
            300,
            fill=COLORS["st_fill"],
            outline=COLORS["block_outline"],
            width=2,
        )
        self._node_shapes["condenser"] = self.create_rectangle(
            520,
            280,
            680,
            360,
            fill=COLORS["cond_fill"],
            outline=COLORS["block_outline"],
            width=2,
        )

        self._default_fills = {
            "gt": COLORS["gt_fill"],
            "hrsg": COLORS["hrsg_fill"],
            "st_hp": COLORS["st_fill"],
            "st_ip": COLORS["st_fill"],
            "st_lp": COLORS["st_fill"],
            "condenser": COLORS["cond_fill"],
        }

        # Labels for blocks
        self.create_text(
            140,
            120,
            text="Gas Turbine\n가스터빈",
            font=FONTS["section"],
            fill=COLORS["text_primary"],
            anchor="s",
            justify="center",
        )
        self.create_text(
            270,
            80,
            text="HRSG",
            font=FONTS["section"],
            fill=COLORS["text_primary"],
            anchor="s",
        )
        self.create_text(
            410,
            100,
            text="HP",
            font=FONTS["label"],
            fill=COLORS["text_secondary"],
            anchor="s",
        )
        self.create_text(
            410,
            170,
            text="IP",
            font=FONTS["label"],
            fill=COLORS["text_secondary"],
            anchor="s",
        )
        self.create_text(
            410,
            240,
            text="LP",
            font=FONTS["label"],
            fill=COLORS["text_secondary"],
            anchor="s",
        )
        self.create_text(
            600,
            270,
            text="Condenser\n복수기",
            font=FONTS["section"],
            fill=COLORS["text_primary"],
            anchor="s",
            justify="center",
        )

    def _create_hotspots(self) -> None:
        """Create interactive hotspots according to the specification."""

        for spec in HOTSPOTS:
            rect = self.create_rectangle(
                *spec.bbox,
                fill=COLORS["hotspot_bg"],
                outline=COLORS["hotspot_border"],
                width=1,
            )
            label_text = f"{spec.label_en}\n{spec.label_ko}"
            self.create_text(
                spec.bbox[0] + 6,
                spec.bbox[1] + 6,
                text=label_text,
                font=FONTS["label"],
                fill=COLORS["text_secondary"],
                anchor="nw",
                justify="left",
            )
            value_id = self.create_text(
                spec.value_pos[0],
                spec.value_pos[1],
                text="",
                font=FONTS["value"],
                fill=COLORS["value_text"],
                anchor="nw",
            )
            self.tag_bind(rect, "<Button-1>", lambda event, s=spec: self._open_editor(s))
            self.tag_bind(value_id, "<Button-1>", lambda event, s=spec: self._open_editor(s))
            self.tag_bind(rect, "<Button-3>", lambda event, s=spec: self._show_hotspot_help(s))
            self.tag_bind(value_id, "<Button-3>", lambda event, s=spec: self._show_hotspot_help(s))
            self._hotspot_items[spec] = {"rect": rect, "value": value_id}
            self._value_labels[spec] = value_id

    # ------------------------------------------------------------------
    # User interaction
    # ------------------------------------------------------------------
    def _open_editor(self, spec: HotspotSpec) -> None:
        """Open an inline Spinbox editor for the given hotspot."""

        self._close_editor()
        current_value = self._get_numeric_value(spec)
        var = tk.StringVar(value=self._format_value(current_value, spec))
        editor = ttk.Spinbox(
            self,
            from_=spec.min_value,
            to=spec.max_value,
            increment=spec.step,
            format=f"%.{spec.decimals}f",
            textvariable=var,
            width=12,
            justify="center",
        )
        x1, y1, x2, y2 = spec.bbox
        editor.place(x=x1 + 4, y=y2 - 26, width=x2 - x1 - 8, height=22)
        editor.focus_set()

        def commit(*_args: object) -> None:
            try:
                raw_value = float(editor.get())
            except ValueError:
                self.bell()
                return
            clamped = min(max(raw_value, spec.min_value), spec.max_value)
            self._set_value(spec.path, clamped)
            self._on_change(spec.path, clamped)
            self.update_case_values()
            self._close_editor()

        def cancel(*_args: object) -> None:
            self._close_editor()

        editor.bind("<Return>", commit)
        editor.bind("<KP_Enter>", commit)
        editor.bind("<FocusOut>", commit)
        editor.bind("<Escape>", cancel)
        self._editor = editor

    def _close_editor(self) -> None:
        if self._editor is not None:
            self._editor.destroy()
            self._editor = None

    def _show_hotspot_help(self, spec: HotspotSpec) -> None:
        message = (
            f"{spec.label_en} / {spec.label_ko}\n"
            f"Range: {spec.min_value:.3f} – {spec.max_value:.3f} {spec.unit}\n"
            f"Step: {spec.step}"
        )
        messagebox.showinfo("Hotspot Info", message, parent=self)

    def _get_numeric_value(self, spec: HotspotSpec) -> float:
        value = self._get_value(spec.path)
        if isinstance(value, (int, float)):
            return float(value)
        return float(spec.min_value)

    # ------------------------------------------------------------------
    # Value and overlay updates
    # ------------------------------------------------------------------
    def update_case_values(self) -> None:
        """Refresh hotspot labels to reflect the current case data."""

        for spec, widgets in self._hotspot_items.items():
            value = self._get_value(spec.path)
            if value is None:
                text = "—"
                color = COLORS["warning_text"]
            elif isinstance(value, (int, float)):
                numeric = float(value)
                text = self._format_value(numeric, spec)
                if numeric < spec.min_value or numeric > spec.max_value:
                    color = COLORS["warning_text"]
                else:
                    color = COLORS["value_text"]
            else:
                text = str(value)
                color = COLORS["value_text"]
            self.itemconfig(widgets["value"], text=f"{text} {spec.unit}".strip())
            self.itemconfig(widgets["value"], fill=color)

    def clear_results(self) -> None:
        """Remove dynamic overlays and reset node colours."""

        for item_id in self._overlay_items:
            self.delete(item_id)
        self._overlay_items.clear()
        for name, shape_id in self._node_shapes.items():
            fill = self._default_fills.get(name, COLORS["overlay_bg"])
            self.itemconfig(shape_id, fill=fill)

    def update_results(
        self,
        result: Mapping[str, Any] | None,
        warnings: Sequence[str] | None = None,
    ) -> None:
        """Overlay solver results on the diagram."""

        self.clear_results()
        if not result:
            return

        gt = result.get("gt_block", {})
        hrsg = result.get("hrsg_block", {})
        st = result.get("st_block", {})
        condenser = result.get("condenser_block", {})
        summary = result.get("summary", {})
        mass_balance = result.get("mass_energy_balance", {})

        if not hrsg.get("converged", True):
            self.itemconfig(self._node_shapes["hrsg"], fill=COLORS["warning_fill"])
        if not mass_balance.get("converged", True):
            self.itemconfig(self._node_shapes["st_hp"], fill=COLORS["warning_fill"])
            self.itemconfig(self._node_shapes["st_ip"], fill=COLORS["warning_fill"])
            self.itemconfig(self._node_shapes["st_lp"], fill=COLORS["warning_fill"])
            self.itemconfig(self._node_shapes["condenser"], fill=COLORS["warning_fill"])

        if warnings:
            warning_text = "\n".join(warnings)
            self._overlay_items.append(
                self.create_text(
                    40,
                    420,
                    text=f"Warnings:\n{warning_text}",
                    anchor="sw",
                    fill=COLORS["warning_text"],
                    font=FONTS["overlay"],
                    justify="left",
                )
            )

        self._overlay_items.append(
            self.create_text(
                140,
                210,
                text=(
                    f"GT Power: {gt.get('electric_power_MW', 0):.1f} MW\n"
                    f"Fuel Heat: {gt.get('fuel_heat_input_MW_LHV', 0):.1f} MW\n"
                    f"Exhaust: {gt.get('exhaust', {}).get('temp_C', 0):.0f}°C"
                ),
                anchor="n",
                font=FONTS["overlay"],
                fill=COLORS["text_secondary"],
                justify="center",
            )
        )

        self._overlay_items.append(
            self.create_text(
                270,
                320,
                text=(
                    f"HP {hrsg.get('hp', {}).get('steam_flow_kg_s', 0):.1f} kg/s\n"
                    f"IP {hrsg.get('ip', {}).get('steam_flow_kg_s', 0):.1f} kg/s\n"
                    f"LP {hrsg.get('lp', {}).get('steam_flow_kg_s', 0):.1f} kg/s\n"
                    f"Stack {hrsg.get('stack_temp_C', 0):.0f}°C"
                ),
                anchor="n",
                font=FONTS["overlay"],
                fill=COLORS["text_secondary"],
                justify="center",
            )
        )

        self._overlay_items.append(
            self.create_text(
                410,
                300,
                text=(
                    f"HP {st.get('hp_section', {}).get('power_MW', 0):.1f} MW\n"
                    f"IP {st.get('ip_section', {}).get('power_MW', 0):.1f} MW\n"
                    f"LP {st.get('lp_section', {}).get('power_MW', 0):.1f} MW\n"
                    f"ST Gen: {st.get('electric_power_MW', 0):.1f} MW"
                ),
                anchor="n",
                font=FONTS["overlay"],
                fill=COLORS["text_secondary"],
                justify="center",
            )
        )

        self._overlay_items.append(
            self.create_text(
                600,
                360,
                text=(
                    f"Heat Rejected: {condenser.get('heat_rejected_MW', 0):.1f} MW\n"
                    f"CW Out: {condenser.get('cw_outlet_C', 0):.1f}°C"
                ),
                anchor="n",
                font=FONTS["overlay"],
                fill=COLORS["text_secondary"],
                justify="center",
            )
        )

        self._overlay_items.append(
            self.create_text(
                520,
                40,
                text=(
                    f"Net Power: {summary.get('NET_power_MW', 0):.1f} MW\n"
                    f"Net Eff.: {summary.get('NET_eff_LHV_pct', 0):.1f}%\n"
                    f"Closure: {mass_balance.get('closure_error_pct', 0):.2f}%"
                ),
                anchor="n",
                font=FONTS["overlay"],
                fill=COLORS["text_primary"],
                justify="center",
            )
        )

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _format_value(value: float, spec: HotspotSpec) -> str:
        return f"{value:.{spec.decimals}f}"
