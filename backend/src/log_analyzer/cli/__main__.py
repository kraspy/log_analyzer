"""CLI entrypoint for log_analyzer.

Usage::

    python -m log_analyzer --config config.yaml
    python -m log_analyzer                        # uses defaults

The script:
1. Loads config from YAML (or uses defaults).
2. Finds the most recent ``nginx-access-ui.log-*`` in the log directory.
3. Checks idempotency — skips if report already exists (Req 7).
4. Parses the log (generator, O(1) memory for reading).
5. Computes per-URL statistics in memory.
6. Renders an HTML report via ``string.Template`` with ``$table_json``.
7. Validates the error threshold (once, at the end).
8. Touches a ``.ts`` heartbeat file.

Monitoring:
- **structlog** JSON logs — ``debug``, ``info``, ``error`` only.
- Log file path from config; if unset → ``stdout``.
- Unexpected exceptions caught globally with traceback in log.
"""

import argparse
import gzip
import json
import logging
import statistics as stats_module
import sys
from collections import defaultdict
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import structlog

from log_analyzer.cli.config import Config, load_config
from log_analyzer.cli.log_finder import find_latest_log
from log_analyzer.cli.report_renderer import render_report
from log_analyzer.domain.models import LogEntry
from log_analyzer.infrastructure.parsers.combined import CombinedLogParser


def _setup_structlog(config: Config) -> None:
    """Configure structlog with JSON rendering.

    Writes to ``config.log_file`` if set, otherwise to ``stdout``.
    Only ``debug``, ``info``, and ``error`` levels are used
    throughout the script (per monitoring spec).
    """
    # Determine output: file or stdout
    handler: logging.Handler
    if config.log_file is not None:
        config.log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(config.log_file, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stdout)

    # Configure stdlib logging as structlog backend
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    # Configure structlog — JSON renderer for structured logs
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _compute_url_stats(
    entries: dict[str, list[float]],
    total_requests: int,
    report_size: int,
) -> list[dict[str, object]]:
    """Compute per-URL metrics from in-memory data.

    Args:
        entries: Mapping of URL → list of request_time values.
        total_requests: Total number of parsed requests.
        report_size: Max URLs to include in report.

    Returns:
        List of stat dicts sorted by time_sum descending,
        limited to *report_size* entries.
    """
    total_time = sum(sum(times) for times in entries.values())

    result: list[dict[str, object]] = []
    for url, times in entries.items():
        time_sum = sum(times)
        count = len(times)
        result.append(
            {
                "url": url,
                "count": count,
                "count_perc": round(count / total_requests * 100, 3) if total_requests else 0,
                "time_sum": round(time_sum, 3),
                "time_perc": round(time_sum / total_time * 100, 3) if total_time else 0,
                "time_avg": round(time_sum / count, 3) if count else 0,
                "time_max": round(max(times), 3) if times else 0,
                "time_med": round(stats_module.median(times), 3) if times else 0,
            }
        )

    result.sort(key=lambda s: float(s.get("time_sum", 0)), reverse=True)  # type: ignore[arg-type]
    return result[:report_size]


def _parse_log_lines(
    path: Path,
    ext: str,
    parser: CombinedLogParser,
) -> Iterator[LogEntry | None]:
    """Generator function: yields parsed entries (or None for bad lines).

    Opens the file with gzip.open or built-in open depending on extension.
    Memory usage is O(1) — reads one line at a time.

    Args:
        path: Path to the log file.
        ext: File extension ('.gz' or other).
        parser: Parser instance to use.

    Yields:
        LogEntry for successfully parsed lines, None for unparseable lines.
    """
    opener = gzip.open if ext == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as f:
        for line_number, line in enumerate(f, start=1):
            yield parser.parse_line(line, path.name, line_number)


