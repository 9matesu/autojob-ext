import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        assert "default_model" in p


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
