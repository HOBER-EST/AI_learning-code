"""Launches a built desktop app and checks it end to end through its API.

    python desktop/smoke_test.py [path/to/app/executable]

Covers the parts that differ in the packaged app: serving the bundled
frontend, and re-running the executable as the sandbox child.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DIST = Path(__file__).resolve().parent / "dist"

# Windows consoles default to a legacy code page that cannot print Chinese.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def default_executable() -> Path:
    if sys.platform == "darwin":
        return DIST / "Learn61A.app" / "Contents" / "MacOS" / "Learn61A"
    return DIST / "Learn61A" / ("Learn61A.exe" if sys.platform == "win32" else "Learn61A")


def post(base: str, path: str, body: dict) -> dict:
    req = urllib.request.Request(
        base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main() -> None:
    exe = Path(sys.argv[1]) if len(sys.argv) > 1 else default_executable()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen([str(exe), "--browser", "--port", str(port)])
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(base + "/api/health", timeout=1):
                    break
            except OSError:
                time.sleep(0.5)
        else:
            raise SystemExit("app did not start")

        with urllib.request.urlopen(base + "/", timeout=10) as r:
            assert "61A" in r.read().decode("utf-8"), "frontend not served"

        trace = post(base, "/api/trace", {"code": "def f(n):\n    if n == 0:\n        return 0\n    return n + f(n - 1)\nf(3)\n"})
        assert trace["ok"] and len(trace["calls"]) == 4, trace

        tests = post(base, "/api/test", {"code": 'def sq(x):\n    """\n    >>> sq(3)\n    9\n    >>> sq(2)\n    5\n    """\n    return x * x\n'})
        assert tests["summary"] == {"passed": 1, "failed": 1, "total": 2}, tests

        spin = post(base, "/api/test", {"code": 'def spin():\n    """\n    >>> spin()\n    1\n    """\n    while True:\n        pass\n'})
        assert spin["results"][0]["status"] == "timeout", spin

        blocked = post(base, "/api/run", {"code": "open('x.txt', 'w')"})
        assert blocked["error"]["type"] == "PermissionError", blocked
        with urllib.request.urlopen(base + "/api/settings", timeout=10) as r:
            assert "models" in json.load(r), "settings endpoint broken"

        req = urllib.request.Request(
            base + "/api/explain",
            data=json.dumps({"code": "def f(n):\n    return n\n", "call": "f(1)"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            stream = r.read().decode("utf-8")
        assert '"type": "done"' in stream and "逐行讲解" in stream, stream[:500]
        print("smoke test passed")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
