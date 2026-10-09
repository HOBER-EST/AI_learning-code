"""Runs doctests, exercise tests and ``test_*`` functions against student code.

Executed inside the sandboxed child process. Every example gets its own
time budget (via ``SIGALRM``) so that one infinite loop only fails one example
instead of the whole run.
"""

from __future__ import annotations

import doctest
import io
import linecache
import signal
import sys
import traceback
import types

STUDENT_FILE = "<student>"
MODULE_NAME = "student"
OPTIONFLAGS = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
MAX_TEXT = 2000


class ExampleTimeout(Exception):
    pass


def _on_alarm(signum, frame):
    raise ExampleTimeout("运行超时：可能存在无限循环或无限递归")


def _arm(seconds: float) -> None:
    signal.setitimer(signal.ITIMER_REAL, seconds)


def _disarm() -> None:
    signal.setitimer(signal.ITIMER_REAL, 0)


def _clip(text: str) -> str:
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + "\n…（输出过长，已截断）"


def _exception_summary(exc_type, exc_value) -> str:
    if exc_type is ExampleTimeout:
        return str(exc_value)
    return "".join(traceback.format_exception_only(exc_type, exc_value)).strip()


class CollectingRunner(doctest.DocTestRunner):
    """A DocTestRunner that records a structured result for every example."""

    def __init__(self, origin: str, timeout: float):
        super().__init__(optionflags=OPTIONFLAGS, verbose=False)
        self.origin = origin
        self.timeout = timeout
        self.results: list[dict] = []

    def _base(self, test, example) -> dict:
        line = None
        if test.lineno is not None and example.lineno is not None:
            line = test.lineno + example.lineno + 1
        return {
            "name": test.name.split(".")[-1],
            "origin": self.origin,
            "source": example.source.rstrip("\n"),
            "want": example.want.rstrip("\n"),
            "line": line,
        }

    def report_start(self, out, test, example):
        _arm(self.timeout)

    def report_success(self, out, test, example, got):
        _disarm()
        self.results.append({**self._base(test, example), "status": "passed", "got": _clip(got.rstrip("\n"))})

    def report_failure(self, out, test, example, got):
        _disarm()
        self.results.append({**self._base(test, example), "status": "failed", "got": _clip(got.rstrip("\n"))})

    def report_unexpected_exception(self, out, test, example, exc_info):
        _disarm()
        exc_type, exc_value, _ = exc_info
        status = "timeout" if exc_type is ExampleTimeout else "error"
        self.results.append(
            {
                **self._base(test, example),
                "status": status,
                "got": _clip(_exception_summary(exc_type, exc_value)),
                "error_type": exc_type.__name__,
            }
        )


def _load_module(code: str, builtins_dict: dict | None):
    linecache.cache[STUDENT_FILE] = (len(code), None, code.splitlines(True), STUDENT_FILE)
    module = types.ModuleType(MODULE_NAME)
    if builtins_dict is not None:
        module.__dict__["__builtins__"] = builtins_dict
    sys.modules[MODULE_NAME] = module
    compiled = compile(code, STUDENT_FILE, "exec")
    exec(compiled, module.__dict__)
    return module


def _describe_load_error(exc: BaseException) -> dict:
    line = getattr(exc, "lineno", None) if isinstance(exc, SyntaxError) else None
    tb = exc.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == STUDENT_FILE:
            line = tb.tb_lineno
        tb = tb.tb_next
    frames = [fs for fs in traceback.extract_tb(exc.__traceback__) if fs.filename == STUDENT_FILE]
    text = ""
    if frames:
        text = "Traceback (most recent call last):\n" + "".join(traceback.format_list(frames[-8:]))
    if isinstance(exc, ExampleTimeout):
        text += str(exc)
    else:
        text += "".join(traceback.format_exception_only(type(exc), exc))
    message = exc.msg if isinstance(exc, SyntaxError) else str(exc)
    return {"type": type(exc).__name__, "message": message, "line": line, "traceback": text}


