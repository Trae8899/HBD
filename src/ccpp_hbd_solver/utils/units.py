"""Unit conversion helpers with an optional Pint dependency."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.util import find_spec
from typing import Any, Callable, Dict, Tuple

if find_spec("pint") is not None:  # pragma: no cover - exercised in pint-enabled environments
    from pint import Quantity, UnitRegistry  # type: ignore
else:

    @dataclass
    class Quantity:  # pragma: no cover - trivial behaviour
        """Lightweight stand-in for :class:`pint.Quantity`."""

        magnitude: float
        unit: str

        def to(self, unit: str) -> "Quantity":
            return Quantity(_convert_unit(self.magnitude, self.unit, unit), unit)

    class UnitRegistry:  # pragma: no cover - trivial behaviour
        """Fallback registry supporting the minimal Pint API surface we rely on."""

        def __init__(self, *_: Any, **__: Any) -> None:
            self.default_format = "~P"

        def Quantity(self, value: Any, unit: str) -> Quantity:
            return Quantity(float(value), unit)

        def setup_matplotlib(self, *_: Any, **__: Any) -> None:
            return None

        def define(self, *_: Any, **__: Any) -> None:
            return None


_ALIASES: Dict[str, str] = {
    "%": "percent",
    "pct": "percent",
}


def _canonical(unit: str) -> str:
    normalized = unit.strip()
    return _ALIASES.get(normalized, normalized)


_CONVERSIONS: Dict[Tuple[str, str], Callable[[float], float]] = {
    ("degC", "kelvin"): lambda value: value + 273.15,
    ("kelvin", "degC"): lambda value: value - 273.15,
    ("bar", "pascal"): lambda value: value * 1e5,
    ("bar", "kilopascal"): lambda value: value * 1e2,
    ("bar", "megapascal"): lambda value: value * 1e-1,
    ("pascal", "bar"): lambda value: value / 1e5,
    ("kilopascal", "bar"): lambda value: value / 1e2,
    ("megapascal", "bar"): lambda value: value * 10.0,
    ("megapascal", "pascal"): lambda value: value * 1e6,
    ("pascal", "megapascal"): lambda value: value / 1e6,
    ("kilopascal", "pascal"): lambda value: value * 1e3,
    ("pascal", "kilopascal"): lambda value: value / 1e3,
    ("dimensionless", "percent"): lambda value: value * 100.0,
    ("percent", "dimensionless"): lambda value: value / 100.0,
}


def _convert_unit(value: float, from_unit: str, to_unit: str) -> float:
    source = _canonical(from_unit)
    target = _canonical(to_unit)
    if source == target:
        return float(value)
    key = (source, target)
    if key in _CONVERSIONS:
        return float(_CONVERSIONS[key](float(value)))
    raise ValueError(f"Unsupported conversion from '{from_unit}' to '{to_unit}'")


@lru_cache(maxsize=1)
def _build_registry() -> UnitRegistry:
    registry = UnitRegistry(auto_reduce_dimensions=True)
    if hasattr(registry, "setup_matplotlib"):
        registry.setup_matplotlib(True)
    registry.default_format = "~P"
    if hasattr(registry, "define"):
        registry.define("pct = 0.01 = percent")
    return registry


ureg = _build_registry()
Q_ = ureg.Quantity


def ensure_quantity(value: Any, unit: str) -> Quantity:
    """Return *value* as a quantity expressed in *unit*."""

    if isinstance(value, Quantity):
        return value.to(unit)
    return Q_(float(value), unit)


def magnitude(value: Any, unit: str) -> float:
    """Return the float magnitude of *value* expressed in *unit*."""

    return ensure_quantity(value, unit).magnitude


__all__ = ["ureg", "Q_", "ensure_quantity", "magnitude"]