def _run(config: Config) -> int:
    """Execute the main processing pipeline.

    Separated from ``main()`` so the global exception handler can
    catch any unexpected error with a full traceback.

    Args:
        config: Application configuration (passed, never global — Req 5).

    Returns:
        Exit code: 0 for success, 1 for error threshold exceeded.
    """
    log = structlog.get_logger()

    log.info("config_loaded", log_dir=str(config.log_dir), report_dir=str(config.report_dir))

    # ── 1. Find the most recent log ──────────────────────────
    log_info = find_latest_log(config.log_dir)
    if log_info is None:
        # Requirement 1: "an empty directory is possible, this is NOT an error"
        log.info("no_logs_found", log_dir=str(config.log_dir))
        return 0

    log.info(
        "log_found",
        path=str(log_info.path),
        date=log_info.date.strftime("%Y.%m.%d"),
    )

    # ── 2. Idempotency check (Req 7) ────────────────────────
    report_date = log_info.date.strftime("%Y.%m.%d")
    report_path = config.report_dir / f"report-{report_date}.html"

    if report_path.exists():
        log.info("report_already_exists", path=str(report_path))
        return 0

    # ── 3. Parse via generator (yield, O(1) memory) ─────────
    line_parser = CombinedLogParser()
    url_times: dict[str, list[float]] = defaultdict(list)
    total_lines = 0
    parsed_lines = 0

    for entry in _parse_log_lines(log_info.path, log_info.ext, line_parser):
        total_lines += 1
        if entry is not None:
            parsed_lines += 1
            request_time = entry.request_time if entry.request_time is not None else 0.0
            url_times[entry.path].append(request_time)

    error_lines = total_lines - parsed_lines
    log.info(
        "parsing_complete",
        parsed=parsed_lines,
        total=total_lines,
        errors=error_lines,
        unique_urls=len(url_times),
    )

    # ── 4. Error threshold check (Req M3) ────────────────────
    if total_lines > 0:
        error_ratio = error_lines / total_lines
        if error_ratio > config.error_threshold:
            log.error(
                "error_threshold_exceeded",
                error_ratio=round(error_ratio * 100, 1),
                threshold=round(config.error_threshold * 100, 1),
            )
            return 1

    # ── 5. Compute per-URL statistics ────────────────────────
    url_stats = _compute_url_stats(url_times, parsed_lines, config.report_size)
    log.debug("url_stats_computed", count=len(url_stats))

    # ── 6. Render HTML report ($table_json) ──────────────────
    table_json = json.dumps(url_stats, ensure_ascii=False)
    render_report(table_json, report_date, report_path)
    log.info("report_saved", path=str(report_path))

    # ── 7. Heartbeat (.ts file) ──────────────────────────────
    if config.ts_file is not None:
        config.ts_file.write_text(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            encoding="utf-8",
        )
        log.info("heartbeat_updated", ts_file=str(config.ts_file))

    log.info("done")
    return 0


def main() -> None:
    """CLI entrypoint — parse args, configure structlog, run pipeline.

    This is the ONLY place where ``sys.exit()`` is called.
    All other functions return values or raise exceptions.

    Wraps ``_run()`` in a global exception handler so that any
    unexpected error (bugs, disk full, Ctrl+C, etc.) is logged
    with a full traceback (Requirement M2).
    """
    arg_parser = argparse.ArgumentParser(
        description="Nginx log analyzer — generates per-URL statistics report.",
    )
    arg_parser.add_argument(
        "--config",
        type=Path,
        default=Path("./config/config.yaml"),
        help="Path to YAML config file (default: ./config/config.yaml).",
    )
    args = arg_parser.parse_args()

    # Detect if user explicitly passed --config (vs argparse default)
    config_explicit = "--config" in sys.argv

    # Load config — errors are caught here (Req 3).
    # sys.exit only in main(), never in library code.
    try:
        config = load_config(args.config, explicit=config_explicit)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Setup structlog (Req M1)
    _setup_structlog(config)

    log = structlog.get_logger()

    try:
        exit_code = _run(config)
    except KeyboardInterrupt:
        log.error("interrupted")
        sys.exit(130)
    except Exception:
        # Requirement M2: unexpected errors → log with traceback
        log.error("unexpected_error", exc_info=True)
        sys.exit(1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
