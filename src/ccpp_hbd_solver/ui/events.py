"""Simple event bus utilities for decoupling UI components."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict


EventCallback = Callable[..., None]


class EventBus:
    """Lightweight publish/subscribe dispatcher."""

    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, list[EventCallback]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------
    def subscribe(self, event: str, callback: EventCallback) -> Callable[[], None]:
        """Register *callback* for *event* and return an unsubscribe handle."""

        self._subscribers[event].append(callback)

        def _unsubscribe() -> None:
            callbacks = self._subscribers.get(event)
            if not callbacks:
                return
            try:
                callbacks.remove(callback)
            except ValueError:
                return
            if not callbacks:
                self._subscribers.pop(event, None)

        return _unsubscribe

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------
    def publish(self, event: str, **payload: Any) -> None:
        """Invoke all callbacks registered for *event* with *payload*."""

        for callback in list(self._subscribers.get(event, [])):
            try:
                callback(**payload)
            except Exception:  # pragma: no cover - GUI diagnostics
                # Individual subscriber failures should not break the bus.
                continue


__all__ = ["EventBus", "EventCallback"]
