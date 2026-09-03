"""AutoJob Configuration and Settings."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("AUTOJOB_DATA_DIR", PROJECT_ROOT / "data"))
OUTPUT_DIR = DATA_DIR / "output"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
TEMPLATE_DIR = TEMPLATES_DIR
BIN_DIR = PROJECT_ROOT / "bin"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BIN_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

@dataclass
class Settings:
    ai_provider: str = "gemini"  # "gemini" | "openai" | "ollama" | "openrouter" | "anthropic" | "groq"
    ai_model: str = "gemini-2.0-flash"
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_temperature: float = 0.2
    ai_max_tokens: int = 4096
    default_template: str = "editorial"
    default_lang: str = "en"     # "en" or "pt"
    compiler_preference: str = "auto" # "auto" | "tectonic" | "pdflatex"

def get_settings() -> Settings:
    from . import db
    s = Settings()
    # defaults from env
    s.ai_provider = os.environ.get("AI_PROVIDER", s.ai_provider)
    s.ai_model = os.environ.get("AI_MODEL", s.ai_model)
    s.ai_api_key = os.environ.get("AI_API_KEY", s.ai_api_key)
    s.ai_base_url = os.environ.get("AI_BASE_URL", s.ai_base_url)
    s.default_template = os.environ.get("DEFAULT_TEMPLATE", s.default_template)
    s.default_lang = os.environ.get("DEFAULT_LANG", s.default_lang)
    s.compiler_preference = os.environ.get("COMPILER_PREFERENCE", s.compiler_preference)
    
    # DB overrides
    rows = db.query("SELECT key, value FROM settings")
    db_map = {r["key"]: r["value"] for r in rows}
    if "ai_provider" in db_map: s.ai_provider = db_map["ai_provider"]
    if "ai_model" in db_map: s.ai_model = db_map["ai_model"]
    if "ai_api_key" in db_map: s.ai_api_key = db_map["ai_api_key"]
    if "ai_base_url" in db_map: s.ai_base_url = db_map["ai_base_url"]
    if "default_template" in db_map: s.default_template = db_map["default_template"]
    if "default_lang" in db_map: s.default_lang = db_map["default_lang"]
    if "compiler_preference" in db_map: s.compiler_preference = db_map["compiler_preference"]
    return s

def update_setting(key: str, value: str):
    from . import db
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value)
    )
