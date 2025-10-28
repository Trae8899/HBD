"""Diagram-centric Tkinter GUI for the CCPP HBD solver."""

from __future__ import annotations

import json
from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from threading import Event
from typing import Any, Callable, Mapping, Sequence

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..pipeline import (
    PipelineArtifacts,
    PipelineCancelled,
    load_defaults,
    merge_case_with_defaults,
    run_pipeline,
)
from ..reporter.console_reporter import export_calculation_log
from ..reporter.diagram_svg import export_flow_diagram
from ..reporter.excel_reporter import export_summary_to_excel
from .diagram_canvas import DiagramCanvas
from .events import EventBus
from .model import CaseModel
from .theme import Theme, get_theme


class SummaryRow:
    """Row definition for the summary tree view."""

    def __init__(self, label: str, path: Sequence[str], decimals: int = 1) -> None:
        self.label = label
        self.path = tuple(path)
        self.decimals = decimals


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
        self.project_root = Path(__file__).resolve().parents[2]

        self.bus = EventBus()
        self.model = CaseModel(self.bus)
        self.theme: Theme = get_theme(high_contrast=False)

        self.defaults = load_defaults(self.project_root / "defaults" / "defaults.json")
        self.case_path: Path | None = None
        self.current_artifacts: PipelineArtifacts | None = None

        self.auto_run_var = tk.BooleanVar(value=True)
        self.high_contrast_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready.")
        self.warnings_var = tk.StringVar(value="No warnings.")
        self.progress_text_var = tk.StringVar(value="Idle")

        self.executor = ThreadPoolExecutor(max_workers=1)
        self._current_future: Future[PipelineArtifacts] | None = None
        self._cancel_event: Event | None = None
        self._pending_run_id: str | None = None
        self._running = False
        self._subscriptions: list[Callable[[], None]] = []

        self._build_ui()
        self._register_bus_handlers()
        self._load_initial_case()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.root.title("CCPP HBD Diagram")
        self.root.configure(bg=self.theme.palette.window_bg)

        self._apply_theme_to_styles()

        toolbar = ttk.Frame(self.root, padding=(12, 8))
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="Load Case…", command=self.load_case).pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="Save Case", command=self.save_case).pack(side="left", padx=(0, 8))

        self.run_button = ttk.Button(toolbar, text="Run Solver", command=self.execute_pipeline)
        self.run_button.pack(side="left", padx=(0, 8))

        self.cancel_button = ttk.Button(toolbar, text="Cancel", command=self.cancel_run, state="disabled")
        self.cancel_button.pack(side="left", padx=(0, 8))

        ttk.Button(toolbar, text="Export Artifacts", command=self.export_results).pack(side="left", padx=(0, 8))

        self.undo_button = ttk.Button(toolbar, text="Undo", command=self._handle_undo, state="disabled")
        self.undo_button.pack(side="left", padx=(16, 4))
        self.redo_button = ttk.Button(toolbar, text="Redo", command=self._handle_redo, state="disabled")
        self.redo_button.pack(side="left", padx=(4, 16))

        ttk.Checkbutton(toolbar, text="Auto-run (0.5 s)", variable=self.auto_run_var, command=self._on_auto_run_toggled).pack(
            side="left", padx=(0, 16)
        )
        ttk.Checkbutton(toolbar, text="High contrast", variable=self.high_contrast_var, command=self._toggle_contrast).pack(
            side="left"
        )

        content = ttk.Frame(self.root, padding=(12, 8))
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        self.diagram = DiagramCanvas(content, model=self.model, bus=self.bus, theme=self.theme)
        self.diagram.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        sidebar = ttk.Frame(content)
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(1, weight=1)

        summary_frame = ttk.LabelFrame(sidebar, text="Result Summary", padding=(8, 8))
        summary_frame.grid(row=0, column=0, sticky="ew")

        self.summary_tree = ttk.Treeview(
            summary_frame,
            columns=("metric", "value"),
            show="headings",
            height=len(SUMMARY_ROWS),
        )
        self.summary_tree.heading("metric", text="Metric")
        self.summary_tree.heading("value", text="Value")
        self.summary_tree.column("metric", anchor="w", width=180)
        self.summary_tree.column("value", anchor="e", width=120)
        self.summary_tree.pack(fill="x", expand=True)

        inputs_frame = ttk.LabelFrame(sidebar, text="Case Inputs", padding=(8, 8))
        inputs_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))

        self.case_tree = ttk.Treeview(inputs_frame, columns=("value",), show="tree headings")
        self.case_tree.heading("#0", text="Parameter")
        self.case_tree.heading("value", text="Value")
        self.case_tree.column("#0", anchor="w", width=220)
        self.case_tree.column("value", anchor="e", width=120)
        self.case_tree.pack(fill="both", expand=True)

        warnings_frame = ttk.LabelFrame(sidebar, text="Warnings", padding=(8, 8))
        warnings_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        ttk.Label(warnings_frame, textvariable=self.warnings_var, wraplength=260, justify="left").pack(fill="x")

        status_frame = ttk.Frame(self.root, padding=(12, 4))
        status_frame.pack(fill="x")
        status_frame.columnconfigure(0, weight=1)

        ttk.Label(status_frame, textvariable=self.status_var, anchor="w").grid(row=0, column=0, sticky="w")
        progress_container = ttk.Frame(status_frame)
        progress_container.grid(row=0, column=1, sticky="e")
        self.progress_bar = ttk.Progressbar(progress_container, length=180, maximum=100, mode="determinate")
        self.progress_bar.pack(side="left", padx=(0, 8))
        ttk.Label(progress_container, textvariable=self.progress_text_var, anchor="e").pack(side="left")

        self.root.bind_all("<Control-z>", self._handle_undo_event)
        self.root.bind_all("<Control-y>", self._handle_redo_event)

    def _apply_theme_to_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("default")
        palette = self.theme.palette
        fonts = self.theme.fonts.as_dict()

        self.root.configure(bg=palette.window_bg)
        style.configure("TFrame", background=palette.window_bg)
        style.configure("TLabelframe", background=palette.window_bg, foreground=palette.text_primary, font=fonts["section"])
        style.configure("TLabelframe.Label", background=palette.window_bg, foreground=palette.text_primary, font=fonts["section"])
        style.configure("TLabel", background=palette.window_bg, foreground=palette.text_primary, font=fonts["value"])
        style.configure("Treeview", font=fonts["value"], rowheight=22)
        style.configure("Treeview.Heading", font=fonts["label"], background=palette.window_bg)
        style.configure("TButton", font=fonts["value"])
        style.configure("TCheckbutton", background=palette.window_bg, foreground=palette.text_primary, font=fonts["value"])
        style.configure("TProgressbar", background=palette.block_outline)

    # ------------------------------------------------------------------
    # Event bus hooks
    # ------------------------------------------------------------------
    def _register_bus_handlers(self) -> None:
        self._subscriptions.append(self.bus.subscribe("case_loaded", self._on_case_loaded))
        self._subscriptions.append(self.bus.subscribe("value_changed", self._on_value_changed))
        self._subscriptions.append(self.bus.subscribe("result_updated", self._on_result_updated))
        self._subscriptions.append(self.bus.subscribe("result_cleared", self._on_result_cleared))
        self._subscriptions.append(self.bus.subscribe("progress", self._on_progress))
        self._subscriptions.append(self.bus.subscribe("history_changed", self._on_history_changed))

    # ------------------------------------------------------------------
    # Case management
    # ------------------------------------------------------------------
    def _load_initial_case(self) -> None:
        sample_path = self.project_root / "data" / "plant_case_summer_35C.json"
        case_data = {}
        if sample_path.exists():
            try:
                raw = json.loads(sample_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                raw = {}
            else:
                self.case_path = sample_path
            case_data = merge_case_with_defaults(self._normalize_case(raw), self.defaults)
        else:
            case_data = merge_case_with_defaults({}, self.defaults)
        self.model.load_case(case_data)
        self.diagram.update()
        if self.auto_run_var.get():
            self.schedule_run(delay_ms=200)

    def load_case(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Open Case JSON", filetypes=(("JSON Files", "*.json"), ("All Files", "*"))
        )
        if not file_path:
            return
        try:
            raw_case = json.loads(Path(file_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Load Error", f"Failed to load case:\n{exc}", parent=self.root)
            return
        self.case_path = Path(file_path)
        merged = merge_case_with_defaults(self._normalize_case(raw_case), self.defaults)
        self.model.load_case(merged)
        self.current_artifacts = None
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
            Path(file_path).write_text(json.dumps(self.model.case_data, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Save Error", f"Failed to save case:\n{exc}", parent=self.root)
            return
        self.case_path = Path(file_path)
        self.update_status(f"Saved case to {self.case_path}")

    def _normalize_case(self, raw_case: Mapping[str, Any]) -> dict[str, Any]:
        if "fixed" in raw_case:
            merged = deepcopy(raw_case["fixed"])
            meta = dict(raw_case.get("meta", {}))
            meta.setdefault("case_schema_version", str(raw_case.get("version", "0.2")))
            merged["meta"] = meta
            return merged
        return deepcopy(dict(raw_case))

    # ------------------------------------------------------------------
    # Solver orchestration
    # ------------------------------------------------------------------
    def schedule_run(self, delay_ms: int = 500) -> None:
        if self._pending_run_id is not None:
            self.root.after_cancel(self._pending_run_id)
        self._pending_run_id = self.root.after(delay_ms, self.execute_pipeline)

    def execute_pipeline(self) -> None:
        if self._running:
            if self._pending_run_id is None:
                self._pending_run_id = self.root.after(300, self.execute_pipeline)
            return
        if self._pending_run_id is not None:
            self.root.after_cancel(self._pending_run_id)
            self._pending_run_id = None
        self._running = True
        self.run_button.state(["disabled"])
        self.cancel_button.state(["!disabled"])
        self.update_status("Running solver…")
        self.model.set_progress("Queued", 0.0)

        case_copy = deepcopy(self.model.case_data)
        self._cancel_event = Event()

        def _progress(step: str, fraction: float) -> None:
            self.root.after(0, lambda: self.model.set_progress(step, fraction))

        future = self.executor.submit(
            self._run_pipeline_worker,
            case_copy,
            self._cancel_event,
            _progress,
        )
        future.add_done_callback(lambda fut: self.root.after(0, lambda: self._handle_pipeline_future(fut)))
        self._current_future = future

    def _run_pipeline_worker(
        self,
        case_data: Mapping[str, Any],
        cancel_event: Event,
        progress: Callable[[str, float], None],
    ) -> PipelineArtifacts:
        return run_pipeline(case_data, progress_callback=progress, cancel_event=cancel_event)

    def _handle_pipeline_future(self, future: Future[PipelineArtifacts]) -> None:
        self._running = False
        self.run_button.state(["!disabled"])
        self.cancel_button.state(["disabled"])
        self._current_future = None
        self._cancel_event = None

        try:
            artifacts = future.result()
        except PipelineCancelled:
            self.model.set_progress(None, 0.0)
            self.update_status("Solver cancelled.")
            return
        except Exception as exc:  # pragma: no cover - GUI feedback path
            self.model.set_progress(None, 0.0)
            self.model.set_result(None)
            messagebox.showerror("Solver Error", str(exc), parent=self.root)
            self.update_status("Solver failed.")
            return

        self.current_artifacts = artifacts
        warnings = artifacts.result.get("meta", {}).get("warnings", [])
        self.model.set_result(artifacts.result, warnings)
        self.model.set_progress(None, 0.0)
        self.update_status("Solver completed successfully.")

    def cancel_run(self) -> None:
        if not self._running:
            return
        if self._cancel_event is not None:
            self._cancel_event.set()
        self.update_status("Cancelling run…")

    # ------------------------------------------------------------------
    # Event handlers from model/bus
    # ------------------------------------------------------------------
    def _on_case_loaded(self, case: Mapping[str, Any], **_: Any) -> None:
        self._populate_case_tree(case)
        self._clear_summary()
        self.warnings_var.set("No warnings.")

    def _on_value_changed(self, path: Sequence[str], case: Mapping[str, Any], **_: Any) -> None:
        self._populate_case_tree(case)
        if self.auto_run_var.get():
            self.schedule_run()
        else:
            self.update_status("Value changed. Auto-run disabled.")

    def _on_result_updated(self, result: Mapping[str, Any], warnings: Sequence[str], **_: Any) -> None:
        self._populate_summary(result)
        if warnings:
            self.warnings_var.set("\n".join(f"• {msg}" for msg in warnings))
        else:
            self.warnings_var.set("No warnings.")

    def _on_result_cleared(self, **_: Any) -> None:
        self._clear_summary()
        self.warnings_var.set("No warnings.")

    def _on_progress(self, step: str | None, value: float, **_: Any) -> None:
        if step is None:
            self.progress_bar.configure(value=0)
            self.progress_text_var.set("Idle")
        else:
            self.progress_bar.configure(value=value * 100.0)
            self.progress_text_var.set(f"{step} ({int(value * 100)}%)")

    def _on_history_changed(self, can_undo: bool, can_redo: bool, **_: Any) -> None:
        self.undo_button.state(["!disabled"] if can_undo else ["disabled"])
        self.redo_button.state(["!disabled"] if can_redo else ["disabled"])

    # ------------------------------------------------------------------
    # Case tree and summary helpers
    # ------------------------------------------------------------------
    def _populate_case_tree(self, case: Mapping[str, Any]) -> None:
        self.case_tree.delete(*self.case_tree.get_children())

        def add_section(parent: str, key: str, value: Any) -> None:
            node_id = self.case_tree.insert(parent, "end", text=key, values=("",))
            self.case_tree.item(node_id, open=True)
            if isinstance(value, Mapping):
                for child_key, child_value in value.items():
                    add_section(node_id, str(child_key), child_value)
            else:
                self.case_tree.item(node_id, values=(self._format_number(value, 3),))

        for key in ("ambient", "gas_turbine", "hrsg", "steam_turbine", "condenser", "bop"):
            add_section("", key.replace("_", " ").title(), case.get(key, {}))

    def _populate_summary(self, result: Mapping[str, Any]) -> None:
        self.summary_tree.delete(*self.summary_tree.get_children())
        for row in SUMMARY_ROWS:
            value = self._resolve_path(result, row.path)
            self.summary_tree.insert("", "end", values=(row.label, self._format_number(value, row.decimals)))

    def _clear_summary(self) -> None:
        self.summary_tree.delete(*self.summary_tree.get_children())
        for row in SUMMARY_ROWS:
            self.summary_tree.insert("", "end", values=(row.label, "—"))

    # ------------------------------------------------------------------
    # Formatting & status helpers
    # ------------------------------------------------------------------
    def _format_number(self, value: Any, decimals: int) -> str:
        if value is None:
            return "—"
        if isinstance(value, (int, float)):
            formatted = f"{float(value):.{decimals}f}" if decimals else f"{int(round(float(value)))}"
            return formatted.rstrip("0").rstrip(".") if decimals else formatted
        return str(value)

    def _resolve_path(self, data: Mapping[str, Any], path: Sequence[str]) -> Any:
        current: Any = data
        for key in path:
            if not isinstance(current, Mapping):
                return None
            current = current.get(key)
        return current

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

    def _toggle_contrast(self) -> None:
        self.theme = get_theme(high_contrast=self.high_contrast_var.get())
        self._apply_theme_to_styles()
        self.diagram.apply_theme(self.theme)

    # ------------------------------------------------------------------
    # Undo / redo
    # ------------------------------------------------------------------
    def _handle_undo(self) -> None:
        self.model.undo()

    def _handle_redo(self) -> None:
        self.model.redo()

    def _handle_undo_event(self, event: tk.Event) -> str:
        self._handle_undo()
        return "break"

    def _handle_redo_event(self, event: tk.Event) -> str:
        self._handle_redo()
        return "break"

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

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        if self._current_future is not None and not self._current_future.done():
            if self._cancel_event is not None:
                self._cancel_event.set()
            self._current_future.cancel()
        self.executor.shutdown(wait=False)
        for unsubscribe in self._subscriptions:
            try:
                unsubscribe()
            except Exception:
                continue


def launch_gui() -> None:
    """Entry point for launching the Tkinter GUI."""

    root = tk.Tk()
    app = HBDGuiApp(root)

    def _on_close() -> None:
        app.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()


__all__ = ["HBDGuiApp", "launch_gui"]
