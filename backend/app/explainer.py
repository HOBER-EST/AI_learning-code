"""Code explanations: execution facts plus an offline, rule-based walkthrough.

``execution_summary`` runs the code once in the sandbox (with an example call)
so that every explanation, rule-based or from Claude, is grounded in what the
program really does. ``explain_offline`` turns the AST into a line-by-line
explanation in Chinese, used when Claude is not configured.
"""

from __future__ import annotations

import ast
import re
import textwrap

from . import analyzer, sandbox

MAX_TREE_LINES = 24


def _src(node: ast.AST) -> str:
    text = ast.unparse(node)
    return text if len(text) <= 70 else text[:67] + "..."


def _first_doctest_call(code: str) -> str | None:
    match = re.search(r"^\s*>>> (.+)$", code, re.M)
    return match.group(1).strip() if match else None


def _has_top_level_call(module: ast.Module) -> bool:
    return any(
        not isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom))
        and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
        for n in module.body
    )


# ------------------------------------------------------------ execution facts


def execution_summary(code: str, call: str | None = None) -> dict | None:
    """Run the code once (plus ``call``) and summarize what happened."""
    try:
        module = ast.parse(code)
    except SyntaxError:
        return None
    if not call and not _has_top_level_call(module):
        call = _first_doctest_call(code)
    if not call and not _has_top_level_call(module):
        return None
    program = code.rstrip() + ("\n\n" + call + "\n" if call else "\n")
    trace = sandbox.trace(program, max_steps=600)
    if trace.get("sandbox_error"):
        return {"call": call, "error": trace["sandbox_error"]["message"]}

    calls = trace.get("calls", [])
    children: dict[str | None, list[dict]] = {}
    for c in calls:
        children.setdefault(c["parent"], []).append(c)
    lines: list[str] = []

    def walk(node: dict, depth: int) -> None:
        if len(lines) >= MAX_TREE_LINES:
            return
        ret = f" → {node['ret']}" if node.get("ret") is not None else ""
        lines.append("    " * depth + node["label"] + ret)
        for child in children.get(node["id"], []):
            walk(child, depth + 1)

    for root in children.get(None, []):
        walk(root, 0)
    if len(calls) > len(lines):
        lines.append(f"…（共 {len(calls)} 次调用，只显示前 {len(lines)} 个）")

    labels = [c["label"] for c in calls]
    repeated = sorted({lbl for lbl in labels if labels.count(lbl) > 1}, key=lambda lbl: -labels.count(lbl))
    error = trace.get("error")
    return {
        "call": call,
        "total_calls": len(calls),
        "max_depth": max((c["depth"] for c in calls), default=0),
        "call_tree": "\n".join(lines),
        "repeated": [(lbl, labels.count(lbl)) for lbl in repeated[:5]],
        "stdout": (trace.get("stdout") or "")[:1000],
        "error": f"{error['type']}: {error['message']}" if error else None,
        "truncated": bool(trace.get("truncated")),
        "steps": len(trace.get("steps", [])),
    }


def format_summary(summary: dict | None) -> str:
    """Execution facts as plain text (also given to Claude as ground truth)."""
    if not summary:
        return "（没有可运行的调用，未实际执行）"
    if summary.get("error") and "total_calls" not in summary:
        return f"运行失败：{summary['error']}"
    parts = [f"执行的调用：{summary['call'] or '（代码中已有的语句）'}"]
    parts.append(f"共 {summary['steps']} 步，{summary['total_calls']} 次函数调用，最大递归深度 {summary['max_depth']}")
    if summary["call_tree"]:
        parts.append("调用树（→ 后是返回值）：\n" + summary["call_tree"])
    if summary["repeated"]:
        parts.append("重复计算的调用：" + "，".join(f"{lbl} ×{n}" for lbl, n in summary["repeated"]))
    if summary["stdout"]:
        parts.append("程序输出：\n" + summary["stdout"].rstrip())
    if summary["truncated"]:
        parts.append("注意：执行步数达到上限被截断，可能存在无限递归。")
    if summary["error"]:
        parts.append(f"运行出错：{summary['error']}")
    return "\n".join(parts)


# ------------------------------------------------------- offline walkthrough


def _calls_to(node: ast.AST, name: str) -> bool:
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name for n in ast.walk(node))


