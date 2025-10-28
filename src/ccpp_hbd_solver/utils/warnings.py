"""Standard warning message catalogue for solver blocks."""

from __future__ import annotations

from typing import Final

WARNING_MESSAGES: Final[dict[str, str]] = {
    "HRSG_PINCH_VIOLATION": "HRSG pinch constraint violated",
    "HRSG_APPROACH_VIOLATION": "HRSG approach constraint violated",
    "HRSG_STACK_LOW": "Stack temperature below configured minimum",
    "ATTEMP_LIMIT_REACHED": "Attemperator spray mass flow reached limit",
    "ATTEMP_NOT_REQUIRED": "Attemperator target already satisfied",
    "CLOSURE_NEAR_LIMIT": "Mass/energy closure within 0.3-0.5% band",
    "CLOSURE_GT_0P5": "Mass/energy closure exceeds 0.5% tolerance",
    "GT_VENDOR_CURVE_MISSING": "Gas turbine vendor curve could not be resolved",
}


def format_warning(code: str, detail: str | None = None) -> str:
    """Return a formatted warning string with catalogue lookup."""

    base = WARNING_MESSAGES.get(code, code)
    if detail:
        return f"[{code}] {base}: {detail}"
    return f"[{code}] {base}"


__all__ = ["format_warning", "WARNING_MESSAGES"]
