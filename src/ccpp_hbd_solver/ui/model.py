"""View-model abstractions for the diagram-based GUI."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Deque, Iterable, Mapping, MutableMapping, Sequence

from .events import EventBus


PathTuple = tuple[str, ...]


def _resolve_path(data: Mapping[str, Any], path: Sequence[str]) -> Any:
    value: Any = data
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _assign_path(data: MutableMapping[str, Any], path: Sequence[str], value: Any) -> None:
    current: MutableMapping[str, Any] = data
    for key in path[:-1]:
        next_value = current.get(key)
        if not isinstance(next_value, MutableMapping):
            next_value = {}
            current[key] = next_value
        current = next_value
    current[path[-1]] = value


def _delete_path(data: MutableMapping[str, Any], path: Sequence[str]) -> None:
    current: MutableMapping[str, Any] = data
    for key in path[:-1]:
        next_value = current.get(key)
        if not isinstance(next_value, MutableMapping):
            return
        current = next_value
    current.pop(path[-1], None)


@dataclass
class CaseModel:
    """State container for the GUI, exposing undo/redo and progress updates."""

    bus: EventBus
    max_history: int = 10
    case_data: dict[str, Any] = field(default_factory=dict)
    result: Mapping[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    progress_step: str | None = None
    progress_value: float = 0.0

    def __post_init__(self) -> None:
        self._undo_stack: Deque[dict[str, Any]] = deque(maxlen=self.max_history)
        self._redo_stack: Deque[dict[str, Any]] = deque(maxlen=self.max_history)

    # ------------------------------------------------------------------
    # Case data lifecycle
    # ------------------------------------------------------------------
    def load_case(self, data: Mapping[str, Any]) -> None:
        self.case_data = deepcopy(dict(data))
        self.result = None
        self.warnings = []
        self.progress_step = None
        self.progress_value = 0.0
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.bus.publish("case_loaded", case=deepcopy(self.case_data))
        self.bus.publish("result_cleared")
        self.bus.publish("history_changed", can_undo=False, can_redo=False)

    def get_value(self, path: Sequence[str]) -> Any:
        return _resolve_path(self.case_data, path)

    def set_value(self, path: Sequence[str], value: Any, *, record_history: bool = True) -> None:
        if not path:
            return
        current = self.get_value(path)
        if current == value:
            return
        if record_history:
            self._push_history_snapshot()
        _assign_path(self.case_data, path, value)
        self.bus.publish("value_changed", path=tuple(path), value=value, case=deepcopy(self.case_data))
        self.bus.publish("history_changed", can_undo=bool(self._undo_stack), can_redo=bool(self._redo_stack))

    def delete_path(self, path: Sequence[str]) -> None:
        if not path:
            return
        if self.get_value(path) is None:
            return
        self._push_history_snapshot()
        _delete_path(self.case_data, path)
        self.bus.publish("value_changed", path=tuple(path), value=None, case=deepcopy(self.case_data))
        self.bus.publish("history_changed", can_undo=bool(self._undo_stack), can_redo=bool(self._redo_stack))

    # ------------------------------------------------------------------
    # Undo / redo
    # ------------------------------------------------------------------
    def _push_history_snapshot(self) -> None:
        self._undo_stack.append(deepcopy(self.case_data))
        self._redo_stack.clear()

    def undo(self) -> None:
        if not self._undo_stack:
            return
        snapshot = self._undo_stack.pop()
        self._redo_stack.append(deepcopy(self.case_data))
        self.case_data = snapshot
        self.bus.publish("case_loaded", case=deepcopy(self.case_data))
        self.bus.publish("history_changed", can_undo=bool(self._undo_stack), can_redo=bool(self._redo_stack))

    def redo(self) -> None:
        if not self._redo_stack:
            return
        snapshot = self._redo_stack.pop()
        self._undo_stack.append(deepcopy(self.case_data))
        self.case_data = snapshot
        self.bus.publish("case_loaded", case=deepcopy(self.case_data))
        self.bus.publish("history_changed", can_undo=bool(self._undo_stack), can_redo=bool(self._redo_stack))

    # ------------------------------------------------------------------
    # Solver results / progress
    # ------------------------------------------------------------------
    def set_result(self, result: Mapping[str, Any] | None, warnings: Iterable[str] | None = None) -> None:
        if result is None:
            self.result = None
            self.warnings = []
            self.bus.publish("result_cleared")
            return
        self.result = result
        self.warnings = list(warnings or [])
        self.bus.publish("result_updated", result=result, warnings=self.warnings)

    def set_progress(self, step: str | None, value: float) -> None:
        self.progress_step = step
        self.progress_value = value
        self.bus.publish("progress", step=step, value=value)


__all__ = ["CaseModel", "PathTuple"]
