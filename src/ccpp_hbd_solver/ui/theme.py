"""Color and font constants for the HBD diagram GUI."""

from __future__ import annotations

COLORS: dict[str, str] = {
    "window_bg": "#f4f6fb",
    "canvas_bg": "#ffffff",
    "grid_line": "#dce1eb",
    "block_outline": "#1d3557",
    "gt_fill": "#f3c4c4",
    "hrsg_fill": "#cce3de",
    "st_fill": "#c5dff8",
    "cond_fill": "#ffe8d6",
    "hotspot_bg": "#edf2fb",
    "hotspot_border": "#8d99ae",
    "text_primary": "#1d3557",
    "text_secondary": "#415a77",
    "value_text": "#0b3954",
    "warning_text": "#d1495b",
    "warning_fill": "#ffe066",
    "critical_fill": "#f25f5c",
    "overlay_bg": "#ffffff",
}

FONTS: dict[str, tuple[str, int] | tuple[str, int, str]] = {
    "title": ("Segoe UI", 14, "bold"),
    "section": ("Segoe UI", 11, "bold"),
    "label": ("Segoe UI", 9, "bold"),
    "value": ("Segoe UI", 10),
    "overlay": ("Segoe UI", 10),
    "status": ("Segoe UI", 9),
}
