"""Multimodal vision and text job extraction services."""
from __future__ import annotations

from .gateway import get_provider, AIProvider
from . import prompts
from ...config import Settings

VISION_PROMPT = """Analyze this screenshot of a job posting.
Extract the structured job posting details. Disregard navigation menus, advertisements, browser tabs, or unrelated page elements.
Return STRICT JSON with these keys:
{
  "title": string,
  "company": string,
  "location": string,
  "workplace_type": "remote" | "hybrid" | "on-site",
  "requirements": array of strings (key qualifications and tech stack required),
  "description": string (clean summary of responsibilities and role overview),
  "keywords": array of strings (top ATS keywords found in the post)
}
"""

def extract_job_from_image(image_bytes: bytes, settings: Settings, mime_type: str = "image/png") -> dict:
    prov = get_provider(settings)
    raw = prov.vision(
        system="You are an expert job description analyzer and structured information extractor.",
        prompt=VISION_PROMPT,
        image_bytes=image_bytes,
        mime_type=mime_type,
    )
    return AIProvider._extract_json(raw)


def extract_job_from_text(job_text: str, settings: Settings, page_title: str = "", page_url: str = "") -> dict:
    prov = get_provider(settings)
    system, user = prompts.build_job_from_text_request(job_text, page_title, page_url)
    raw = prov.chat(system, user, expect_json=True)
    return AIProvider._extract_json(raw)
