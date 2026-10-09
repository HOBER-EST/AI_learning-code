"""Tests for the environment-diagram tracer (run in-process for speed)."""


def last_frames(result):
    return {f["label"]: f for f in result["steps"][-1]["frames"]}


def prim(value):
    return {"t": "prim", "v": value}


def test_frames_parents_and_return_values(trace):
    code = (
        "def make_adder(n):\n"
        "    def adder(k):\n"
        "        return n + k\n"
        "    return adder\n"
        "add3 = make_adder(3)\n"
        "x = add3(4)\n"
    )
    result = trace(code)
    assert result["ok"] and result["error"] is None
    frames = last_frames(result)
    assert frames["f1: make_adder"]["parent"] == "Global"
    assert frames["f2: adder"]["parent"] == "f1"
    assert frames["f2: adder"]["ret"] == prim("7")
    # Free variables are looked up in the parent frame, not shown in the child frame.
    assert [name for name, _ in frames["f2: adder"]["vars"]] == ["k"]
    heap = result["steps"][-1]["heap"]
    adder_ref = dict(result["steps"][-1]["globals"])["add3"]
    assert heap[adder_ref["id"]] == {"t": "func", "name": "adder", "params": "(k)", "parent": "f1", "line": None}


def test_lambda_frames_are_named_with_line_numbers(trace):
    result = trace("square = lambda x: x * x\ny = square(5)\n")
    frames = last_frames(result)
    assert "f1: λ <line 1>" in frames
    assert frames["f1: λ <line 1>"]["parent"] == "Global"


def test_lambda_passed_as_argument_keeps_defining_parent(trace):
    code = "def apply(f, x):\n    return f(x)\n\ndef outer():\n    return apply(lambda y: y + 1, 1)\n\nouter()\n"
    frames = last_frames(trace(code))
    assert frames["f3: λ <line 5>"]["parent"] == "f1"
    assert frames["f2: apply"]["parent"] == "Global"


def test_distinguishes_closures_created_by_the_same_code(trace):
    code = (
        "def make(n):\n"
        "    return lambda: n\n"
        "a = make(1)\n"
        "b = make(2)\n"
        "a()\n"
        "b()\n"
    )
    frames = last_frames(trace(code))
    assert frames["f3: λ <line 2>"]["parent"] == "f1"
    assert frames["f4: λ <line 2>"]["parent"] == "f2"


def test_recursion_call_tree(trace):
    code = "def fib(n):\n    if n <= 1:\n        return n\n    return fib(n - 1) + fib(n - 2)\nfib(4)\n"
    result = trace(code)
    calls = result["calls"]
    assert len(calls) == 9  # fib(4) makes 9 calls in total
    root = calls[0]
    assert root["label"] == "fib(4)" and root["parent"] is None and root["ret"] == "3"
    children = [c["label"] for c in calls if c["parent"] == root["id"]]
    assert children == ["fib(3)", "fib(2)"]
    assert max(c["depth"] for c in calls) == 4
    for c in calls:
        assert c["status"] == "returned"
        assert c["call_step"] < c["return_step"]


def test_exited_frames_are_kept_with_return_values(trace):
    code = "def fact(n):\n    if n == 0:\n        return 1\n    return n * fact(n - 1)\nr = fact(3)\n"
    result = trace(code)
    frames = result["steps"][-1]["frames"]
    assert [f["label"] for f in frames] == ["f1: fact", "f2: fact", "f3: fact", "f4: fact"]
    assert [f["ret"]["v"] for f in frames] == ["6", "2", "1", "1"]
    assert not any(f["live"] for f in frames)
    # In the middle of the recursion the call stack is visible.
    deepest = max(result["steps"], key=lambda s: len(s["stack"]))
    assert deepest["stack"] == ["Global", "f1", "f2", "f3", "f4"]


def test_link_and_tree_are_encoded_structurally(trace):
    result = trace("s = Link(1, Link(2))\nt = Tree(1, [Tree(2), Tree(3)])\n")
    step = result["steps"][-1]
    g = dict(step["globals"])
    heap = step["heap"]
    head = heap[g["s"]["id"]]
    assert head["t"] == "link" and head["first"] == prim("1")
    second = heap[head["rest"]["id"]]
    assert second == {"t": "link", "first": prim("2"), "rest": {"t": "empty"}}
    tree = heap[g["t"]["id"]]
    assert tree["t"] == "tree" and tree["label"] == prim("1")
    assert [heap[b["id"]]["label"]["v"] for b in tree["branches"]] == ["2", "3"]
    # Prelude names are builtins: they never clutter the Global frame.
    assert set(g) == {"s", "t"}


def test_shared_objects_keep_the_same_id(trace):
    result = trace("a = [1, 2]\nb = a\nb.append(3)\n")
    step = result["steps"][-1]
    g = dict(step["globals"])
    assert g["a"] == g["b"]
    assert step["heap"][g["a"]["id"]]["items"] == [prim("1"), prim("2"), prim("3")]


def test_stdout_is_captured_per_step(trace):
    result = trace("print('hi')\nx = 1\nprint('bye')\n")
    assert result["steps"][-1]["stdout"] == "hi\nbye\n"
    assert result["stdout"] == "hi\nbye\n"


def test_infinite_recursion_is_truncated(trace):
    result = trace("def f(n):\n    return f(n + 1)\nf(0)\n", max_steps=200)
    assert result["truncated"] is True
    assert len(result["steps"]) == 200
    assert result["ok"] is False


def test_errors_are_reported_with_line(trace):
    result = trace("x = 1\ny = x / 0\n")
    assert result["error"]["type"] == "ZeroDivisionError"
    assert result["error"]["line"] == 2
    assert result["steps"][-1]["exception"].startswith("ZeroDivisionError")


def test_function_that_raises_marks_frame(trace):
    code = "def boom():\n    raise ValueError('bad')\ntry:\n    boom()\nexcept ValueError:\n    pass\n"
    result = trace(code)
    assert result["ok"]
    frame = last_frames(result)["f1: boom"]
    assert frame.get("raised") is True and "ret" not in frame
    assert result["calls"][0]["status"] == "error"


def test_syntax_error(trace):
    result = trace("def f(:\n    pass\n")
    assert result["ok"] is False
    assert result["error"]["type"] == "SyntaxError"
    assert result["steps"] == []


def test_methods_and_classes(trace):
    code = (
        "class Counter:\n"
        "    def __init__(self):\n"
        "        self.n = 0\n"
        "    def inc(self):\n"
        "        self.n += 1\n"
        "c = Counter()\n"
        "c.inc()\n"
    )
    result = trace(code)
    step = result["steps"][-1]
    g = dict(step["globals"])
    cls = step["heap"][g["Counter"]["id"]]
    assert cls["t"] == "class" and [a[0] for a in cls["attrs"]] == ["__init__", "inc"]
    inst = step["heap"][g["c"]["id"]]
    assert inst == {"t": "instance", "cls": "Counter", "attrs": [["n", prim("1")]]}
    # Class bodies do not create frames; methods' parent is Global.
    assert [f["label"] for f in step["frames"]] == ["f1: __init__", "f2: inc"]
    assert all(f["parent"] == "Global" for f in step["frames"])