class _Describer:
    def __init__(self, line_offset: int):
        self.offset = line_offset
        self.lines: list[str] = []
        self.current_function: str | None = None

    def line(self, node: ast.AST, depth: int, text: str) -> None:
        number = getattr(node, "lineno", 0) + self.offset
        self.lines.append(f"{'  ' * depth}- **第 {number} 行**：{text}")

    def recursive_note(self, node: ast.AST) -> str:
        name = self.current_function
        if name and _calls_to(node, name):
            return f"（这里**递归**调用了 `{name}`：先相信它能正确解决更小的问题，再用它的结果拼出当前答案）"
        return ""

    def block(self, body: list[ast.stmt], depth: int) -> None:
        for stmt in body:
            self.stmt(stmt, depth)

    def stmt(self, node: ast.stmt, depth: int) -> None:
        if isinstance(node, ast.FunctionDef):
            params = ", ".join(a.arg for a in node.args.args)
            self.line(node, depth, f"定义函数 `{node.name}({params})`。定义时只是创建函数对象并绑定到名字 `{node.name}`，函数体要等调用时才执行。")
            outer, self.current_function = self.current_function, node.name
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                self.line(body[0], depth + 1, "文档字符串（docstring）：说明函数的作用，其中 `>>>` 开头的是 doctest 示例。")
                body = body[1:]
            self.block(body, depth + 1)
            self.current_function = outer
        elif isinstance(node, ast.ClassDef):
            self.line(node, depth, f"定义类 `{node.name}`。")
            self.block(node.body, depth + 1)
        elif isinstance(node, ast.Return):
            if node.value is None:
                self.line(node, depth, "结束函数，返回 `None`。")
            else:
                self.line(node, depth, f"计算 `{_src(node.value)}` 并把结果**返回**给调用者，函数到此结束。{self.recursive_note(node.value)}")
        elif isinstance(node, ast.If):
            self.line(node, depth, f"**如果** `{_src(node.test)}` 成立，执行下面缩进的语句：")
            self.block(node.body, depth + 1)
            orelse = node.orelse
            while len(orelse) == 1 and isinstance(orelse[0], ast.If):
                branch = orelse[0]
                self.line(branch, depth, f"**否则如果** `{_src(branch.test)}` 成立：")
                self.block(branch.body, depth + 1)
                orelse = branch.orelse
            if orelse:
                self.lines.append(f"{'  ' * depth}- **否则**（前面的条件都不成立）：")
                self.block(orelse, depth + 1)
        elif isinstance(node, ast.For):
            self.line(node, depth, f"**循环**：依次取出 `{_src(node.iter)}` 中的每个元素，记作 `{_src(node.target)}`，对它执行：")
            self.block(node.body, depth + 1)
        elif isinstance(node, ast.While):
            self.line(node, depth, f"**循环**：只要 `{_src(node.test)}` 成立，就反复执行：")
            self.block(node.body, depth + 1)
        elif isinstance(node, ast.Assign):
            targets = " = ".join(_src(t) for t in node.targets)
            if any(isinstance(t, (ast.Attribute, ast.Subscript)) for t in node.targets):
                what = f"**修改**对象：把 `{targets}` 设为 `{_src(node.value)}`（原地修改，所有指向这个对象的名字都会看到变化）。"
            else:
                what = f"计算 `{_src(node.value)}`，把结果绑定到名字 `{targets}`。"
            self.line(node, depth, what + self.recursive_note(node.value))
        elif isinstance(node, ast.AugAssign):
            op = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.FloorDiv: "//", ast.Div: "/", ast.Mod: "%"}.get(type(node.op), "?")
            self.line(node, depth, f"把 `{_src(node.target)}` 更新为 `{_src(node.target)} {op} {_src(node.value)}`。")
        elif isinstance(node, ast.Expr):
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                if "YOUR CODE HERE" in value.value:
                    self.line(node, depth, "占位符：这里还需要你写代码。")
                else:
                    self.line(node, depth, "一个字符串（通常是说明文字），不影响运行。")
            elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "print":
                self.line(node, depth, f"**打印** `{_src(value)}`：只是显示在屏幕上，并不会把值交给调用者（这和 return 不同）。")
            elif isinstance(value, ast.Call):
                note = self.recursive_note(value)
                if note:
                    note = f"（递归调用了 `{self.current_function}`；注意它的返回值没有被使用——如果需要结果，应该 return 或保存它）"
                self.line(node, depth, f"调用 `{_src(value)}`。{note}")
            else:
                self.line(node, depth, f"计算表达式 `{_src(value)}`。")
        elif isinstance(node, ast.Raise):
            self.line(node, depth, f"**抛出异常** `{_src(node.exc) if node.exc else ''}`，立即中止当前函数。")
        elif isinstance(node, ast.Assert):
            self.line(node, depth, f"**断言** `{_src(node.test)}` 必须成立，否则抛出 AssertionError。")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            self.line(node, depth, f"导入模块：`{_src(node)}`。")
        elif isinstance(node, ast.Pass):
            self.line(node, depth, "`pass`：什么也不做（占位）。")
        elif isinstance(node, ast.Break):
            self.line(node, depth, "`break`：立即跳出所在循环。")
        elif isinstance(node, ast.Continue):
            self.line(node, depth, "`continue`：跳过本轮剩余语句，进入下一轮循环。")
        else:
            self.line(node, depth, f"`{_src(node)}`")


