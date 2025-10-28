"""Thermophysical property wrappers with CoolProp primary backend."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Protocol

from .units import ensure_quantity, ureg

try:  # pragma: no cover - optional dependency resolution
    from CoolProp.CoolProp import PropsSI as coolprop_props  # type: ignore
    from CoolProp.HumidAir import HAPropsSI  # type: ignore
except ImportError:  # pragma: no cover
    coolprop_props = None
    HAPropsSI = None

try:  # pragma: no cover - fallback backend
    from iapws import IAPWS97  # type: ignore
except ImportError:  # pragma: no cover
    IAPWS97 = None


class PropertyBackend(Protocol):
    """Protocol implemented by thermophysical property backends."""

    def steam_props(self, pressure_bar: float, temperature_c: float) -> Dict[str, float]:
        ...

    def saturated_steam(self, pressure_bar: float) -> Dict[str, float]:
        ...

    def humid_air(self, temperature_c: float, rh_pct: float, pressure_bar: float) -> Dict[str, float]:
        ...


@dataclass
class CoolPropBackend:
    """CoolProp-backed property evaluator."""

    def steam_props(self, pressure_bar: float, temperature_c: float) -> Dict[str, float]:
        pressure_pa = ensure_quantity(pressure_bar, "bar").to("pascal").magnitude
        temperature_k = ensure_quantity(temperature_c, "degC").to("kelvin").magnitude
        enthalpy = coolprop_props("H", "P", pressure_pa, "T", temperature_k, "Water") / 1000.0
        entropy = coolprop_props("S", "P", pressure_pa, "T", temperature_k, "Water") / 1000.0
        density = coolprop_props("D", "P", pressure_pa, "T", temperature_k, "Water")
        return {
            "h_kJ_per_kg": float(enthalpy),
            "s_kJ_per_kgK": float(entropy),
            "rho_kg_per_m3": float(density),
        }

    def saturated_steam(self, pressure_bar: float) -> Dict[str, float]:
        pressure_pa = ensure_quantity(pressure_bar, "bar").to("pascal").magnitude
        temperature_k = coolprop_props("T", "P", pressure_pa, "Q", 1.0, "Water")
        enthalpy = coolprop_props("H", "P", pressure_pa, "Q", 1.0, "Water") / 1000.0
        entropy = coolprop_props("S", "P", pressure_pa, "Q", 1.0, "Water") / 1000.0
        return {
            "T_C": ensure_quantity(temperature_k, "kelvin").to("degC").magnitude,
            "h_kJ_per_kg": float(enthalpy),
            "s_kJ_per_kgK": float(entropy),
        }

    def humid_air(self, temperature_c: float, rh_pct: float, pressure_bar: float) -> Dict[str, float]:
        temperature_k = ensure_quantity(temperature_c, "degC").to("kelvin").magnitude
        pressure_pa = ensure_quantity(pressure_bar, "bar").to("pascal").magnitude
        humidity_ratio = max(min(rh_pct / 100.0, 1.0), 0.0)
        if HAPropsSI is None:
            cp = 1.005
            h = cp * (temperature_k - ureg.Quantity(0.0, "kelvin").magnitude)
            return {
                "specific_heat_kJ_per_kgK": cp,
                "enthalpy_kJ_per_kg": h / 1000.0,
                "humidity_ratio": humidity_ratio,
            }
        enthalpy = HAPropsSI("H", "T", temperature_k, "R", humidity_ratio, "P", pressure_pa)
        cp = HAPropsSI("C", "T", temperature_k, "R", humidity_ratio, "P", pressure_pa)
        omega = HAPropsSI("W", "T", temperature_k, "R", humidity_ratio, "P", pressure_pa)
        rho = HAPropsSI("D", "T", temperature_k, "R", humidity_ratio, "P", pressure_pa)
        return {
            "enthalpy_kJ_per_kg": enthalpy / 1000.0,
            "specific_heat_kJ_per_kgK": cp / 1000.0,
            "humidity_ratio": omega,
            "rho_kg_per_m3": rho,
        }


@dataclass
class IAPWSBackend:
    """Fallback backend based on the `iapws` package."""

    def steam_props(self, pressure_bar: float, temperature_c: float) -> Dict[str, float]:
        pressure_mpa = ensure_quantity(pressure_bar, "bar").to("megapascal").magnitude
        temperature_k = ensure_quantity(temperature_c, "degC").to("kelvin").magnitude
        state = IAPWS97(P=pressure_mpa, T=temperature_k)
        return {
            "h_kJ_per_kg": float(state.h),
            "s_kJ_per_kgK": float(state.s),
            "rho_kg_per_m3": float(state.rho),
        }

    def saturated_steam(self, pressure_bar: float) -> Dict[str, float]:
        pressure_mpa = ensure_quantity(pressure_bar, "bar").to("megapascal").magnitude
        state = IAPWS97(P=pressure_mpa, x=1.0)
        return {
            "T_C": ensure_quantity(state.T, "kelvin").to("degC").magnitude,
            "h_kJ_per_kg": float(state.h),
            "s_kJ_per_kgK": float(state.s),
        }

    def humid_air(self, temperature_c: float, rh_pct: float, pressure_bar: float) -> Dict[str, float]:  # pragma: no cover - simple fallback
        temperature_k = ensure_quantity(temperature_c, "degC").to("kelvin").magnitude
        cp = 1.005
        enthalpy = cp * (temperature_k - 273.15)
        return {
            "enthalpy_kJ_per_kg": enthalpy / 1000.0,
            "specific_heat_kJ_per_kgK": cp,
            "humidity_ratio": rh_pct / 100.0,
        }


def _default_backend() -> PropertyBackend:
    if coolprop_props is not None:
        return CoolPropBackend()
    if IAPWS97 is not None:
        return IAPWSBackend()
    raise RuntimeError("Neither CoolProp nor iapws is available for property calculations")


BACKEND: PropertyBackend = _default_backend()


def steam_props(pressure_bar: float, temperature_c: float) -> Dict[str, float]:
    """Return primary steam properties for the provided state."""

    return BACKEND.steam_props(pressure_bar, temperature_c)


def saturated_steam(pressure_bar: float) -> Dict[str, float]:
    """Return saturated steam properties at the supplied pressure."""

    return BACKEND.saturated_steam(pressure_bar)


def humid_air_props(temperature_c: float, rh_pct: float, pressure_bar: float) -> Dict[str, float]:
    """Return humid air properties using the available backend."""

    return BACKEND.humid_air(temperature_c, rh_pct, pressure_bar)


def load_vendor_curve(curve_id: str) -> Dict[str, Any] | None:
    """Load a vendor curve JSON dictionary using environment hints."""

    path = os.getenv("HBD_VENDOR_CURVE_PATH")
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError:
        return None
    return data.get(curve_id)


__all__ = [
    "steam_props",
    "saturated_steam",
    "humid_air_props",
    "load_vendor_curve",
]
