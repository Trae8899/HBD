"""Solver pipeline orchestration with optional progress reporting."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Any, Callable, Dict, Mapping

from .ambient.ambient_correction import apply_site_corrections
from .condenser_loop.condenser_solver import solve_condenser_loop
from .gt_block.gt_solver import solve_gt_block
from .hrsg_block.hrsg_solver import solve_hrsg_block
from .plant_summary.plant_summary import summarize_plant
from .st_block.st_solver import solve_steam_turbine


DEFAULTS_PATH = Path("defaults/defaults.json")

ProgressCallback = Callable[[str, float], None]


class PipelineCancelled(RuntimeError):
    """Raised when the solver pipeline is cancelled by the caller."""


@dataclass
class PipelineArtifacts:
    """Container for primary solver outputs and diagnostics."""

    result: Dict[str, Any]
    trace: Dict[str, Any]
    merged_case: Dict[str, Any]


def load_defaults(defaults_path: Path = DEFAULTS_PATH) -> Dict[str, Any]:
    """Load default solver configuration values."""

    with defaults_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries without mutating the inputs."""

    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], Mapping) and isinstance(value, Mapping):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def merge_case_with_defaults(case_data: Mapping[str, Any], defaults: Mapping[str, Any]) -> Dict[str, Any]:
    """Apply repository defaults to the provided case data."""

    return deep_merge(defaults, case_data)


def _resolve_git_commit() -> str:
    """Return the current repository HEAD commit hash if available."""

    try:
        commit_bytes = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return commit_bytes.decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover - git optional
        return "unknown"


def run_pipeline(
    case_data: Mapping[str, Any],
    *,
    progress_callback: ProgressCallback | None = None,
    cancel_event: Event | None = None,
) -> PipelineArtifacts:
    """Execute the solver pipeline for a merged case dictionary."""

    def _notify(step: str, fraction: float) -> None:
        if progress_callback is not None:
            progress_callback(step, max(0.0, min(1.0, fraction)))

    def _check_cancel() -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise PipelineCancelled()

    ambient = case_data.get("ambient", {})
    gas_turbine = case_data.get("gas_turbine", {})
    hrsg_spec = case_data.get("hrsg", {})
    steam_turbine_spec = case_data.get("steam_turbine", {})
    condenser_spec = case_data.get("condenser", {})
    bop_spec = case_data.get("bop", {})

    _check_cancel()
    ambient_trace = apply_site_corrections(ambient, gas_turbine.get("corr_coeff", {}))
    _notify("Ambient corrections", 0.15)

    _check_cancel()
    gt_result, gt_trace = solve_gt_block(
        {
            "ambient": ambient,
            "gas_turbine": gas_turbine,
            "corrections": ambient_trace,
        }
    )
    _notify("Gas turbine", 0.30)

    _check_cancel()
    hrsg_result, hrsg_trace = solve_hrsg_block(
        {
            "gt_exhaust": gt_result["exhaust"],
            "hrsg": hrsg_spec,
            "ambient": ambient,
        }
    )
    _notify("HRSG", 0.50)

    _check_cancel()
    st_result, st_trace = solve_steam_turbine(
        {
            "hrsg": hrsg_result,
            "steam_turbine": steam_turbine_spec,
            "condenser": condenser_spec,
        }
    )
    _notify("Steam turbine", 0.70)

    _check_cancel()
    condenser_result, condenser_trace = solve_condenser_loop(
        {
            "steam_turbine": st_result,
            "condenser": condenser_spec,
            "gt_block": gt_result,
        }
    )
    _notify("Condenser loop", 0.85)

    _check_cancel()
    summary, mass_balance, summary_trace = summarize_plant(
        {
            "gt_block": gt_result,
            "hrsg_block": hrsg_result,
            "st_block": st_result,
            "condenser_block": condenser_result,
        },
        {
            "bop": bop_spec,
            "meta": {
                "input_case": case_data.get("meta", {}).get("input_case"),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "solver_commit": _resolve_git_commit(),
            },
        },
    )
    _notify("Summary", 1.0)

    result = {
        "summary": summary,
        "gt_block": gt_result,
        "hrsg_block": hrsg_result,
        "st_block": st_result,
        "condenser_block": condenser_result,
        "mass_energy_balance": mass_balance,
        "meta": {
            **summary_trace["meta"],
            "input_case": summary_trace["meta"].get("input_case"),
            "solver_commit": summary_trace["meta"].get("solver_commit"),
            "timestamp_utc": summary_trace["meta"].get("timestamp_utc"),
            "warnings": summary_trace.get("warnings", []),
        },
    }

    trace = {
        "ambient": ambient_trace,
        "gt_block": gt_trace,
        "hrsg_block": hrsg_trace,
        "st_block": st_trace,
        "condenser_block": condenser_trace,
        "summary": summary_trace,
    }

    return PipelineArtifacts(result=result, trace=trace, merged_case=dict(case_data))


__all__ = [
    "PipelineArtifacts",
    "PipelineCancelled",
    "ProgressCallback",
    "DEFAULTS_PATH",
    "deep_merge",
    "load_defaults",
    "merge_case_with_defaults",
    "run_pipeline",
]
