"""The AI tutor.

If an Anthropic API key is configured (on the settings page, or via
``ANTHROPIC_API_KEY``), questions are answered by Claude with a Socratic
CS61A-TA persona. Otherwise - or if the API call fails - a rule-based answer
is assembled from the static analysis and the test results, so the platform
works fully offline.
"""

from __future__ import annotations

import logging
import os

from . import explainer, settings
from .analyzer import analyze

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是 UC Berkeley CS61A 课程的一名耐心的助教，正在帮助中文学生学习递归（Recursion）、链表（Link）和树（Tree）。

教学原则：
- 用中文回答，语气友好、简洁。
- 采用苏格拉底式引导：指出问题所在的位置和原因，给出思考方向或一个更小的例子，但不要直接给出完整的正确答案代码。
- 学生明确要求看答案时，也只给出关键的一两行或伪代码，并解释为什么。
- 结合提供的测试结果、静态分析和题目说明作答；引用代码时注明行号。
- 适时建议学生使用平台的“可视化”功能（环境图 Environment Diagram、递归调用树）来观察执行过程。
- 讲解递归时强调三件事：基本情况（base case）、问题如何变小、如何信任递归调用（recursive leap of faith）。
- 回答使用 Markdown，代码用 ```python 代码块。"""


def claude_enabled() -> bool:
    if os.environ.get("LEARN_TUTOR", "").lower() == "off":
        return False
    return settings.api_key()[0] is not None


_client = None
_client_key: str | None = None


def _get_client():
    """An Anthropic client for the currently configured key (rebuilt if it changes)."""
    global _client, _client_key
    key = settings.api_key()[0]
    if _client is None or key != _client_key:
        import anthropic

        _client = anthropic.Anthropic(api_key=key)
        _client_key = key
    return _client


def _request_options(model: str) -> dict:
    """Model-specific request options shared by every tutor call."""
    options: dict = {"output_config": {"effort": "medium"}}
    # Server-side fallback re-runs a declined request on another model. Haiku
    # has no fallback model, so the parameter is not sent for it.
    if not model.startswith("claude-haiku"):
        options["betas"] = ["server-side-fallback-2026-07-01"]
        options["fallbacks"] = "default"
    return options


def check_connection(api_key: str | None = None, model: str | None = None) -> dict:
    """Verify a key and model with a cheap Models API call (no tokens are billed)."""
    import anthropic

    key = api_key or settings.api_key()[0]
    model = model or settings.model()
    if not key:
        return {"ok": False, "message": "还没有填写 API key。"}
    try:
        anthropic.Anthropic(api_key=key, max_retries=0, timeout=15).models.retrieve(model)
    except anthropic.AuthenticationError:
        return {"ok": False, "message": "API key 无效：请检查是否复制完整（以 sk-ant- 开头）。"}
    except anthropic.PermissionDeniedError:
        return {"ok": False, "message": "这个 API key 没有权限使用该模型。"}
    except anthropic.NotFoundError:
        return {"ok": False, "message": f"找不到模型 {model}，请换一个模型。"}
    except anthropic.APIConnectionError:
        return {"ok": False, "message": "连不上 Anthropic 服务器：请检查网络或代理设置。"}
    except anthropic.APIStatusError as e:
        return {"ok": False, "message": f"Anthropic 返回错误（{e.status_code}）：{e.message}"}
    return {"ok": True, "message": f"连接成功，将使用 {model}。"}


def _format_results(test_results: dict | None) -> str:
    if not test_results:
        return "（学生还没有运行测试）"
    if test_results.get("load_error"):
        e = test_results["load_error"]
        return f"代码无法加载：{e.get('type')}: {e.get('message')}（第 {e.get('line')} 行）"
    if test_results.get("sandbox_error"):
        return f"运行失败：{test_results['sandbox_error'].get('message')}"
    summary = test_results.get("summary") or {}
    lines = [f"通过 {summary.get('passed', 0)} / {summary.get('total', 0)} 个测试。"]
    for r in [r for r in test_results.get("results", []) if r.get("status") != "passed"][:6]:
        lines.append(
            f"- [{r.get('status')}] >>> {r.get('source')}\n  期望: {r.get('want') or '(无输出)'}\n  实际: {r.get('got') or '(无输出)'}"
        )
    return "\n".join(lines)


def _format_findings(findings: list[dict]) -> str:
    if not findings:
        return "（静态分析没有发现问题）"
    return "\n".join(f"- [{f['level']}] {f['title']}：{f['message']}" for f in findings)


def rule_based_answer(question: str, findings: list[dict], test_results: dict | None, exercise=None) -> str:
    parts: list[str] = []
    serious = [f for f in findings if f["level"] in ("error", "warning")]
    if serious:
        parts.append("我检查了你的代码，发现这些值得注意的地方：\n")
        for f in serious:
            loc = f"（第 {f['line']} 行）" if f.get("line") else ""
            parts.append(f"- **{f['title']}**{loc}：{f['message']}")
    summary = (test_results or {}).get("summary") or {}
    failed = [r for r in (test_results or {}).get("results", []) if r.get("status") != "passed"]
    if failed:
        r = failed[0]
        parts.append(
            "\n第一个没通过的测试是：\n\n```python\n>>> "
            + r.get("source", "")
            + "\n```\n\n"
            + f"期望 `{r.get('want') or '(无输出)'}`，实际得到 `{r.get('got') or '(无输出)'}`。"
            + "\n\n建议：点击 **可视化**，把这个调用放到代码末尾，一步一步观察环境图和递归调用树，看看哪一步的值和你预想的不一样。"
        )
    elif test_results and summary.get("total") and not serious:
        parts.append(
            f"所有 {summary['total']} 个测试都通过了，做得好！🎉\n\n可以再想一想：这个函数一共会产生多少次递归调用？用 **递归调用树** 验证你的猜想。"
        )
    if exercise is not None and (failed or serious or not test_results):
        parts.append(f"\n💡 提示：{exercise.hints[0]}")
    if not parts:
        parts.append(
            "我没有发现明显的问题。写递归函数时可以按这三步检查：\n\n"
            "1. **基本情况**：最简单的输入是什么？直接返回什么？\n"
            "2. **缩小问题**：递归调用的参数是否更接近基本情况？\n"
            "3. **信任递归**：假设递归调用已经返回正确结果，如何用它得到当前问题的答案？"
        )
    if question.strip():
        parts.append("\n> 当前为离线规则导师模式。配置 `ANTHROPIC_API_KEY` 后，可以用自然语言和 Claude 导师对话。")
    return "\n".join(parts)


