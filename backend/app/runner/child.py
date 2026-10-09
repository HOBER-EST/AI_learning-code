"""Entry point of the sandboxed child process.

Usage: python -I child.py RESULT_PATH  (JSON request on stdin)

The result file is opened *before* the audit hook is installed, which then
refuses any file writes, process spawning or network access by student code.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prelude  # noqa: E402
import test_runner  # noqa: E402
import tracer  # noqa: E402

_BLOCKED_EVENTS = (
    "subprocess.Popen",
    "os.system",
    "os.exec",
    "os.posix_spawn",
    "os.spawn",
    "os.fork",
    "os.forkpty",
    "os.kill",
    "os.killpg",
    "os.remove",
    "os.rmdir",
    "os.rename",
    "os.chmod",
    "os.chown",
    "os.link",
    "os.symlink",
    "os.truncate",
    "os.mkdir",
    "shutil.rmtree",
    "socket.connect",
    "socket.bind",
    "socket.getaddrinfo",
    "ctypes.dlopen",
    "webbrowser.open",
)
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


def _audit(event, args):
    if event in _BLOCKED_EVENTS:
        raise PermissionError(f"出于安全考虑，本平台禁止该操作：{event}")
    if event == "open":
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else 0
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and flags & _WRITE_FLAGS
        )
        if writing:
            raise PermissionError("出于安全考虑，本平台禁止写文件")


def main() -> None:
    request = json.loads(sys.stdin.read())
    out = open(sys.argv[1], "w", encoding="utf-8")
    sys.stdin = open(os.devnull, encoding="utf-8")
    sys.addaudithook(_audit)

    mode = request["mode"]
    code = request["code"]
    builtins_dict = prelude.make_builtins()
    if mode == "trace":
        result = tracer.trace_code(code, request.get("max_steps", 1000), builtins_dict)
    elif mode == "test":
        result = test_runner.run_tests(
            code,
            tests=request.get("tests"),
            run_doctests=request.get("run_doctests", True),
            example_timeout=request.get("example_timeout", 2.0),
            builtins_dict=builtins_dict,
        )
    elif mode == "run":
        result = test_runner.run_program(code, request.get("timeout", 5.0), builtins_dict)
    else:
        result = {"ok": False, "error": {"type": "ValueError", "message": f"unknown mode {mode}"}}

    json.dump(result, out, ensure_ascii=False)
    out.close()


if __name__ == "__main__":
    main()
