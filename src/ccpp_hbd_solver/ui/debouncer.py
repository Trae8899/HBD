"""Tkinter-friendly debouncer utility."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Debouncer:
    widget: any
    delay_ms: int = 300
    _after_id: str | None = field(default=None, init=False)
    _last_run: float = field(default=0.0, init=False)

    def schedule(self, callback: Callable[[], None]) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:  # pragma: no cover - Tkinter internals
                pass
        def _run() -> None:
            self._after_id = None
            self._last_run = time.time()
            callback()

        self._after_id = self.widget.after(self.delay_ms, _run)


__all__ = ["Debouncer"]