def ask(question: str, code: str, test_results: dict | None = None, exercise=None) -> dict:
    analysis = analyze(code, test_results)
    findings = analysis["findings"]
    if not claude_enabled():
        return {
            "source": "rules",
            "answer": rule_based_answer(question, findings, test_results, exercise),
            "findings": findings,
        }

    context = []
    if exercise is not None:
        context.append(f"## 题目：{exercise.title}\n{exercise.description}")
    context.append(f"## 学生代码\n```python\n{_numbered(code)}\n```")
    context.append(f"## 测试结果\n{_format_results(test_results)}")
    context.append(f"## 静态分析\n{_format_findings(findings)}")
    context.append(f"## 学生的问题\n{question.strip() or '我的代码哪里有问题？请给我一点提示。'}")
    try:
        model = settings.model()
        response = _get_client().beta.messages.create(
            model=model,
            max_tokens=16000,
            **_request_options(model),
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "\n\n".join(context)}],
        )
    except Exception as e:  # noqa: BLE001 - any API failure falls back to rules
        log.warning("Claude tutor request failed: %s", e)
        answer = rule_based_answer(question, findings, test_results, exercise)
        return {"source": "rules", "answer": answer, "findings": findings, "notice": "Claude 暂时不可用，已切换为规则导师。"}

    if response.stop_reason == "refusal":
        answer = rule_based_answer(question, findings, test_results, exercise)
        return {"source": "rules", "answer": answer, "findings": findings, "notice": "Claude 拒绝了这个请求，已切换为规则导师。"}
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return {"source": "claude", "answer": text, "findings": findings}


