"""Backfill: re-renderiza todos os adapted_resumes com o template devcelio.

Uso (com o venv do backend ativado, a partir de backend/):
    python scripts/backfill_devcelio.py

Para cada registro: renderiza o tailored_json guardado com o template
`devcelio`, recompila o PDF e atualiza tex_code/pdf_path. Falha por
registro nao aborta o lote (log + relatorio final). Sem custo de IA.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db
from app.services.latex import engine


def main() -> int:
    db.init_db()
    rows = db.query(
        "SELECT id, job_id, tailored_json FROM adapted_resumes ORDER BY created_at"
    )
    print(f"{len(rows)} registro(s) para re-renderizar com devcelio")
    ok, fail = 0, []
    for r in rows:
        try:
            tailored = json.loads(r["tailored_json"])
            job = db.query_one("SELECT * FROM jobs WHERE id=?", (r["job_id"],)) or {}
            batch = db.new_id("backfill")
            gen = engine.generate("devcelio", tailored, job, batch)
            db.execute(
                "UPDATE adapted_resumes SET tex_code=?, pdf_path=? WHERE id=?",
                (gen["tex"], gen["pdf_path"], r["id"]),
            )
            ok += 1
            print(f"OK   {r['id']} -> {gen['pdf_path']}")
        except Exception as e:  # noqa: BLE001 - um registro nao pode abortar o lote
            fail.append((r["id"], str(e)[:200]))
            print(f"FAIL {r['id']}: {e}")
    print(f"\n{ok} ok, {len(fail)} com falha")
    for rid, err in fail:
        print(f"  {rid}: {err}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
