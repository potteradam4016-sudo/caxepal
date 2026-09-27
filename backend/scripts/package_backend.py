"""Package only tracked-style backend source and docs into one ZIP."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / "SCNU_PICK_backend_username.zip"
SKIP_DIRS = {".test-deps", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".git", "data", "uploads"}
SKIP_FILES = {".env", "SHA256SUMS.txt"}


def included(path: Path) -> bool:
    parts = path.relative_to(ROOT).parts
    return (not any(part in SKIP_DIRS for part in parts[:-1])
            and path.name not in SKIP_FILES
            and (not path.name.startswith(".env.") or path.name == ".env.example")
            and not path.name.endswith((".pyc", ".db", ".sqlite3", ".log", ".pem", ".key")))


def main():
    manifest = ROOT / "docs" / "FILE_MANIFEST.md"
    preliminary = sorted(p for p in ROOT.rglob("*") if p.is_file() and included(p))
    names = sorted({p.relative_to(ROOT).as_posix() for p in preliminary} | {"SHA256SUMS.txt"})
    lines = ["# 전체 백엔드 파일 목록", "", f"통합 ZIP의 `backend/`에는 파일 {len(names)}개가 들어 있습니다.",
             "개인 설정, DB, 가상환경, 테스트 캐시는 제외합니다.", "", "| 경로 | 역할 |", "| --- | --- |"]
    for name in names:
        role = ("자동 테스트" if name.startswith("tests/") else
                "DB 마이그레이션" if name.startswith("migrations/") else
                "API·업무 코드" if name.startswith("app/") else
                "실행·검증 도구" if name.startswith("scripts/") or name in {"start.py", "START.cmd"} else
                "설명·명세" if name.startswith("docs/") or name == "README.md" else "구성 파일")
        lines.append(f"| `{name}` | {role} |")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and included(p))
    hashes = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(ROOT).as_posix()}"
              for path in files]
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in [*files, ROOT / "SHA256SUMS.txt"]:
            archive.write(path, "backend/" + path.relative_to(ROOT).as_posix())
    print(f"{OUTPUT} ({len(files) + 1} files, {OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
