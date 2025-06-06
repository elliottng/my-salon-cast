import os
import importlib
from app.config import Config

def test_use_pydantic_ai_flag(monkeypatch):
    monkeypatch.setenv("USE_PYDANTIC_AI", "true")
    cfg = Config()
    assert cfg.use_pydantic_ai is True
    monkeypatch.setenv("USE_PYDANTIC_AI", "false")
    cfg = Config()
    assert cfg.use_pydantic_ai is False


def test_pydantic_ai_importable():
    try:
        import pydantic_ai  # noqa: F401
    except Exception as e:
        raise AssertionError(f"Failed to import pydantic_ai: {e}")
