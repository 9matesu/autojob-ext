"""FastAPI REST routes for AutoJob."""
from __future__ import annotations

import json
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile, Response
from pydantic import BaseModel

from ..config import get_settings, update_setting, OUTPUT_DIR
from .. import db
from ..models import profile as profile_model, job as job_model
from ..services.resume import importer
from ..services.latex import engine as latex_engine
from ..services.ai import gateway, prompts, vision
from ..services.ai.gateway import AIError

router = APIRouter(prefix="/api")

class SettingsPayload(BaseModel):
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_base_url: str | None = None
    default_template: str | None = None
    default_lang: str | None = None
    compiler_preference: str | None = None

class ProfilePayload(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    profile: dict

class PolishBulletPayload(BaseModel):
    bullet: str
    role_context: str | None = ""

class CompilePayload(BaseModel):
    profile: dict | None = None
    raw_tex: str | None = None
    template: str = "editorial"
    lang: str = "en"
    job: dict | None = None

class AdaptJobPayload(BaseModel):
    job: dict
    lang: str = "en"

@router.get("/health")
def health_check():
    s = get_settings()
    comp_type, comp_path = latex_engine.find_compiler()
    active_cand = profile_model.get_active()
    return {
        "status": "ok",
        "ai_provider": s.ai_provider,
        "ai_model": s.ai_model,
        "has_api_key": bool(s.ai_api_key),
        "compiler_type": comp_type,
        "compiler_path": comp_path,
        "has_active_candidate": active_cand is not None,
        "candidate_name": active_cand["name"] if active_cand else None,
    }

@router.get("/settings")
def get_settings_endpoint():
    s = get_settings()
    comp_type, comp_path = latex_engine.find_compiler()
    # Mask API key for security
    masked_key = ""
    if s.ai_api_key:
        masked_key = s.ai_api_key[:4] + "..." + s.ai_api_key[-4:] if len(s.ai_api_key) > 8 else "***"
    return {
        "ai_provider": s.ai_provider,
        "ai_model": s.ai_model,
        "ai_api_key_masked": masked_key,
        "has_key": bool(s.ai_api_key),
        "ai_base_url": s.ai_base_url,
        "default_template": s.default_template,
        "default_lang": s.default_lang,
        "compiler_preference": s.compiler_preference,
        "detected_compiler": comp_type,
        "compiler_path": comp_path,
    }

@router.post("/settings")
def save_settings_endpoint(payload: SettingsPayload):
    if payload.ai_provider is not None: update_setting("ai_provider", payload.ai_provider)
    if payload.ai_model is not None: update_setting("ai_model", payload.ai_model)
    if payload.ai_api_key is not None:
        update_setting("ai_api_key", payload.ai_api_key)
        gateway.set_runtime_api_key(payload.ai_api_key)
    if payload.ai_base_url is not None: update_setting("ai_base_url", payload.ai_base_url)
    if payload.default_template is not None: update_setting("default_template", payload.default_template)
    if payload.default_lang is not None: update_setting("default_lang", payload.default_lang)
    if payload.compiler_preference is not None: update_setting("compiler_preference", payload.compiler_preference)
    return {"status": "saved"}

@router.post("/settings/test")
def test_ai_connection(payload: SettingsPayload):
    s = get_settings()
    if payload.ai_provider: s.ai_provider = payload.ai_provider
    if payload.ai_model: s.ai_model = payload.ai_model
    if payload.ai_api_key: s.ai_api_key = payload.ai_api_key
    if payload.ai_base_url: s.ai_base_url = payload.ai_base_url
    try:
        prov = gateway.get_provider(s)
        resp = prov.chat("You are a helpful assistant.", "Reply with {\"test\": \"ok\"}", expect_json=True)
        return {"status": "success", "response": resp}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/providers")
def list_providers():
    """Provider catalog (single source of truth for the UI). No secrets."""
    return {"providers": gateway.PROVIDER_CATALOG}

@router.post("/models")
def list_models(payload: SettingsPayload):
    """List model IDs available on a provider using the given credentials.

    Uses a transient settings object — nothing is persisted. Returns exactly
    what the provider API lists; never fabricates. Empty list + 200 when the
    provider has no listing endpoint; 400 with a clear message otherwise.
    """
    from ..config import Settings
    s = Settings(
        ai_provider=payload.ai_provider or "gemini",
        ai_api_key=payload.ai_api_key or "",
        ai_base_url=payload.ai_base_url or "",
        ai_model=payload.ai_model or "",
    )
    try:
        prov = gateway.get_provider(s)
        models = prov.models()
        return {"models": models, "count": len(models)}
    except AIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile")
def get_master_profile():
    cand = profile_model.get_active()
    if not cand:
        return {"has_profile": False, "profile": profile_model.EMPTY_PROFILE}
    return {"has_profile": True, "candidate": cand, "profile": cand["profile"]}

@router.post("/profile")
def save_master_profile_endpoint(payload: ProfilePayload):
    updated = profile_model.save_master_profile(
        profile=payload.profile,
        name=payload.name,
        email=payload.email,
        phone=payload.phone
    )
    return {"status": "saved", "candidate": updated}

@router.post("/parse-resume")
async def parse_resume_file(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        text = importer.extract_text(file.filename, raw)
        parsed = importer.parse_resume_text(text)
        return {"status": "success", "profile": parsed, "raw_preview": text[:500]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {e}")

class ParsePathPayload(BaseModel):
    file_path: str

@router.post("/parse-resume-path")
def parse_resume_from_path(payload: ParsePathPayload):
    from pathlib import Path
    p = Path(payload.file_path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=400, detail="File path does not exist")
    try:
        raw = p.read_bytes()
        text = importer.extract_text(p.name, raw)
        parsed = importer.parse_resume_text(text)
        return {"status": "success", "profile": parsed, "raw_preview": text[:500]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {e}")

def _run_adapt_pipeline(job_data: dict, captured_chars: int | None = None) -> dict:
    """Shared pipeline: adapt master profile against job, compile LaTeX, save history."""
    cand = profile_model.get_active()
    if not cand:
        raise HTTPException(status_code=400, detail="Perfil mestre não encontrado. Complete o onboarding primeiro.")
    master_profile = cand["profile"]
    s = get_settings()

    try:
        prov = gateway.get_provider(s)
        lang = latex_engine.detect_language(job_data)
        user_prompt = prompts.build_adapt_payload(master_profile, job_data, lang=lang)
        adapted_raw = prov.chat(prompts.SYSTEM_RULES, user_prompt, expect_json=True)
        adapted_json = gateway.AIProvider._extract_json(adapted_raw)
    except HTTPException:
        raise
    except AIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Adaptação de currículo falhou: {e}")

    tailored_profile = {
        **master_profile,
        "summary": adapted_json.get("summary") or master_profile.get("summary", ""),
        "skills": adapted_json.get("skills") or master_profile.get("skills", []),
        "experience": adapted_json.get("experience") or master_profile.get("experience", []),
        "projects": adapted_json.get("projects") or master_profile.get("projects", []),
    }
    try:
        match_score = float(adapted_json.get("match_score") or 0.0)
    except (TypeError, ValueError):
        match_score = 0.0
    match_score = max(0.0, min(100.0, match_score))
    applied_keywords = [str(k) for k in (adapted_json.get("applied_keywords") or [])][:20]

    job_rec = job_model.save_job({**job_data, "match_score": match_score})
    batch_label = db.new_id("ext")
    try:
        gen_result = latex_engine.generate(s.default_template, tailored_profile, job_data, batch_label)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compilação LaTeX falhou: {e}")

    res_rec = job_model.save_adapted_resume(
        job_id=job_rec["id"],
        candidate_id=cand["id"],
        tailored_json=tailored_profile,
        tex_code=gen_result["tex"],
        pdf_path=gen_result["pdf_path"],
        recruiter_pitch="",
        match_score=match_score,
    )

    return {
        "job": {**job_data, "id": job_rec["id"]},
        "captured_chars": captured_chars,
        "adaptation": {
            "id": res_rec["id"],
            "match_score": match_score,
            "applied_keywords": applied_keywords,
            "tailored_profile": tailored_profile,
            "tex_code": gen_result["tex"],
            "pdf_url": f"/api/resumes/{res_rec['id']}/pdf",
        },
    }


class TextAdaptPayload(BaseModel):
    job_text: str
    page_title: str | None = ""
    page_url: str | None = ""


@router.post("/adapt-text")
def adapt_from_text(payload: TextAdaptPayload):
    """DOM-based capture path: raw job panel text from the browser extension."""
    if not payload.job_text or len(payload.job_text.strip()) < 80:
        raise HTTPException(status_code=400, detail="Texto da vaga muito curto para extração.")
    s = get_settings()
    try:
        job_data = vision.extract_job_from_text(
            payload.job_text, s,
            page_title=payload.page_title or "",
            page_url=payload.page_url or "",
        )
    except HTTPException:
        raise
    except AIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extração da vaga falhou: {e}")
    return _run_adapt_pipeline(job_data, captured_chars=len(payload.job_text))


@router.post("/adapt-job")
def adapt_job_endpoint(payload: AdaptJobPayload):
    cand = profile_model.get_active()
    if not cand:
        raise HTTPException(status_code=400, detail="No master profile found. Please complete onboarding first.")
    master_profile = cand["profile"]
    s = get_settings()

    job_data = payload.job
    lang = payload.lang or latex_engine.detect_language(job_data)
    prov = gateway.get_provider(s)
    user_prompt = prompts.build_adapt_payload(master_profile, job_data, lang=lang)
    adapted_raw = prov.chat(prompts.SYSTEM_RULES, user_prompt, expect_json=True)
    adapted_json = gateway.AIProvider._extract_json(adapted_raw)

    tailored_profile = {
        **master_profile,
        "summary": adapted_json.get("summary") or master_profile.get("summary", ""),
        "skills": adapted_json.get("skills") or master_profile.get("skills", []),
        "experience": adapted_json.get("experience") or master_profile.get("experience", []),
    }
    match_score = float(adapted_json.get("match_score") or 90.0)
    recruiter_pitch = adapted_json.get("recruiter_pitch") or ""

    job_rec = job_model.save_job({**job_data, "match_score": match_score})
    batch_label = db.new_id("run")
    gen_result = latex_engine.generate(s.default_template, tailored_profile, job_data, batch_label)

    res_rec = job_model.save_adapted_resume(
        job_id=job_rec["id"],
        candidate_id=cand["id"],
        tailored_json=tailored_profile,
        tex_code=gen_result["tex"],
        pdf_path=gen_result["pdf_path"],
        recruiter_pitch=recruiter_pitch,
        match_score=match_score,
    )

    return {
        "job": job_rec,
        "adaptation": {
            "id": res_rec["id"],
            "match_score": match_score,
            "recruiter_pitch": recruiter_pitch,
            "tailored_profile": tailored_profile,
            "tex_code": gen_result["tex"],
            "pdf_url": f"/api/resumes/{res_rec['id']}/pdf",
        }
    }

@router.post("/compile")
def compile_resume_endpoint(payload: CompilePayload):
    s = get_settings()
    cand = profile_model.get_active()
    cand_id = cand["id"] if cand else "anon"
    job = payload.job or {"title": "Application", "company": "Company"}
    
    batch_label = db.new_id("preview")
    folder = latex_engine.slugify(job.get("company", "app"), job.get("title", "role"))
    out_dir = OUTPUT_DIR / "resumes" / batch_label / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    if payload.raw_tex:
        tex = payload.raw_tex
        (out_dir / "resume.tex").write_text(tex, encoding="utf-8")
        pdf_path = latex_engine.compile_pdf(tex, out_dir)
    elif payload.profile:
        tex = latex_engine.render_tex(payload.template or s.default_template, payload.profile, job, lang=payload.lang)
        (out_dir / "resume.tex").write_text(tex, encoding="utf-8")
        pdf_path = latex_engine.compile_pdf(tex, out_dir)
    else:
        raise HTTPException(status_code=400, detail="Must provide profile or raw_tex")

    return {
        "status": "compiled",
        "pdf_path": str(pdf_path),
        "tex": tex,
        "pdf_url": f"/output/resumes/{batch_label}/{folder}/resume.pdf"
    }

@router.post("/polish-bullet")
def polish_bullet_endpoint(payload: PolishBulletPayload):
    s = get_settings()
    try:
        prov = gateway.get_provider(s)
    except AIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    prompt = prompts.POLISH_BULLET_PROMPT.format(
        original_bullet=payload.bullet,
        context=payload.role_context or "Enhance clarity and measurable impact."
    )
    raw = prov.chat("You are a resume writing expert.", prompt, expect_json=True)
    res = gateway.AIProvider._extract_json(raw)
    return {"polished": res.get("polished", payload.bullet)}

@router.get("/history")
def get_history_endpoint():
    return {"history": job_model.list_history(50)}

@router.get("/resumes/{res_id}/pdf")
def get_resume_pdf(res_id: str):
    res = job_model.get_adapted_resume(res_id)
    if not res or not res.get("pdf_path"):
        raise HTTPException(status_code=404, detail="Resume PDF not found.")
    p = Path(res["pdf_path"])
    if not p.exists():
        raise HTTPException(status_code=404, detail="PDF file does not exist on disk.")
    pdf_bytes = p.read_bytes()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=resume.pdf"}
    )
