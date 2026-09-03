"""Candidate Master Profile data model and store."""
from __future__ import annotations

import json
from .. import db

EMPTY_PROFILE = {
    "personal": {
        "name": "",
        "email": "",
        "phone": "",
        "location": "",
        "linkedin": "",
        "github": "",
        "portfolio": "",
    },
    "summary": "",
    "experience": [],
    "education": [],
    "skills": [],
    "projects": [],
    "certifications": [],
    "languages": [],
}

def get_active() -> dict | None:
    row = db.query_one("SELECT * FROM candidates WHERE is_active=1 ORDER BY updated_at DESC LIMIT 1")
    if not row:
        return None
    row["profile"] = json.loads(row["profile_json"])
    return row

def deactivate_active() -> bool:
    """Deactivates the active master profile (e.g. to redo onboarding).
    History rows are kept. Returns True if there was an active profile."""
    row = db.query_one("SELECT id FROM candidates WHERE is_active=1 LIMIT 1")
    if not row:
        return False
    db.execute("UPDATE candidates SET is_active=0, updated_at=? WHERE is_active=1", (db.utcnow(),))
    return True

def save_master_profile(profile: dict, name: str | None = None, email: str | None = None, phone: str | None = None, source_file: str | None = None) -> dict:
    active = get_active()
    now = db.utcnow()
    pers = profile.get("personal") or {}
    resolved_name = name or pers.get("name") or (active["name"] if active else "Anonymous")
    resolved_email = email or pers.get("email") or (active["email"] if active else "")
    resolved_phone = phone or pers.get("phone") or (active["phone"] if active else "")
    profile_str = json.dumps(profile, ensure_ascii=False)

    if active:
        cid = active["id"]
        db.execute(
            "UPDATE candidates SET name=?, email=?, phone=?, profile_json=?, updated_at=? WHERE id=?",
            (resolved_name, resolved_email, resolved_phone, profile_str, now, cid)
        )
    else:
        cid = db.new_id("cand")
        db.execute(
            "INSERT INTO candidates (id, name, email, phone, profile_json, source_file, is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
            (cid, resolved_name, resolved_email, resolved_phone, profile_str, source_file, now, now)
        )
    return get_active()
