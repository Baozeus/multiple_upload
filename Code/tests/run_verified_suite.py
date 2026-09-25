"""Run the current verification suite and save fresh, timestamped evidence."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = PROJECT_ROOT / "evidence"


def run_command(name: str, arguments: list[str], extra_env=None) -> dict[str, object]:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    if extra_env:
        environment.update(extra_env)
    started = datetime.now().astimezone()
    completed = subprocess.run(
        arguments,
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    ended = datetime.now().astimezone()
    log_path = EVIDENCE_DIR / f"{name}.log"
    log_path.write_text(
        "$ " + subprocess.list2cmdline(arguments) + "\n\n"
        + completed.stdout
        + ("\n[stderr]\n" + completed.stderr if completed.stderr else ""),
        encoding="utf-8",
    )
    return {
        "name": name,
        "command": subprocess.list2cmdline(arguments),
        "started_at": started.isoformat(timespec="seconds"),
        "ended_at": ended.isoformat(timespec="seconds"),
        "exit_code": completed.returncode,
        "log": str(log_path.relative_to(PROJECT_ROOT)),
    }


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    results = [
        run_command(
            "unit-integration-ui-tests",
            [
                sys.executable,
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "Code/tests",
                "-v",
            ],
        ),
        run_command(
            "mysql-package-tests",
            [
                sys.executable,
                "-B",
                "-m",
                "pytest",
                "Code/mysql_database/tests",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            {
                "PYTHONPATH": str(
                    PROJECT_ROOT / "Code" / "mysql_database" / "src"
                )
            },
        ),
    ]
    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "project_root": str(PROJECT_ROOT),
        "results": results,
        "passed": all(result["exit_code"] == 0 for result in results),
    }
    (EVIDENCE_DIR / "test-results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
