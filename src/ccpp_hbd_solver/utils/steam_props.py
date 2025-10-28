"""Interfaces to steam and water property correlations."""

from __future__ import annotations

from typing import Any


def specific_enthalpy(pressure_bar: float, temperature_C: float, *, phase: str | None = None) -> float:
    """Return the specific enthalpy in kJ/kg for the requested state."""
    raise NotImplementedError("Steam property lookup not yet implemented")


def saturation_pressure(temperature_C: float) -> float:
    """Return saturation pressure in bar(abs) for the given temperature."""
    raise NotImplementedError("Saturation property lookup not yet implemented")
