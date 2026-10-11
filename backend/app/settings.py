"""User settings for the AI tutor (API key, model), stored on this machine.

The file lives at ``~/.learn61a/settings.json`` (override with
``LEARN_SETTINGS_FILE``) and is only readable by the current user. A key saved
here takes precedence over the ``ANTHROPIC_API_KEY`` environment variable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_MODEL = "claude-opus-5-5"

MODELS = [
    {"id": "claude-opus-5-5", "label": "Claude Opus 5.5", "note": "讲解最透彻（默认）"},
    {"id": "claude-sonnet-5-5", "label": "Claude Sonnet 5.5", "note": "更快、更便宜"},
    {"id": "claude-haiku-5-5", "label": "Claude Haiku 5.5", "note": "最快、最便宜"},
]
MODEL_IDS = {m["id"] for m in MODELS}


def settings_path() -> Path:
    custom = os.environ.get("LEARN_SETTINGS_FILE")
    return Path(custom) if custom else Path.home() / ".learn61a" / "settings.json"


def load() -> dict:
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(data: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create the file readable by its owner only: it holds an API key.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update(api_key: str | None = None, clear_key: bool = False, model: str | None = None) -> dict:
    data = load()
    if clear_key:
        data.pop("api_key", None)
    elif api_key is not None and api_key.strip():
        data["api_key"] = api_key.strip()
    if model is not None:
        if model not in MODEL_IDS:
            raise ValueError(f"不支持的模型：{model}")
        data["model"] = model
    save(data)
    return data


def api_key() -> tuple[str | None, str | None]:
    """The key to use and where it came from: ("settings" | "env" | None)."""
    saved = load().get("api_key")
    if saved:
        return saved, "settings"
    env = os.environ.get("ANTHROPIC_API_KEY")
    if env:
        return env, "env"
    return None, None


def model() -> str:
    chosen = load().get("model") or os.environ.get("LEARN_TUTOR_MODEL") or DEFAULT_MODEL
    return chosen


def key_hint(key: str | None) -> str | None:
    if not key:
        return None
    return f"{key[:7]}…{key[-4:]}" if len(key) > 14 else "已设置"


def public() -> dict:
    """What the settings page may see: never the key itself."""
    key, source = api_key()
    return {
        "has_key": bool(key),
        "key_hint": key_hint(key),
        "key_source": source,
        "model": model(),
        "models": MODELS,
        "settings_file": str(settings_path()),
    }
