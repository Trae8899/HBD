"""Top-level package for the CCPP Heat Balance Data solver."""

from importlib import metadata


def get_version() -> str:
    """Return the installed package version."""
    try:
        return metadata.version("ccpp-hbd-solver")
    except metadata.PackageNotFoundError:  # pragma: no cover - local dev fallback
        return "0.0.0"
