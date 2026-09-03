import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.profile import EMPTY_PROFILE
from app.services.ai import prompts
from app.services.latex import engine
from app.services.resume import importer


def test_empty_profile_has_leadership():
    assert EMPTY_PROFILE["leadership"] == []


def test_leadership_bucket_english():
    text = """John Doe
john@example.com
Leadership Activities
Tech Lead | Open Source Org | Remote | 2021 - Present
- Led a team of 5 volunteers
"""
    profile = importer.parse_resume_text(text)
    assert len(profile["leadership"]) == 1
    lead = profile["leadership"][0]
    assert lead["title"] == "Tech Lead"
    assert lead["company"] == "Open Source Org"
    assert lead["location"] == "Remote"
    assert lead["period"] == "2021 - Present"
    assert lead["description"] == ["Led a team of 5 volunteers"]


def test_leadership_bucket_portuguese():
    text = """Maria Silva
maria@exemplo.com
Atividades de Liderança
Líder Técnica | ONG Tech | São Paulo, SP | 2022 - Atual
- Mentorei 10 pessoas
"""
    profile = importer.parse_resume_text(text)
    assert len(profile["leadership"]) == 1
    lead = profile["leadership"][0]
    assert lead["title"] == "Líder Técnica"
    assert lead["company"] == "ONG Tech"
    assert lead["location"] == "São Paulo, SP"
    assert lead["period"] == "2022 - Atual"
    assert lead["description"] == ["Mentorei 10 pessoas"]


def test_experience_location_extraction():
    text = """John Doe
john@example.com
Experience
Senior Dev | Nubank | São Paulo, SP | 2022 - Present
- Did things
"""
    profile = importer.parse_resume_text(text)
    assert len(profile["experience"]) == 1
    exp = profile["experience"][0]
    assert exp["title"] == "Senior Dev"
    assert exp["company"] == "Nubank"
    assert exp["location"] == "São Paulo, SP"
    assert exp["period"] == "2022 - Present"


def test_education_location_extraction():
    text = """John Doe
john@example.com
Education
Universidade de São Paulo | São Paulo, SP | 2015 - 2019
"""
    profile = importer.parse_resume_text(text)
    assert len(profile["education"]) == 1
    edu = profile["education"][0]
    assert edu["institution"] == "Universidade de São Paulo"
    assert edu["location"] == "São Paulo, SP"


def test_no_invented_defaults():
    text = """John Doe
john@example.com
Experience
Some Random Role
- Did stuff
Education
Bacharelado
"""
    profile = importer.parse_resume_text(text)
    assert profile["experience"][0]["company"] == ""
    assert profile["experience"][0]["location"] == ""
    assert profile["experience"][0]["period"] == ""
    assert profile["education"][0]["institution"] == ""
    assert profile["education"][0]["degree"] == "Bacharelado"
    assert profile["education"][0]["year"] == ""


def _sample_profile():
    return {
        "personal": {
            "name": "Ana Silva",
            "email": "ana@exemplo.com",
            "phone": "+55 11 99999-9999",
            "location": "São Paulo, SP",
            "linkedin": "https://linkedin.com/in/anasilva",
            "github": "https://github.com/anasilva",
            "portfolio": "https://ana.dev",
        },
        "summary": "Engenheira de software com 5 anos de experiência.",
        "leadership": [
            {"title": "Líder", "company": "Liga", "location": "Remoto",
             "period": "2023 - Atual", "description": ["Fez X"]},
        ],
        "experience": [
            {"title": "Dev", "company": "Nubank", "location": "São Paulo, SP",
             "period": "2022 - Atual", "description": ["Fez Y"]},
        ],
        "education": [
            {"institution": "USP", "degree": "BS", "year": "2020",
             "location": "São Paulo, SP"},
        ],
        "skills": ["Python"],
        "languages": [{"name": "Inglês (Avançado)"}],
        "projects": [],
        "certifications": [],
    }


def test_devcelio_template_section_order_pt():
    tex = engine.render_tex("devcelio", _sample_profile(), {"title": "Dev"}, lang="pt")
    order = ["Resumo Profissional", "Atividades de Liderança", "Experiência",
             "Habilidades", "Educação"]
    idx = [tex.index(f"\\section{{{s}}}") for s in order]
    assert idx == sorted(idx)
    assert "\\section{Projetos}" not in tex
    assert "\\section{Certificações}" not in tex


def test_devcelio_template_section_order_en():
    tex = engine.render_tex("devcelio", _sample_profile(), {"title": "Dev"}, lang="en")
    order = ["Professional Summary", "Leadership Activities", "Experience",
             "Skills", "Education"]
    idx = [tex.index(f"\\section{{{s}}}") for s in order]
    assert idx == sorted(idx)


def test_devcelio_header_has_no_phone():
    tex = engine.render_tex("devcelio", _sample_profile(), {"title": "Dev"}, lang="pt")
    assert "+55 11 99999-9999" not in tex
    assert "ana.dev" not in tex
    assert "São Paulo, SP" in tex
    assert "linkedin.com/in/anasilva" in tex


def test_devcelio_cventry_renders_location():
    tex = engine.render_tex("devcelio", _sample_profile(), {"title": "Dev"}, lang="pt")
    assert "Remoto" in tex  # leadership location
    assert "Nubank" in tex


def test_adapt_schema_includes_leadership():
    assert "leadership" in prompts.ADAPT_SCHEMA_HINT
