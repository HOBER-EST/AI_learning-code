from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import exercises, tutor
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def offline_tutor(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok", "tutor": "rules"}


def test_run_and_trace():
    assert client.post("/api/run", json={"code": "print(6 * 7)"}).json()["stdout"] == "42\n"
    data = client.post("/api/trace", json={"code": "def f(x):\n    return x\nf(1)\n"}).json()
    assert data["ok"] and data["calls"][0]["label"] == "f(1)"
    assert client.post("/api/trace", json={"code": "x = 1", "max_steps": 1}).status_code == 422


def test_test_endpoint_includes_analysis():
    code = 'def f(n):\n    """\n    >>> f(2)\n    4\n    """\n    n * 2\n'
    data = client.post("/api/test", json={"code": code}).json()
    assert data["summary"] == {"passed": 0, "failed": 1, "total": 1}
    assert "函数没有返回值" in [f["title"] for f in data["analysis"]["findings"]]


def test_upload_runs_tests_automatically():
    code = 'def double(n):\n    """\n    >>> double(3)\n    6\n    """\n    return n * 2\n'
    resp = client.post("/api/upload", files={"file": ("hw.py", code.encode(), "text/x-python")})
    data = resp.json()
    assert resp.status_code == 200
    assert data["filename"] == "hw.py" and data["functions"] == ["double"]
    assert data["tests"]["summary"]["passed"] == 1


def test_upload_validation():
    bad_ext = client.post("/api/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert bad_ext.status_code == 400
    too_big = client.post("/api/upload", files={"file": ("big.py", b"#" * 200_000, "text/x-python")})
    assert too_big.status_code == 413
    syntax = client.post(
        "/api/upload", files={"file": ("bad.py", b"def f(:\n", "text/x-python")}
    ).json()
    assert syntax["syntax"]["ok"] is False and syntax["tests"] is None
    assert syntax["analysis"]["findings"][0]["title"] == "语法错误"


def test_exercise_endpoints():
    listing = client.get("/api/exercises").json()
    assert len(listing) == len(exercises.EXERCISES)
    detail = client.get("/api/exercises/factorial").json()
    assert detail["starter"].startswith("def factorial")
    assert "solution" not in detail
    assert client.get("/api/exercises/nope").status_code == 404
    assert client.get("/api/topics").json().keys() == exercises.TOPICS.keys()


def test_submit_wrong_then_right():
    ex = exercises.get_exercise("factorial")
    wrong = client.post("/api/exercises/factorial/submit", json={"code": ex.starter}).json()
    assert wrong["solved"] is False
    loop = "def factorial(n):\n    r = 1\n    for i in range(1, n + 1):\n        r *= i\n    return r\n"
    looped = client.post("/api/exercises/factorial/submit", json={"code": loop}).json()
    assert looped["solved"] is False
    constraint = [r for r in looped["results"] if r["origin"] == "constraint"]
    assert constraint and constraint[0]["status"] == "failed"
    right = client.post("/api/exercises/factorial/submit", json={"code": ex.solution}).json()
    assert right["solved"] is True
    assert right["summary"]["passed"] == right["summary"]["total"]
    sol = client.get("/api/exercises/factorial/solution").json()
    assert sol["solution"] == ex.solution


def test_quiz_endpoints():
    quizzes = client.get("/api/quizzes").json()
    assert quizzes and "answer" not in quizzes[0]
    good = client.post("/api/quizzes/link-rest/check", json={"answer": "2"}).json()
    assert good["correct"] is True
    bad = client.post("/api/quizzes/link-rest/check", json={"answer": "3"}).json()
    assert bad["correct"] is False and bad["answer"] == "2"
    assert client.post("/api/quizzes/x/check", json={"answer": "1"}).status_code == 404


def test_tutor_rule_based():
    code = "def f(n):\n    return f(n)\n"
    data = client.post("/api/tutor", json={"code": code, "question": "为什么会报错？"}).json()
    assert data["source"] == "rules"
    assert "基本情况" in data["answer"]


def test_tutor_uses_claude_when_configured(monkeypatch):
    calls = {}

    class FakeMessages:
        def create(self, **kwargs):
            calls.update(kwargs)
            return SimpleNamespace(
                stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text="想一想 n == 0 时应该返回什么？")],
            )

    fake = SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages()))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(tutor, "_client", fake)
    data = client.post(
        "/api/tutor",
        json={"code": "def factorial(n):\n    return n * factorial(n - 1)\n", "question": "提示？", "exercise_id": "factorial"},
    ).json()
    assert data == {
        "source": "claude",
        "answer": "想一想 n == 0 时应该返回什么？",
        "findings": data["findings"],
    }
    assert calls["model"] == tutor.MODEL
    assert calls["fallbacks"] == "default"
    prompt = calls["messages"][0]["content"]
    assert "阶乘" in prompt and "factorial(n - 1)" in prompt


def test_tutor_falls_back_when_claude_fails(monkeypatch):
    class Broken:
        def create(self, **kwargs):
            raise RuntimeError("network down")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(tutor, "_client", SimpleNamespace(beta=SimpleNamespace(messages=Broken())))
    data = client.post("/api/tutor", json={"code": "x = 1", "question": "hi"}).json()
    assert data["source"] == "rules" and "notice" in data
