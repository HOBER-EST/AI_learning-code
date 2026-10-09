"""End-to-end tests of the sandboxed child process (test runner, run, trace)."""

from app import sandbox

FACT = '''
def fact(n):
    """
    >>> fact(3)
    6
    >>> fact(4)
    25
    """
    if n == 0:
        return 1
    return n * fact(n - 1)

def test_fact():
    assert fact(2) == 2

def test_fact_wrong():
    assert fact(2) == 3, "fact(2) should be 2"
'''


def by_source(results):
    return {r["source"]: r for r in results["results"]}


def test_doctests_extra_tests_and_test_functions():
    result = sandbox.run_tests(FACT, tests=">>> fact(5)\n120\n")
    r = by_source(result)
    assert r["fact(3)"]["status"] == "passed"
    assert r["fact(4)"]["status"] == "failed"
    assert r["fact(4)"]["want"] == "25" and r["fact(4)"]["got"] == "24"
    assert r["fact(5)"]["origin"] == "exercise" and r["fact(5)"]["status"] == "passed"
    assert r["test_fact()"]["status"] == "passed"
    assert r["test_fact_wrong()"]["status"] == "failed"
    assert "fact(2) should be 2" in r["test_fact_wrong()"]["got"]
    assert result["summary"] == {"passed": 3, "failed": 2, "total": 5}
    assert result["ok"] is False


def test_each_example_has_its_own_timeout():
    code = 'def spin():\n    """\n    >>> spin()\n    1\n    """\n    while True:\n        pass\n\ndef ok():\n    """\n    >>> ok()\n    1\n    """\n    return 1\n'
    r = by_source(sandbox.run_tests(code))
    assert r["spin()"]["status"] == "timeout"
    assert r["ok()"]["status"] == "passed"


def test_recursion_error_is_reported_per_example():
    code = 'def bad(n):\n    """\n    >>> bad(1)\n    1\n    """\n    return bad(n)\n'
    r = by_source(sandbox.run_tests(code))
    assert r["bad(1)"]["status"] == "error"
    assert r["bad(1)"]["error_type"] == "RecursionError"


def test_load_errors_are_reported():
    result = sandbox.run_tests("x = 1\nprint(undefined_name)\n")
    assert result["load_error"]["type"] == "NameError"
    assert result["load_error"]["line"] == 2
    syntax = sandbox.run_tests("def f(:\n  pass")
    assert syntax["load_error"]["type"] == "SyntaxError"


def test_prelude_is_available_in_tests():
    code = 'def first(s):\n    """\n    >>> first(Link(3, Link(4)))\n    3\n    >>> label(tree(5))\n    5\n    """\n    return s.first\n'
    assert sandbox.run_tests(code)["ok"] is True


def test_run_program_captures_output():
    result = sandbox.run_program("for i in range(3):\n    print(i)\n")
    assert result == {"ok": True, "stdout": "0\n1\n2\n", "error": None}


def test_run_program_timeout():
    result = sandbox.run_program("while True:\n    pass\n")
    assert result["ok"] is False
    assert result["error"]["type"] == "Timeout"


def test_dangerous_operations_are_blocked():
    for code in (
        "import os\nos.system('echo hi')",
        "open('pwned.txt', 'w').write('x')",
        "import subprocess\nsubprocess.run(['ls'])",
        "import socket\nsocket.create_connection(('example.com', 80))",
        "import os\nos.remove('/etc/hosts')",
    ):
        result = sandbox.run_program(code)
        assert result["ok"] is False, code
        assert result["error"]["type"] in ("PermissionError", "OSError"), (code, result)


def test_input_is_disabled():
    result = sandbox.run_program("x = input()")
    assert result["ok"] is False
    assert "input()" in result["error"]["message"]


def test_memory_limit():
    result = sandbox.run_program("x = [0] * (10 ** 10)")
    assert result["ok"] is False
    assert result["error"]["type"] in ("MemoryError", "OverflowError")


def test_trace_through_sandbox():
    result = sandbox.trace("def sq(x):\n    return x * x\ny = sq(3)\n")
    assert result["ok"] is True
    assert result["calls"][0]["label"] == "sq(3)"
    assert result["calls"][0]["ret"] == "9"


def test_trace_respects_step_limit():
    result = sandbox.trace("while True:\n    x = 1\n", max_steps=50)
    assert result["truncated"] is True
    assert len(result["steps"]) == 50
