"""
app_settings.py — Runtime settings that the admin can change from the UI.

Why not just edit config.py?
  config.py is code — changing it requires restarting Streamlit and risks
  breaking syntax. This module uses a JSON file (settings.json) as a simple
  persistent store that survives restarts but can be updated at runtime.

Priority: settings.json overrides config.py defaults.
  If a key is absent from settings.json (first run), the config.py value is used.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from config import (
    USE_RAG            as _DEFAULT_USE_RAG,
    RULE_WEIGHT        as _DEFAULT_RULE_WEIGHT,
    SEMANTIC_WEIGHT    as _DEFAULT_SEMANTIC_WEIGHT,
    LLM_CANDIDATE_LIMIT as _DEFAULT_LLM_CANDIDATE_LIMIT,
    GROQ_TIMEOUT       as _DEFAULT_GROQ_TIMEOUT,
)

SETTINGS_PATH = Path(__file__).parent / "settings.json"

DEFAULTS: dict = {
    "use_rag":              _DEFAULT_USE_RAG,
    "rule_weight":          _DEFAULT_RULE_WEIGHT,
    "semantic_weight":      _DEFAULT_SEMANTIC_WEIGHT,
    "llm_candidate_limit":  _DEFAULT_LLM_CANDIDATE_LIMIT,
    "groq_timeout":         _DEFAULT_GROQ_TIMEOUT,
}


def load() -> dict:
    """Load settings from JSON, falling back to config.py defaults."""
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**DEFAULTS, **saved}   # saved values override defaults
        except Exception:
            pass
    return dict(DEFAULTS)


def save(settings: dict) -> None:
    """Persist settings to JSON."""
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def get(key: str):
    """Convenience: get a single setting value."""
    return load().get(key, DEFAULTS.get(key))


def reset() -> None:
    """Delete settings.json to restore all defaults from config.py."""
    if SETTINGS_PATH.exists():
        SETTINGS_PATH.unlink()
