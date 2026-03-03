"""Domain enums — business-level constants."""

from enum import StrEnum


class LogFormat(StrEnum):
    """Supported Nginx log formats."""

    COMBINED = "combined"
    CUSTOM = "custom"
