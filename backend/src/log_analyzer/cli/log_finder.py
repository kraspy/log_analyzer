"""Find the most recent Nginx log file in a directory.

Scans the directory **once** with ``os.scandir`` and a compiled regex
to locate files matching ``nginx-access-ui.log-YYYYMMDD[.gz]``.
Files with other extensions (``.bz2``, etc.) are intentionally ignored.
"""

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Matches: nginx-access-ui.log-20170630      (plain)
#           nginx-access-ui.log-20170630.gz   (gzip)
_LOG_PATTERN = re.compile(
    r"^nginx-access-ui\.log-(?P<date>\d{8})(?P<ext>\.gz)?$",
)


@dataclass(frozen=True)
class LogFileInfo:
    """Metadata about a discovered log file.

    Attributes:
        path: Absolute path to the log file.
        date: Date parsed from the filename.
        ext: File extension (``.gz`` or empty string).
    """

    path: Path
    date: datetime
    ext: str


def find_latest_log(log_dir: Path) -> LogFileInfo | None:
    """Find the most recent ``nginx-access-ui.log-*`` in *log_dir*.

    Performs a **single pass** over directory entries using ``os.scandir``
    (no ``glob``, no sorting). Only plain and ``.gz`` files are considered;
    ``.bz2`` and other extensions are skipped.

    Args:
        log_dir: Directory to search.

    Returns:
        ``LogFileInfo`` for the newest log, or ``None`` if nothing found.
    """
    latest: LogFileInfo | None = None

    if not log_dir.is_dir():
        return None

    with os.scandir(log_dir) as entries:
        for entry in entries:
            if not entry.is_file():
                continue

            match = _LOG_PATTERN.match(entry.name)
            if match is None:
                continue

            date = datetime.strptime(match.group("date"), "%Y%m%d")
            ext = match.group("ext") or ""
            info = LogFileInfo(
                path=Path(entry.path),
                date=date,
                ext=ext,
            )

            if latest is None or info.date > latest.date:
                latest = info

    return latest
