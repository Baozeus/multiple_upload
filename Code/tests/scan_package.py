"""Static package hygiene scan that never prints candidate secret values."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = PROJECT_ROOT / "evidence"
TEXT_EXTENSIONS = {
    ".py", ".md", ".json", ".txt", ".sql", ".toml", ".yaml", ".yml", ".ini", ".cfg"
}
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "assigned_secret": re.compile(
        r"(?i)\b(password|passwd|api[_-]?key|access[_-]?token|secret)\b\s*[:=]\s*['\"]([^'\"]{4,})['\"]"
    ),
}
PERSONAL_PATH = re.compile(r"(?i)\bC:\\Users\\[^\\\s]+")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    findings: list[dict[str, object]] = []
    forbidden_artifacts: list[str] = []
    absolute_paths: list[dict[str, object]] = []
    files = [path for path in PROJECT_ROOT.rglob("*") if path.is_file()]
    for path in files:
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        parts = set(path.parts)
        if (
            path.name == ".env"
            or path.suffix.lower() == ".pyc"
            or "__pycache__" in parts
            or ".pytest_cache" in parts
            or ".venv" in parts
        ):
            forbidden_artifacts.append(relative)
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                findings.append({
                    "file": relative,
                    "line": text.count("\n", 0, match.start()) + 1,
                    "kind": name,
                })
        if path.suffix.lower() == ".py":
            for match in PERSONAL_PATH.finditer(text):
                absolute_paths.append({
                    "file": relative,
                    "line": text.count("\n", 0, match.start()) + 1,
                })

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "file_count": len(files),
        "secret_findings": findings,
        "forbidden_artifacts": forbidden_artifacts,
        "personal_absolute_paths_in_python": absolute_paths,
        "clean": not findings and not forbidden_artifacts and not absolute_paths,
        "input_hashes_after": {
            "multiple_upload-main (5).zip": sha256(
                Path("D:/Download/multiple_upload-main (5).zip")
            ),
            "test_cases_upload_multiple.xlsx": sha256(
                Path("D:/Download/test_cases_upload_multiple.xlsx")
            ),
        },
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "package-scan.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
