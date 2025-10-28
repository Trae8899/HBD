"""Diagram-centric Tkinter GUI for the CCPP HBD solver."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

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
from .diagram_canvas import DiagramCanvas
from .theme import COLORS, FONTS


def _resolve_path(data: Mapping[str, Any], path: Sequence[str]) -> Any:
    value: Any = data
    for key in path:
        if isinstance(value, Mapping):
            value = value.get(key)
        else:
            return None
    return value


def _assign_path(data: dict[str, Any], path: Sequence[str], value: Any) -> None:
    current: dict[str, Any] = data
    for key in path[:-1]:
        next_value = current.get(key)
        if not isinstance(next_value, dict):
            next_value = {}
            current[key] = next_value
        current = next_value
    current[path[-1]] = value


@dataclass
class SummaryRow:
    label: str
    path: tuple[str, ...]
    decimals: int = 1


SUMMARY_ROWS: tuple[SummaryRow, ...] = (
    SummaryRow("GT Power (MW)", ("summary", "GT_power_MW")),
    SummaryRow("ST Power (MW)", ("summary", "ST_power_MW")),
    SummaryRow("Aux Load (MW)", ("summary", "AUX_load_MW")),
    SummaryRow("Net Power (MW)", ("summary", "NET_power_MW")),
    SummaryRow("Net Eff. (% LHV)", ("summary", "NET_eff_LHV_pct"), decimals=2),
    SummaryRow("Stack Temp (°C)", ("hrsg_block", "stack_temp_C")),
    SummaryRow("Closure Error (%)", ("mass_energy_balance", "closure_error_pct"), decimals=3),
)


class HBDGuiApp:
    """Controller for the diagram-based GUI."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CCPP HBD Diagram")
        self.root.configure(bg=COLORS["window_bg"])

        self.project_root = Path(__file__).resolve().parents[2]
        defaults_path = self.project_root / "defaults" / "defaults.json"
        try:
            self.defaults = load_defaults(defaults_path)
        except FileNotFoundError:
            self.defaults = {}

        self.case_path: Path | None = None
        self.case_data: dict[str, Any] = {}
        self.current_artifacts: PipelineArtifacts | None = None
        self._pending_run_id: str | None = None
        self._running = False

        self.auto_run_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready.")

        self._build_ui()
        self._load_initial_case()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        style = ttk.Style()
        style.configure("TFrame", background=COLORS["window_bg"])
        style.configure(
            "TLabel",
            background=COLORS["window_bg"],
            foreground=COLORS["text_primary"],
        )
        style.configure(
            "TLabelframe",
            background=COLORS["window_bg"],
            foreground=COLORS["text_primary"],
        )
        style.configure(
            "TLabelframe.Label",
            background=COLORS["window_bg"],
            foreground=COLORS["text_primary"],
            font=FONTS["section"],
        )
        style.configure(
            "Status.TLabel",
            background=COLORS["window_bg"],
            foreground=COLORS["text_secondary"],
            font=FONTS["status"],
        )

        toolbar = ttk.Frame(self.root, padding=(12, 8))
        toolbar.pack(fill="x")

        ttk.Button(
            toolbar,
            text="Load Case…",
            command=self.load_case,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            toolbar,
            text="Save Case",
            command=self.save_case,
        ).pack(side="left", padx=(0, 8))
        self.run_button = ttk.Button(
            toolbar,
            text="Run Solver",
            command=self.execute_pipeline,
        )
        self.run_button.pack(side="left", padx=(0, 8))
        ttk.Button(
            toolbar,
            text="Export Artifacts",
            command=self.export_results,
        ).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(
            toolbar,
            text="Auto-run (0.5 s)",
            variable=self.auto_run_var,
            command=self._on_auto_run_toggled,
        ).pack(side="left", padx=(16, 0))

        content = ttk.Frame(self.root, padding=(12, 8))
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        self.diagram = DiagramCanvas(
            content,
            get_value=self._get_value,
            set_value=self._set_value,
            on_change=self._on_value_changed,
        )
        self.diagram.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        sidebar = ttk.Frame(content)
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)

        summary_frame = ttk.LabelFrame(sidebar, text="Result Summary", padding=(8, 8))
        summary_frame.grid(row=0, column=0, sticky="ew")
        self.summary_tree = ttk.Treeview(
            summary_frame,
            columns=("metric", "value"),
            show="headings",
            height=7,
        )
        self.summary_tree.heading("metric", text="Metric")
        self.summary_tree.heading("value", text="Value")
        self.summary_tree.column("metric", anchor="w", width=180)
        self.summary_tree.column("value", anchor="e", width=120)
        self.summary_tree.pack(fill="x", expand=True)

        inputs_frame = ttk.LabelFrame(sidebar, text="Case Inputs", padding=(8, 8))
        inputs_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        sidebar.rowconfigure(1, weight=1)
        self.case_tree = ttk.Treeview(inputs_frame, columns=("value",), show="tree headings")
        self.case_tree.heading("#0", text="Parameter")
        self.case_tree.heading("value", text="Value")
        self.case_tree.column("#0", anchor="w", width=200)
        self.case_tree.column("value", anchor="e", width=120)
        self.case_tree.pack(fill="both", expand=True)

        warnings_frame = ttk.LabelFrame(sidebar, text="Warnings", padding=(8, 8))
        warnings_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.warnings_var = tk.StringVar(value="No warnings.")
        ttk.Label(
            warnings_frame,
            textvariable=self.warnings_var,
            wraplength=260,
            justify="left",
        ).pack(fill="x")

        ttk.Label(
            self.root,
            textvariable=self.status_var,
            style="Status.TLabel",
            anchor="w",
            padding=(12, 4),
        ).pack(fill="x")

    # ------------------------------------------------------------------
    # Case management helpers
    # ------------------------------------------------------------------
    def _load_initial_case(self) -> None:
        sample_path = self.project_root / "data" / "plant_case_summer_35C.json"
        if sample_path.exists():
            try:
                case = json.loads(sample_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                case = {}
            else:
                self.case_path = sample_path
        else:
            case = {}
        self.case_data = merge_case_with_defaults(case, self.defaults)
        self.refresh_case_tree()
        self.diagram.update_case_values()
        self.diagram.update_results(None)
        if self.auto_run_var.get():
            self.schedule_run(delay_ms=200)

    def load_case(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Open Case JSON",
            filetypes=(("JSON Files", "*.json"), ("All Files", "*")),
        )
        if not file_path:
            return
        try:
            raw_case = json.loads(Path(file_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Load Error", f"Failed to load case:\n{exc}", parent=self.root)
            return
        self.case_path = Path(file_path)
        self.case_data = merge_case_with_defaults(raw_case, self.defaults)
        self.current_artifacts = None
        self.diagram.update_results(None)
        self.refresh_case_tree()
        self.diagram.update_case_values()
        self.update_status(f"Loaded case: {self.case_path.name}")
        if self.auto_run_var.get():
            self.schedule_run()

    def save_case(self) -> None:
        initial_file = self.case_path.name if self.case_path else "case.json"
        file_path = filedialog.asksaveasfilename(
            title="Save Case JSON",
            defaultextension=".json",
            initialfile=initial_file,
            filetypes=(("JSON Files", "*.json"), ("All Files", "*")),
        )
        if not file_path:
            return
        try:
            Path(file_path).write_text(json.dumps(self.case_data, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Save Error", f"Failed to save case:\n{exc}", parent=self.root)
            return
        self.case_path = Path(file_path)
        self.update_status(f"Saved case to {self.case_path}")

    # ------------------------------------------------------------------
    # Solver orchestration
    # ------------------------------------------------------------------
    def schedule_run(self, delay_ms: int = 500) -> None:
        if self._pending_run_id is not None:
            self.root.after_cancel(self._pending_run_id)
        self._pending_run_id = self.root.after(delay_ms, self.execute_pipeline)

    def execute_pipeline(self) -> None:
        if self._running:
            return
        if self._pending_run_id is not None:
            self.root.after_cancel(self._pending_run_id)
            self._pending_run_id = None
        self._running = True
        self.run_button.state(["disabled"])
        self.update_status("Running solver…")
        case_copy = json.loads(json.dumps(self.case_data))
        thread = threading.Thread(target=self._run_pipeline_thread, args=(case_copy,), daemon=True)
        thread.start()

    def _run_pipeline_thread(self, case_data: dict[str, Any]) -> None:
        try:
            artifacts = run_pipeline(case_data)
        except Exception as exc:  # pragma: no cover - GUI feedback path
            self.root.after(0, lambda: self._handle_pipeline_error(exc))
            return
        self.root.after(0, lambda: self._handle_pipeline_result(artifacts))

    def _handle_pipeline_result(self, artifacts: PipelineArtifacts) -> None:
        self._running = False
        self.run_button.state(["!disabled"])
        self.current_artifacts = artifacts
        warnings = artifacts.result.get("meta", {}).get("warnings", [])
        self.diagram.update_results(artifacts.result, warnings)
        self._populate_summary(artifacts.result)
        self._update_warnings(warnings)
        self.update_status("Solver completed successfully.")

    def _handle_pipeline_error(self, exc: Exception) -> None:
        self._running = False
        self.run_button.state(["!disabled"])
        self.update_status("Solver failed.")
        messagebox.showerror("Solver Error", str(exc), parent=self.root)

    # ------------------------------------------------------------------
    # Data binding
    # ------------------------------------------------------------------
    def _get_value(self, path: Sequence[str]) -> Any:
        return _resolve_path(self.case_data, path)

    def _set_value(self, path: Sequence[str], value: float) -> None:
        _assign_path(self.case_data, path, value)

    def _on_value_changed(self, path: Sequence[str], value: float) -> None:
        self.refresh_case_tree()
        if self.auto_run_var.get():
            self.schedule_run()
        else:
            self.update_status("Value changed. Auto-run disabled.")

    def _populate_summary(self, result: Mapping[str, Any]) -> None:
        self.summary_tree.delete(*self.summary_tree.get_children())
        for row in SUMMARY_ROWS:
            value = _resolve_path(result, row.path)
            display = self._format_number(value, row.decimals)
            self.summary_tree.insert("", "end", values=(row.label, display))

    def _update_warnings(self, warnings: Sequence[str]) -> None:
        if warnings:
            text = "\n".join(f"• {msg}" for msg in warnings)
        else:
            text = "No warnings."
        self.warnings_var.set(text)

    def refresh_case_tree(self) -> None:
        self.case_tree.delete(*self.case_tree.get_children())

        def add_section(title: str, data: Any, parent: str = "") -> None:
            node_id = self.case_tree.insert(parent, "end", text=title, values=("",))
            self.case_tree.item(node_id, open=True)
            if isinstance(data, Mapping):
                for key, value in data.items():
                    if isinstance(value, Mapping):
                        add_section(str(key), value, parent=node_id)
                    else:
                        self.case_tree.insert(
                            node_id,
                            "end",
                            text=str(key),
                            values=(self._format_number(value, 3),),
                        )
            else:
                self.case_tree.insert(
                    node_id,
                    "end",
                    text="value",
                    values=(self._format_number(data, 3),),
                )

        for section in ("ambient", "gas_turbine", "hrsg", "steam_turbine", "condenser", "bop"):
            pretty = section.replace("_", " ").title()
            add_section(pretty, self.case_data.get(section, {}))

    # ------------------------------------------------------------------
    # Formatting & status helpers
    # ------------------------------------------------------------------
    def _format_number(self, value: Any, decimals: int) -> str:
        if value is None:
            return "—"
        if isinstance(value, (int, float)):
            formatted = f"{float(value):.{decimals}f}"
            return formatted.rstrip("0").rstrip(".") if decimals > 0 else formatted
        return str(value)

    def update_status(self, message: str) -> None:
        self.status_var.set(message)

    def _on_auto_run_toggled(self) -> None:
        if self.auto_run_var.get():
            self.update_status("Auto-run enabled.")
            self.schedule_run()
        else:
            if self._pending_run_id is not None:
                self.root.after_cancel(self._pending_run_id)
                self._pending_run_id = None
            self.update_status("Auto-run disabled.")

    # ------------------------------------------------------------------
    # Artifact export
    # ------------------------------------------------------------------
    def export_results(self) -> None:
        if self.current_artifacts is None:
            messagebox.showinfo("Export", "Run the solver before exporting.", parent=self.root)
            return
        directory = filedialog.askdirectory(title="Select output directory")
        if not directory:
            return
        output_dir = Path(directory)
        base_name = self.case_path.stem if self.case_path else "case"
        try:
            export_summary_to_excel(
                self.current_artifacts.result,
                self.current_artifacts.trace,
                output_dir / f"{base_name}_summary.xlsx",
            )
            export_flow_diagram(
                self.current_artifacts.result,
                output_dir / f"{base_name}_diagram.svg",
            )
            export_calculation_log(
                self.current_artifacts.trace,
                output_dir / f"{base_name}_calculations.json",
            )
        except Exception as exc:  # pragma: no cover - GUI feedback path
            messagebox.showerror(
                "Export Error",
                f"Failed to export artifacts:\n{exc}",
                parent=self.root,
            )
            return
        messagebox.showinfo(
            "Export Complete",
            f"Artifacts saved to {output_dir}",
            parent=self.root,
        )
        self.update_status(f"Artifacts saved to {output_dir}")


def launch_gui() -> None:
    """Entry point for the GUI runner."""

    root = tk.Tk()
    HBDGuiApp(root)
    root.mainloop()
