"""Unit conversion helpers backed by Pint."""

from __future__ import annotations

from .units import ensure_quantity


def c_to_k(temperature_c: float) -> float:
    """Convert Celsius to Kelvin using Pint for validation."""

    return ensure_quantity(temperature_c, "degC").to("kelvin").magnitude


def k_to_c(temperature_k: float) -> float:
    """Convert Kelvin to Celsius using Pint for validation."""

    return ensure_quantity(temperature_k, "kelvin").to("degC").magnitude


def bar_to_kpa(pressure_bar: float) -> float:
    """Convert bar to kPa using Pint."""

    return ensure_quantity(pressure_bar, "bar").to("kilopascal").magnitude


def kpa_to_bar(pressure_kpa: float) -> float:
    """Convert kPa to bar using Pint."""

    return ensure_quantity(pressure_kpa, "kilopascal").to("bar").magnitude


def ratio_to_pct(value: float) -> float:
    """Convert a ratio (0-1) to percent."""

    return ensure_quantity(value, "dimensionless").to("percent").magnitude


__all__ = ["c_to_k", "k_to_c", "bar_to_kpa", "kpa_to_bar", "ratio_to_pct"]
