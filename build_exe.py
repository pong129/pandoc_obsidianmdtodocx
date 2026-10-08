from pathlib import Path
import os
import shutil
import sys
from datetime import datetime

import PyInstaller.__main__


ROOT = Path(__file__).resolve().parent
APP_NAME = "ObsidianToDocx"


def require_path(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {description}: {path}")


def build(dist_dir=None):
    main_script = ROOT / "src" / "main.py"
    icon_file = ROOT / "resources" / "icon.ico"
    resources_dir = ROOT / "resources"
    spec_file = ROOT / f"{APP_NAME}.spec"
    dist_dir = Path(dist_dir).resolve() if dist_dir else ROOT / "dist"
    build_dir = ROOT / "build"

    require_path(main_script, "application entry point")
    require_path(icon_file, "application icon")
    require_path(resources_dir, "resources directory")
    require_path(spec_file, "PyInstaller spec file")

    # Keep previous releases and unrelated files; replace only the built EXE.
    previous = dist_dir / f'{APP_NAME}.exe'
    if previous.exists():
        backups = ROOT / 'backups'
        backups.mkdir(exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(previous, backups / f'{APP_NAME}_{stamp}.exe')

    print("Running PyInstaller...")
    os.chdir(ROOT)
    PyInstaller.__main__.run([
        str(spec_file),
        "--noconfirm",
        "--clean",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
    ])
    
    exe_path = dist_dir / f"{APP_NAME}.exe"
    require_path(exe_path, "built executable")
    # Pandoc stays external: no repeated extraction from the one-file GUI EXE.
    if (ROOT / 'pandoc.exe').exists():
        shutil.copy2(ROOT / 'pandoc.exe', dist_dir / 'pandoc.exe')
    if (ROOT / 'PORTABLE_README.txt').exists():
        shutil.copy2(ROOT / 'PORTABLE_README.txt', dist_dir / '사용방법.txt')
    print(f"Build complete: {exe_path}")
    return exe_path

if __name__ == "__main__":
    try:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--dist-dir', help='Build to a separate directory while the installed EXE is running')
        build(parser.parse_args().dist_dir)
    except Exception as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
