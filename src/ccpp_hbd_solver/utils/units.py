"""Shared Pint unit registry for the solver."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pint import Quantity, UnitRegistry


@lru_cache(maxsize=1)
def _build_registry() -> UnitRegistry:
    registry = UnitRegistry(auto_reduce_dimensions=True)
    registry.setup_matplotlib(True)
    registry.default_format = "~P"
    registry.define("pct = 0.01 = percent")
    return registry


ureg = _build_registry()
Q_ = ureg.Quantity


def ensure_quantity(value: Any, unit: str) -> Quantity:
    """Return *value* as a Pint quantity expressed in *unit*."""

    if isinstance(value, Quantity):
        return value.to(unit)
    return Q_(float(value), unit)


def magnitude(value: Any, unit: str) -> float:
    """Return the float magnitude of *value* expressed in *unit*."""

    return ensure_quantity(value, unit).magnitude


__all__ = ["ureg", "Q_", "ensure_quantity", "magnitude"]
