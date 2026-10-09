"""Static analysis that powers the rule-based "AI tutor".

It inspects student code with the ``ast`` module (the code is never executed
here) and produces beginner-friendly findings about recursion, ``Link`` and
``Tree`` usage. When test results are supplied, runtime errors such as
``RecursionError`` are explained as well.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

PLACEHOLDER = "*** YOUR CODE HERE ***"
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)


@dataclass
class FunctionInfo:
    name: str
    line: int
    params: list[str]
    recursive: bool = False
    recursive_calls: list[int] = field(default_factory=list)
    has_base_case: bool = False
    tree_recursion: bool = False
    has_loops: bool = False

    def to_dict(self) -> dict:
        kind = None
        if self.recursive:
            kind = "树递归" if self.tree_recursion else "线性递归"
        return {
            "name": self.name,
            "line": self.line,
            "params": self.params,
            "recursive": self.recursive,
            "kind": kind,
            "recursive_calls": self.recursive_calls,
            "has_base_case": self.has_base_case,
            "has_loops": self.has_loops,
        }


def _finding(level: str, title: str, message: str, line: int | None = None, function: str | None = None) -> dict:
    return {"level": level, "title": title, "message": message, "line": line, "function": function}


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


class _BodyWalker(ast.NodeVisitor):
    """Walks one function body without descending into nested functions/classes."""

    def __init__(self):
        self.nodes: list[ast.AST] = []

    def generic_visit(self, node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            self.nodes.append(child)
            self.generic_visit(child)


def _own_nodes(func: ast.FunctionDef) -> list[ast.AST]:
    walker = _BodyWalker()
    walker.generic_visit(func)
    return walker.nodes


def _contains_call_to(node: ast.AST, name: str) -> bool:
    return any(isinstance(n, ast.Call) and _call_name(n) == name for n in ast.walk(node))


def _can_fall_through(body: list[ast.stmt]) -> bool:
    if not body:
        return True
    last = body[-1]
    if isinstance(last, (ast.Return, ast.Raise)):
        return False
    if isinstance(last, ast.If):
        return _can_fall_through(last.body) or _can_fall_through(last.orelse)
    if isinstance(last, ast.While) and isinstance(last.test, ast.Constant) and last.test.value is True:
        return False
    if isinstance(last, ast.Try):
        return _can_fall_through(last.body + last.orelse) or any(_can_fall_through(h.body) for h in last.handlers)
    if isinstance(last, ast.Expr) and isinstance(last.value, ast.Constant):
        return True
    return True


def _has_base_case(func: ast.FunctionDef, name: str) -> bool:
    """A base case is a path that leaves the function without recursing.

    We approximate it as: some ``return``/``raise``/fall-through that does not
    contain a recursive call, reachable before every recursive call, or an
    ``if``/loop guarding the recursive calls.
    """
    for node in _own_nodes(func):
        if isinstance(node, ast.Return) and (node.value is None or not _contains_call_to(node.value, name)):
            return True
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, (ast.If, ast.For, ast.While, ast.IfExp) + _COMPREHENSIONS):
            if _contains_call_to(node, name):
                return True
        if isinstance(node, ast.BoolOp) and _contains_call_to(node, name):
            return True
    return False


def _count_calls(node: ast.AST, name: str) -> int:
    return sum(1 for n in ast.walk(node) if isinstance(n, ast.Call) and _call_name(n) == name)


def _block_has_multiple_calls(body: list[ast.stmt], name: str) -> bool:
    """True if two recursive calls can run on the same path through ``body``."""
    count = 0
    for stmt in body:
        if isinstance(stmt, ast.If):
            count += _count_calls(stmt.test, name)
            through = []
            for branch in (stmt.body, stmt.orelse):
                calls = sum(_count_calls(s, name) for s in branch)
                if _block_has_multiple_calls(branch, name) or count + min(calls, 1) > 1:
                    return True
                if _can_fall_through(branch):
                    through.append(min(calls, 1))
            count += max(through, default=0)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        else:
            count += _count_calls(stmt, name)
        if count > 1:
            return True
    return False


def _same_args(call: ast.Call, params: list[str]) -> bool:
    if not call.args or len(call.args) != len(params) or call.keywords:
        return False
    return all(isinstance(a, ast.Name) and a.id == p for a, p in zip(call.args, params))


def analyze(code: str, test_results: dict | None = None) -> dict:
    try:
        module = ast.parse(code)
    except SyntaxError as e:
        return {
            "functions": [],
            "findings": [
                _finding(
                    "error",
                    "语法错误",
                    f"第 {e.lineno} 行：{e.msg}。检查括号、冒号和缩进是否正确。",
                    e.lineno,
                )
            ],
        }

    findings: list[dict] = []
    functions: list[FunctionInfo] = []

    if PLACEHOLDER in code:
        findings.append(_finding("info", "还没写完", "代码中还有 \"*** YOUR CODE HERE ***\" 占位符，把它替换成你的实现吧。"))

    for func in [n for n in ast.walk(module) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        name = func.name
        params = [a.arg for a in func.args.args]
        info = FunctionInfo(name=name, line=func.lineno, params=params)
        own = _own_nodes(func)
        # Calls from nested helper functions to the outer function also count.
        calls = [
            n for n in ast.walk(func)
            if isinstance(n, ast.Call) and _call_name(n) == name and n is not func
        ]
        info.recursive_calls = sorted({c.lineno for c in calls})
        info.recursive = bool(calls)
        info.has_loops = any(isinstance(n, (ast.For, ast.While)) for n in own)
        if info.recursive:
            info.has_base_case = _has_base_case(func, name)
            in_loop = any(
                isinstance(n, (ast.For, ast.While) + _COMPREHENSIONS) and _contains_call_to(n, name)
                for n in own
            )
            info.tree_recursion = in_loop or _block_has_multiple_calls(func.body, name)
        functions.append(info)

        returns_value = any(isinstance(n, ast.Return) and n.value is not None for n in own)

        if info.recursive and not info.has_base_case:
            findings.append(
                _finding(
                    "error",
                    "可能缺少基本情况（base case）",
                    f"`{name}` 中所有路径都会继续递归，没有一个不递归就返回的出口。"
                    "递归函数需要先处理最简单的情况（例如 n == 0、链表为空、树是叶子）并直接返回结果。",
                    func.lineno,
                    name,
                )
            )

        for call in calls:
            if _same_args(call, params):
                findings.append(
                    _finding(
                        "error",
                        "递归调用的参数没有变小",
                        f"第 {call.lineno} 行用完全相同的参数调用了 `{name}`，问题规模没有缩小，会无限递归。"
                        "每次递归都应该让问题更接近基本情况（例如 n - 1、lnk.rest、t.branches 中的分支）。",
                        call.lineno,
                        name,
                    )
                )

        if returns_value:
            for node in own:
                if (
                    isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Call)
                    and _call_name(node.value) == name
                ):
                    findings.append(
                        _finding(
                            "warning",
                            "递归调用的结果被丢弃了",
                            f"第 {node.lineno} 行调用了 `{name}(...)`，但没有使用它的返回值。"
                            "如果需要这个结果，记得 `return` 它或把它组合进答案里。",
                            node.lineno,
                            name,
                        )
                    )
            body = func.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                body = body[1:]
            if body and _can_fall_through(body):
                findings.append(
                    _finding(
                        "warning",
                        "有的执行路径没有 return",
                        f"`{name}` 在某些分支里返回了值，但执行到函数末尾时没有 return，此时会返回 None。",
                        func.lineno,
                        name,
                    )
                )

    findings.extend(_link_tree_findings(module))
    if test_results:
        findings.extend(_runtime_findings(test_results))

    return {"functions": [f.to_dict() for f in functions], "findings": _dedupe(findings)}


def _link_tree_findings(module: ast.Module) -> list[dict]:
    out = []
    for node in ast.walk(module):
        if isinstance(node, ast.Compare):
            for op, right in zip(node.ops, node.comparators):
                left_attr = node.left
                if (
                    isinstance(op, (ast.Is, ast.IsNot, ast.Eq, ast.NotEq))
                    and isinstance(right, ast.Constant)
                    and right.value is None
                    and isinstance(left_attr, ast.Attribute)
                    and left_attr.attr == "rest"
                ):
                    out.append(
                        _finding(
                            "error",
                            "空链表是 Link.empty，不是 None",
                            f"第 {node.lineno} 行把 `.rest` 和 None 比较。链表的结尾是 `Link.empty`，应写成 `lnk.rest is Link.empty`。",
                            node.lineno,
                        )
                    )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("branches", "label") and isinstance(node.func.value, ast.Name):
                out.append(
                    _finding(
                        "warning",
                        f"`{node.func.attr}` 是属性，不是方法",
                        f"第 {node.lineno} 行写了 `{ast.unparse(node.func)}()`。对 Tree 类，"
                        f"应写成 `t.{node.func.attr}`（不加括号）；如果你用的是函数式 ADT，应写成 `{node.func.attr}(t)`。",
                        node.lineno,
                    )
                )
            if node.func.attr in ("first", "rest"):
                out.append(
                    _finding(
                        "warning",
                        f"`{node.func.attr}` 是属性，不是方法",
                        f"第 {node.lineno} 行写了 `{ast.unparse(node.func)}()`，应去掉括号。",
                        node.lineno,
                    )
                )
        if isinstance(node, (ast.If, ast.While, ast.IfExp)):
            test = node.test
            if isinstance(test, ast.UnaryOp):
                test = test.operand
            if isinstance(test, ast.Attribute) and test.attr == "is_leaf":
                out.append(
                    _finding(
                        "error",
                        "is_leaf 需要调用",
                        f"第 {node.lineno} 行用 `{ast.unparse(test)}` 作条件，它是一个方法对象，永远为真。应写成 `{ast.unparse(test)}()`。",
                        node.lineno,
                    )
                )
    return out


def _runtime_findings(test_results: dict) -> list[dict]:
    out = []
    results = list(test_results.get("results") or [])
    load_error = test_results.get("load_error") or test_results.get("error")
    errors = [(r.get("error_type"), r.get("got", ""), r.get("source", "")) for r in results if r.get("status") in ("error", "timeout")]
    if load_error:
        errors.append((load_error.get("type"), f"{load_error.get('type')}: {load_error.get('message')}", ""))
    sandbox_error = test_results.get("sandbox_error")
    if sandbox_error:
        errors.append((sandbox_error.get("type"), sandbox_error.get("message", ""), ""))

    for error_type, got, source in errors:
        where = f"（运行 `{source}` 时）" if source else ""
        got = got or ""
        if error_type == "RecursionError" or "RecursionError" in got:
            out.append(_finding("error", "递归太深：RecursionError", f"{where}递归没有在合理的深度停下来。检查基本情况是否能被达到，以及每次递归参数是否在向基本情况靠近。"))
        elif error_type in ("ExampleTimeout", "Timeout"):
            out.append(_finding("error", "运行超时", f"{where}程序没有在时限内结束，可能是无限循环（例如 while 的条件永远为真）或无限递归。"))
        elif "NoneType" in got:
            out.append(_finding("error", "对 None 进行了运算", f"{where}{got}。通常是某个函数忘了 `return`，于是返回了 None。检查每个分支是否都有 return。"))
        elif "'tuple' object has no attribute" in got:
            out.append(_finding("error", "访问了空链表的属性", f"{where}{got}。Link.empty 是空元组 ()，没有 first / rest。访问前先检查 `lnk is Link.empty`。"))
        elif "'list' object is not callable" in got:
            out.append(_finding("error", "把列表当函数调用了", f"{where}{got}。`t.branches` 是列表属性，去掉括号。"))
        elif "object has no attribute 'label'" in got or "object has no attribute 'branches'" in got:
            out.append(_finding("error", "混用了 Tree 类和函数式 tree ADT", f"{where}{got}。Tree 对象用 `t.label` / `t.branches`；tree ADT（列表）用 `label(t)` / `branches(t)`。"))
        elif error_type == "NameError" or "NameError" in got:
            out.append(_finding("error", "名字未定义：NameError", f"{where}{got}。检查拼写，或者变量是否在使用前被赋值。"))
        elif error_type == "IndexError" or "IndexError" in got:
            out.append(_finding("warning", "下标越界：IndexError", f"{where}{got}。检查列表是否可能为空，或下标是否从 0 开始。"))

    failed = [r for r in results if r.get("status") == "failed"]
    if failed and not errors:
        first = failed[0]
        if first.get("got", "") == "" and first.get("want"):
            out.append(
                _finding(
                    "warning",
                    "函数没有返回值",
                    f"`{first.get('source')}` 期望得到 {first.get('want')}，但什么都没有显示——函数很可能返回了 None。是不是用了 print 而不是 return，或者忘了 return？",
                )
            )
    return out


def _dedupe(findings: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for f in findings:
        key = (f["title"], f.get("line"), f.get("function"))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def check_constraints(code: str, function: str, constraints: list[dict]) -> list[dict]:
    """Return test-result entries for an exercise's structural constraints."""
    if not constraints:
        return []
    try:
        module = ast.parse(code)
    except SyntaxError:
        return []
    funcs = [n for n in ast.walk(module) if isinstance(n, ast.FunctionDef) and n.name == function]
    results = []
    for constraint in constraints:
        kind = constraint["type"]
        if kind == "recursive":
            ok = any(_contains_call_to(f, function) for f in funcs)
            message = f"{function} 必须是递归函数" if not ok else ""
            label = f"约束：{function} 使用递归"
        elif kind == "no_loops":
            ok = not any(isinstance(n, (ast.For, ast.While)) for f in funcs for n in ast.walk(f))
            message = f"{function} 中不能使用 for / while 循环" if not ok else ""
            label = f"约束：{function} 不使用循环"
        else:
            continue
        results.append(
            {
                "name": function,
                "origin": "constraint",
                "source": label,
                "want": "满足",
                "got": "满足" if ok else message,
                "status": "passed" if ok else "failed",
                "line": funcs[0].lineno if funcs else None,
            }
        )
    return results
