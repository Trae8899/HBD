"""Theme tokens used across the diagram UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


FontDef = Tuple[str, int] | Tuple[str, int, str]


@dataclass(frozen=True)
class ThemePalette:
    window_bg: str
    canvas_bg: str
    grid_line: str
    block_outline: str
    gt_fill: str
    hrsg_fill: str
    st_fill: str
    cond_fill: str
    text_primary: str
    text_secondary: str
    value_text: str
    hotspot_bg: str
    hotspot_border: str
    warning_outline: str
    warning_fill: str
    critical_outline: str
    critical_fill: str


@dataclass(frozen=True)
class ThemeMetrics:
    canvas_width: int
    canvas_height: int
    block_outline_width: int
    stream_width: int
    hotspot_border_width: int
    spacing_small: int
    spacing_medium: int
    spacing_large: int


@dataclass(frozen=True)
class ThemeFonts:
    title: FontDef
    section: FontDef
    label: FontDef
    value: FontDef
    overlay: FontDef
    status: FontDef

    def as_dict(self) -> Dict[str, FontDef]:
        return {
            "title": self.title,
            "section": self.section,
            "label": self.label,
            "value": self.value,
            "overlay": self.overlay,
            "status": self.status,
        }


@dataclass(frozen=True)
class Theme:
    palette: ThemePalette
    fonts: ThemeFonts
    metrics: ThemeMetrics


DEFAULT_THEME = Theme(
    palette=ThemePalette(
        window_bg="#f4f6fb",
        canvas_bg="#ffffff",
        grid_line="#dce1eb",
        block_outline="#1d3557",
        gt_fill="#f3c4c4",
        hrsg_fill="#cce3de",
        st_fill="#c5dff8",
        cond_fill="#ffe8d6",
        text_primary="#1d3557",
        text_secondary="#415a77",
        value_text="#0b3954",
        hotspot_bg="#edf2fb",
        hotspot_border="#8d99ae",
        warning_outline="#f4a259",
        warning_fill="#ffe066",
        critical_outline="#d1495b",
        critical_fill="#f25f5c",
    ),
    fonts=ThemeFonts(
        title=("Segoe UI", 14, "bold"),
        section=("Segoe UI", 11, "bold"),
        label=("Segoe UI", 9, "bold"),
        value=("Segoe UI", 10),
        overlay=("Segoe UI", 10),
        status=("Segoe UI", 9),
    ),
    metrics=ThemeMetrics(
        canvas_width=1100,
        canvas_height=460,
        block_outline_width=2,
        stream_width=3,
        hotspot_border_width=1,
        spacing_small=4,
        spacing_medium=8,
        spacing_large=12,
    ),
)


HIGH_CONTRAST_THEME = Theme(
    palette=ThemePalette(
        window_bg="#1b1b1b",
        canvas_bg="#101010",
        grid_line="#3a3a3a",
        block_outline="#ffffff",
        gt_fill="#5c1a1a",
        hrsg_fill="#104c3f",
        st_fill="#0d3f70",
        cond_fill="#5a3210",
        text_primary="#f5f5f5",
        text_secondary="#d7d7d7",
        value_text="#f1c40f",
        hotspot_bg="#232323",
        hotspot_border="#f1f1f1",
        warning_outline="#ffcc00",
        warning_fill="#4d3a00",
        critical_outline="#ff5f57",
        critical_fill="#661a18",
    ),
    fonts=ThemeFonts(
        title=("Segoe UI", 14, "bold"),
        section=("Segoe UI", 11, "bold"),
        label=("Segoe UI", 9, "bold"),
        value=("Segoe UI", 10),
        overlay=("Segoe UI", 10),
        status=("Segoe UI", 9),
    ),
    metrics=ThemeMetrics(
        canvas_width=1100,
        canvas_height=460,
        block_outline_width=3,
        stream_width=4,
        hotspot_border_width=2,
        spacing_small=4,
        spacing_medium=8,
        spacing_large=12,
    ),
)


def get_theme(high_contrast: bool = False) -> Theme:
    """Return the default or high-contrast theme."""

    return HIGH_CONTRAST_THEME if high_contrast else DEFAULT_THEME


__all__ = ["Theme", "ThemePalette", "ThemeMetrics", "ThemeFonts", "get_theme"]
