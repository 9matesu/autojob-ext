"""Job and Adapted Resume Models."""
from __future__ import annotations

import json
from .. import db

def save_job(job_data: dict) -> dict:
    jid = db.new_id("job")
    now = db.utcnow()
    db.execute(
        """INSERT INTO jobs (id, title, company, location, workplace_type, description, requirements_json, keywords_json, screenshot_path, url, match_score, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            jid,
            job_data.get("title") or "Unknown Role",
            job_data.get("company") or "Unknown Company",
            job_data.get("location") or "",
            job_data.get("workplace_type") or "remote",
            job_data.get("description") or "",
            json.dumps(job_data.get("requirements") or [], ensure_ascii=False),
            json.dumps(job_data.get("keywords") or [], ensure_ascii=False),
            job_data.get("screenshot_path") or "",
            job_data.get("url") or "",
            float(job_data.get("match_score") or 0.0),
            now,
        )
    )
    return get_job(jid)

def get_job(job_id: str) -> dict | None:
    row = db.query_one("SELECT * FROM jobs WHERE id=?", (job_id,))
    if not row:
        return None
    row["requirements"] = json.loads(row["requirements_json"] or "[]")
    row["keywords"] = json.loads(row["keywords_json"] or "[]")
    return row

def save_adapted_resume(job_id: str, candidate_id: str, tailored_json: dict, tex_code: str, pdf_path: str, recruiter_pitch: str, match_score: float) -> dict:
    rid = db.new_id("res")
    now = db.utcnow()
    db.execute(
        """INSERT INTO adapted_resumes (id, job_id, candidate_id, tailored_json, tex_code, pdf_path, recruiter_pitch, match_score, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            rid,
            job_id,
            candidate_id,
            json.dumps(tailored_json, ensure_ascii=False),
            tex_code,
            pdf_path,
            recruiter_pitch,
            float(match_score),
            now,
        )
    )
    return get_adapted_resume(rid)

def get_adapted_resume(res_id: str) -> dict | None:
    row = db.query_one("SELECT * FROM adapted_resumes WHERE id=?", (res_id,))
    if not row:
        return None
    row["tailored_profile"] = json.loads(row["tailored_json"])
    return row

def list_history(limit: int = 50) -> list[dict]:
    rows = db.query(
        """SELECT r.id, r.job_id, r.match_score, r.pdf_path, r.recruiter_pitch, r.created_at,
                  j.title, j.company, j.location, j.url
           FROM adapted_resumes r
           JOIN jobs j ON r.job_id = j.id
           ORDER BY r.created_at DESC LIMIT ?""",
        (limit,)
    )
    return rows
