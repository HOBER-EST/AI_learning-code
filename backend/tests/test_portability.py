"""Code paths used by the packaged desktop app and on Windows."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

from app import sandbox

BACKEND = Path(__file__).resolve().parents[1]


def run_python(script: str) -> dict:
    out = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_watchdog_timeouts_without_interval_timers():
    # Windows has no setitimer/SIGALRM: per-example timeouts use a watchdog thread.
    result = run_python(
        '''
        import json
        from app.runner import test_runner
        test_runner.USE_ITIMER = False
        code = (
            'def spin():\\n    """\\n    >>> spin()\\n    1\\n    """\\n    while True:\\n        pass\\n\\n'
            'def ok():\\n    """\\n    >>> ok()\\n    1\\n    """\\n    return 1\\n'
        )
        res = test_runner.run_tests(code, example_timeout=0.5)
        print(json.dumps({r["source"]: r["status"] for r in res["results"]}))
        '''
    )
    assert result == {"spin()": "timeout", "ok()": "passed"}


def test_watchdog_timeout_for_whole_program():
    result = run_python(
        '''
        import json
        from app.runner import test_runner
        test_runner.USE_ITIMER = False
        res = test_runner.run_program("while True:\\n    pass\\n", timeout=0.5)
        print(json.dumps(res["error"]["type"]))
        '''
    )
    assert result == "Timeout"


def test_frozen_app_runs_itself_as_the_child(monkeypatch, tmp_path):
    # In the desktop app sys.executable is the app; it is re-run with CHILD_FLAG.
    launcher = tmp_path / "fake_app.py"
    launcher.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(BACKEND)!r})\n"
        "assert sys.argv[1] == '--learn61a-child'\n"
        "from app.runner import child\n"
        "child.main(sys.argv[2], sys.argv[3])\n"
    )
    wrapper = tmp_path / "fake_app"
    wrapper.write_text(f"#!/bin/sh\nexec {sys.executable} {launcher} \"$@\"\n")
    wrapper.chmod(0o755)
    monkeypatch.setattr(sandbox, "FROZEN", True)
    monkeypatch.setattr(sandbox.sys, "executable", str(wrapper))
    result = sandbox.trace("def sq(x):\n    return x * x\ny = sq(4)\n")
    assert result["ok"] is True
    assert result["calls"][0]["ret"] == "16"


def test_blocked_child_launch_is_reported(monkeypatch):
    # E.g. antivirus software refusing to start the (unsigned) app executable.
    def refuse(command, workdir):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(sandbox, "_spawn", refuse)
    result = sandbox.run_program("print(1)")
    assert result["ok"] is False
    assert result["sandbox_error"]["type"] == "LaunchError"
    assert "杀毒软件" in result["sandbox_error"]["message"]
