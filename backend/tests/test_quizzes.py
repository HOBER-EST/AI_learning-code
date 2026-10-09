"""Verifies every stored WWPD answer against what Python actually displays."""

import contextlib
import io

import pytest

from app import quizzes
from app.runner.prelude import make_builtins


def what_python_displays(setup: str, expression: str) -> str:
    env = {"__builtins__": make_builtins()}
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            exec(setup, env)
            value = eval(expression, env)
            if value is not None:
                print(repr(value) if not callable(value) else "Function")
    except Exception:  # noqa: BLE001
        return quizzes.normalize(out.getvalue() + "\nError")
    return quizzes.normalize(out.getvalue())


@pytest.mark.parametrize("quiz", quizzes.QUIZZES, ids=lambda q: q.id)
def test_stored_answer_matches_python(quiz):
    assert quizzes.normalize(quiz.answer) == what_python_displays(quiz.setup, quiz.expression)


def test_check_answer_normalization():
    quiz = quizzes.QUIZZES_BY_ID["rec-order"]
    assert quizzes.check_answer(quiz, "2\n1\n'done'\n")["correct"]
    assert quizzes.check_answer(quiz, '  2\r\n1\n"done"  ')["correct"]
    assert not quizzes.check_answer(quiz, "2\n1\ndone")["correct"]
    error_quiz = quizzes.QUIZZES_BY_ID["rec-infinite"]
    assert quizzes.check_answer(error_quiz, "error")["correct"]
    result = quizzes.check_answer(error_quiz, "None")
    assert result == {"correct": False, "answer": "Error", "explanation": error_quiz.explanation}


def test_ids_unique():
    assert len(quizzes.QUIZZES_BY_ID) == len(quizzes.QUIZZES)
