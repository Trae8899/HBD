"""Tkinter-based desktop GUI for the CCPP HBD solver."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Sequence, cast

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..pipeline import (
    PipelineArtifacts,
    load_defaults,
    merge_case_with_defaults,
    run_pipeline,
)
from ..reporter.console_reporter import export_calculation_log
from ..reporter.diagram_svg import export_flow_diagram
from ..reporter.excel_reporter import export_summary_to_excel


@dataclass(frozen=True)
class FieldItem:
    """Representation of a single input field in the GUI."""

    path: Sequence[str]
    label: str
    field_type: str = "float"
    help_text: str | None = None


@dataclass(frozen=True)
class SectionItem:
    """Marker for grouping fields inside a tab."""

    title: str


INPUT_LAYOUT: Dict[str, Sequence[FieldItem | SectionItem]] = {
    "Ambient": (
        FieldItem(
            ("ambient", "Ta_C"),
            "Dry-bulb temperature (°C)",
            help_text="외기 건구 온도. 사이트 설계 조건을 섭씨 온도로 입력합니다.",
        ),
        FieldItem(
            ("ambient", "RH_pct"),
            "Relative humidity (%)",
            help_text="외기 상대습도. 0~100% 범위의 값을 입력합니다.",
        ),
        FieldItem(
            ("ambient", "P_bar"),
            "Ambient pressure (bar abs)",
            help_text="현장 대기압. 절대압(bar abs) 기준으로 입력합니다.",
        ),
    ),
    "Gas Turbine": (
        FieldItem(
            ("gas_turbine", "model"),
            "GT model",
            field_type="str",
            help_text="가스터빈 기기 모델명 또는 구분자입니다.",
        ),
        FieldItem(
            ("gas_turbine", "ISO_power_MW"),
            "ISO gross power (MW)",
            help_text="ISO 조건(15°C, 60%RH, 1.013 bar)에서의 정격 발전기출력(MW).",
        ),
        FieldItem(
            ("gas_turbine", "ISO_heat_rate_kJ_per_kWh"),
            "ISO heat rate (kJ/kWh)",
            help_text="ISO 조건에서의 열소비율(저위발열량 기준 kJ/kWh).", 
        ),
        FieldItem(
            ("gas_turbine", "fuel_LHV_kJ_per_kg"),
            "Fuel LHV (kJ/kg)",
            help_text="연료 저위발열량(LHV). 천연가스의 경우 약 48,000~50,000 kJ/kg 입니다.",
        ),
        FieldItem(
            ("gas_turbine", "ISO_exhaust_temp_C"),
            "ISO exhaust temp (°C)",
            help_text="ISO 조건에서 측정된 배기가스 온도.",
        ),
        FieldItem(
            ("gas_turbine", "ISO_exhaust_flow_kg_s"),
            "ISO exhaust flow (kg/s)",
            help_text="ISO 조건에서 배기가스 질량유량(kg/s).",
        ),
        SectionItem("Temperature correction"),
        FieldItem(
            ("gas_turbine", "corr_coeff", "dPower_pct_per_K"),
            "ΔPower (%/K)",
            help_text="외기 온도 변화 1K 당 전기출력 변화율(%).",
        ),
        FieldItem(
            ("gas_turbine", "corr_coeff", "dFlow_pct_per_K"),
            "ΔFlow (%/K)",
            help_text="외기 온도 변화 1K 당 배기가스 유량 변화율(%).",
        ),
        FieldItem(
            ("gas_turbine", "corr_coeff", "dExhT_K_per_K"),
            "ΔExhaust temp (K/K)",
            help_text="외기 온도 변화 1K 당 배기가스 온도 변화량(K).",
        ),
    ),
    "HRSG": (
        SectionItem("High pressure level"),
        FieldItem(
            ("hrsg", "hp", "pressure_bar"),
            "HP pressure (bar abs)",
            help_text="HP 증기 드럼 압력 또는 터빈 입구 압력(bar abs).",
        ),
        FieldItem(
            ("hrsg", "hp", "steam_temp_C"),
            "HP steam temp (°C)",
            help_text="HP 증기 과열온도(°C).",
        ),
        FieldItem(
            ("hrsg", "hp", "pinch_K"),
            "HP pinch (K)",
            help_text="HP 증발부 pinch temperature difference(K).",
        ),
        FieldItem(
            ("hrsg", "hp", "approach_K"),
            "HP approach (K)",
            help_text="HP 드럼 급수온도와 포화온도 간 온도차(approach).",
        ),
        SectionItem("Intermediate pressure level"),
        FieldItem(
            ("hrsg", "ip", "pressure_bar"),
            "IP pressure (bar abs)",
            help_text="IP 증기 압력(bar abs).",
        ),
        FieldItem(
            ("hrsg", "ip", "steam_temp_C"),
            "IP steam temp (°C)",
            help_text="IP 증기 과열온도(°C).",
        ),
        FieldItem(
            ("hrsg", "ip", "pinch_K"),
            "IP pinch (K)",
            help_text="IP 증발부 pinch temperature difference(K).",
        ),
        FieldItem(
            ("hrsg", "ip", "approach_K"),
            "IP approach (K)",
            help_text="IP 드럼 approach temperature difference(K).",
        ),
        SectionItem("Low pressure level"),
        FieldItem(
            ("hrsg", "lp", "pressure_bar"),
            "LP pressure (bar abs)",
            help_text="LP 증기 압력(bar abs).",
        ),
        FieldItem(
            ("hrsg", "lp", "steam_temp_C"),
            "LP steam temp (°C)",
            help_text="LP 증기 과열온도(°C).",
        ),
        FieldItem(
            ("hrsg", "lp", "pinch_K"),
            "LP pinch (K)",
            help_text="LP 증발부 pinch temperature difference(K).",
        ),
        FieldItem(
            ("hrsg", "lp", "approach_K"),
            "LP approach (K)",
            help_text="LP 드럼 approach temperature difference(K).",
        ),
        FieldItem(
            ("hrsg", "stack_temp_min_C"),
            "Minimum stack temp (°C)",
            help_text="굴뚝 배출 최소 허용온도. 이 값 이하로 떨어지면 경보를 발생합니다.",
        ),
    ),
    "Steam Turbine": (
        FieldItem(
            ("steam_turbine", "isentropic_eff_hp"),
            "HP isentropic efficiency",
            help_text="HP 터빈 단 등엔트로피 효율(0~1).",
        ),
        FieldItem(
            ("steam_turbine", "isentropic_eff_ip"),
            "IP isentropic efficiency",
            help_text="IP 터빈 단 등엔트로피 효율(0~1).",
        ),
        FieldItem(
            ("steam_turbine", "isentropic_eff_lp"),
            "LP isentropic efficiency",
            help_text="LP 터빈 단 등엔트로피 효율(0~1).",
        ),
        FieldItem(
            ("steam_turbine", "mech_elec_eff"),
            "Mechanical & generator efficiency",
            help_text="증기터빈 축에서 발전기까지의 기계 및 전기 효율.",
        ),
    ),
    "Condenser": (
        FieldItem(
            ("condenser", "vacuum_kPa_abs"),
            "Condenser vacuum (kPa abs)",
            help_text="복수기 내부 진공 절대압(kPa abs).",
        ),
        FieldItem(
            ("condenser", "cw_inlet_C"),
            "Cooling water inlet (°C)",
            help_text="복수기 순환수 입구온도(°C).",
        ),
    ),
    "Balance of Plant": (
        FieldItem(
            ("bop", "aux_load_MW"),
            "Auxiliary load (MW)",
            help_text="발전소 자체 사용 전력(AUX load) 추정치(MW).",
        ),
    ),
}


def _format_float(value: float) -> str:
    """Render numeric values in a compact human-friendly format."""

    return f"{value:.6g}"


class HBDGuiApp:
    """Main application window for the desktop solver interface."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CCPP HBD Solver")
        self.root.minsize(1100, 700)

        self.style = ttk.Style()
        self.style.configure("Section.TLabel", font=("TkDefaultFont", 10, "bold"))
        self.style.configure("Help.TLabel", font=("TkDefaultFont", 9), foreground="#555555")

        self.defaults = load_defaults()
        self.current_case_path: Path | None = None
        self.current_artifacts: PipelineArtifacts | None = None
        self.case_name_var = tk.StringVar(value="gui_case")
        self.status_var = tk.StringVar(value="Load a case or edit the defaults to get started.")

        self.field_vars: Dict[str, tk.StringVar] = {}
        self.field_types: Dict[str, str] = {}
        self.field_paths: Dict[str, Sequence[str]] = {}

        self._build_layout()
        self._load_initial_case()

    # ------------------------------------------------------------------
    # Layout construction
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)

        input_container = ttk.Frame(paned, padding=10)
        output_container = ttk.Frame(paned, padding=10)
        paned.add(input_container, weight=1)
        paned.add(output_container, weight=2)

        self._build_input_panel(input_container)
        self._build_output_panel(output_container)

        status_bar = ttk.Label(self.root, textvariable=self.status_var, anchor="w")
        status_bar.pack(fill="x", side=tk.BOTTOM)

    def _build_input_panel(self, container: ttk.Frame) -> None:
        controls = ttk.Frame(container)
        controls.pack(fill="x", pady=(0, 8))

        ttk.Label(controls, text="Case name:").grid(row=0, column=0, padx=(0, 6))
        case_entry = ttk.Entry(controls, textvariable=self.case_name_var, width=20)
        case_entry.grid(row=0, column=1, sticky="we", padx=(0, 12))

        ttk.Button(controls, text="Load case…", command=self._prompt_open_case).grid(row=0, column=2, padx=2)
        ttk.Button(controls, text="Save case as…", command=self._prompt_save_case).grid(row=0, column=3, padx=2)
        ttk.Button(controls, text="Reset", command=self._reset_fields).grid(row=0, column=4, padx=2)
        ttk.Button(controls, text="Run solver", command=self._run_solver).grid(row=0, column=5, padx=2)
        ttk.Button(controls, text="Export reports", command=self._export_reports).grid(row=0, column=6, padx=(10, 0))

        controls.columnconfigure(1, weight=1)

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)

        for tab_name, items in INPUT_LAYOUT.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=tab_name)
            frame.columnconfigure(1, weight=1)
            row = 0
            for item in items:
                if isinstance(item, SectionItem):
                    label = ttk.Label(frame, text=item.title, style="Section.TLabel")
                    label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 2))
                    row += 1
                    continue

                key = ".".join(item.path)
                label = ttk.Label(frame, text=item.label)
                label.grid(row=row, column=0, sticky="w", pady=(6, 0), padx=(0, 6))

                var = tk.StringVar()
                width = 28 if item.field_type == "str" else 18
                entry = ttk.Entry(frame, textvariable=var, width=width)
                entry.grid(row=row, column=1, sticky="we", pady=(6, 0))

                self.field_vars[key] = var
                self.field_types[key] = item.field_type
                self.field_paths[key] = item.path
                row += 1

                if item.help_text:
                    help_label = ttk.Label(
                        frame,
                        text=item.help_text,
                        style="Help.TLabel",
                        wraplength=320,
                        justify="left",
                    )
                    help_label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 6))
                    row += 1

    def _build_output_panel(self, container: ttk.Frame) -> None:
        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)
        self.output_notebook = notebook

        self.case_tree = self._create_tree_tab("Case input")
        self.summary_tree = self._create_tree_tab("Summary")
        self.gt_tree = self._create_tree_tab("Gas turbine")
        self.hrsg_tree = self._create_tree_tab("HRSG")
        self.st_tree = self._create_tree_tab("Steam turbine")
        self.cond_tree = self._create_tree_tab("Condenser")
        self.balance_tree = self._create_tree_tab("Mass & energy balance")
        self.trace_text = self._create_text_tab("Calculation trace")

    def _create_tree_tab(self, title: str) -> ttk.Treeview:
        frame = ttk.Frame(self.output_notebook)
        self.output_notebook.add(frame, text=title)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        tree = ttk.Treeview(frame, columns=("value",), show="tree headings")
        tree.heading("#0", text="Field", anchor="w")
        tree.heading("value", text="Value", anchor="w")
        tree.column("#0", width=260, anchor="w")
        tree.column("value", width=260, anchor="w")

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        return tree

    def _create_text_tab(self, title: str) -> tk.Text:
        frame = ttk.Frame(self.output_notebook)
        self.output_notebook.add(frame, text=title)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        text_widget = tk.Text(frame, wrap="none")
        text_widget.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=yscroll.set)
        yscroll.grid(row=0, column=1, sticky="ns")
        return text_widget

    # ------------------------------------------------------------------
    # Case management helpers
    # ------------------------------------------------------------------
    def _load_initial_case(self) -> None:
        sample_path = Path("data/plant_case_summer_35C.json")
        if sample_path.exists():
            case_data = self._read_case(sample_path)
            self.current_case_path = sample_path
            self.case_name_var.set(sample_path.stem)
            self.status_var.set(f"Loaded sample case '{sample_path.name}'.")
        else:
            case_data = {}
            self.status_var.set("Defaults loaded. Provide the missing inputs before running the solver.")
        merged = merge_case_with_defaults(case_data, self.defaults)
        self._apply_case_to_fields(merged)
        self._populate_tree(self.case_tree, merged)

    def _read_case(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _apply_case_to_fields(self, case_data: Mapping[str, Any]) -> None:
        for key, path in self.field_paths.items():
            value = self._lookup_path(case_data, path)
            var = self.field_vars[key]
            if value is None:
                var.set("")
                continue
            if self.field_types[key] == "float":
                try:
                    var.set(_format_float(float(value)))
                except (TypeError, ValueError):
                    var.set(str(value))
            else:
                var.set(str(value))

    def _lookup_path(self, data: Mapping[str, Any], path: Sequence[str]) -> Any:
        current: Any = data
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                return None
            current = current[key]
        return current

    def _reset_fields(self) -> None:
        base_case = merge_case_with_defaults({}, self.defaults)
        self._apply_case_to_fields(base_case)
        self.case_name_var.set("gui_case")
        self.current_case_path = None
        self.status_var.set("Inputs reset to repository defaults.")
        self._populate_tree(self.case_tree, base_case)
        self.current_artifacts = None
        self._clear_output_views()

    def _prompt_open_case(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Open HBD case", filetypes=[("JSON files", "*.json"), ("All files", "*")]
        )
        if not file_path:
            return
        path = Path(file_path)
        case_data = self._read_case(path)
        merged = merge_case_with_defaults(case_data, self.defaults)
        self.current_case_path = path
        self.case_name_var.set(path.stem)
        self._apply_case_to_fields(merged)
        self._populate_tree(self.case_tree, merged)
        self.status_var.set(f"Case '{path.name}' loaded. Adjust values and run the solver.")
        self.current_artifacts = None
        self._clear_output_views()

    def _prompt_save_case(self) -> None:
        try:
            case_data = self._collect_case_data()
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        file_path = filedialog.asksaveasfilename(
            title="Save HBD case", defaultextension=".json", filetypes=[("JSON files", "*.json")]
        )
        if not file_path:
            return
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(case_data, handle, ensure_ascii=False, indent=2)
        self.current_case_path = path
        self.case_name_var.set(path.stem)
        self.status_var.set(f"Case saved to {path}.")

    # ------------------------------------------------------------------
    # Solver execution & outputs
    # ------------------------------------------------------------------
    def _collect_case_data(self) -> Dict[str, Any]:
        case: Dict[str, Any] = {}
        for key, path in self.field_paths.items():
            raw = self.field_vars[key].get().strip()
            if raw == "":
                continue
            if self.field_types[key] == "float":
                try:
                    value: Any = float(raw)
                except ValueError as exc:
                    raise ValueError(f"Field '{key}' must be a number.") from exc
            else:
                value = raw
            self._assign_path(case, path, value)
        return case

    def _assign_path(self, container: MutableMapping[str, Any], path: Sequence[str], value: Any) -> None:
        current: MutableMapping[str, Any] = container
        for key in path[:-1]:
            if key not in current or not isinstance(current[key], MutableMapping):
                current[key] = {}
            current = cast(MutableMapping[str, Any], current[key])
        current[path[-1]] = value

    def _run_solver(self) -> None:
        try:
            case_data = self._collect_case_data()
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        case_name = self.case_name_var.get().strip() or "gui_case"
        meta = case_data.setdefault("meta", {})
        if self.current_case_path is not None:
            meta.setdefault("input_case", self.current_case_path.name)
        else:
            meta.setdefault("input_case", f"{case_name}.json")

        merged_case = merge_case_with_defaults(case_data, self.defaults)
        try:
            artifacts = run_pipeline(merged_case)
        except Exception as exc:  # pragma: no cover - surfaced to the user
            messagebox.showerror("Solver error", f"The solver encountered an error:\n{exc}")
            self.status_var.set("Solver execution failed. Check the input values.")
            return

        self.current_artifacts = artifacts
        self._populate_tree(self.case_tree, artifacts.merged_case)
        self._populate_tree(self.summary_tree, {"summary": artifacts.result.get("summary", {}), "meta": artifacts.result.get("meta", {})})
        self._populate_tree(self.gt_tree, artifacts.result.get("gt_block", {}))
        self._populate_tree(self.hrsg_tree, artifacts.result.get("hrsg_block", {}))
        self._populate_tree(self.st_tree, artifacts.result.get("st_block", {}))
        self._populate_tree(self.cond_tree, artifacts.result.get("condenser_block", {}))
        balance_payload = {
            "mass_energy_balance": artifacts.result.get("mass_energy_balance", {}),
            "warnings": artifacts.result.get("meta", {}).get("warnings", []),
        }
        self._populate_tree(self.balance_tree, balance_payload)
        self._render_trace(artifacts.trace)

        net_power = artifacts.result.get("summary", {}).get("NET_power_MW")
        if isinstance(net_power, (int, float)):
            net_text = f"Net power {net_power:.2f} MW"
        else:
            net_text = "Solver run complete"
        self.status_var.set(f"{net_text} • Results available for export.")
        self.output_notebook.select(self.summary_tree.master)

    def _clear_output_views(self) -> None:
        for tree in (
            self.summary_tree,
            self.gt_tree,
            self.hrsg_tree,
            self.st_tree,
            self.cond_tree,
            self.balance_tree,
        ):
            for item in tree.get_children():
                tree.delete(item)
        self.trace_text.delete("1.0", tk.END)

    def _populate_tree(self, tree: ttk.Treeview, payload: Any, parent: str = "") -> None:
        for item in tree.get_children(parent):
            tree.delete(item)
        self._fill_tree(tree, payload, parent)

    def _fill_tree(self, tree: ttk.Treeview, payload: Any, parent: str) -> None:
        if isinstance(payload, Mapping):
            for key, value in payload.items():
                if isinstance(value, (Mapping, list, tuple)):
                    node = tree.insert(parent, "end", text=str(key), values=("",))
                    self._fill_tree(tree, value, node)
                else:
                    tree.insert(parent, "end", text=str(key), values=(self._format_value(value),))
        elif isinstance(payload, (list, tuple)):
            for index, value in enumerate(payload):
                if isinstance(value, (Mapping, list, tuple)):
                    node = tree.insert(parent, "end", text=f"[{index}]", values=("",))
                    self._fill_tree(tree, value, node)
                else:
                    tree.insert(parent, "end", text=f"[{index}]", values=(self._format_value(value),))
        else:
            tree.insert(parent, "end", text="value", values=(self._format_value(payload),))

    def _render_trace(self, trace: Mapping[str, Any]) -> None:
        self.trace_text.delete("1.0", tk.END)
        self.trace_text.insert("1.0", json.dumps(trace, ensure_ascii=False, indent=2))
        self.trace_text.mark_set(tk.INSERT, "1.0")

    def _format_value(self, value: Any) -> str:
        if isinstance(value, (int, float)):
            return _format_float(float(value))
        return str(value)

    def _export_reports(self) -> None:
        if self.current_artifacts is None:
            messagebox.showinfo("Export unavailable", "Run the solver before exporting reports.")
            return

        directory = filedialog.askdirectory(title="Select output directory")
        if not directory:
            return
        out_dir = Path(directory)
        out_dir.mkdir(parents=True, exist_ok=True)

        case_name = self.case_name_var.get().strip() or "gui_case"
        result = self.current_artifacts.result
        trace = self.current_artifacts.trace

        excel_path = export_summary_to_excel(result, trace, out_dir / f"{case_name}.xlsx")
        svg_path = export_flow_diagram(result, out_dir / f"{case_name}.svg")
        calc_path = export_calculation_log(trace, out_dir / f"{case_name}_calculations.json")
        json_path = out_dir / f"{case_name}_result.json"
        json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        messagebox.showinfo(
            "Export complete",
            "\n".join(
                [
                    "Reports generated:",
                    f"Excel: {excel_path}",
                    f"Diagram: {svg_path}",
                    f"Calculations: {calc_path}",
                    f"Result JSON: {json_path}",
                ]
            ),
        )
        self.status_var.set(f"Artifacts exported to {out_dir}.")


def launch_gui() -> None:
    """Launch the Tkinter GUI for interactive case management."""

    root = tk.Tk()
    app = HBDGuiApp(root)
    root.mainloop()
