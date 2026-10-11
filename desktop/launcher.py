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

import os
import sys

CHILD_FLAG = "--learn61a-child"
TITLE = "61A 递归实验室"


def _run_child() -> None:
    from app.runner import child

    child.main(sys.argv[2], sys.argv[3])


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


def _open_window(url: str) -> bool:
    try:
        import webview
    except ImportError:
        return False
    try:
        webview.create_window(TITLE, url, width=1440, height=920, min_size=(960, 640))
        webview.start()
        return True
    except Exception:  # noqa: BLE001 - no usable GUI backend on this system
        return False


def main() -> None:
    if len(sys.argv) >= 4 and sys.argv[1] == CHILD_FLAG:
        _run_child()
        return

    # A windowed app may have no console streams; uvicorn and logging need them.
    if sys.stdout is None or sys.stderr is None:
        sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):  # legacy Windows code pages cannot print Chinese
            stream.reconfigure(encoding="utf-8", errors="replace")

    import threading
    import webbrowser

    import uvicorn

    from app.main import app

    args = sys.argv[1:]
    port = int(args[args.index("--port") + 1]) if "--port" in args else _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/"
    if not _wait_until_up(url):
        print("后端启动失败。", file=sys.stderr)
        sys.exit(1)

    if "--browser" in args or not _open_window(url):
        webbrowser.open(url)
        print(f"{TITLE} 已在浏览器中打开：{url}\n关闭此窗口（或按 Ctrl+C）即可退出。")
        try:
            thread.join()
        except KeyboardInterrupt:
            pass
    server.should_exit = True


if __name__ == "__main__":
    main()
