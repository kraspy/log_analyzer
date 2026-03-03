"""Tests for the CLI log finder module."""

from datetime import datetime
from pathlib import Path

import pytest

from log_analyzer.cli.log_finder import LogFileInfo, find_latest_log


@pytest.fixture()
def log_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with sample log files."""
    return tmp_path


class TestFindLatestLog:
    """Tests for find_latest_log()."""

    def test_finds_plain_log(self, log_dir: Path) -> None:
        """Detects a plain (uncompressed) log file by date pattern."""
        (log_dir / "nginx-access-ui.log-20170630").touch()
        result = find_latest_log(log_dir)
        assert result is not None
        assert result.date == datetime(2017, 6, 30)
        assert result.ext == ""

    def test_finds_gz_log(self, log_dir: Path) -> None:
        """Detects a gzip-compressed log file."""
        (log_dir / "nginx-access-ui.log-20170630.gz").touch()
        result = find_latest_log(log_dir)
        assert result is not None
        assert result.ext == ".gz"

    def test_returns_latest_by_date(self, log_dir: Path) -> None:
        """Returns the log with the most recent date when several exist."""
        (log_dir / "nginx-access-ui.log-20170628").touch()
        (log_dir / "nginx-access-ui.log-20170630").touch()
        (log_dir / "nginx-access-ui.log-20170629").touch()
        result = find_latest_log(log_dir)
        assert result is not None
        assert result.date == datetime(2017, 6, 30)

    def test_ignores_bz2(self, log_dir: Path) -> None:
        """Must NOT match .bz2 files (HW requirement)."""
        (log_dir / "nginx-access-ui.log-20170630.bz2").touch()
        result = find_latest_log(log_dir)
        assert result is None

    def test_ignores_other_extensions(self, log_dir: Path) -> None:
        """Skips .zip, .xz and other non-supported extensions."""
        (log_dir / "nginx-access-ui.log-20170630.zip").touch()
        (log_dir / "nginx-access-ui.log-20170630.xz").touch()
        result = find_latest_log(log_dir)
        assert result is None

    def test_ignores_unrelated_files(self, log_dir: Path) -> None:
        """Skips files that don't match the nginx log naming pattern."""
        (log_dir / "access.log").touch()
        (log_dir / "error.log").touch()
        (log_dir / "readme.txt").touch()
        result = find_latest_log(log_dir)
        assert result is None

    def test_empty_directory(self, log_dir: Path) -> None:
        """Returns None when the directory contains no log files."""
        result = find_latest_log(log_dir)
        assert result is None

    def test_ignores_directories(self, log_dir: Path) -> None:
        """Skips subdirectories even if their name matches the pattern."""
        (log_dir / "nginx-access-ui.log-20170630").mkdir()
        result = find_latest_log(log_dir)
        assert result is None

    def test_prefers_plain_over_gz_same_date(self, log_dir: Path) -> None:
        """When both plain and .gz exist for same date, either is fine."""
        (log_dir / "nginx-access-ui.log-20170630").touch()
        (log_dir / "nginx-access-ui.log-20170630.gz").touch()
        result = find_latest_log(log_dir)
        assert result is not None
        assert result.date == datetime(2017, 6, 30)

    def test_result_is_dataclass(self, log_dir: Path) -> None:
        """Result is a LogFileInfo dataclass with proper field types."""
        (log_dir / "nginx-access-ui.log-20170630").touch()
        result = find_latest_log(log_dir)
        assert isinstance(result, LogFileInfo)
        assert isinstance(result.path, Path)
        assert isinstance(result.date, datetime)
