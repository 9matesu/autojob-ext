"""resuMe Local Persistence (SQLite WAL mode)."""
from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR

DB_PATH: Path = DATA_DIR / "resume.db"
_local = threading.local()

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  profile_json TEXT NOT NULL,
  source_file TEXT,
  is_active INTEGER DEFAULT 1,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  company TEXT,
  location TEXT,
  workplace_type TEXT DEFAULT 'remote',
  description TEXT,
  requirements_json TEXT DEFAULT '[]',
  keywords_json TEXT DEFAULT '[]',
  screenshot_path TEXT,
  url TEXT,
  match_score REAL DEFAULT 0.0,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS adapted_resumes (
  id TEXT PRIMARY KEY,
  job_id TEXT,
  candidate_id TEXT,
  tailored_json TEXT NOT NULL,
  tex_code TEXT,
  pdf_path TEXT,
  recruiter_pitch TEXT,
  match_score REAL DEFAULT 0.0,
  created_at TEXT,
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (candidate_id) REFERENCES candidates(id)
);
"""

def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_id(prefix: str = "") -> str:
    s = uuid.uuid4().hex[:12]
    return f"{prefix}_{s}" if prefix else s

def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return _local.conn

def init_db():
    conn = _get_conn()
    conn.executescript(SCHEMA)
    conn.commit()

def execute(sql: str, params: tuple = ()) -> int:
    conn = _get_conn()
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.rowcount

def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = _get_conn()
    cur = conn.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]

def query_one(sql: str, params: tuple = ()) -> dict | None:
    conn = _get_conn()
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    return dict(row) if row else None
