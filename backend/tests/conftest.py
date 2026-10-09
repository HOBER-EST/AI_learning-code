import pytest

from app.runner.prelude import make_builtins
from app.runner.tracer import trace_code


@pytest.fixture
def trace():
    def run(code: str, max_steps: int = 1000) -> dict:
        return trace_code(code, max_steps=max_steps, builtins_dict=make_builtins())

    return run
