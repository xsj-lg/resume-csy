#!/usr/bin/env python3
from __future__ import annotations

import shutil
import tarfile
import tempfile
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT_DIR / "VERSION"
VERSION = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "dev"
PACKAGE_NAME = f"recruitment-system-linux-{VERSION}"
RELEASE_DIR = ROOT_DIR / "release" / "linux"
BUILD_BASE = ROOT_DIR / ".package_build"
INCLUDE_DIRS = ["app", "web", "data", "deploy", "scripts", "templates","config"]
INCLUDE_FILES = ["README.md", "VERSION"]


def create_run_sh(package_root: Path) -> None:
    content = """#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail
cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required to run this release." >&2
  exit 1
fi
bash scripts/resume_app_up.sh
"""
    run_script = package_root / "run.sh"
    run_script.write_text(content)
    run_script.chmod(0o755)


def copy_content(temp_package_root: Path) -> None:
    temp_package_root.mkdir(parents=True, exist_ok=True)
    for rel in INCLUDE_DIRS:
        src = ROOT_DIR / rel
        dest = temp_package_root / rel
        if src.exists():
            if src.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest, symlinks=True, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)
    for rel in INCLUDE_FILES:
        src = ROOT_DIR / rel
        if src.is_file():
            shutil.copy2(src, temp_package_root / rel)


def make_tarball(temp_dir: Path, package_root_name: str) -> Path:
    tarball_dir = RELEASE_DIR
    tarball_dir.mkdir(parents=True, exist_ok=True)
    tarball_path = tarball_dir / f"{package_root_name}.tar.gz"
    if tarball_path.exists():
        try:
            tarball_path.unlink()
        except PermissionError:
            suffix = int(time.time())
            tarball_path = tarball_dir / f"{package_root_name}-{suffix}.tar.gz"
    with tarfile.open(tarball_path, "w:gz") as tar:
        tar.add(temp_dir / package_root_name, arcname=package_root_name)
    return tarball_path


def main() -> int:
    if BUILD_BASE.exists():
        shutil.rmtree(BUILD_BASE, ignore_errors=True)
    BUILD_BASE.mkdir(parents=True, exist_ok=True)

    package_root = BUILD_BASE / PACKAGE_NAME
    copy_content(package_root)
    create_run_sh(package_root)
    tarball = make_tarball(BUILD_BASE, PACKAGE_NAME)
    print("Created Linux release:", tarball)
    shutil.rmtree(BUILD_BASE, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
