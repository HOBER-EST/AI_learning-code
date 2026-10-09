"""Every exercise must be solvable, and its starter code must not pass."""

import ast

import pytest

from app import analyzer, exercises, sandbox
from app.runner.prelude import make_builtins
from app.runner.tracer import trace_code

ALL = exercises.EXERCISES


def test_ids_are_unique_and_topics_known():
    ids = [e.id for e in ALL]
    assert len(ids) == len(set(ids))
    assert {e.topic for e in ALL} == set(exercises.TOPICS)
    for topic in exercises.TOPICS:
        assert sum(1 for e in ALL if e.topic == topic) >= 5


@pytest.mark.parametrize("ex", ALL, ids=lambda e: e.id)
def test_solution_passes_all_tests(ex):
    result = sandbox.run_tests(ex.solution, ex.all_tests, run_doctests=True)
    failures = [r for r in result["results"] if r["status"] != "passed"]
    assert result["load_error"] is None
    assert not failures, failures
    assert result["summary"]["total"] >= 4
    constraints = analyzer.check_constraints(ex.solution, ex.function, ex.constraints)
    assert all(c["status"] == "passed" for c in constraints)


@pytest.mark.parametrize("ex", ALL, ids=lambda e: e.id)
def test_starter_fails(ex):
    result = sandbox.run_tests(ex.starter, ex.all_tests, run_doctests=False)
    assert result["load_error"] is None
    assert result["summary"]["failed"] > 0


@pytest.mark.parametrize("ex", ALL, ids=lambda e: e.id)
def test_exercise_metadata(ex):
    assert ex.function in [n.name for n in ast.parse(ex.starter).body if isinstance(n, ast.FunctionDef)]
    assert ex.hints and ex.description.strip()
    assert ex.visible_tests.startswith(">>> ")
    assert ex.hidden_tests.strip().startswith(">>> ")
    detail = ex.detail()
    assert "solution" not in detail and "hidden_tests" not in detail
    assert detail["hidden_test_count"] >= 1


@pytest.mark.parametrize("ex", ALL, ids=lambda e: e.id)
def test_trace_example_visualizes_the_solution(ex):
    result = trace_code(ex.solution + "\n" + ex.trace + "\n", builtins_dict=make_builtins())
    assert result["ok"], result["error"]
    assert any(c["name"] == ex.function for c in result["calls"])