def _run_test_functions(module, timeout: float) -> list[dict]:
    results = []
    for name, obj in list(vars(module).items()):
        if not (name.startswith("test") and isinstance(obj, types.FunctionType)):
            continue
        if obj.__module__ != MODULE_NAME or obj.__code__.co_argcount > 0:
            continue
        entry = {
            "name": name,
            "origin": "test_function",
            "source": f"{name}()",
            "want": "",
            "line": obj.__code__.co_firstlineno,
        }
        out = io.StringIO()
        old = sys.stdout
        sys.stdout = out
        try:
            _arm(timeout)
            obj()
            _disarm()
            entry.update(status="passed", got=_clip(out.getvalue().rstrip("\n")))
        except ExampleTimeout as e:
            _disarm()
            entry.update(status="timeout", got=str(e), error_type="ExampleTimeout")
        except AssertionError as e:
            _disarm()
            entry.update(status="failed", got=_clip(f"AssertionError: {e}" if str(e) else "AssertionError"))
        except BaseException as e:  # noqa: BLE001
            _disarm()
            entry.update(status="error", got=_clip(_exception_summary(type(e), e)), error_type=type(e).__name__)
        finally:
            sys.stdout = old
        results.append(entry)
    return results


def run_tests(
    code: str,
    tests: str | None = None,
    run_doctests: bool = True,
    example_timeout: float = 2.0,
    builtins_dict: dict | None = None,
) -> dict:
    signal.signal(signal.SIGALRM, _on_alarm)
    stdout = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout
    try:
        _arm(example_timeout * 2)
        module = _load_module(code, builtins_dict)
        _disarm()
    except BaseException as e:  # noqa: BLE001
        _disarm()
        sys.stdout = old_stdout
        error = _describe_load_error(e)
        if isinstance(e, ExampleTimeout):
            error["type"] = "Timeout"
        return {
            "ok": False,
            "load_error": error,
            "results": [],
            "summary": {"passed": 0, "failed": 0, "total": 0},
            "stdout": _clip(stdout.getvalue()),
        }
    finally:
        sys.stdout = old_stdout

    results: list[dict] = []
    if run_doctests:
        finder = doctest.DocTestFinder(exclude_empty=True)
        runner = CollectingRunner("doctest", example_timeout)
        try:
            found = finder.find(module, MODULE_NAME, globs=dict(vars(module)))
        except Exception:  # noqa: BLE001 - odd student objects can break the finder
            found = []
        found.sort(key=lambda t: (t.lineno or 0, t.name))
        for test in found:
            runner.run(test, clear_globs=False)
        results.extend(runner.results)

    if tests:
        runner = CollectingRunner("exercise", example_timeout)
        test = doctest.DocTestParser().get_doctest(tests, dict(vars(module)), "exercise", None, None)
        runner.run(test, clear_globs=False)
        results.extend(runner.results)

    results.extend(_run_test_functions(module, example_timeout))

    passed = sum(1 for r in results if r["status"] == "passed")
    return {
        "ok": passed == len(results),
        "load_error": None,
        "results": results,
        "summary": {"passed": passed, "failed": len(results) - passed, "total": len(results)},
        "stdout": _clip(stdout.getvalue()),
    }


def run_program(code: str, timeout: float = 5.0, builtins_dict: dict | None = None) -> dict:
    """Execute a program once and capture its output."""
    signal.signal(signal.SIGALRM, _on_alarm)
    stdout = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout
    error = None
    try:
        _arm(timeout)
        _load_module(code, builtins_dict)
    except BaseException as e:  # noqa: BLE001
        error = _describe_load_error(e)
        if isinstance(e, ExampleTimeout):
            error["type"] = "Timeout"
    finally:
        _disarm()
        sys.stdout = old_stdout
    return {"ok": error is None, "stdout": _clip(stdout.getvalue()), "error": error}