def _numbered(code: str) -> str:
    return "\n".join(f"{i:>3} | {line}" for i, line in enumerate(code.split("\n"), start=1))


EXPLAIN_PROMPT = """你是 UC Berkeley CS61A 课程的一名助教，正在给中文学生**讲解一段 Python 代码**，重点是递归（Recursion）、链表（Link）和树（Tree）。

讲解要求：
- 用中文，Markdown 格式，语气友好清晰；引用代码时注明行号（行号以提供的带行号代码为准）。
- 结构：
  1. **整体在做什么**：两三句话说明代码的目的。
  2. **逐段讲解**：按代码顺序解释关键语句，说明每一步为什么这样写。
  3. **递归分析**（如果有递归）：基本情况是什么、问题如何一步步变小、怎样“信任递归调用”把子问题的答案组合成当前答案；如果是树递归，指出调用树的形状。
  4. **走一遍例子**：用提供的“实际运行结果”（这是在沙箱中真实执行得到的事实）一步步说明调用和返回的过程，不要编造与之矛盾的结果。
  5. **注意事项**：指出代码中的错误、隐患或可以改进的地方（如重复计算、缺少 return）。
- 如果代码是一道练习的未完成答案，只讲解学生已经写出的部分和思路方向，**不要直接写出完整解法**。
- 如果学生只选中了一部分代码，重点讲解选中的部分，必要时结合上下文。
- 如果学生提出了具体问题，先直接回答这个问题。"""


def _numbered_from(code: str, start: int) -> str:
    return "\n".join(f"{i:>3} | {line}" for i, line in enumerate(code.split("\n"), start=start))


def explain_stream(
    code: str,
    selection: str | None = None,
    selection_line: int = 1,
    question: str = "",
    call: str | None = None,
    exercise=None,
):
    """Yield (event, payload) pairs: ("meta", {...}), ("delta", text), ("done", None) or ("error", message)."""
    summary = explainer.execution_summary(code, call)

    if not claude_enabled():
        yield "meta", {"source": "rules"}
        text = explainer.explain_offline(code, selection, selection_line, summary)
        # Emit paragraph by paragraph so the UI fills in progressively.
        for chunk in text.split("\n"):
            yield "delta", chunk + "\n"
        yield "done", None
        return

    model = settings.model()
    yield "meta", {"source": "claude", "model": model}
    context = []
    if exercise is not None:
        context.append(f"## 练习题目：{exercise.title}\n{exercise.description}")
    context.append(f"## 完整代码（带行号）\n```python\n{_numbered(code)}\n```")
    if selection and selection.strip():
        context.append(
            f"## 学生选中的部分（从第 {selection_line} 行开始）\n```python\n{_numbered_from(selection, selection_line)}\n```"
        )
    context.append(f"## 实际运行结果（沙箱真实执行）\n{explainer.format_summary(summary)}")
    context.append(
        "## 学生的请求\n" + (question.strip() or ("请讲解我选中的这部分代码。" if selection and selection.strip() else "请讲解这段代码。"))
    )
    try:
        with _get_client().beta.messages.stream(
            model=model,
            max_tokens=32000,
            **_request_options(model),
            system=EXPLAIN_PROMPT,
            messages=[{"role": "user", "content": "\n\n".join(context)}],
        ) as stream:
            for text in stream.text_stream:
                yield "delta", text
            final = stream.get_final_message()
        if final.stop_reason == "refusal":
            yield "error", "Claude 拒绝了这次讲解请求，请换一种问法或只选中部分代码再试。"
            return
        yield "done", None
    except Exception as e:  # noqa: BLE001 - surface API problems to the user
        log.warning("Claude explain request failed: %s", e)
        yield "error", f"Claude 暂时不可用（{type(e).__name__}）。可以在“设置”里点“测试连接”检查 API key 和网络。"
