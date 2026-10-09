"""The AI tutor.

If Claude API credentials are configured (``ANTHROPIC_API_KEY`` or
``ANTHROPIC_AUTH_TOKEN``), questions are answered by Claude with a Socratic
CS61A-TA persona. Otherwise - or if the API call fails - a rule-based answer
is assembled from the static analysis and the test results, so the platform
works fully offline.
"""

from __future__ import annotations

import logging
import os

from .analyzer import analyze

log = logging.getLogger(__name__)

MODEL = os.environ.get("LEARN_TUTOR_MODEL", "claude-opus-5-5")

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
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()
    return _client


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
        response = _get_client().beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium"},
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
