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


def _parse_locked_paths(ui_state: Mapping[str, Any] | None) -> set[PathTuple]:
    locked: set[PathTuple] = set()
    if not ui_state:
        return locked
    raw_paths = ui_state.get("locked_paths", [])
    for entry in raw_paths:
        if isinstance(entry, Sequence) and not isinstance(entry, (str, bytes)):
            locked.add(tuple(str(part) for part in entry))
        elif isinstance(entry, str):
            parts = [segment.strip() for segment in entry.split(".") if segment.strip()]
            if parts:
                locked.add(tuple(parts))
    return locked


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
    locked_paths: set[PathTuple] = field(default_factory=set)

    def __post_init__(self) -> None:
        self._undo_stack: Deque[tuple[dict[str, Any], tuple[PathTuple, ...]]] = deque(maxlen=self.max_history)
        self._redo_stack: Deque[tuple[dict[str, Any], tuple[PathTuple, ...]]] = deque(maxlen=self.max_history)

    # ------------------------------------------------------------------
    # Case data lifecycle
    # ------------------------------------------------------------------
    def load_case(self, data: Mapping[str, Any]) -> None:
        raw_case = deepcopy(dict(data))
        ui_state = raw_case.pop("_ui", {}) if isinstance(raw_case, MutableMapping) else {}
        self.case_data = raw_case
        self.result = None
        self.warnings = []
        self.progress_step = None
        self.progress_value = 0.0
        self.locked_paths = _parse_locked_paths(ui_state)
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.bus.publish("case_loaded", case=deepcopy(self.case_data))
        self._publish_lock_state()
        self.bus.publish("result_cleared")
        self.bus.publish("history_changed", can_undo=False, can_redo=False)

    def get_value(self, path: Sequence[str]) -> Any:
        return _resolve_path(self.case_data, path)

    def set_value(self, path: Sequence[str], value: Any, *, record_history: bool = True) -> None:
        if not path:
            return
        if self.is_locked(path):
            self.bus.publish("lock_violation", path=tuple(path))
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
        if self.is_locked(path):
            self.bus.publish("lock_violation", path=tuple(path))
            return
        if self.get_value(path) is None:
            return
        self._push_history_snapshot()
        _delete_path(self.case_data, path)
        self.bus.publish("value_changed", path=tuple(path), value=None, case=deepcopy(self.case_data))
        self.bus.publish("history_changed", can_undo=bool(self._undo_stack), can_redo=bool(self._redo_stack))

    def is_locked(self, path: Sequence[str]) -> bool:
        target = tuple(path)
        return any(target == locked or target[: len(locked)] == locked for locked in self.locked_paths)

    def is_explicitly_locked(self, path: Sequence[str]) -> bool:
        return tuple(path) in self.locked_paths

    def set_locked(self, path: Sequence[str], locked: bool, *, record_history: bool = True) -> None:
        target = tuple(path)
        currently_locked = any(target == existing for existing in self.locked_paths)
        if locked == currently_locked:
            return
        if record_history:
            self._push_history_snapshot()
        if locked:
            self.locked_paths.add(target)
        else:
            self.locked_paths = {item for item in self.locked_paths if item != target and not item[: len(target)] == target}
        self._publish_lock_state()
        self.bus.publish("history_changed", can_undo=bool(self._undo_stack), can_redo=bool(self._redo_stack))
        self.bus.publish("lock_toggled", path=target, locked=locked)

    def serialize_case(self) -> dict[str, Any]:
        case_copy = deepcopy(self.case_data)
        if self.locked_paths:
            case_copy["_ui"] = {"locked_paths": [list(path) for path in sorted(self.locked_paths)]}
        return case_copy

    # ------------------------------------------------------------------
    # Undo / redo
    # ------------------------------------------------------------------
    def _push_history_snapshot(self) -> None:
        snapshot = (deepcopy(self.case_data), tuple(sorted(self.locked_paths)))
        self._undo_stack.append(snapshot)
        self._redo_stack.clear()

    def undo(self) -> None:
        if not self._undo_stack:
            return
        snapshot_case, snapshot_locked = self._undo_stack.pop()
        redo_snapshot = (deepcopy(self.case_data), tuple(sorted(self.locked_paths)))
        self._redo_stack.append(redo_snapshot)
        self.case_data = snapshot_case
        self.locked_paths = set(snapshot_locked)
        self.bus.publish("case_loaded", case=deepcopy(self.case_data))
        self._publish_lock_state()
        self.bus.publish("history_changed", can_undo=bool(self._undo_stack), can_redo=bool(self._redo_stack))

    def redo(self) -> None:
        if not self._redo_stack:
            return
        snapshot_case, snapshot_locked = self._redo_stack.pop()
        undo_snapshot = (deepcopy(self.case_data), tuple(sorted(self.locked_paths)))
        self._undo_stack.append(undo_snapshot)
        self.case_data = snapshot_case
        self.locked_paths = set(snapshot_locked)
        self.bus.publish("case_loaded", case=deepcopy(self.case_data))
        self._publish_lock_state()
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

    def _publish_lock_state(self) -> None:
        self.bus.publish("locks_changed", locked_paths=tuple(sorted(self.locked_paths)))


__all__ = ["CaseModel", "PathTuple"]
