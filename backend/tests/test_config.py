"""Tests for CLI config loader."""

from pathlib import Path

import pytest

from log_analyzer.cli.config import Config, load_config


class TestConfig:
    """Tests for Config and load_config()."""

    def test_default_config(self) -> None:
        """Default config has expected values when no YAML provided."""
        config = load_config(None)
        assert isinstance(config, Config)
        assert config.report_size == 1000
        assert config.error_threshold == 0.2

    def test_load_from_yaml(self, tmp_path: Path) -> None:
        """Config loads all fields from a full YAML file."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(
            "LOG_DIR: /var/log/nginx\n"
            "REPORT_DIR: /var/reports\n"
            "REPORT_SIZE: 500\n"
            "ERROR_THRESHOLD: 0.1\n",
            encoding="utf-8",
        )
        config = load_config(cfg_file)
        assert config.log_dir == Path("/var/log/nginx")
        assert config.report_dir == Path("/var/reports")
        assert config.report_size == 500
        assert config.error_threshold == pytest.approx(0.1)

    def test_partial_yaml_uses_defaults(self, tmp_path: Path) -> None:
        """Unspecified YAML keys fall back to Config defaults."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("LOG_DIR: /my/logs\n", encoding="utf-8")
        config = load_config(cfg_file)
        assert config.log_dir == Path("/my/logs")
        assert config.report_size == 1000  # default

    def test_empty_yaml_uses_defaults(self, tmp_path: Path) -> None:
        """An empty YAML file produces the default Config."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("", encoding="utf-8")
        config = load_config(cfg_file)
        assert config == Config()

    def test_config_is_frozen(self) -> None:
        """Config dataclass is frozen — attribute assignment raises."""
        config = Config()
        with pytest.raises(AttributeError):
            config.report_size = 999  # type: ignore[misc]

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Explicit load of a missing file raises FileNotFoundError."""
        missing = tmp_path / "nope.yaml"
        with pytest.raises(FileNotFoundError, match="config file not found"):
            load_config(missing, explicit=True)

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """A YAML file with invalid syntax raises ValueError."""
        bad = tmp_path / "bad.yaml"
        bad.write_text("{{{invalid", encoding="utf-8")
        with pytest.raises(ValueError, match="cannot parse config file"):
            load_config(bad)

    def test_missing_default_falls_back(self, tmp_path: Path) -> None:
        """Non-explicit load of missing file silently uses defaults."""
        missing = tmp_path / "nope.yaml"
        config = load_config(missing, explicit=False)
        assert config == Config()
