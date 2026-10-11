import os
import sys

TRACE_TIMEOUT = float(os.environ.get("LEARN_TRACE_TIMEOUT", "10"))
TEST_TIMEOUT = float(os.environ.get("LEARN_TEST_TIMEOUT", "20"))
RUN_TIMEOUT = float(os.environ.get("LEARN_RUN_TIMEOUT", "5"))
EXAMPLE_TIMEOUT = float(os.environ.get("LEARN_EXAMPLE_TIMEOUT", "2"))
MAX_TRACE_STEPS = int(os.environ.get("LEARN_MAX_TRACE_STEPS", "1000"))
MEMORY_LIMIT_MB = int(os.environ.get("LEARN_MEMORY_LIMIT_MB", "512"))
MAX_CONCURRENT_RUNS = int(os.environ.get("LEARN_MAX_CONCURRENT_RUNS", "4"))
MAX_CODE_BYTES = int(os.environ.get("LEARN_MAX_CODE_BYTES", str(100 * 1024)))
if getattr(sys, "frozen", False):  # packaged desktop app (PyInstaller)
    _default_dist = os.path.join(getattr(sys, "_MEIPASS", ""), "frontend_dist")
else:
    _default_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
FRONTEND_DIST = os.environ.get("LEARN_FRONTEND_DIST", _default_dist)
