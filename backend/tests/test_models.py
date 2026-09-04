import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import db

client = TestClient(app)


def test_providers_catalog_lists_all_ids():
    resp = client.get("/api/providers")
    assert resp.status_code == 200
    providers = resp.json()["providers"]
    ids = {p["id"] for p in providers}
    for expected in ("gemini", "openai", "anthropic", "groq", "openrouter",
                     "nvidia", "deepseek", "xai", "together", "mistral",
                     "ollama", "openai-compatible"):
        assert expected in ids
    for p in providers:
        assert p["label"]
        assert isinstance(p["needs_key"], bool)
        assert "default_model" not in p  # sem modelo padrão: detecção dinâmica


def test_get_provider_injects_default_base_url(monkeypatch):
    from app.services.ai import gateway as gw
    from app.config import Settings
    monkeypatch.setattr(gw, "_runtime_api_key", None)
    for pid, host in (
        ("nvidia", "integrate.api.nvidia.com"),
        ("deepseek", "api.deepseek.com"),
        ("xai", "api.x.ai"),
        ("together", "api.together.xyz"),
        ("mistral", "api.mistral.ai"),
        ("groq", "api.groq.com"),
        ("gemini", "generativelanguage.googleapis.com"),
    ):
        s = Settings(ai_provider=pid, ai_api_key="k", ai_model="m")
        prov = gw.get_provider(s)
        assert host in s.ai_base_url, f"{pid} -> {s.ai_base_url}"
        assert isinstance(prov, gw.AIProvider)


def test_chat_without_model_fails_loudly(monkeypatch):
    from app.services.ai import gateway as gw
    from app.config import Settings
    monkeypatch.setattr(gw, "_runtime_api_key", None)
    s = Settings(ai_provider="openai", ai_api_key="k", ai_model="")
    prov = gw.get_provider(s)
    with pytest.raises(gw.AIError):
        prov.chat("sys", "user")
    s2 = Settings(ai_provider="anthropic", ai_api_key="k", ai_model="")
    with pytest.raises(gw.AIError):
        gw.get_provider(s2).chat("sys", "user")


def test_providers_catalog_leaks_no_secrets():
    providers = client.get("/api/providers").json()["providers"]
    for p in providers:
        assert "ai_api_key" not in p
        assert "api_key" not in p
        # key_hint é só placeholder explícito, nunca chave real
        hint = p.get("key_hint", "")
        assert hint == "" or hint.endswith("...")


def test_models_unknown_provider_fails_loudly():
    resp = client.post("/api/models", json={"ai_provider": "nonsense-xyz"})
    assert resp.status_code == 400


def test_models_unreachable_host_fails_loudly():
    resp = client.post("/api/models", json={
        "ai_provider": "ollama",
        "ai_base_url": "http://127.0.0.1:9/v1",
    })
    assert resp.status_code in (400, 500)
    assert resp.json()["detail"]


