"""Read-only MCP tools for searching AutoSys job log files."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any

from mcp.server.fastmcp import FastMCP

DEFAULT_LOG_ROOT = r"\\server01\Log"
MAX_RESULT_LIMIT = 1000
MAX_SNIPPET_LENGTH = 1000

mcp = FastMCP("autosys-log-search")


def _validate_date(date: str) -> None:
    try:
        parsed_date = datetime.strptime(date, "%d%m%Y")
    except ValueError as exc:
        raise ValueError("date must be a valid date in DDMMYYYY format") from exc
    if parsed_date.strftime("%d%m%Y") != date:
        raise ValueError("date must be a valid date in DDMMYYYY format")


def _validate_job_name(job_name: str) -> None:
    windows_job_path = PureWindowsPath(job_name)
    if (
        not job_name
        or job_name in {".", ".."}
        or windows_job_path.name != job_name
        or re.search(r'[<>:"/\\|?*\x00-\x1f]', job_name)
    ):
        raise ValueError("job_name must be a single valid folder name")


def _is_log_date(value: str) -> bool:
    try:
        _validate_date(value)
    except ValueError:
        return False
    return True


def search_log_files(
    log_root: str | Path,
    date: str | None = None,
    job_name: str | None = None,
    search_text: str | None = None,
    *,
    case_sensitive: bool = False,
    max_results: int = 100,
) -> dict[str, Any]:
    """Search matching lines under ``log_root/date/job_name``."""
    if date is None and job_name is None and not search_text:
        raise ValueError("provide at least one of date, job_name, or search_text")
    if date is not None:
        _validate_date(date)
    if job_name is not None:
        _validate_job_name(job_name)
    if not 1 <= max_results <= MAX_RESULT_LIMIT:
        raise ValueError(f"max_results must be between 1 and {MAX_RESULT_LIMIT}")

    root = Path(log_root)
    if not root.is_dir():
        raise FileNotFoundError(f"AutoSys log root does not exist: {root}")

    if date is not None:
        date_dirs = [root / date]
        if not date_dirs[0].is_dir():
            raise FileNotFoundError(f"AutoSys log date directory does not exist: {date_dirs[0]}")
    else:
        date_dirs = sorted(
            path for path in root.iterdir()
            if path.is_dir() and _is_log_date(path.name)
        )

    job_dirs: list[Path] = []
    for date_dir in date_dirs:
        if job_name is not None:
            candidate = date_dir / job_name
            if candidate.is_dir():
                job_dirs.append(candidate)
            elif date is not None:
                raise FileNotFoundError(f"AutoSys job directory does not exist: {candidate}")
        else:
            job_dirs.extend(sorted(path for path in date_dir.iterdir() if path.is_dir()))
    if job_name is not None and not job_dirs:
        raise FileNotFoundError(f"AutoSys job directory not found for job: {job_name}")

    search_dir = job_dirs[0] if date is not None and job_name is not None else root
    needle = search_text if case_sensitive else (search_text or "").casefold()
    files_scanned = 0
    matches: list[dict[str, Any]] = []
    truncated = False

    for job_dir in job_dirs:
        files = sorted(
            path for path in job_dir.rglob("*") if path.is_file() and not path.is_symlink()
        )
        for file_path in files:
            files_scanned += 1
            with file_path.open("r", encoding="utf-8", errors="replace") as log_file:
                for line_number, line in enumerate(log_file, start=1):
                    haystack = line if case_sensitive else line.casefold()
                    if needle not in haystack:
                        continue
                    if len(matches) == max_results:
                        truncated = True
                        break

                    snippet = line.rstrip("\r\n")
                    if len(snippet) > MAX_SNIPPET_LENGTH:
                        snippet = snippet[:MAX_SNIPPET_LENGTH] + "…"
                    matches.append(
                        {
                            "date": job_dir.parent.name,
                            "job_name": job_dir.name,
                            "file": str(file_path.relative_to(job_dir)),
                            "line": line_number,
                            "text": snippet,
                        }
                    )
                if truncated:
                    break
        if truncated:
            break

    return {
        "directory": str(search_dir),
        "search_text": search_text,
        "files_scanned": files_scanned,
        "match_count": len(matches),
        "truncated": truncated,
        "matches": matches,
    }


@mcp.tool()
def search_autosys_logs(
    date: str | None = None,
    job_name: str | None = None,
    search_text: str | None = None,
    case_sensitive: bool = False,
    max_results: int = 100,
) -> dict[str, Any]:
    """Search AutoSys logs with any combination of date, job, and text filters.

    The folder structure is ``AUTOSYS_LOG_ROOT/<DDMMYYYY>/<job_name>``.
    Matching is case-insensitive by default and includes nested files. Supply
    at least one filter to avoid scanning the entire log root.
    """
    log_root = os.environ.get("AUTOSYS_LOG_ROOT", DEFAULT_LOG_ROOT)
    return search_log_files(
        log_root,
        date,
        job_name,
        search_text,
        case_sensitive=case_sensitive,
        max_results=max_results,
    )


def main() -> None:
    """Start the MCP server using configured stdio or HTTP transport."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run(transport="stdio")
        return

    if transport in {"streamable-http", "sse"}:
        mcp.settings.host = os.environ.get("MCP_HOST", "0.0.0.0")
        mcp.settings.port = int(os.environ.get("MCP_PORT", "8001"))
        mcp.run(transport=transport)
        return

    raise ValueError(
        "MCP_TRANSPORT must be one of: stdio, streamable-http, sse"
    )


if __name__ == "__main__":
    main()
