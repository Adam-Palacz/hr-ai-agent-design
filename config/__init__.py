"""Configuration package."""
try:
    from config.settings import Settings, settings
except Exception:  # pragma: no cover
    # Allow importing config package in minimal environments (e.g. seed/reset scripts)
    Settings = None  # type: ignore
    settings = None  # type: ignore

__all__ = ["Settings", "settings"]

