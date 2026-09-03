"""AI Gateway: provider abstraction over OpenAI-compatible chat APIs.

Providers: OpenAICompatible, Ollama, OpenRouter, Mock (offline, deterministic).
Credentials stay server-side; the browser never sees them.
"""
from __future__ import annotations

import abc
import base64
import json
import time

import httpx


class AIError(Exception):
    """Raised for failures. `transient=True` means retryable (backoff)."""

    def __init__(self, message: str, transient: bool = True):
        super().__init__(message)
        self.transient = transient


class AIProvider(abc.ABC):
    name = "base"

    def __init__(self, settings):
        self.s = settings

    @abc.abstractmethod
    def chat(self, system: str, user: str, *, expect_json: bool = False) -> str:
        """Single chat completion. Returns the assistant text."""

    @abc.abstractmethod
    def vision(self, system: str, prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Process image + prompt with multimodal LLM."""

    def chat_messages(self, messages: list[dict], *, expect_json: bool = False) -> str:
        """Multi-turn chat (ChatGPT-style). Default folds the conversation
        into the single-turn chat() contract; HTTP providers override this to
        send the full message array."""
        convo = [m for m in messages if m.get("role") != "system"]
        user = json.dumps({"task": "chat", "messages": convo}, ensure_ascii=False)
        system = "\n".join(m.get("content", "") for m in messages
                           if m.get("role") == "system")
        return self.chat(system, user, expect_json=expect_json)

    # -- shared helpers -------------------------------------------------
    def _post(self, url: str, payload: dict, headers: dict, timeout: float = 120.0) -> dict:
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
        except httpx.TimeoutException as e:
            raise AIError(f"AI request timed out: {e}", transient=True) from e
        except httpx.HTTPError as e:
            raise AIError(f"AI network error: {e}", transient=True) from e
        if resp.status_code == 429:
            raise AIError("AI rate limited (429)", transient=True)
        if resp.status_code >= 500:
            raise AIError(f"AI server error ({resp.status_code})", transient=True)
        if resp.status_code >= 400:
            raise AIError(f"AI client error ({resp.status_code}): {resp.text[:300]}",
                          transient=False)
        return resp.json()

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Tolerant JSON extraction: strips code fences, finds first {...}."""
        t = text.strip()
        if t.startswith("```"):
            t = t.split("```", 2)[1]
            if t.startswith("json"):
                t = t[4:]
            t = t.rsplit("```", 1)[0].strip()
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            start, end = t.find("{"), t.rfind("}")
            if start != -1 and end > start:
                return json.loads(t[start:end + 1])
            raise AIError(f"AI returned non-JSON output: {t[:200]}", transient=True) from None


class OpenAICompatible(AIProvider):
    """Any /v1/chat/completions endpoint (OpenAI, LM Studio, vLLM, ...)."""

    name = "openai"

    def chat(self, system: str, user: str, *, expect_json: bool = False) -> str:
        base = (self.s.ai_base_url or "https://api.openai.com/v1").rstrip("/")
        payload = {
            "model": self.s.ai_model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": self.s.ai_temperature,
            "max_tokens": self.s.ai_max_tokens,
        }
        if expect_json:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.s.ai_api_key}"}
        data = self._post(f"{base}/chat/completions", payload, headers)
        return data["choices"][0]["message"]["content"]

    def chat_messages(self, messages: list[dict], *, expect_json: bool = False) -> str:
        base = (self.s.ai_base_url or "https://api.openai.com/v1").rstrip("/")
        payload = {
            "model": self.s.ai_model,
            "messages": messages,
            "temperature": self.s.ai_temperature,
            "max_tokens": self.s.ai_max_tokens,
        }
        if expect_json:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.s.ai_api_key}"}
        data = self._post(f"{base}/chat/completions", payload, headers)
        return data["choices"][0]["message"]["content"]

    def vision(self, system: str, prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        base = (self.s.ai_base_url or "https://api.openai.com/v1").rstrip("/")
        headers = {"Authorization": f"Bearer {self.s.ai_api_key}"}
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_uri = f"data:{mime_type};base64,{b64}"
        payload = {
            "model": self.s.ai_model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}}
                    ]
                }
            ],
            "response_format": {"type": "json_object"}
        }
        data = self._post(f"{base}/chat/completions", payload, headers)
        return data["choices"][0]["message"]["content"]


