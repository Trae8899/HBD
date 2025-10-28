"""Unit conversion helpers."""

from __future__ import annotations


def c_to_k(temperature_C: float) -> float:
    """Convert Celsius to Kelvin."""
    return temperature_C + 273.15


def k_to_c(temperature_K: float) -> float:
    """Convert Kelvin to Celsius."""
    return temperature_K - 273.15


def bar_to_kpa(pressure_bar: float) -> float:
    """Convert bar to kPa."""
    return pressure_bar * 100.0


def kpa_to_bar(pressure_kpa: float) -> float:
    """Convert kPa to bar."""
    return pressure_kpa / 100.0
