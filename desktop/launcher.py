"""Desktop entry point: runs the platform as a stand-alone app.

Starts the backend on a free local port and shows the UI in a native window
(pywebview). If no native web view is available (e.g. a Linux system without
GTK/Qt web view libraries), it opens the default browser instead.

The same executable doubles as the sandbox child process:
``Learn61A --learn61a-child REQUEST_PATH RESULT_PATH`` (see app/sandbox.py).

Options: ``--browser`` always use the default browser instead of a window;
``--port N`` use a fixed port.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys

CHILD_FLAG = "--learn61a-child"
TITLE = "61A 递归实验室"


def _run_child() -> None:
    from app.runner import child

    child.main(sys.argv[2], sys.argv[3])


def _setup_logging() -> str:
    """Log to ~/.learn61a/desktop.log so problems on users' machines can be diagnosed."""
    log_dir = os.path.join(os.path.expanduser("~"), ".learn61a")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "desktop.log")
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=1, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler],
    )
    os.environ["LEARN_LOG_FILE"] = log_file  # read by app.config for error messages
    return log_file


def _free_port() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(url: str, timeout: float = 20.0) -> bool:
    import time
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url + "api/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except OSError:
            time.sleep(0.1)
    return False


def _open_window(url: str) -> str | None:
    """Show the UI in a native window. Returns None on success, else why it failed."""
    log = logging.getLogger(__name__)
    try:
        import webview

        webview.create_window(TITLE, url, width=1440, height=920, min_size=(960, 640))
        webview.start()
        return None
    except Exception as e:  # noqa: BLE001 - no usable GUI backend on this system
        log.exception("could not open a native window; falling back to the browser")
        return f"{type(e).__name__}: {e}"


def _check_gui(result_file: str) -> None:
    """``--check-gui FILE``: open a real window, wait for it to load, close it.

    Used by CI to prove the packaged app gets a native window instead of
    silently falling back to the browser. Writes a JSON verdict to FILE.
    """
    import json
    import traceback

    result = {"ok": False, "gui": None, "error": None}
    try:
        import webview

        window = webview.create_window(TITLE, html="<h1>61A</h1>")

        def probe():
            result["ok"] = window.events.loaded.wait(60)
            result["gui"] = getattr(webview.guilib, "__name__", None)
            window.destroy()

        webview.start(probe)
    except Exception:  # noqa: BLE001
        result["error"] = traceback.format_exc()
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f)


def main() -> None:
    if len(sys.argv) >= 4 and sys.argv[1] == CHILD_FLAG:
        _run_child()
        return
    if len(sys.argv) >= 3 and sys.argv[1] == "--check-gui":
        _check_gui(sys.argv[2])
        return

    # A windowed app may have no console streams; uvicorn and logging need them.
    if sys.stdout is None or sys.stderr is None:
        sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):  # legacy Windows code pages cannot print Chinese
            stream.reconfigure(encoding="utf-8", errors="replace")

    log_file = _setup_logging()

    import threading
    import webbrowser

    import uvicorn

    from app.main import app

    args = sys.argv[1:]
    port = int(args[args.index("--port") + 1]) if "--port" in args else _free_port()
    # log_config=None: keep our file logging instead of uvicorn's console setup.
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/"
    logging.getLogger(__name__).info("serving on %s", url)
    if not _wait_until_up(url):
        print(f"后端启动失败，详见日志：{log_file}", file=sys.stderr)
        sys.exit(1)

    window_error = None if "--browser" in args else _open_window(url)
    if "--browser" in args or window_error:
        if window_error:
            # Shown by the UI so the user knows why they got a browser tab.
            import app.config

            app.config.WINDOW_ERROR = window_error
        webbrowser.open(url)
        print(f"{TITLE} 已在浏览器中打开：{url}\n关闭此窗口（或按 Ctrl+C）即可退出。")
        try:
            thread.join()
        except KeyboardInterrupt:
            pass
    server.should_exit = True


if __name__ == "__main__":
    main()
