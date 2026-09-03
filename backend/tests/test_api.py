import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import db

@pytest.fixture(autouse=True)
def setup_clean_db():
    db.init_db()

def test_health():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "compiler_type" in data

def test_save_and_get_profile():
    client = TestClient(app)
    profile_data = {
        "name": "Matheus Costa",
        "email": "matheus@example.com",
        "phone": "+55 11 98765-4321",
        "profile": {
            "personal": {
                "name": "Matheus Costa",
                "email": "matheus@example.com",
                "phone": "+55 11 98765-4321",
                "location": "São Paulo, Brazil",
                "linkedin": "https://linkedin.com/in/matheuscosta",
                "github": "https://github.com/9matesu",
            },
            "summary": "Senior Software Architect with deep experience in AI systems.",
            "experience": [
                {
                    "title": "Senior AI Engineer",
                    "company": "AutoJob Corp",
                    "period": "2023 - Present",
                    "description": ["Engineered low-latency resume compiler."]
                }
            ],
            "education": [
                {"institution": "USP", "degree": "B.S. CS", "year": "2020"}
            ],
            "skills": ["Python", "Rust", "React"]
        }
    }
    resp = client.post("/api/profile", json=profile_data)
    assert resp.status_code == 200
    assert resp.json()["status"] == "saved"

    get_resp = client.get("/api/profile")
    assert get_resp.status_code == 200
    assert get_resp.json()["has_profile"] is True

