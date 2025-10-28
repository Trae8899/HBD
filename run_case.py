"""CLI entry point for executing a single CCPP HBD case."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Mapping

# Ensure the local src directory is available for direct execution without installation.
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))

from ccpp_hbd_solver.pipeline import (
    PipelineArtifacts,
    load_defaults,
    merge_case_with_defaults,
    run_pipeline,
)
from ccpp_hbd_solver.reporter.console_reporter import (
    export_calculation_log,
    render_console_view,
)
from ccpp_hbd_solver.reporter.diagram_svg import export_flow_diagram
from ccpp_hbd_solver.reporter.excel_reporter import export_summary_to_excel


def parse_args() -> argparse.Namespace:
    """Parse command-line options for the case runner."""
    parser = argparse.ArgumentParser(description="Run a CCPP HBD case file")
    parser.add_argument("--case", required=True, type=Path, help="Path to the input JSON case file")
    parser.add_argument("--out", required=True, type=Path, help="Output directory for generated artifacts")
    parser.add_argument(
        "--show-steps",
        action="store_true",
        help="Display calculation trace availability in the console output",
    )
    parser.add_argument(
        "--no-console",
        action="store_true",
        help="Skip interactive console formatting (useful for scripted runs)",
    )
    return parser.parse_args()


def load_case(case_path: Path) -> dict[str, Any]:
    """Load and parse the JSON case file."""
    with case_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _prepare_case(case_data: dict[str, Any], case_path: Path) -> dict[str, Any]:
    """Normalize legacy and v0.2 case layouts into a single merged dict."""

    base_meta = dict(case_data.get("meta", {}))
    base_meta.setdefault("input_case", case_path.name)

    if "fixed" in case_data:
        fixed_case = copy.deepcopy(case_data["fixed"])
        fixed_meta = dict(base_meta)
        fixed_meta.setdefault(
            "case_schema_version",
            str(case_data.get("schema_version", case_data.get("version", "0.3"))),
        )
        if case_data.get("devices"):
            fixed_meta["declared_devices"] = copy.deepcopy(case_data["devices"])
        if case_data.get("vary"):
            fixed_meta["declared_vary_axes"] = list(case_data["vary"].keys())
        fixed_case["meta"] = fixed_meta
        fixed_case["case_constraints"] = copy.deepcopy(case_data.get("constraints", {}))
        fixed_case["declared_devices"] = copy.deepcopy(case_data.get("devices", []))
        fixed_case["schema_version"] = case_data.get("schema_version", case_data.get("version"))
        fixed_case["units_system"] = case_data.get("units_system", "SI_IF97")
        return fixed_case

    legacy_case = copy.deepcopy(case_data)
    legacy_meta = dict(legacy_case.get("meta", {}))
    legacy_meta.update(base_meta)
    legacy_case["meta"] = legacy_meta
    return legacy_case


def _write_result_json(result: Mapping[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    """Entry point for executing the CCPP HBD solver pipeline."""
    args = parse_args()
    case_data = load_case(args.case)
    case_data = _prepare_case(case_data, args.case)

    defaults = load_defaults()
    merged_case = merge_case_with_defaults(case_data, defaults)

    artifacts: PipelineArtifacts = run_pipeline(merged_case)

    args.out.mkdir(parents=True, exist_ok=True)
    case_stem = args.case.stem

    if not args.no_console:
        render_console_view(args.case, merged_case, artifacts.result, show_calcs=args.show_steps)

    excel_path = export_summary_to_excel(artifacts.result, artifacts.trace, args.out / f"{case_stem}.xlsx")
    svg_path = export_flow_diagram(artifacts.result, args.out / f"{case_stem}.svg")
    calc_log_path = export_calculation_log(artifacts.trace, args.out / f"{case_stem}_calculations.json")
    json_result_path = _write_result_json(artifacts.result, args.out / f"{case_stem}_result.json")

    if not args.no_console:
        print()
        print("Artifacts saved:")
        print(f"  Excel report  : {excel_path}")
        print(f"  Flow diagram  : {svg_path}")
        print(f"  Calc trace    : {calc_log_path}")
        print(f"  Result JSON   : {json_result_path}")


if __name__ == "__main__":
    main()