def _parse_fragment(code: str) -> ast.Module | None:
    try:
        return ast.parse(textwrap.dedent(code))
    except SyntaxError:
        return None


def _recursion_section(info: dict, func: ast.FunctionDef | None) -> list[str]:
    name = info["name"]
    out = [f"### 递归分析：`{name}`（{info['kind']}）"]
    if info["has_base_case"]:
        out.append("1. **基本情况（base case）**：函数里有不需要递归就能直接返回的分支，递归会在那里停下。")
    else:
        out.append("1. **基本情况（base case）**：⚠ 没有找到不递归就返回的出口，递归可能停不下来。")
    if func is not None:
        params = [a.arg for a in func.args.args]
        shrink = []
        for call in [n for n in ast.walk(func) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name]:
            args = ", ".join(_src(a) for a in call.args)
            shrink.append(f"`{name}({args})`")
        if shrink:
            out.append(
                f"2. **问题变小**：参数从 `{name}({', '.join(params)})` 变成 "
                + "、".join(dict.fromkeys(shrink))
                + "，每次都更接近基本情况。"
            )
    if info["kind"] == "树递归":
        out.append("3. **树递归**：一次调用会产生多个递归调用，调用关系像一棵树；看看下面的调用树里有没有重复计算。")
    else:
        out.append("3. **线性递归**：每次调用最多再产生一个递归调用，调用关系是一条链。")
    out.append("4. **信任递归（recursive leap of faith）**：写递归时，假设对更小问题的递归调用已经返回了正确答案，只需要想清楚怎么用它得到当前答案。")
    return out


def explain_offline(code: str, selection: str | None, selection_line: int, summary: dict | None) -> str:
    target = selection if selection and selection.strip() else code
    offset = selection_line - 1 if selection and selection.strip() else 0
    parts: list[str] = []
    module = _parse_fragment(target)
    full = _parse_fragment(code)
    analysis = analyzer.analyze(code)

    parts.append("## 整体在做什么" if not selection else "## 选中的代码")
    funcs = [n for n in (module.body if module else []) if isinstance(n, ast.FunctionDef)]
    if funcs:
        for f in funcs:
            first = next((ln.strip() for ln in (ast.get_docstring(f) or "").split("\n") if ln.strip()), "")
            doc = "" if first.startswith(">>>") else first  # a docstring of only doctests has no summary
            info = next((i for i in analysis["functions"] if i["name"] == f.name), None)
            kind = f"，是一个**{info['kind']}**函数" if info and info["recursive"] else ""
            parts.append(f"- `{f.name}({', '.join(a.arg for a in f.args.args)})`{kind}。{('说明：' + doc) if doc else ''}")
    elif module is None:
        parts.append("这段选中的内容不是完整的语句（比如只选了 `if` 的条件行），下面按整段代码讲解。")
        module, offset = full, 0
    else:
        parts.append("这段代码由若干条语句组成，逐条说明如下。")

    if module is not None:
        parts.append("\n## 逐行讲解")
        describer = _Describer(offset)
        describer.block(module.body, 0)
        parts.extend(describer.lines)

    recursive = [i for i in analysis["functions"] if i["recursive"] and (not funcs or i["name"] in {f.name for f in funcs})]
    if recursive:
        parts.append("\n## 递归是怎么工作的")
        defs = {n.name: n for n in ast.walk(full) if isinstance(n, ast.FunctionDef)} if full else {}
        for info in recursive:
            node = defs.get(info["name"])
            parts.extend(_recursion_section(info, node if isinstance(node, ast.FunctionDef) else None))

    if summary:
        parts.append("\n## 实际运行一遍")
        parts.append("```text\n" + format_summary(summary) + "\n```")
        if summary.get("repeated"):
            parts.append("同样的参数被计算了好几次——这就是树递归常见的**重复计算**，可以用记忆化（memoization）优化。")
        parts.append("想一步一步看清楚？点击 **🔍 可视化**，在环境图和递归调用树里逐步执行。")

    problems = [f for f in analysis["findings"] if f["level"] in ("error", "warning")]
    if problems:
        parts.append("\n## 需要注意")
        parts.extend(f"- **{f['title']}**：{f['message']}" for f in problems)

    parts.append("\n> 当前为离线讲解。在“设置”中填写 Anthropic API key 后，可以获得 Claude 的详细讲解，并能继续追问。")
    return "\n".join(parts)