def test_parse_resume_path(tmp_path):
    client = TestClient(app)
    test_file = tmp_path / "sample_resume.txt"
    test_file.write_text("John Doe\njohn@example.com\nExperience\nSoftware Developer at BigTech\nBuilt scalable web services\nSkills\nPython, Docker, TypeScript", encoding="utf-8")
    resp = client.post("/api/parse-resume-path", json={"file_path": str(test_file)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert len(data["profile"]["skills"]) > 0

def _keyless_settings():
    from app.config import Settings
    return Settings(ai_provider="gemini", ai_api_key="", ai_model="gemini-2.0-flash")

def _patch_settings(monkeypatch, settings):
    import app.api.routes as routes
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

def test_get_provider_raises_without_key(monkeypatch):
    from app.services.ai import gateway as gw
    monkeypatch.setattr(gw, "_runtime_api_key", None)
    with pytest.raises(gw.AIError):
        gw.get_provider(_keyless_settings())

def test_get_provider_raises_unknown_provider(monkeypatch):
    from app.services.ai import gateway as gw
    from app.config import Settings
    monkeypatch.setattr(gw, "_runtime_api_key", None)
    with pytest.raises(gw.AIError):
        gw.get_provider(Settings(ai_provider="nonsense-xyz", ai_api_key="x"))

def test_adapt_prompt_builders_contain_fences_and_schema():
    from app.services.ai import prompts
    system, user = prompts.build_adapt_request({"personal": {"name": "T"}}, {"title": "Dev"}, lang="pt")
    assert "===UNTRUSTED_JOB_DATA_BEGIN===" in user
    assert "adapt_resume" in user
    assert "match_score" in system
    assert "applied_keywords" in system
    system2, user2 = prompts.build_job_from_text_request("some job text here", "T", "http://x")
    assert "extract_job" in user2
    assert "title" in system2

SAMPLE_JOB_TEXT = """Senior Software Engineer
Nubank
Sao Paulo, Brazil - Hybrid

Responsibilities:
- Design, build and maintain high-throughput backend services in Python and Go.
- Collaborate with product and design teams to ship measurable outcomes.

Requirements:
- 5+ years of software development experience.
- Strong knowledge of Python, FastAPI, Docker and Kubernetes.
- Experience with event-driven architectures using Kafka.

Benefits: flexible hours, health plan, stock options.
"""

def test_adapt_text_without_key_fails_loudly(monkeypatch):
    _patch_settings(monkeypatch, _keyless_settings())
    client = TestClient(app)
    test_save_and_get_profile()
    resp = client.post("/api/adapt-text", json={
        "job_text": SAMPLE_JOB_TEXT,
        "page_title": "Senior Software Engineer - Nubank",
        "page_url": "https://example.com/job/123",
    })
    assert resp.status_code == 400
    assert "chave" in resp.json()["detail"].lower()

def test_delete_profile_deactivates_and_gates_onboarding():
    client = TestClient(app)
    test_save_and_get_profile()
    assert client.get("/api/profile").json()["has_profile"] is True

    resp = client.delete("/api/profile")
    assert resp.status_code == 200
    assert resp.json()["had_active"] is True

    assert client.get("/api/profile").json()["has_profile"] is False
    assert client.get("/api/health").json()["has_active_candidate"] is False

    resp2 = client.delete("/api/profile")
    assert resp2.json()["had_active"] is False

def test_adapt_text_without_profile_mentions_onboarding(monkeypatch):
    _patch_settings(monkeypatch, _keyless_settings())
    client = TestClient(app)
    client.delete("/api/profile")
    resp = client.post("/api/adapt-text", json={
        "job_text": SAMPLE_JOB_TEXT,
        "page_title": "Senior Software Engineer - Nubank",
        "page_url": "https://example.com/job/123",
    })
    assert resp.status_code == 400
    assert "onboarding" in resp.json()["detail"].lower()

def test_get_profile_exposes_source_file():
    client = TestClient(app)
    test_save_and_get_profile()
    data = client.get("/api/profile").json()
    assert data["has_profile"] is True
    assert "source_file" in data["candidate"]

def test_adapt_text_live():
    from app.config import get_settings
    if not get_settings().ai_api_key:
        pytest.skip("sem chave de API real; integração opt-in")
    client = TestClient(app)
    test_save_and_get_profile()
    resp = client.post("/api/adapt-text", json={
        "job_text": SAMPLE_JOB_TEXT,
        "page_title": "Senior Software Engineer - Nubank",
        "page_url": "https://example.com/job/123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "job" in data
    assert "adaptation" in data
    adaptation = data["adaptation"]
    assert 0 <= adaptation["match_score"] <= 100
    assert "applied_keywords" in adaptation
    assert "recruiter_pitch" not in adaptation
    assert adaptation["pdf_url"].startswith("/api/resumes/")

    pdf_resp = client.get(adaptation["pdf_url"])
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF-")

def test_adapt_text_rejects_short_input():
    client = TestClient(app)
    resp = client.post("/api/adapt-text", json={"job_text": "too short"})
    assert resp.status_code == 400

def test_polish_bullet_without_key_fails_loudly(monkeypatch):
    _patch_settings(monkeypatch, _keyless_settings())
    client = TestClient(app)
    resp = client.post("/api/polish-bullet", json={
        "bullet": "built backend APIs and improved performance",
        "role_context": "Senior Engineer"
    })
    assert resp.status_code == 400
    assert "chave" in resp.json()["detail"].lower()

def test_polish_bullet_live():
    from app.config import get_settings
    if not get_settings().ai_api_key:
        pytest.skip("sem chave de API real; integração opt-in")
    client = TestClient(app)
    resp = client.post("/api/polish-bullet", json={
        "bullet": "built backend APIs and improved performance",
        "role_context": "Senior Engineer"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "polished" in data
    assert len(data["polished"]) > 10

def test_enhanced_resume_parsing(tmp_path):
    client = TestClient(app)
    content = """Carlos Mendes
carlos@tech.com.br
(11) 98765-4321
São Paulo, SP

EXPERIÊNCIA
Líder Técnico - Fintech Brasil (2022 - Atual)
- Arquitetou microsserviços em Go e Python processando 15k req/seg
- Reduziu a latência do pipeline em 38% com Redis e Kafka

Engenheiro de Software Sênior | Nubank | 2019 - 2022
- Liderou equipe de 6 engenheiros desenvolvendo produtos de cartão de crédito
- Implementou observabilidade com Prometheus e Grafana

EDUCAÇÃO
Universidade de São Paulo (USP) - Bacharelado em Ciência da Computação - 2018

HABILIDADES
Go, Python, Docker, Kubernetes, AWS, PostgreSQL, Redis, Kafka
"""
    resume_file = tmp_path / "cv_carlos.txt"
    resume_file.write_text(content, encoding="utf-8")

    resp = client.post("/api/parse-resume-path", json={"file_path": str(resume_file)})
    assert resp.status_code == 200
    profile = resp.json()["profile"]

    # Verify extracted candidate details
    assert profile["personal"]["name"] == "Carlos Mendes"
    assert profile["personal"]["email"] == "carlos@tech.com.br"
    assert profile["personal"]["phone"] == "(11) 98765-4321"

    # Verify multiple jobs parsed
    assert len(profile["experience"]) >= 2
    assert "Líder Técnico" in profile["experience"][0]["title"]
    assert "Fintech Brasil" in profile["experience"][0]["company"]
    assert len(profile["experience"][0]["description"]) >= 2

    # Verify education parsed
    assert len(profile["education"]) >= 1
    assert "Universidade de São Paulo" in profile["education"][0]["institution"]

    # Verify skills parsed
    assert "Go" in profile["skills"]
    assert "Python" in profile["skills"]
    assert "Docker" in profile["skills"]

