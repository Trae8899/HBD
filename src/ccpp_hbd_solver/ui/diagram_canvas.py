"""Interactive diagram canvas that reacts to model events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

import tkinter as tk
from tkinter import ttk

from .events import EventBus
from .model import CaseModel, PathTuple
from .theme import Theme


@dataclass(frozen=True)
class HotspotSpec:
    path: PathTuple
    label: str
    unit: str
    rect: tuple[int, int, int, int]
    value_pos: tuple[int, int]
    min_value: float
    max_value: float
    step: float
    decimals: int


HOTSPOTS: tuple[HotspotSpec, ...] = (
    HotspotSpec(("ambient", "Ta_C"), "Ambient T", "°C", (20, 20, 200, 80), (28, 56), -20.0, 55.0, 0.5, 1),
    HotspotSpec(("ambient", "RH_pct"), "Relative Humidity", "%", (220, 20, 400, 80), (228, 56), 0.0, 100.0, 1.0, 0),
    HotspotSpec(("ambient", "P_bar"), "Ambient Pressure", "bar abs", (420, 20, 600, 80), (428, 56), 0.8, 1.1, 0.01, 3),
    HotspotSpec(("gas_turbine", "ISO_power_MW"), "GT ISO Power", "MW", (20, 120, 180, 180), (28, 156), 50.0, 600.0, 1.0, 0),
    HotspotSpec(("gas_turbine", "ISO_heat_rate_kJ_per_kWh"), "ISO Heat Rate", "kJ/kWh", (20, 190, 180, 250), (28, 226), 8000.0, 12000.0, 10.0, 0),
    HotspotSpec(("gas_turbine", "fuel_LHV_kJ_per_kg"), "Fuel LHV", "kJ/kg", (20, 260, 180, 320), (28, 296), 38000.0, 52000.0, 25.0, 0),
    HotspotSpec(("gas_turbine", "ISO_exhaust_temp_C"), "ISO Exhaust T", "°C", (20, 330, 180, 390), (28, 366), 450.0, 700.0, 1.0, 0),
    HotspotSpec(("gas_turbine", "ISO_exhaust_flow_kg_s"), "ISO Exhaust Flow", "kg/s", (200, 120, 360, 180), (208, 156), 200.0, 900.0, 5.0, 0),
    HotspotSpec(("gas_turbine", "corr_coeff", "dPower_pct_per_K"), "ΔPower", "%/K", (200, 190, 360, 250), (208, 226), -1.0, 0.0, 0.01, 2),
    HotspotSpec(("gas_turbine", "corr_coeff", "dFlow_pct_per_K"), "ΔFlow", "%/K", (200, 260, 360, 320), (208, 296), 0.0, 1.0, 0.01, 2),
    HotspotSpec(("gas_turbine", "corr_coeff", "dExhT_K_per_K"), "ΔExhaust T", "K/K", (200, 330, 360, 390), (208, 366), 0.0, 2.0, 0.05, 2),
    HotspotSpec(("hrsg", "hp", "pressure_bar"), "HP Pressure", "bar abs", (380, 120, 540, 170), (388, 152), 60.0, 160.0, 1.0, 0),
    HotspotSpec(("hrsg", "hp", "steam_temp_C"), "HP Steam T", "°C", (380, 176, 540, 226), (388, 208), 450.0, 600.0, 1.0, 0),
    HotspotSpec(("hrsg", "hp", "pinch_K"), "HP Pinch", "K", (380, 232, 540, 282), (388, 264), 5.0, 20.0, 0.5, 1),
    HotspotSpec(("hrsg", "hp", "approach_K"), "HP Approach", "K", (380, 288, 540, 338), (388, 320), 3.0, 15.0, 0.5, 1),
    HotspotSpec(("hrsg", "ip", "pressure_bar"), "IP Pressure", "bar abs", (560, 120, 720, 170), (568, 152), 15.0, 60.0, 1.0, 0),
    HotspotSpec(("hrsg", "ip", "steam_temp_C"), "IP Steam T", "°C", (560, 176, 720, 226), (568, 208), 400.0, 600.0, 1.0, 0),
    HotspotSpec(("hrsg", "ip", "pinch_K"), "IP Pinch", "K", (560, 232, 720, 282), (568, 264), 8.0, 20.0, 0.5, 1),
    HotspotSpec(("hrsg", "ip", "approach_K"), "IP Approach", "K", (560, 288, 720, 338), (568, 320), 4.0, 15.0, 0.5, 1),
    HotspotSpec(("hrsg", "lp", "pressure_bar"), "LP Pressure", "bar abs", (740, 120, 900, 170), (748, 152), 1.0, 15.0, 0.5, 1),
    HotspotSpec(("hrsg", "lp", "steam_temp_C"), "LP Steam T", "°C", (740, 176, 900, 226), (748, 208), 150.0, 350.0, 1.0, 0),
    HotspotSpec(("hrsg", "lp", "pinch_K"), "LP Pinch", "K", (740, 232, 900, 282), (748, 264), 10.0, 25.0, 0.5, 1),
    HotspotSpec(("hrsg", "lp", "approach_K"), "LP Approach", "K", (740, 288, 900, 338), (748, 320), 5.0, 15.0, 0.5, 1),
    HotspotSpec(("hrsg", "stack_temp_min_C"), "Stack Min T", "°C", (920, 200, 1080, 260), (928, 236), 70.0, 130.0, 1.0, 0),
    HotspotSpec(("steam_turbine", "isentropic_eff_hp"), "HP η", "η", (380, 360, 480, 410), (388, 392), 0.75, 0.92, 0.005, 3),
    HotspotSpec(("steam_turbine", "isentropic_eff_ip"), "IP η", "η", (490, 360, 590, 410), (498, 392), 0.75, 0.92, 0.005, 3),
    HotspotSpec(("steam_turbine", "isentropic_eff_lp"), "LP η", "η", (600, 360, 700, 410), (608, 392), 0.75, 0.90, 0.005, 3),
    HotspotSpec(("steam_turbine", "mech_elec_eff"), "Mech/Gen η", "η", (710, 360, 840, 410), (718, 392), 0.95, 0.995, 0.001, 3),
    HotspotSpec(("condenser", "vacuum_kPa_abs"), "Condenser Vacuum", "kPa abs", (900, 320, 1080, 370), (908, 352), 4.0, 15.0, 0.1, 2),
    HotspotSpec(("condenser", "cw_inlet_C"), "CW Inlet", "°C", (900, 372, 1080, 422), (908, 404), 5.0, 35.0, 0.5, 1),
    HotspotSpec(("bop", "aux_load_MW"), "Aux Load", "MW", (900, 120, 1080, 170), (908, 152), 0.0, 50.0, 0.5, 1),
)


WARNING_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("HRSG", "hrsg"),
    ("PINCH", "hrsg"),
    ("STACK", "hrsg"),
    ("ATTEMP", "hrsg"),
    ("GT", "gt"),
    ("TURBINE", "st"),
    ("STEAM", "st"),
    ("COND", "condenser"),
    ("CLOSURE", "condenser"),
)


def _severity_from_warning(message: str) -> str:
    upper = message.upper()
    if upper.startswith("E-") or "VIOLATION" in upper or "NONCONVERGED" in upper or "CLOSURE" in upper:
        return "critical"
    if "LIMIT" in upper:
        return "critical"
    return "warning"


def _node_from_warning(message: str) -> str | None:
    upper = message.upper()
    for keyword, node in WARNING_KEYWORDS:
        if keyword in upper:
            return node
    return None


class DiagramCanvas(tk.Canvas):
    """Canvas widget responsible only for rendering and interaction."""

    def __init__(self, master: tk.Widget, *, model: CaseModel, bus: EventBus, theme: Theme) -> None:
        super().__init__(
            master,
            width=theme.metrics.canvas_width,
            height=theme.metrics.canvas_height,
            background=theme.palette.canvas_bg,
            highlightthickness=0,
        )
        self.model = model
        self.bus = bus
        self.theme = theme

        self._editor: ttk.Spinbox | None = None
        self._editor_window_id: int | None = None
        self._subscriptions: list[Callable[[], None]] = []
        self._value_items: dict[PathTuple, int] = {}
        self._hotspot_rects: dict[PathTuple, int] = {}
        self._hotspot_labels: dict[PathTuple, int] = {}
        self._overlay_items: list[int] = []
        self._node_shapes: dict[str, int] = {}
        self._focused_index: int | None = None
        self._scale_factor = 1.0
        self._panning = False
        self._progress_item: int | None = None

        self._draw_static_elements()
        self._create_hotspots()
        self._register_events()
        self._refresh_all_values()

    # ------------------------------------------------------------------
    # Event bus bindings
    # ------------------------------------------------------------------
    def _register_events(self) -> None:
        self._subscriptions.append(self.bus.subscribe("case_loaded", self._on_case_loaded))
        self._subscriptions.append(self.bus.subscribe("value_changed", self._on_value_changed))
        self._subscriptions.append(self.bus.subscribe("result_updated", self._on_result_updated))
        self._subscriptions.append(self.bus.subscribe("result_cleared", self._on_result_cleared))
        self._subscriptions.append(self.bus.subscribe("progress", self._on_progress))

        self.bind("<Button-1>", self._on_primary_click)
        self.bind("<Double-Button-1>", self._on_activate_hotspot)
        self.bind("<KeyPress-Tab>", self._on_focus_next)
        self.bind("<Shift-Tab>", self._on_focus_prev)
        self.bind("<KeyPress-Return>", self._on_focus_activate)
        self.bind("<KeyPress-space>", self._on_space_press)
        self.bind("<KeyRelease-space>", self._on_space_release)
        self.bind("<ButtonPress-1>", self._on_button_press, add=True)
        self.bind("<B1-Motion>", self._on_mouse_drag)
        self.bind("<ButtonRelease-1>", self._on_button_release)
        self.bind("<Control-MouseWheel>", self._on_zoom)
        self.bind("<Control-Button-4>", self._on_zoom_button)
        self.bind("<Control-Button-5>", self._on_zoom_button)

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    def _draw_static_elements(self) -> None:
        palette = self.theme.palette
        metrics = self.theme.metrics
        outline = palette.block_outline

        self._node_shapes["gt"] = self.create_rectangle(80, 130, 200, 210, fill=palette.gt_fill, outline=outline, width=metrics.block_outline_width)
        self._node_shapes["hrsg"] = self.create_rectangle(220, 90, 320, 310, fill=palette.hrsg_fill, outline=outline, width=metrics.block_outline_width)
        self._node_shapes["st_hp"] = self.create_rectangle(360, 110, 460, 160, fill=palette.st_fill, outline=outline, width=metrics.block_outline_width)
        self._node_shapes["st_ip"] = self.create_rectangle(360, 180, 460, 230, fill=palette.st_fill, outline=outline, width=metrics.block_outline_width)
        self._node_shapes["st_lp"] = self.create_rectangle(360, 250, 460, 300, fill=palette.st_fill, outline=outline, width=metrics.block_outline_width)
        self._node_shapes["condenser"] = self.create_rectangle(520, 280, 680, 360, fill=palette.cond_fill, outline=outline, width=metrics.block_outline_width)

        # Arrows and connectors
        stream_width = metrics.stream_width
        self.create_line(140, 170, 220, 170, arrow=tk.LAST, fill=outline, width=stream_width)
        self.create_line(320, 170, 360, 170, arrow=tk.LAST, fill=outline, width=stream_width)
        self.create_line(460, 170, 520, 170, arrow=tk.LAST, fill=outline, width=stream_width)
        self.create_line(520, 260, 680, 300, arrow=tk.LAST, fill=outline, width=stream_width)

        font_label = self.theme.fonts.label
        self.create_text(140, 115, text="Gas Turbine", font=font_label, fill=palette.text_primary)
        self.create_text(270, 80, text="HRSG", font=font_label, fill=palette.text_primary)
        self.create_text(410, 100, text="Steam Turbine", font=font_label, fill=palette.text_primary)
        self.create_text(600, 270, text="Condenser", font=font_label, fill=palette.text_primary)

    def _create_hotspots(self) -> None:
        palette = self.theme.palette
        metrics = self.theme.metrics
        for spec in HOTSPOTS:
            rect_id = self.create_rectangle(
                *spec.rect,
                outline=palette.hotspot_border,
                width=metrics.hotspot_border_width,
                fill=palette.hotspot_bg,
            )
            label_id = self.create_text(spec.rect[0] + 4, spec.rect[1] + 12, text=spec.label, anchor="w", font=self.theme.fonts.label, fill=palette.text_primary)
            value_id = self.create_text(spec.value_pos[0], spec.value_pos[1], anchor="w", font=self.theme.fonts.value, fill=palette.value_text)

            self._hotspot_rects[spec.path] = rect_id
            self._hotspot_labels[spec.path] = label_id
            self._value_items[spec.path] = value_id

            self.tag_bind(rect_id, "<Enter>", lambda _e, r=rect_id: self.itemconfig(r, outline=palette.block_outline))
            self.tag_bind(rect_id, "<Leave>", lambda _e, r=rect_id: self._reset_hotspot_outline(r))
            self.tag_bind(rect_id, "<Button-1>", lambda e, s=spec: self._focus_spec(s))
            self.tag_bind(rect_id, "<Double-Button-1>", lambda _e, s=spec: self._open_editor(s))
            self.tag_bind(label_id, "<Button-1>", lambda e, s=spec: self._focus_spec(s))
            self.tag_bind(value_id, "<Button-1>", lambda e, s=spec: self._focus_spec(s))

    # ------------------------------------------------------------------
    # Value updates
    # ------------------------------------------------------------------
    def _refresh_all_values(self) -> None:
        for spec in HOTSPOTS:
            self._update_value_text(spec)

    def _update_value_text(self, spec: HotspotSpec) -> None:
        value = self.model.get_value(spec.path)
        text = "—"
        fill = self.theme.palette.value_text
        if isinstance(value, (int, float)):
            text = f"{float(value):.{spec.decimals}f}" if spec.decimals else f"{int(round(float(value)))}"
            if spec.decimals:
                text = text.rstrip("0").rstrip(".")
            if float(value) < spec.min_value or float(value) > spec.max_value:
                fill = self.theme.palette.warning_outline
        elif value is not None:
            text = str(value)
        self.itemconfig(self._value_items[spec.path], text=f"{text} {spec.unit}".strip(), fill=fill)

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------
    def _focus_spec(self, spec: HotspotSpec) -> None:
        self.focus_set()
        if self._focused_index is not None:
            prev_spec = HOTSPOTS[self._focused_index]
            self._reset_hotspot_outline(self._hotspot_rects[prev_spec.path])
        self._focused_index = HOTSPOTS.index(spec)
        self.itemconfig(self._hotspot_rects[spec.path], outline=self.theme.palette.value_text)

    def _reset_hotspot_outline(self, rect_id: int) -> None:
        if self._focused_index is not None and self._hotspot_rects.get(HOTSPOTS[self._focused_index].path) == rect_id:
            return
        self.itemconfig(rect_id, outline=self.theme.palette.hotspot_border)

    def _open_editor(self, spec: HotspotSpec) -> None:
        self._focus_spec(spec)
        if self._editor is not None:
            self._destroy_editor()
        current = self.model.get_value(spec.path)
        value = float(current) if isinstance(current, (int, float)) else spec.min_value
        var = tk.DoubleVar(value=value)

        def _commit() -> None:
            try:
                new_value = float(var.get())
            except (TypeError, tk.TclError):
                return
            new_value = max(spec.min_value, min(spec.max_value, new_value))
            self.model.set_value(spec.path, round(new_value, spec.decimals) if spec.decimals else float(new_value))
            self._destroy_editor()

        bbox = self.bbox(self._hotspot_rects[spec.path])
        if not bbox:
            return
        x = (bbox[0] + bbox[2]) / 2
        y = bbox[1] - 24
        editor = ttk.Spinbox(
            self,
            from_=spec.min_value,
            to=spec.max_value,
            increment=spec.step,
            textvariable=var,
            width=8,
        )
        editor.bind("<Return>", lambda _e: _commit())
        editor.bind("<Escape>", lambda _e: self._destroy_editor())
        editor.bind("<FocusOut>", lambda _e: _commit())

        window_id = self.create_window(x, y, window=editor, anchor="s")
        self._editor = editor
        self._editor_window_id = window_id
        editor.focus_set()

    def _destroy_editor(self) -> None:
        if self._editor is not None:
            self._editor.destroy()
            self._editor = None
        if self._editor_window_id is not None:
            self.delete(self._editor_window_id)
            self._editor_window_id = None

    # ------------------------------------------------------------------
    # Warning overlays
    # ------------------------------------------------------------------
    def _clear_overlays(self) -> None:
        for item in self._overlay_items:
            self.delete(item)
        self._overlay_items.clear()
        if self._progress_item is not None:
            self.delete(self._progress_item)
            self._progress_item = None
        palette = self.theme.palette
        self.itemconfig(self._node_shapes["gt"], outline=palette.block_outline, fill=palette.gt_fill)
        self.itemconfig(self._node_shapes["hrsg"], outline=palette.block_outline, fill=palette.hrsg_fill)
        for node in ("st_hp", "st_ip", "st_lp"):
            self.itemconfig(self._node_shapes[node], outline=palette.block_outline, fill=palette.st_fill)
        self.itemconfig(self._node_shapes["condenser"], outline=palette.block_outline, fill=palette.cond_fill)

    def _render_results(self, result: dict[str, Any], warnings: Iterable[str]) -> None:
        self._clear_overlays()
        palette = self.theme.palette
        fonts = self.theme.fonts

        gt = result.get("gt_block", {})
        hrsg = result.get("hrsg_block", {})
        st = result.get("st_block", {})
        condenser = result.get("condenser_block", {})
        summary = result.get("summary", {})
        mass_balance = result.get("mass_energy_balance", {})

        if not hrsg.get("converged", True):
            self.itemconfig(self._node_shapes["hrsg"], outline=palette.critical_outline, fill=palette.critical_fill)
        if not mass_balance.get("converged", True):
            for node in ("st_hp", "st_ip", "st_lp", "condenser"):
                self.itemconfig(self._node_shapes[node], outline=palette.critical_outline, fill=palette.critical_fill)

        warning_messages = list(warnings)
        for message in warning_messages:
            severity = _severity_from_warning(message)
            node = _node_from_warning(message)
            color_outline = palette.critical_outline if severity == "critical" else palette.warning_outline
            color_fill = palette.critical_fill if severity == "critical" else palette.warning_fill
            if node == "gt":
                self.itemconfig(self._node_shapes["gt"], outline=color_outline, fill=color_fill)
            elif node == "hrsg":
                self.itemconfig(self._node_shapes["hrsg"], outline=color_outline, fill=color_fill)
            elif node == "st":
                for target in ("st_hp", "st_ip", "st_lp"):
                    self.itemconfig(self._node_shapes[target], outline=color_outline, fill=color_fill)
            elif node == "condenser":
                self.itemconfig(self._node_shapes["condenser"], outline=color_outline, fill=color_fill)

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
                font=fonts.overlay,
                fill=palette.text_secondary,
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
                font=fonts.overlay,
                fill=palette.text_secondary,
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
                font=fonts.overlay,
                fill=palette.text_secondary,
                justify="center",
            )
        )

        self._overlay_items.append(
            self.create_text(
                600,
                360,
                text=(
                    f"Condenser Q: {condenser.get('heat_rejection_MW', 0):.1f} MW\n"
                    f"Vacuum: {condenser.get('vacuum_kPa_abs', 0):.2f} kPa\n"
                    f"NET MW: {summary.get('NET_power_MW', 0):.1f}"
                ),
                anchor="n",
                font=fonts.overlay,
                fill=palette.text_secondary,
                justify="center",
            )
        )

        if warning_messages:
            combined = "\n".join(f"• {msg}" for msg in warning_messages)
            color = palette.critical_outline if any(_severity_from_warning(m) == "critical" for m in warning_messages) else palette.warning_outline
            self._overlay_items.append(
                self.create_text(
                    40,
                    420,
                    text=f"Warnings:\n{combined}",
                    anchor="sw",
                    font=fonts.overlay,
                    fill=color,
                    justify="left",
                )
            )

    # ------------------------------------------------------------------
    # Zoom & pan
    # ------------------------------------------------------------------
    def _on_zoom(self, event: tk.Event) -> None:
        factor = 1.1 if event.delta > 0 else 0.9
        self._apply_zoom(event.x, event.y, factor)

    def _on_zoom_button(self, event: tk.Event) -> None:
        factor = 1.1 if event.num == 4 else 0.9
        self._apply_zoom(event.x, event.y, factor)

    def _apply_zoom(self, x: float, y: float, factor: float) -> None:
        new_scale = self._scale_factor * factor
        if new_scale < 0.6 or new_scale > 1.8:
            return
        self.scale("all", x, y, factor, factor)
        self._scale_factor = new_scale
        if self._editor is not None:
            self._destroy_editor()

    def _on_space_press(self, _event: tk.Event) -> None:
        self._panning = True

    def _on_space_release(self, _event: tk.Event) -> None:
        self._panning = False

    def _on_button_press(self, event: tk.Event) -> None:
        if self._panning:
            self.scan_mark(event.x, event.y)

    def _on_mouse_drag(self, event: tk.Event) -> None:
        if self._panning:
            self.scan_dragto(event.x, event.y, gain=1)

    def _on_button_release(self, _event: tk.Event) -> None:
        pass

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _on_primary_click(self, event: tk.Event) -> None:
        self.focus_set()
        item = self.find_withtag("current")
        if not item:
            return
        for spec in HOTSPOTS:
            if self._hotspot_rects[spec.path] == item[0] or self._hotspot_labels[spec.path] == item[0] or self._value_items[spec.path] == item[0]:
                self._focus_spec(spec)
                break

    def _on_activate_hotspot(self, _event: tk.Event) -> None:
        if self._focused_index is None:
            return
        self._open_editor(HOTSPOTS[self._focused_index])

    def _on_focus_next(self, event: tk.Event) -> str:
        if self._focused_index is None:
            self._focus_spec(HOTSPOTS[0])
        else:
            next_index = (self._focused_index + 1) % len(HOTSPOTS)
            self._focus_spec(HOTSPOTS[next_index])
        return "break"

    def _on_focus_prev(self, event: tk.Event) -> str:
        if self._focused_index is None:
            self._focus_spec(HOTSPOTS[-1])
        else:
            prev_index = (self._focused_index - 1) % len(HOTSPOTS)
            self._focus_spec(HOTSPOTS[prev_index])
        return "break"

    def _on_focus_activate(self, _event: tk.Event) -> str:
        if self._focused_index is not None:
            self._open_editor(HOTSPOTS[self._focused_index])
        return "break"

    def _on_case_loaded(self, case: dict[str, Any], **_: Any) -> None:
        self._refresh_all_values()
        self._destroy_editor()

    def _on_value_changed(self, path: PathTuple, **_: Any) -> None:
        for spec in HOTSPOTS:
            if spec.path == path:
                self._update_value_text(spec)
                break

    def _on_result_updated(self, result: dict[str, Any], warnings: Iterable[str], **_: Any) -> None:
        self._render_results(result, warnings)

    def _on_result_cleared(self, **_: Any) -> None:
        self._clear_overlays()

    def _on_progress(self, step: str | None, value: float, **_: Any) -> None:
        if self._progress_item is not None:
            self.delete(self._progress_item)
            self._progress_item = None
        if step is None:
            return
        progress_text = f"{step}: {int(value * 100)}%"
        self._progress_item = self.create_text(
            1040,
            440,
            text=progress_text,
            anchor="se",
            font=self.theme.fonts.overlay,
            fill=self.theme.palette.text_secondary,
        )

    # ------------------------------------------------------------------
    # Theme updates
    # ------------------------------------------------------------------
    def apply_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.configure(background=theme.palette.canvas_bg)
        self._clear_overlays()
        for node, shape in self._node_shapes.items():
            fill = {
                "gt": theme.palette.gt_fill,
                "hrsg": theme.palette.hrsg_fill,
                "st_hp": theme.palette.st_fill,
                "st_ip": theme.palette.st_fill,
                "st_lp": theme.palette.st_fill,
                "condenser": theme.palette.cond_fill,
            }[node]
            self.itemconfig(shape, fill=fill, outline=theme.palette.block_outline, width=theme.metrics.block_outline_width)
        for spec in HOTSPOTS:
            rect_id = self._hotspot_rects[spec.path]
            self.itemconfig(rect_id, fill=theme.palette.hotspot_bg, outline=theme.palette.hotspot_border, width=theme.metrics.hotspot_border_width)
            self.itemconfig(self._hotspot_labels[spec.path], fill=theme.palette.text_primary, font=theme.fonts.label)
            self.itemconfig(self._value_items[spec.path], fill=theme.palette.value_text, font=theme.fonts.value)
        self._refresh_all_values()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def destroy(self) -> None:  # pragma: no cover - Tkinter shutdown path
        for unsubscribe in self._subscriptions:
            try:
                unsubscribe()
            except Exception:
                continue
        self._subscriptions.clear()
        self._destroy_editor()
        super().destroy()


__all__ = ["DiagramCanvas", "HOTSPOTS", "HotspotSpec"]
