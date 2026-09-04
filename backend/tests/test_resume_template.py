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

def test_bullets_with_list_description():
    entry = {"description": ["Fez A.", "Fez B."]}
    assert engine._bullets(entry) == ["Fez A.", "Fez B."]


def test_bullets_with_string_description():
    entry = {"description": "Fez A.\nFez B."}
    assert engine._bullets(entry) == ["Fez A.", "Fez B."]


def test_bullets_never_stringifies_list():
    entry = {"description": ["Primeiro item", "Segundo item"]}
    for bullet in engine._bullets(entry):
        assert not bullet.startswith("[")
        assert "', '" not in bullet


def test_merge_tailored_keeps_leadership():
    from app.api.routes import _merge_tailored
    master = {"summary": "M", "skills": ["X"], "experience": [],
              "projects": [], "education": []}
    adapted = {"leadership": [{"title": "Lider", "company": "Org"}]}
    merged = _merge_tailored(master, adapted)
    assert merged["leadership"] == [{"title": "Lider", "company": "Org"}]
    assert merged["skills"] == ["X"]


def test_merge_tailored_falls_back_to_master():
    from app.api.routes import _merge_tailored
    master = {"summary": "M", "skills": ["X"], "experience": [],
              "projects": [], "education": [],
              "leadership": [{"title": "Lider"}]}
    merged = _merge_tailored(master, {})
    assert merged["leadership"] == [{"title": "Lider"}]
    assert merged["summary"] == "M"


def test_compile_pdf_retries_transient_failure(tmp_path, monkeypatch):
    import subprocess as sp
    from pathlib import Path

    calls = {"n": 0}

    def fake_run(cmd, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise sp.TimeoutExpired(cmd, 1)

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        out = Path(kw["cwd"])
        (out / "resume.pdf").write_bytes(b"%PDF-1.4 fake")
        return R()

    monkeypatch.setattr(engine.subprocess, "run", fake_run)
    monkeypatch.setattr(engine, "find_compiler", lambda: ("pdflatex", "pdflatex"))
    monkeypatch.setattr(engine.time, "sleep", lambda s: None)
    work = tmp_path / "w"
    work.mkdir()
    pdf = engine.compile_pdf("% tex", work)
    assert pdf.exists()
    assert calls["n"] >= 2


TEX_SAMPLE = r"""\documentclass{article}
\begin{document}
\begin{center}
    {\LARGE \textbf{Mateus Santos}}
    \\ [0.1cm]
    Cruzeiro, SP {\textbullet} \href{mailto:mcos@ex.com}{mcos@ex.com}
\end{center}
\section{Experiência}
    \cventry{Objective}{Cruzeiro, SP}{Designer Gráfico}{2025}
        \begin{itemize}
            \item Otimizou fluxos, reduzindo demandas em 35\%.
        \end{itemize}
\section{Habilidades}
    \begin{itemize}
        \item \textbf{Técnicas:} React, Python, Docker
        \item \textbf{Idiomas:} Inglês: fluente
    \end{itemize}
\section{Educação}
    \cventry{FATEC}{Cruzeiro, SP}{Tecnólogo em ADS}{2024 - 2027}
\end{document}"""


def test_parse_tex_full_structure():
    p = importer.parse_tex(TEX_SAMPLE)
    assert p["personal"]["name"] == "Mateus Santos"
    assert p["personal"]["email"] == "mcos@ex.com"
    exp = p["experience"][0]
    assert exp["company"] == "Objective"
    assert exp["title"] == "Designer Gráfico"
    assert exp["location"] == "Cruzeiro, SP"
    assert exp["description"] == ["Otimizou fluxos, reduzindo demandas em 35%."]
    assert p["skills"] == ["React", "Python", "Docker"]
    assert p["languages"] == [{"name": "Inglês", "level": "fluente"}]
    edu = p["education"][0]
    assert edu["institution"] == "FATEC"
    assert edu["degree"] == "Tecnólogo em ADS"
    assert edu["year"] == "2024 - 2027"


def test_parse_resume_text_detects_tex():
    p = importer.parse_resume_text(TEX_SAMPLE)
    assert p["personal"]["name"] == "Mateus Santos"
    assert p["experience"][0]["company"] == "Objective"
