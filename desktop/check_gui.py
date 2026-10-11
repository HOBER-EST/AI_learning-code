"""Fails unless the built app can open a real native window.

    python desktop/check_gui.py [path/to/app/executable]

Runs ``<app> --check-gui RESULT`` (see launcher.py), which opens a window,
waits for its page to load and closes it again.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke_test import default_executable  # noqa: E402


def main() -> None:
    exe = Path(sys.argv[1]) if len(sys.argv) > 1 else default_executable()
    with tempfile.TemporaryDirectory() as tmp:
        result_file = Path(tmp) / "gui.json"
        subprocess.run([str(exe), "--check-gui", str(result_file)], timeout=180, check=False)
        if not result_file.exists():
            sys.exit("check-gui produced no result (the app crashed before writing it)")
        result = json.loads(result_file.read_text(encoding="utf-8"))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        sys.exit("the packaged app could not open a native window")
    print(f"native window OK ({result['gui']})")


if __name__ == "__main__":
    main()
