"""AI Gateway: provider abstraction over OpenAI-compatible chat APIs.

Providers: OpenAICompatible, Ollama, OpenRouter, Anthropic, Groq, Gemini.
Sem chave de API configurada, os provedores de nuvem levantam AIError —
nunca há fallback silencioso para dados fabricados.
Credentials stay server-side; the browser never sees them.
"""
from __future__ import annotations

import abc
import base64
import json

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

    def vision(self, system: str, prompt: str, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Process image + prompt with multimodal LLM. Optional per provider;
        providers without image support raise a clear AIError."""
        raise AIError(
            f"Provedor {self.name!r} não suporta análise de imagem.",
            transient=False,
        )

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
    def _require_model(self) -> str:
        model = (self.s.ai_model or "").strip()
        if not model:
            raise AIError(
                "Nenhum modelo selecionado. Abra o painel → Config e use "
                "'Detectar' para listar os modelos do provedor.",
                transient=False,
            )
        return model

    def _get(self, url: str, headers: dict, timeout: float = 30.0) -> dict:
        try:
            resp = httpx.get(url, headers=headers, timeout=timeout)
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
        try:
            return resp.json()
        except ValueError as e:
            raise AIError("AI returned non-JSON output", transient=False) from e

    def models(self) -> list[str]:
        """Model IDs available on this provider. Never fabricates: returns
        what the provider API lists, or [] when listing is unsupported."""
        return []
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
            "model": self._require_model(),
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
            "model": self._require_model(),
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
            "model": self._require_model(),
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

    def models(self) -> list[str]:
        base = (self.s.ai_base_url or "https://api.openai.com/v1").rstrip("/")
        headers: dict = {}
        if getattr(self.s, "ai_api_key", ""):
            headers = {"Authorization": f"Bearer {self.s.ai_api_key}"}
        data = self._get(f"{base}/models", headers)
        items = data.get("data", [])
        ids = [m.get("id", "") for m in items if isinstance(m, dict) and m.get("id")]
        return sorted(set(ids))


class Ollama(OpenAICompatible):
    """Ollama exposes an OpenAI-compatible API at /v1."""

    name = "ollama"

    def _native_base(self) -> str:
        return (self.s.ai_base_url or "http://localhost:11434/v1").rstrip("/").removesuffix("/v1")

    def models(self) -> list[str]:
        data = self._get(f"{self._native_base()}/api/tags", {})
        items = data.get("models", [])
        names = [m.get("name", "") for m in items if isinstance(m, dict) and m.get("name")]
        return sorted(set(names))

    def chat(self, system: str, user: str, *, expect_json: bool = False) -> str:
        if not self.s.ai_base_url:
            self.s.ai_base_url = "http://localhost:11434/v1"
        if expect_json:
            # native ollama endpoint supports format=json reliably
            base = self.s.ai_base_url.rstrip("/").removesuffix("/v1")
            payload = {
                "model": self._require_model(),
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




class Anthropic(AIProvider):
    """Native Anthropic Messages API (Claude models).

    POST {base}/v1/messages with x-api-key + anthropic-version headers.
    """

    name = "anthropic"

    def __init__(self, settings):
        super().__init__(settings)
        if not self.s.ai_base_url:
            self.s.ai_base_url = "https://api.anthropic.com"

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
            "model": self._require_model(),
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
            "model": self._require_model(),
            "max_tokens": self.s.ai_max_tokens,
            "messages": convo,
        }
        if system:
            payload["system"] = system
        data = self._post(self._messages_url(), payload, self._headers())
        return self._parse(data)

    def models(self) -> list[str]:
        base = (self.s.ai_base_url or "https://api.anthropic.com").rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        data = self._get(f"{base}/v1/models", self._headers())
        items = data.get("data", [])
        ids = [m.get("id", "") for m in items if isinstance(m, dict) and m.get("id")]
        return sorted(set(ids))


class Gemini(OpenAICompatible):
    """Google Gemini via the OpenAI-compatible endpoint (free AI Studio key)."""

    name = "gemini"

    def __init__(self, settings):
        super().__init__(settings)
        if not self.s.ai_base_url:
            self.s.ai_base_url = (
                "https://generativelanguage.googleapis.com/v1beta/openai")


class Groq(OpenAICompatible):
    """Groq fast LLM provider."""

    name = "groq"

    def __init__(self, settings):
        super().__init__(settings)
        if not self.s.ai_base_url:
            self.s.ai_base_url = "https://api.groq.com/openai/v1"


_PROVIDERS = {
    "openai": OpenAICompatible,
    "openai-compatible": OpenAICompatible,
    "anthropic": Anthropic,
    "ollama": Ollama,
    "openrouter": OpenRouter,
    "groq": Groq,
    "gemini": Gemini,
    "nvidia": OpenAICompatible,
    "deepseek": OpenAICompatible,
    "xai": OpenAICompatible,
    "together": OpenAICompatible,
    "mistral": OpenAICompatible,
}


# Catálogo exibido pela UI. Fonte única de verdade sobre provedores:
# id (usado em ai_provider) -> rótulo, se exige chave e URL base padrão.
# Não há modelo padrão: a UI detecta os modelos do provedor via /api/models.
# "custom_base" mostra o campo de URL base na UI. "key_hint" é só placeholder.
PROVIDER_CATALOG = [
    {"id": "gemini", "label": "Google Gemini", "needs_key": True,
     "default_base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
     "custom_base": False, "key_hint": "AIzaSy..."},
    {"id": "openai", "label": "OpenAI", "needs_key": True,
     "default_base_url": "https://api.openai.com/v1",
     "custom_base": False, "key_hint": "sk-..."},
    {"id": "anthropic", "label": "Anthropic Claude", "needs_key": True,
     "default_base_url": "https://api.anthropic.com",
     "custom_base": False, "key_hint": "sk-ant-..."},
    {"id": "groq", "label": "Groq", "needs_key": True,
     "default_base_url": "https://api.groq.com/openai/v1",
     "custom_base": False, "key_hint": "gsk_..."},
    {"id": "openrouter", "label": "OpenRouter", "needs_key": True,
     "default_base_url": "https://openrouter.ai/api/v1",
     "custom_base": False, "key_hint": "sk-or-..."},
    {"id": "nvidia", "label": "NVIDIA NIM", "needs_key": True,
     "default_base_url": "https://integrate.api.nvidia.com/v1",
     "custom_base": False, "key_hint": "nvapi-..."},
    {"id": "deepseek", "label": "DeepSeek", "needs_key": True,
     "default_base_url": "https://api.deepseek.com/v1",
     "custom_base": False, "key_hint": "sk-..."},
    {"id": "xai", "label": "xAI (Grok)", "needs_key": True,
     "default_base_url": "https://api.x.ai/v1",
     "custom_base": False, "key_hint": "xai-..."},
    {"id": "together", "label": "Together AI", "needs_key": True,
     "default_base_url": "https://api.together.xyz/v1",
     "custom_base": False, "key_hint": "..."},
    {"id": "mistral", "label": "Mistral AI", "needs_key": True,
     "default_base_url": "https://api.mistral.ai/v1",
     "custom_base": False, "key_hint": "..."},
    {"id": "ollama", "label": "Ollama (local)", "needs_key": False,
     "default_base_url": "http://localhost:11434/v1",
     "custom_base": True, "key_hint": ""},
    {"id": "openai-compatible", "label": "Customizado (OpenAI-compatible)", "needs_key": False,
     "default_base_url": "",
     "custom_base": True, "key_hint": ""},
]


# Provedores de nuvem exigem chave de API; Ollama é local e não exige.
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


CLOUD_PROVIDERS = ("gemini", "openai", "openrouter", "anthropic", "groq",
                     "nvidia", "deepseek", "xai", "together", "mistral")

# Base URL padrão por provedor (endpoints OpenAI-compatible). Sem isso,
# provedores mapeados para OpenAICompatible (nvidia, deepseek, xai,
# together, mistral) enviariam a chave para api.openai.com e seriam
# rejeitados. get_provider injeta quando ai_base_url está vazio.
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "anthropic": "https://api.anthropic.com",
    "ollama": "http://localhost:11434/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "xai": "https://api.x.ai/v1",
    "together": "https://api.together.xyz/v1",
    "mistral": "https://api.mistral.ai/v1",
}


def get_provider(settings) -> AIProvider:
    if _runtime_api_key and not getattr(settings, "ai_api_key", ""):
        settings.ai_api_key = _runtime_api_key
    prov_name = (settings.ai_provider or "").lower()
    if prov_name in CLOUD_PROVIDERS and not getattr(settings, "ai_api_key", ""):
        raise AIError(
            "Nenhuma chave de API configurada. Abra o painel → Config e "
            "informe sua chave para usar este provedor.",
            transient=False,
        )
    cls = _PROVIDERS.get(prov_name)
    if cls is None:
        raise AIError(
            f"Provedor de IA desconhecido: {prov_name!r}.",
            transient=False,
        )
    if not getattr(settings, "ai_base_url", ""):
        settings.ai_base_url = DEFAULT_BASE_URLS.get(prov_name, "")
    return cls(settings)

