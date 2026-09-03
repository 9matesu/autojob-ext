"""Job extraction services (raw page text from the browser extension)."""
from __future__ import annotations

from .gateway import get_provider, AIProvider
from . import prompts
from ...config import Settings


def extract_job_from_text(job_text: str, settings: Settings, page_title: str = "", page_url: str = "") -> dict:
    prov = get_provider(settings)
    system, user = prompts.build_job_from_text_request(job_text, page_title, page_url)
    raw = prov.chat(system, user, expect_json=True)
    return AIProvider._extract_json(raw)
