"""FastAPI application: REST API + (optionally) the built frontend."""

from __future__ import annotations

import ast
import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import analyzer, config, exercises, quizzes, sandbox, tutor

app = FastAPI(title="CS61A 递归学习平台", version="1.0.0")
app.add_middleware(GZipMiddleware, minimum_size=2000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("LEARN_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeRequest(BaseModel):
    code: str = Field(max_length=config.MAX_CODE_BYTES)


class TraceRequest(CodeRequest):
    max_steps: int | None = Field(default=None, ge=10, le=5000)


class TestRequest(CodeRequest):
    tests: str | None = Field(default=None, max_length=config.MAX_CODE_BYTES)


class AnalyzeRequest(CodeRequest):
    test_results: dict | None = None


class TutorRequest(CodeRequest):
    question: str = Field(default="", max_length=4000)
    test_results: dict | None = None
    exercise_id: str | None = None


class AnswerRequest(BaseModel):
    answer: str = Field(max_length=2000)


def _with_analysis(code: str, results: dict) -> dict:
    results["analysis"] = analyzer.analyze(code, results)
    return results


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "tutor": "claude" if tutor.claude_enabled() else "rules"}


@app.post("/api/run")
def run(req: CodeRequest) -> dict:
    return sandbox.run_program(req.code)


@app.post("/api/test")
def run_tests_endpoint(req: TestRequest) -> dict:
    return _with_analysis(req.code, sandbox.run_tests(req.code, req.tests))


@app.post("/api/trace")
def trace(req: TraceRequest) -> dict:
    return sandbox.trace(req.code, req.max_steps)


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    return analyzer.analyze(req.code, req.test_results)


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), auto_test: bool = Form(True)) -> dict:
    name = os.path.basename(file.filename or "upload.py")
    if not name.endswith(".py"):
        raise HTTPException(400, "只支持上传 .py 文件")
    raw = await file.read(config.MAX_CODE_BYTES + 1)
    if len(raw) > config.MAX_CODE_BYTES:
        raise HTTPException(413, f"文件太大（上限 {config.MAX_CODE_BYTES // 1024} KB）")
    try:
        code = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "文件不是 UTF-8 编码") from None
    code = code.replace("\r\n", "\n")

    syntax = {"ok": True, "message": None, "line": None}
    functions: list[str] = []
    try:
        module = ast.parse(code)
        functions = [n.name for n in module.body if isinstance(n, ast.FunctionDef)]
    except SyntaxError as e:
        syntax = {"ok": False, "message": e.msg, "line": e.lineno}

    response = {"filename": name, "code": code, "syntax": syntax, "functions": functions, "tests": None}
    if auto_test and syntax["ok"]:
        response["tests"] = _with_analysis(code, sandbox.run_tests(code))
    else:
        response["analysis"] = analyzer.analyze(code)
    return response


@app.get("/api/topics")
def topics() -> dict:
    return exercises.TOPICS


@app.get("/api/exercises")
def list_exercises() -> list[dict]:
    return exercises.list_exercises()


def _exercise_or_404(exercise_id: str):
    ex = exercises.get_exercise(exercise_id)
    if ex is None:
        raise HTTPException(404, "练习不存在")
    return ex


@app.get("/api/exercises/{exercise_id}")
def get_exercise(exercise_id: str) -> dict:
    return _exercise_or_404(exercise_id).detail()


@app.post("/api/exercises/{exercise_id}/submit")
def submit(exercise_id: str, req: CodeRequest) -> dict:
    ex = _exercise_or_404(exercise_id)
    results = sandbox.run_tests(req.code, ex.all_tests, run_doctests=False)
    if results.get("results") is not None and not results.get("load_error"):
        constraint_results = analyzer.check_constraints(req.code, ex.function, ex.constraints)
        results["results"].extend(constraint_results)
        passed = sum(1 for r in results["results"] if r["status"] == "passed")
        total = len(results["results"])
        results["summary"] = {"passed": passed, "failed": total - passed, "total": total}
        results["ok"] = passed == total
    results["solved"] = bool(results.get("ok"))
    return _with_analysis(req.code, results)


@app.get("/api/exercises/{exercise_id}/solution")
def solution(exercise_id: str) -> dict:
    return {"solution": _exercise_or_404(exercise_id).solution}


@app.get("/api/quizzes")
def list_quizzes() -> list[dict]:
    return [q.public() for q in quizzes.QUIZZES]


@app.post("/api/quizzes/{quiz_id}/check")
def check_quiz(quiz_id: str, req: AnswerRequest) -> dict:
    quiz = quizzes.QUIZZES_BY_ID.get(quiz_id)
    if quiz is None:
        raise HTTPException(404, "题目不存在")
    return quizzes.check_answer(quiz, req.answer)


@app.post("/api/tutor")
def ask_tutor(req: TutorRequest) -> dict:
    ex = exercises.get_exercise(req.exercise_id) if req.exercise_id else None
    return tutor.ask(req.question, req.code, req.test_results, ex)


_dist = os.path.abspath(config.FRONTEND_DIST)
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
