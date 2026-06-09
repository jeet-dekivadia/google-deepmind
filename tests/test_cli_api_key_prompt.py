from __future__ import annotations

import importlib
import sys
import types

import pytest


def import_cli(monkeypatch: pytest.MonkeyPatch):
    google_mod = types.ModuleType("google")
    genai_mod = types.ModuleType("google.generativeai")
    setattr(google_mod, "generativeai", genai_mod)

    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.generativeai", genai_mod)
    monkeypatch.setitem(sys.modules, "yt_dlp", types.ModuleType("yt_dlp"))
    monkeypatch.setitem(sys.modules, "ffmpeg", types.ModuleType("ffmpeg"))
    monkeypatch.setitem(sys.modules, "whisper", types.ModuleType("whisper"))
    monkeypatch.setitem(sys.modules, "aiosqlite", types.ModuleType("aiosqlite"))

    sys.modules.pop("halo_video.cli", None)
    return importlib.import_module("halo_video.cli")


class DummyConfigManager:
    def has_api_key(self) -> bool:
        return False

    def save_api_key(self, api_key: str) -> None:  # pragma: no cover - must not be reached
        raise AssertionError(f"unexpected save_api_key({api_key!r})")


def test_setup_api_key_treats_keyboard_interrupt_as_cancel(monkeypatch):
    cli = import_cli(monkeypatch)
    prompt_calls = []

    def raise_keyboard_interrupt(*args, **kwargs):
        prompt_calls.append(kwargs)
        raise KeyboardInterrupt

    monkeypatch.setattr(cli.Prompt, "ask", raise_keyboard_interrupt)
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("input fallback should not run"))

    assert cli.setup_api_key(DummyConfigManager()) is False
    assert prompt_calls == [{"password": True}]


def test_setup_api_key_treats_eof_as_cancel(monkeypatch):
    cli = import_cli(monkeypatch)
    prompt_calls = []

    def raise_eof(*args, **kwargs):
        prompt_calls.append(kwargs)
        raise EOFError

    monkeypatch.setattr(cli.Prompt, "ask", raise_eof)
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("input fallback should not run"))

    assert cli.setup_api_key(DummyConfigManager()) is False
    assert prompt_calls == [{"password": True}]
