"""Runs student code in a separate, resource-limited Python process.

Isolation layers (best effort, not a hardened security boundary):

* a fresh ``python -I`` interpreter in a throw-away working directory with a
  minimal environment;
* CPU-time, address-space and file-size limits via ``setrlimit`` (applied
  by the child before it runs any student code);
* a wall-clock timeout that kills the whole process group;
* an audit hook inside the child that refuses file writes, subprocesses and
  network access (see ``runner/child.py``).

For a public deployment, run the backend inside a container as well.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading

from . import config

CHILD_SCRIPT = os.path.join(os.path.dirname(__file__), "runner", "child.py")
_slots = threading.BoundedSemaphore(config.MAX_CONCURRENT_RUNS)


def _failure(kind: str, message: str, detail: str = "") -> dict:
    return {
        "ok": False,
        "sandbox_error": {"type": kind, "message": message, "detail": detail[-2000:]},
    }


def run_in_sandbox(request: dict, timeout: float) -> dict:
    """Run ``request`` (see ``child.py``) and return the decoded JSON result."""
    with _slots, tempfile.TemporaryDirectory(prefix="learn61a-") as workdir:
        result_path = os.path.join(workdir, "result.json")
        env = {
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        # Resource limits are applied by the child itself (see child.py):
        # preexec_fn is not safe in a multi-threaded server.
        request = {**request, "limits": {"cpu": int(timeout) + 1, "memory_mb": config.MEMORY_LIMIT_MB}}
        proc = subprocess.Popen(
            [sys.executable, "-I", CHILD_SCRIPT, result_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=workdir,
            env=env,
            start_new_session=True,
        )
        try:
            _, stderr = proc.communicate(json.dumps(request).encode("utf-8"), timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill(proc)
            return _failure(
                "Timeout",
                f"程序运行超过 {timeout:g} 秒被终止：请检查是否存在无限循环或缺少递归的基本情况（base case）。",
            )

        stderr_text = stderr.decode("utf-8", "replace")
        try:
            with open(result_path, encoding="utf-8") as f:
                data = f.read()
            if data:
                return json.loads(data)
        except (OSError, json.JSONDecodeError):
            pass

        if proc.returncode in (-signal.SIGXCPU, -signal.SIGKILL):
            return _failure("ResourceLimit", "程序超出了 CPU 时间限制。", stderr_text)
        if "MemoryError" in stderr_text:
            return _failure("MemoryError", f"程序超出了 {config.MEMORY_LIMIT_MB}MB 内存限制。", stderr_text)
        return _failure("Crash", f"运行进程异常退出（返回码 {proc.returncode}）。", stderr_text)


def _kill(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, AttributeError):
        proc.kill()
    proc.communicate()


def trace(code: str, max_steps: int | None = None) -> dict:
    steps = min(max_steps or config.MAX_TRACE_STEPS, config.MAX_TRACE_STEPS)
    return run_in_sandbox({"mode": "trace", "code": code, "max_steps": steps}, config.TRACE_TIMEOUT)


def run_tests(code: str, tests: str | None = None, run_doctests: bool = True) -> dict:
    return run_in_sandbox(
        {
            "mode": "test",
            "code": code,
            "tests": tests,
            "run_doctests": run_doctests,
            "example_timeout": config.EXAMPLE_TIMEOUT,
        },
        config.TEST_TIMEOUT,
    )


def run_program(code: str) -> dict:
    return run_in_sandbox({"mode": "run", "code": code, "timeout": config.RUN_TIMEOUT}, config.RUN_TIMEOUT + 2)
