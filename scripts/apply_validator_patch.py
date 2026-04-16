from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


EXPECTED_VERSION = "0.14.0"
PATCH_FILES = [
    Path("crawler/enrich/generative/openclaw_agent.py"),
    Path("scripts/ws_client.py"),
    Path("scripts/validator_runtime.py"),
]


def _skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_target_root() -> Path:
    return Path.home() / ".codex" / "skills" / "mine-worknet"


def _normalize_target_root(target_root: Path) -> Path:
    if (target_root / "SKILL.md").exists():
        return target_root
    nested = target_root / "mine-worknet"
    if (nested / "SKILL.md").exists():
        return nested
    return target_root


def _read_version(skill_md: Path) -> str | None:
    if not skill_md.exists():
        return None
    for line in skill_md.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def _copy_with_backup(target_root: Path, backup_root: Path, dry_run: bool) -> list[dict[str, str]]:
    operations: list[dict[str, str]] = []
    source_root = _skill_root() / "assets" / "mine-worknet"
    for rel in PATCH_FILES:
        src = source_root / rel
        dst = target_root / rel
        backup = backup_root / rel
        if not src.exists():
            raise FileNotFoundError(f"missing bundled patch file: {src}")
        if not dst.exists():
            raise FileNotFoundError(f"target file not found: {dst}")

        changed = src.read_bytes() != dst.read_bytes()
        operations.append(
            {
                "file": str(rel).replace("\\", "/"),
                "status": "update" if changed else "already_matches",
                "target": str(dst),
                "backup": str(backup),
            }
        )
        if dry_run:
            continue

        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, backup)
        shutil.copy2(src, dst)
    return operations


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Mine validator stability patch.")
    parser.add_argument("--target-root", default=str(_default_target_root()))
    parser.add_argument("--force", action="store_true", help="Apply even when mine-worknet version differs.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target_root = _normalize_target_root(Path(args.target_root).expanduser().resolve())
    skill_md = target_root / "SKILL.md"
    version = _read_version(skill_md)

    if not target_root.exists():
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": f"target root does not exist: {target_root}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    if version and version != EXPECTED_VERSION and not args.force:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "message": f"mine-worknet version mismatch: expected {EXPECTED_VERSION}, found {version}",
                    "target_root": str(target_root),
                    "hint": "Re-run with --force after reviewing the target skill layout.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = target_root / f".validator-stability-backup-{timestamp}"
    operations = _copy_with_backup(target_root, backup_root, args.dry_run)

    print(
        json.dumps(
            {
                "status": "dry_run" if args.dry_run else "ok",
                "target_root": str(target_root),
                "detected_version": version,
                "expected_version": EXPECTED_VERSION,
                "backup_root": str(backup_root),
                "operations": operations,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
