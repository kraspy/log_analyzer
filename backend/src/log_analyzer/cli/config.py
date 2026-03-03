"""CLI configuration loader.

Loads YAML config with sensible defaults. Config path is passed
via ``--config`` CLI argument. If no config is provided,
default values are used.

**Requirement 3**: if the config file does not exist or cannot be
parsed, the script exits with an error.

**Requirement 4**: file values override defaults; missing keys
fall back to defaults (merge semantics).
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Defaults as module-level constants so both Config and load_config
# can reference them without circular class-attribute issues.
_DEFAULT_LOG_DIR = Path("/var/log/nginx")
_DEFAULT_REPORT_DIR = Path("./reports")
_DEFAULT_REPORT_SIZE = 1000
_DEFAULT_ERROR_THRESHOLD = 0.2


@dataclass(frozen=True)
class Config:
    """Application configuration.

    Attributes:
        log_dir: Directory containing Nginx log files.
        report_dir: Directory where HTML reports are saved.
        report_size: Maximum number of URLs in the report table.
        error_threshold: Fraction of unparseable lines that triggers exit (0.0-1.0).
        log_file: Path for the application's own log file (None = stdout).
        ts_file: Path for the heartbeat timestamp file.
    """

    log_dir: Path = field(default_factory=lambda: _DEFAULT_LOG_DIR)
    report_dir: Path = field(default_factory=lambda: _DEFAULT_REPORT_DIR)
    report_size: int = _DEFAULT_REPORT_SIZE
    error_threshold: float = _DEFAULT_ERROR_THRESHOLD
    log_file: Path | None = None
    ts_file: Path | None = None


def load_config(config_path: Path | None) -> Config:
    """Load config from a YAML file, falling back to defaults.

    If *config_path* is ``None``, returns the default ``Config``.

    **Requirement 3**: exits with code 1 when the file is missing
    or fails to parse (YAML syntax error, permission denied, etc.).

    Args:
        config_path: Path to the YAML config file, or ``None`` for defaults.

    Returns:
        Populated ``Config`` instance.
    """
    if config_path is None:
        return Config()

    # Requirement 3: file MUST exist — exit on FileNotFoundError
    if not config_path.exists():
        print(
            f"ERROR: config file not found: {config_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with config_path.open(encoding="utf-8") as f:
            raw: dict[str, Any] = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as exc:
        print(
            f"ERROR: cannot parse config file {config_path}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    return Config(
        log_dir=Path(raw["LOG_DIR"]) if "LOG_DIR" in raw else _DEFAULT_LOG_DIR,
        report_dir=Path(raw["REPORT_DIR"]) if "REPORT_DIR" in raw else _DEFAULT_REPORT_DIR,
        report_size=int(raw.get("REPORT_SIZE", _DEFAULT_REPORT_SIZE)),
        error_threshold=float(raw.get("ERROR_THRESHOLD", _DEFAULT_ERROR_THRESHOLD)),
        log_file=Path(raw["LOG_FILE"]) if "LOG_FILE" in raw else None,
        ts_file=Path(raw["TS_FILE"]) if "TS_FILE" in raw else None,
    )
