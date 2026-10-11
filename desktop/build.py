"""Builds the stand-alone desktop app for the current OS.

    python desktop/build.py            # build frontend + app, then archive it
    python desktop/build.py --skip-frontend

Output:
    desktop/dist/Learn61A/ (Windows, Linux) or desktop/dist/Learn61A.app (macOS)
    desktop/release/Learn61A-<os>-<arch>.zip (Windows, macOS) / .tar.gz (Linux)

Run it with a Python that has backend/requirements.txt, pyinstaller and
pywebview installed. PyInstaller cannot cross-compile: build each OS on that
OS (the GitHub Actions workflow .github/workflows/desktop.yml does this).
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop"
FRONTEND = ROOT / "frontend"
NAME = "Learn61A"

# Windows consoles default to a legacy code page that cannot print Chinese.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True, shell=sys.platform == "win32" and cmd[0] == "npm")


def build_frontend() -> None:
    run(["npm", "ci"], FRONTEND)
    run(["npm", "run", "build"], FRONTEND)


def build_app() -> Path:
    dist = FRONTEND / "dist"
    if not (dist / "index.html").exists():
        sys.exit("frontend/dist 不存在：请先构建前端（去掉 --skip-frontend）。")
    work = DESKTOP / "build"
    out = DESKTOP / "dist"
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(out, ignore_errors=True)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(DESKTOP / "launcher.py"),
        "--name", NAME,
        "--onedir",  # onefile would re-extract itself for every sandboxed run
        "--noconfirm",
        "--clean",
        "--paths", str(ROOT / "backend"),
        "--add-data", f"{dist}{os.pathsep}frontend_dist",
        "--collect-submodules", "uvicorn",
        "--collect-submodules", "app",
        "--distpath", str(out),
        "--workpath", str(work),
        "--specpath", str(work),
    ]
    if sys.platform in ("win32", "darwin"):
        cmd.append("--windowed")  # no console window; Linux keeps one for the browser fallback
    if sys.platform == "darwin":
        cmd += ["--osx-bundle-identifier", "edu.learn61a.recursionlab"]
    run(cmd, ROOT)
    return out / (f"{NAME}.app" if sys.platform == "darwin" else NAME)


def archive(app: Path) -> Path:
    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    arch = platform.machine().lower().replace("amd64", "x86_64").replace("aarch64", "arm64")
    release = DESKTOP / "release"
    release.mkdir(exist_ok=True)
    base = release / f"{NAME}-{system}-{arch}"
    if system == "macos":
        # ditto keeps the .app bundle's symlinks and permissions intact.
        target = base.with_suffix(".zip")
        target.unlink(missing_ok=True)
        run(["ditto", "-c", "-k", "--keepParent", str(app), str(target)], DESKTOP)
        return target
    fmt = "zip" if system == "windows" else "gztar"
    return Path(shutil.make_archive(str(base), fmt, root_dir=app.parent, base_dir=app.name))


def main() -> None:
    if "--skip-frontend" not in sys.argv:
        build_frontend()
    app = build_app()
    print(f"\n应用：{app}\n安装包：{archive(app)}")


if __name__ == "__main__":
    main()
