from app.analyzer import analyze, check_constraints


def titles(code, results=None):
    return [f["title"] for f in analyze(code, results)["findings"]]


def test_clean_recursive_function():
    result = analyze("def fact(n):\n    if n == 0:\n        return 1\n    return n * fact(n - 1)\n")
    assert result["findings"] == []
    (info,) = result["functions"]
    assert info["recursive"] and info["kind"] == "线性递归" and info["has_base_case"]


def test_tree_recursion_detection():
    fib = "def fib(n):\n    if n < 2:\n        return n\n    return fib(n - 1) + fib(n - 2)\n"
    assert analyze(fib)["functions"][0]["kind"] == "树递归"
    tree = "def s(t):\n    return t.label + sum([s(b) for b in t.branches])\n"
    info = analyze(tree)["functions"][0]
    assert info["kind"] == "树递归" and info["has_base_case"]
    # Two call sites in mutually exclusive branches are still linear recursion.
    linear = "def f(n):\n    if n == 0:\n        return 0\n    if n % 2:\n        return f(n - 1)\n    return f(n - 1)\n"
    assert analyze(linear)["functions"][0]["kind"] == "线性递归"


def test_missing_base_case_and_same_arguments():
    found = titles("def f(n):\n    return f(n)\n")
    assert "可能缺少基本情况（base case）" in found
    assert "递归调用的参数没有变小" in found


def test_discarded_recursive_result_and_fall_through():
    found = titles("def f(n):\n    if n == 0:\n        return 0\n    f(n - 1)\n")
    assert "递归调用的结果被丢弃了" in found
    assert "有的执行路径没有 return" in found


def test_mutating_functions_are_not_flagged():
    code = "def square_tree(t):\n    t.label = t.label ** 2\n    for b in t.branches:\n        square_tree(b)\n"
    assert titles(code) == []


def test_link_and_tree_mistakes():
    found = titles(
        "def g(t, lnk):\n"
        "    if t.is_leaf:\n"
        "        return t.branches()\n"
        "    if lnk.rest == None:\n"
        "        return lnk.first()\n"
        "    return 1\n"
    )
    assert "is_leaf 需要调用" in found
    assert "`branches` 是属性，不是方法" in found
    assert "`first` 是属性，不是方法" in found
    assert "空链表是 Link.empty，不是 None" in found


def test_placeholder_and_syntax_error():
    assert "还没写完" in titles('def f():\n    "*** YOUR CODE HERE ***"\n')
    assert titles("def f(:\n") == ["语法错误"]


def test_runtime_findings_from_test_results():
    results = {
        "results": [
            {"status": "error", "error_type": "RecursionError", "got": "RecursionError: maximum recursion depth exceeded", "source": "f(1)"},
            {"status": "error", "error_type": "AttributeError", "got": "AttributeError: 'tuple' object has no attribute 'first'", "source": "g()"},
            {"status": "error", "error_type": "TypeError", "got": "TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'", "source": "h()"},
        ]
    }
    found = titles("x = 1\n", results)
    assert "递归太深：RecursionError" in found
    assert "访问了空链表的属性" in found
    assert "对 None 进行了运算" in found


def test_function_returned_none_hint():
    results = {"results": [{"status": "failed", "source": "f(2)", "want": "4", "got": ""}]}
    assert "函数没有返回值" in titles("def f(n):\n    print(n * 2)\n", results)


def test_constraints():
    loop = "def f(n):\n    total = 0\n    while n:\n        total += n\n        n -= 1\n    return total\n"
    results = check_constraints(loop, "f", [{"type": "recursive"}, {"type": "no_loops"}])
    assert [r["status"] for r in results] == ["failed", "failed"]
    rec = "def f(n):\n    if n == 0:\n        return 0\n    return n + f(n - 1)\n"
    results = check_constraints(rec, "f", [{"type": "recursive"}, {"type": "no_loops"}])
    assert [r["status"] for r in results] == ["passed", "passed"]
