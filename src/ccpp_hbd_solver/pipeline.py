"""End-to-end orchestration helpers for the CCPP HBD solver."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Mapping

from .ambient.ambient_correction import apply_site_corrections
from .gt_block.gt_solver import solve_gt_block
from .hrsg_block.hrsg_solver import solve_hrsg_block
from .st_block.st_solver import solve_steam_turbine
from .condenser_loop.condenser_solver import solve_condenser_loop
from .plant_summary.plant_summary import summarize_plant


DEFAULTS_PATH = Path("defaults/defaults.json")


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


def run_pipeline(case_data: Mapping[str, Any]) -> PipelineArtifacts:
    """Execute the solver pipeline for a merged case dictionary."""
    ambient = case_data.get("ambient", {})
    gas_turbine = case_data.get("gas_turbine", {})
    hrsg_spec = case_data.get("hrsg", {})
    steam_turbine_spec = case_data.get("steam_turbine", {})
    condenser_spec = case_data.get("condenser", {})
    bop_spec = case_data.get("bop", {})

    # Step 1: ambient corrections
    ambient_trace = apply_site_corrections(ambient, gas_turbine.get("corr_coeff", {}))

    # Step 2: gas turbine block
    gt_result, gt_trace = solve_gt_block(
        {
            "ambient": ambient,
            "gas_turbine": gas_turbine,
            "corrections": ambient_trace,
        }
    )

    # Step 3: HRSG block
    hrsg_result, hrsg_trace = solve_hrsg_block(
        {
            "gt_exhaust": gt_result["exhaust"],
            "hrsg": hrsg_spec,
            "ambient": ambient,
        }
    )

    # Step 4: Steam turbine block
    st_result, st_trace = solve_steam_turbine(
        {
            "hrsg": hrsg_result,
            "steam_turbine": steam_turbine_spec,
            "condenser": condenser_spec,
        }
    )

    # Step 5: Condenser / feedwater loop
    condenser_result, condenser_trace = solve_condenser_loop(
        {
            "steam_turbine": st_result,
            "condenser": condenser_spec,
            "gt_block": gt_result,
        }
    )

    # Step 6: plant summary
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
