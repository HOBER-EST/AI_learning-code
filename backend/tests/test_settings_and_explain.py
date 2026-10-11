import json
import os
import stat
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import explainer, settings, tutor
from app.main import app

client = TestClient(app)
FIB = "def fib(n):\n    if n <= 1:\n        return n\n    return fib(n - 1) + fib(n - 2)\n"


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LEARN_TUTOR_MODEL", raising=False)
    monkeypatch.setenv("LEARN_SETTINGS_FILE", str(tmp_path / "settings.json"))
    monkeypatch.setattr(tutor, "_client", None)
    monkeypatch.setattr(tutor, "_client_key", None)


def events(resp):
    return [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]


# ------------------------------------------------------------------ settings


def test_settings_roundtrip_never_returns_the_key(tmp_path):
    assert client.get("/api/settings").json()["has_key"] is False
    data = client.put("/api/settings", json={"api_key": "  sk-ant-api03-SECRETSECRET-wxyz ", "model": "claude-sonnet-5-5"}).json()
    assert data["has_key"] and data["key_source"] == "settings"
    assert data["key_hint"] == "sk-ant-…wxyz"
    assert data["model"] == "claude-sonnet-5-5"
    assert "SECRET" not in json.dumps(data)
    path = tmp_path / "settings.json"
    assert json.loads(path.read_text())["api_key"] == "sk-ant-api03-SECRETSECRET-wxyz"
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert client.get("/api/health").json()["tutor"] == "claude"

    cleared = client.put("/api/settings", json={"clear_key": True}).json()
    assert cleared["has_key"] is False and cleared["model"] == "claude-sonnet-5-5"
    assert client.get("/api/health").json()["tutor"] == "rules"


def test_settings_key_overrides_environment(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-environment-1234")
    assert settings.public()["key_source"] == "env"
    settings.update(api_key="sk-ant-from-settings-page-5678")
    assert settings.api_key() == ("sk-ant-from-settings-page-5678", "settings")


def test_settings_reject_unknown_model():
    assert client.put("/api/settings", json={"model": "gpt-4"}).status_code == 400


def test_settings_are_local_only():
    remote = TestClient(app, client=("203.0.113.9", 5000))
    assert remote.get("/api/settings").status_code == 403
    assert remote.put("/api/settings", json={"api_key": "sk-ant-x"}).status_code == 403


def test_connection_check_reports_bad_keys(monkeypatch):
    import anthropic

    class FakeModels:
        def retrieve(self, model):
            request = SimpleNamespace(method="GET", url="x", headers={})
            raise anthropic.AuthenticationError("bad key", response=SimpleNamespace(status_code=401, request=request, headers={}), body=None)

    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: SimpleNamespace(models=FakeModels()))
    result = client.post("/api/settings/test", json={"api_key": "sk-ant-wrong"}).json()
    assert result == {"ok": False, "message": "API key 无效：请检查是否复制完整（以 sk-ant- 开头）。"}
    assert client.post("/api/settings/test", json={}).json()["ok"] is False  # no key at all


def test_connection_check_success(monkeypatch):
    import anthropic

    seen = {}

    class FakeModels:
        def retrieve(self, model):
            seen["model"] = model

    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: SimpleNamespace(models=FakeModels()))
    result = client.post("/api/settings/test", json={"api_key": "sk-ant-ok", "model": "claude-haiku-5-5"}).json()
    assert result["ok"] is True and seen["model"] == "claude-haiku-5-5"


# ------------------------------------------------------------------ explain


def test_execution_summary_runs_the_first_doctest_call():
    code = FIB.replace("    if", '    """\n    >>> fib(4)\n    3\n    """\n    if', 1)
    summary = explainer.execution_summary(code)
    assert summary["call"] == "fib(4)"
    assert summary["total_calls"] == 9 and summary["max_depth"] == 4
    assert summary["call_tree"].startswith("fib(4) → 3")
    assert ("fib(1)", 3) in summary["repeated"]


def test_offline_explanation_streams_a_walkthrough():
    resp = client.post("/api/explain", json={"code": FIB, "call": "fib(3)"})
    assert resp.headers["content-type"].startswith("text/event-stream")
    evs = events(resp)
    assert evs[0] == {"type": "meta", "source": "rules"}
    assert evs[-1] == {"type": "done"}
    text = "".join(e["text"] for e in evs if e["type"] == "delta")
    assert "**第 1 行**：定义函数 `fib(n)`" in text
    assert "**如果** `n <= 1` 成立" in text
    assert "树递归" in text and "fib(3) → 2" in text
    assert "fib(n - 1)" in text  # how the problem shrinks


def test_offline_explanation_of_a_selection_uses_real_line_numbers():
    selection = "    if n <= 1:\n        return n\n"
    evs = events(client.post("/api/explain", json={"code": FIB, "selection": selection, "selection_line": 2}))
    text = "".join(e["text"] for e in evs if e["type"] == "delta")
    assert "## 选中的代码" in text
    assert "**第 2 行**：**如果** `n <= 1`" in text
    assert "**第 3 行**：计算 `n` 并把结果**返回**" in text


def test_explanation_mentions_problems():
    code = "def f(n):\n    if n == 0:\n        return 0\n    f(n - 1)\n"
    evs = events(client.post("/api/explain", json={"code": code, "call": "f(2)"}))
    text = "".join(e["text"] for e in evs if e["type"] == "delta")
    assert "返回值没有被使用" in text and "需要注意" in text


def test_claude_explanation_streams_and_gets_execution_facts(monkeypatch):
    seen = {}

    class FakeStream:
        text_stream = iter(["## 整体", "在做什么\n", "fib 计算斐波那契数。"])

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_final_message(self):
            return SimpleNamespace(stop_reason="end_turn")

    class FakeMessages:
        def stream(self, **kwargs):
            seen.update(kwargs)
            return FakeStream()

    settings.update(api_key="sk-ant-test-key-abcd", model="claude-haiku-5-5")
    monkeypatch.setattr(tutor, "_client", SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages())))
    monkeypatch.setattr(tutor, "_client_key", "sk-ant-test-key-abcd")
    evs = events(client.post("/api/explain", json={"code": FIB, "call": "fib(3)", "question": "为什么是树递归？"}))
    assert evs[0] == {"type": "meta", "source": "claude", "model": "claude-haiku-5-5"}
    assert "".join(e["text"] for e in evs if e["type"] == "delta") == "## 整体在做什么\nfib 计算斐波那契数。"
    assert evs[-1] == {"type": "done"}
    prompt = seen["messages"][0]["content"]
    assert "fib(3) → 2" in prompt and "为什么是树递归" in prompt
    assert seen["model"] == "claude-haiku-5-5"
    assert "fallbacks" not in seen  # Haiku has no server-side fallback


def test_claude_explanation_errors_are_reported(monkeypatch):
    class Broken:
        def stream(self, **kwargs):
            raise RuntimeError("network down")

    settings.update(api_key="sk-ant-test-key-abcd")
    monkeypatch.setattr(tutor, "_client", SimpleNamespace(beta=SimpleNamespace(messages=Broken())))
    monkeypatch.setattr(tutor, "_client_key", "sk-ant-test-key-abcd")
    evs = events(client.post("/api/explain", json={"code": "x = 1"}))
    assert evs[-1]["type"] == "error" and "测试连接" in evs[-1]["message"]