def test_models_probe_selects_working(monkeypatch):
    from app.services.ai import gateway as gw
    import app.api.routes as routes

    class FakeProv:
        def __init__(self, settings):
            self.s = settings

        def models(self):
            return ["blocked-model", "good-model", "other"]

        def chat(self, system, user, *, expect_json=False):
            if self.s.ai_model != "good-model":
                raise gw.AIError("blocked", transient=False)
            return "ok"

    monkeypatch.setattr(routes.gateway, "get_provider", lambda s: FakeProv(s))
    resp = client.post("/api/models", json={"ai_provider": "groq", "probe": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["working"] == "good-model"
    assert body["models"] == ["blocked-model", "good-model", "other"]


def test_models_without_probe_skips_chat(monkeypatch):
    from app.services.ai import gateway as gw

    class NoChatProv:
        def models(self):
            return ["a", "b"]

        def chat(self, *a, **k):
            raise AssertionError("chat não deve rodar sem probe")

    import app.api.routes as routes
    monkeypatch.setattr(routes.gateway, "get_provider", lambda s: NoChatProv())
    resp = client.post("/api/models", json={"ai_provider": "groq"})
    assert resp.status_code == 200
    assert resp.json()["working"] == ""


def test_models_parsing_openai_compatible(monkeypatch):
    from app.services.ai import gateway as gw
    from app.config import Settings
    payload = {"data": [{"id": "b-model"}, {"id": "a-model"}, {"id": "a-model"}, {}]}
    monkeypatch.setattr(
        gw.OpenAICompatible, "_get",
        lambda self, url, headers, timeout=30.0: payload,
    )
    prov = gw.OpenAICompatible(Settings(ai_provider="openai", ai_api_key="x"))
    assert prov.models() == ["a-model", "b-model"]


def test_models_parsing_ollama(monkeypatch):
    from app.services.ai import gateway as gw
    from app.config import Settings
    payload = {"models": [{"name": "llama3"}, {"name": "mistral"}, {}]}
    monkeypatch.setattr(
        gw.Ollama, "_get",
        lambda self, url, headers, timeout=30.0: payload,
    )
    prov = gw.Ollama(Settings(ai_provider="ollama"))
    assert prov.models() == ["llama3", "mistral"]


def test_models_parsing_anthropic():
    from types import SimpleNamespace
    from app.services.ai import gateway as gw
    from app.config import Settings
    payload = {"data": [{"id": "claude-3-5-haiku-latest"}, {"id": ""}]}
    # Anthropic não implementa vision (classe abstrata): testa o método
    # desvinculado com um stub que só fornece settings + _get.
    stub = SimpleNamespace(
        s=Settings(ai_provider="anthropic", ai_api_key="x"),
        _get=lambda url, headers: payload,
        _headers=lambda: {},
    )
    assert gw.Anthropic.models(stub) == ["claude-3-5-haiku-latest"]


def test_get_provider_new_ids_map_to_openai_compatible(monkeypatch):
    from app.services.ai import gateway as gw
    from app.config import Settings
    monkeypatch.setattr(gw, "_runtime_api_key", None)
    for pid in ("nvidia", "deepseek", "xai", "together", "mistral", "openai-compatible"):
        prov = gw.get_provider(Settings(ai_provider=pid, ai_api_key="k"))
        assert isinstance(prov, gw.OpenAICompatible)


def test_get_provider_new_cloud_ids_require_key(monkeypatch):
    from app.services.ai import gateway as gw
    from app.config import Settings
    monkeypatch.setattr(gw, "_runtime_api_key", None)
    for pid in ("nvidia", "deepseek", "xai", "together", "mistral"):
        with pytest.raises(gw.AIError):
            gw.get_provider(Settings(ai_provider=pid, ai_api_key=""))
    # openai-compatible sem chave (ex.: LM Studio local) constrói normalmente
    prov = gw.get_provider(Settings(ai_provider="openai-compatible", ai_api_key=""))
    assert isinstance(prov, gw.OpenAICompatible)


def test_models_live():
    from app.config import get_settings
    s = get_settings()
    if not s.ai_api_key:
        pytest.skip("sem chave de API real; integração opt-in")
    resp = client.post("/api/models", json={
        "ai_provider": s.ai_provider,
        "ai_api_key": s.ai_api_key,
        "ai_base_url": s.ai_base_url,
    })
    assert resp.status_code == 200
    assert isinstance(resp.json()["models"], list)


def test_json_word_present_in_all_json_mode_prompts(monkeypatch):
    """Strict OpenAI-compatible providers 400 response_format=json_object
    unless the word JSON appears in the prompt. Guard every call site."""
    from app.services.ai import prompts as pr
    from app.services.ai import gateway as gw

    captured = {}

    class Probe(gw.OpenAICompatible):
        def _post(self, url, payload, headers, timeout=120.0):
            captured["payload"] = payload
            return {"choices": [{"message": {"content": '{"test": "ok"}'}}]}

    # 1. adapt pipeline prompts
    system, user = pr.build_adapt_request({"personal": {"name": "T"}}, {"title": "Dev"}, lang="pt")
    assert "json" in (system + user).lower()
    # 2. job extraction prompts
    system2, user2 = pr.build_job_from_text_request("texto", "T", "http://x")
    assert "json" in (system2 + user2).lower()
    # 3. polish prompt
    assert "json" in pr.POLISH_BULLET_PROMPT.lower()
    # 4. connection-test prompt goes through a real chat() call
    import app.api.routes as routes
    from app.config import Settings
    monkeypatch.setattr(routes.gateway, "get_provider", lambda s: Probe(
        Settings(ai_provider="openai", ai_api_key="x", ai_model="gpt-4o-mini")))
    resp = client.post("/api/settings/test", json={
        "ai_provider": "openai",
        "ai_api_key": "x",
        "ai_model": "gpt-4o-mini",
    })
    assert resp.status_code == 200
    sent = captured["payload"]
    assert sent.get("response_format") == {"type": "json_object"}
    blob = json.dumps(sent["messages"]).lower()
    assert "json" in blob