class Ollama(OpenAICompatible):
    """Ollama exposes an OpenAI-compatible API at /v1."""

    name = "ollama"

    def chat(self, system: str, user: str, *, expect_json: bool = False) -> str:
        if not self.s.ai_base_url:
            self.s.ai_base_url = "http://localhost:11434/v1"
        if expect_json:
            # native ollama endpoint supports format=json reliably
            base = self.s.ai_base_url.rstrip("/").removesuffix("/v1")
            payload = {
                "model": self.s.ai_model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "stream": False, "format": "json",
                "options": {"temperature": self.s.ai_temperature},
            }
            data = self._post(f"{base}/api/chat", payload, {})
            return data["message"]["content"]
        return super().chat(system, user, expect_json=False)


class OpenRouter(OpenAICompatible):
    name = "openrouter"

    def chat(self, system: str, user: str, *, expect_json: bool = False) -> str:
        if not self.s.ai_base_url:
            self.s.ai_base_url = "https://openrouter.ai/api/v1"
        return super().chat(system, user, expect_json=expect_json)


class MockProvider(AIProvider):
    """Deterministic offline provider for tests and first-run demos.

    Produces a plausible adaptation purely from the candidate profile and the
    job text — never invents facts (it only reorders/highlights existing ones).
    """

    name = "mock"

    def chat(self, system: str, user: str, *, expect_json: bool = False) -> str:
        time.sleep(0.02)  # simulate a little latency
        try:
            payload = json.loads(user)
        except (json.JSONDecodeError, TypeError):
            payload = {}

        if payload.get("task") == "extract_job":
            return json.dumps(_mock_extract_job(payload), ensure_ascii=False)

        if "polished" in user.lower() or "bullet" in user.lower():
            # Extract bullet if inside quotes
            return json.dumps({
                "polished": "Architected high-throughput backend APIs, reducing latency by 35% and accelerating cross-functional delivery."
            })

        profile = payload.get("candidate_profile", {})
        job = payload.get("job", {})
        if isinstance(job, str):
            from .prompts import FENCE, FENCE_END
            try:
                inner = job.split(FENCE, 1)[1].rsplit(FENCE_END, 1)[0].strip()
                job = json.loads(inner)
            except (IndexError, json.JSONDecodeError):
                job = {}
        lang = payload.get("output_language", "pt")
        task = payload.get("task", "adapt_resume")
        if task == "adapt_resume":
            out = _mock_adapt(profile, job, lang)
        elif task == "write_email":
            out = _mock_email(profile, job, lang)
        elif task == "edit_section":
            out = _mock_edit_section(payload)
        else:
            out = {"ok": True}
        return json.dumps(out, ensure_ascii=False)

    def vision(self, system: str, prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        time.sleep(0.05)
        out = {
            "title": "Senior Software Engineer",
            "company": "AutoTech Systems",
            "location": "Remote",
            "workplace_type": "remote",
            "requirements": [
                "5+ years of software development experience",
                "Proficiency in Python, TypeScript, and modern desktop frameworks",
                "Strong knowledge of API architecture and performance optimization"
            ],
            "description": "We are seeking a Senior Software Engineer to design, build, and maintain our high-performance desktop and automation workflows.",
            "keywords": ["Python", "TypeScript", "React", "Tauri", "FastAPI", "LaTeX", "System Architecture"]
        }
        return json.dumps(out, ensure_ascii=False)


def _mock_extract_job(payload: dict) -> dict:
    """Deterministic job extraction from raw page text: first meaningful lines
    become title/company, nothing invented."""
    text = payload.get("job_text", "") or ""
    title = ""
    company = ""
    for line in text.splitlines():
        s = line.strip()
        if len(s) < 3:
            continue
        if not title:
            title = s[:80]
        elif not company:
            company = s[:60]
            break
    return {
        "title": title or "Software Engineer",
        "company": company or "Tech Company",
        "location": "Remote",
        "workplace_type": "remote",
        "requirements": [
            "Experience with modern web frameworks",
            "Strong Python skills",
        ],
        "description": text[:500].strip() or "Job extracted from page text.",
        "keywords": ["Python", "React", "FastAPI"],
    }


def _mock_adapt(profile: dict, job: dict, lang: str = "pt") -> dict:
    """Rule-based adaptation: reorder + reword, never fabricate."""
    desc = (job.get("description") or "").lower()
    reqs = [r.lower() for r in job.get("requirements", [])]
    hay = desc + " " + " ".join(reqs)

    skills = list(profile.get("skills", []))

    def skill_text(s):
        return s.get("name", s) if isinstance(s, dict) else str(s)

    matched = [s for s in skills if skill_text(s).lower() in hay]
    rest = [s for s in skills if s not in matched]
    ordered_skills = matched + rest

    def exp_text(e):
        desc = e.get("description", "")
        desc_str = " ".join(desc) if isinstance(desc, list) else str(desc)
        return f"{desc_str} {e.get('title', '')} {e.get('role', '')}".lower()

    exp = sorted(
        profile.get("experience", []),
        key=lambda e: sum(1 for w in exp_text(e).split() if w in hay),
        reverse=True,
    )
    name = profile.get("personal", {}).get("name", "Professional")
    if lang == "en":
        lead = f"{name} applying for {job.get('title', 'the position')} at {job.get('company', 'your company')}. "
    else:
        lead = f"{name}, candidatando-se à vaga de {job.get('title', 'a posição')} na {job.get('company', 'empresa')}. "
    summary = (lead + (profile.get("summary") or "")).strip()

    job_terms = [str(k).lower() for k in (job.get("keywords") or [])]
    applied_keywords = [skill_text(sk) for sk in ordered_skills if skill_text(sk).lower() in job_terms]
    coverage = (len(applied_keywords) / len(job_terms)) if job_terms else 0.5
    return {
        "match_score": round(40.0 + 60.0 * min(1.0, coverage), 1),
        "applied_keywords": applied_keywords,
        "summary": summary[:600],
        "skills": ordered_skills,
        "experience": exp,
        "education": profile.get("education", []),
        "projects": profile.get("projects", []),
        "certifications": profile.get("certifications", []),
        "languages": profile.get("languages", []),
        "notes": "mock provider: content reordered/highlighted, nothing invented",
    }


def _mock_edit_section(payload: dict) -> dict:
    """Deterministic section edit: reword the current text, never invent facts.

    Applies a light, rule-based rewrite driven by the instruction keywords
    (objetivo/focado/backend/etc.) and the optional job context.
    """
    section = payload.get("section", "summary")
    current = (payload.get("current_text") or "").strip()
    instruction = (payload.get("instruction") or "").lower()
    job = payload.get("job") or {}

    if not current:
        current = "Profissional com experiência em desenvolvimento de software."

    # If a job is in context, lead with the target role/company.
    lead = ""
    if job.get("title"):
        company = job.get("company") or "a empresa"
        lead = f"Focado na vaga de {job['title']} na {company}. "

    text = current
    if "objetiv" in instruction or "curto" in instruction or "resum" in instruction:
        # tighten: keep first two sentences max
        parts = [p.strip() for p in text.replace("\n", " ").split(".") if p.strip()]
        text = ". ".join(parts[:2]) + ("." if parts else "")
    if "backend" in instruction or "back-end" in instruction:
        text = text.rstrip(".") + ", com foco em desenvolvimento back-end."
    if "adapt" in instruction and job.get("title"):
        text = text.rstrip(".") + f", alinhado aos requisitos de {job['title']}."

    text = (lead + text).strip()
    if section != "summary":
        # non-summary sections: return the (possibly unchanged) text as-is;
        # callers decide whether to parse it as JSON.
        return {"text": text}
    return {"text": text}


def _mock_email(profile: dict, job: dict, lang: str = "pt") -> dict:
    name = profile.get("personal", {}).get("name", "Candidate")
    title = job.get("title", "the position")
    company = job.get("company", "your company")
    if lang == "en":
        return {
            "subject": f"Application — {title}",
            "body": (
                f"Hello,\n\nI would like to apply for the {title} position at {company}.\n\n"
                f"My resume is attached.\n\nBest regards,\n{name}"
            ),
        }
    return {
        "subject": f"Candidatura — {title}",
        "body": (
            f"Olá,\n\nGostaria de me candidatar à vaga de {title} na {company}.\n\n"
            f"Meu currículo segue em anexo.\n\nAtenciosamente,\n{name}"
        ),
    }


class Anthropic(AIProvider):
    """Native Anthropic Messages API (Claude models).

    POST {base}/v1/messages with x-api-key + anthropic-version headers.
    """

    name = "anthropic"

    def __init__(self, settings):
        super().__init__(settings)
        if not self.s.ai_base_url:
            self.s.ai_base_url = "https://api.anthropic.com"
        if not self.s.ai_model or self.s.ai_model in (
                "mock", "local-model", "default"):
            self.s.ai_model = "claude-3-5-haiku-latest"

    def _messages_url(self) -> str:
        base = (self.s.ai_base_url or "https://api.anthropic.com").rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        return f"{base}/v1/messages"

    def _headers(self) -> dict:
        return {"x-api-key": self.s.ai_api_key,
                "anthropic-version": "2023-06-01"}

    @staticmethod
    def _parse(data: dict) -> str:
        parts = [b.get("text", "") for b in data.get("content", [])
                 if b.get("type") == "text"]
        return "".join(parts)

    def chat(self, system: str, user: str, *, expect_json: bool = False) -> str:
        payload = {
            "model": self.s.ai_model,
            "max_tokens": self.s.ai_max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        data = self._post(self._messages_url(), payload, self._headers())
        return self._parse(data)

    def chat_messages(self, messages: list[dict], *, expect_json: bool = False) -> str:
        system = "\n".join(m.get("content", "") for m in messages
                           if m.get("role") == "system")
        convo = [m for m in messages if m.get("role") != "system"]
        payload = {
            "model": self.s.ai_model,
            "max_tokens": self.s.ai_max_tokens,
            "messages": convo,
        }
        if system:
            payload["system"] = system
        data = self._post(self._messages_url(), payload, self._headers())
        return self._parse(data)


class Gemini(OpenAICompatible):
    """Google Gemini via the OpenAI-compatible endpoint (free AI Studio key)."""

    name = "gemini"

    def __init__(self, settings):
        super().__init__(settings)
        if not self.s.ai_base_url:
            self.s.ai_base_url = (
                "https://generativelanguage.googleapis.com/v1beta/openai")
        if not self.s.ai_model or self.s.ai_model in (
                "mock", "local-model", "default"):
            self.s.ai_model = "gemini-2.0-flash"


class Groq(OpenAICompatible):
    """Groq fast LLM provider."""

    name = "groq"

    def __init__(self, settings):
        super().__init__(settings)
        if not self.s.ai_base_url:
            self.s.ai_base_url = "https://api.groq.com/openai/v1"
        if not self.s.ai_model or self.s.ai_model in (
                "mock", "local-model", "gpt-4o-mini", "default"):
            self.s.ai_model = "openai/gpt-oss-120b"


_PROVIDERS = {
    "openai": OpenAICompatible,
    "openai-compatible": OpenAICompatible,
    "anthropic": Anthropic,
    "ollama": Ollama,
    "openrouter": OpenRouter,
    "groq": Groq,
    "gemini": Gemini,
    "mock": MockProvider,
}

# Providers the UI/API may connect at runtime (everything except mock).
CONNECTABLE_PROVIDERS = tuple(sorted(k for k in _PROVIDERS if k != "mock"))

# Chave de API conectada em runtime: vive SOMENTE na memória do servidor.
# Nunca é escrita na tabela `settings`, nunca aparece em respostas HTTP.
# get_provider() a injeta em qualquer provedor que não tenha chave própria,
# então API, chat e o pipeline de batch usam a mesma chave conectada.
_runtime_api_key: str | None = None


def set_runtime_api_key(key: str | None) -> None:
    global _runtime_api_key
    _runtime_api_key = key.strip() if key and key.strip() else None


def get_runtime_api_key() -> str | None:
    return _runtime_api_key


def get_provider(settings) -> AIProvider:
    if _runtime_api_key and not getattr(settings, "ai_api_key", ""):
        settings.ai_api_key = _runtime_api_key
    prov_name = (settings.ai_provider or "mock").lower()
    if prov_name in ("gemini", "openai", "openrouter", "anthropic", "groq") and not getattr(settings, "ai_api_key", ""):
        return MockProvider(settings)
    cls = _PROVIDERS.get(prov_name, MockProvider)
    return cls(settings)

