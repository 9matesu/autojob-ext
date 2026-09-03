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

def _use_mock_provider(monkeypatch):
    from app.services.ai import gateway as gw
    from app.services.ai import vision as vis
    monkeypatch.setattr(gw, "get_provider", lambda s: gw.MockProvider(s))
    monkeypatch.setattr(vis, "get_provider", lambda s: gw.MockProvider(s))

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

def test_adapt_text(monkeypatch):
    _use_mock_provider(monkeypatch)
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
    assert data["adaptation"]["match_score"] > 0
    assert data["adaptation"]["pdf_url"].startswith("/api/resumes/")

    pdf_resp = client.get(data["adaptation"]["pdf_url"])
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF-")

def test_adapt_text_rejects_short_input():
    client = TestClient(app)
    resp = client.post("/api/adapt-text", json={"job_text": "too short"})
    assert resp.status_code == 400

def test_polish_bullet():
    client = TestClient(app)
    resp = client.post("/api/polish-bullet", json={
        "bullet": "built backend APIs and improved performance",
        "role_context": "Senior Engineer"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "polished" in data
    assert len(data["polished"]) > 10

def test_adapt_image(monkeypatch):
    import base64
    _use_mock_provider(monkeypatch)
    client = TestClient(app)
    test_save_and_get_profile()
    png_1x1 = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    resp = client.post("/api/adapt-image", json={"image_base64": base64.b64encode(png_1x1).decode()})
    assert resp.status_code == 200
    data = resp.json()
    assert data["adaptation"]["pdf_url"].startswith("/api/resumes/")

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

