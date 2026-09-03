"""Validation gate: only VALIDATED items may proceed to apply/email.

Checks: PDF exists + non-trivial size, page count within bounds, candidate
name present in tex, no obvious empty-field artifacts, file integrity
(readable header %PDF).
"""
from __future__ import annotations

from pathlib import Path


class ValidationError(Exception):
    def __init__(self, message: str, transient: bool = False):
        super().__init__(message)
        self.transient = transient


def validate_pdf(pdf_path: str | Path, tex_source: str,
                 candidate_name: str | None) -> dict:
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise ValidationError("PDF file missing after render")
    size = pdf.stat().st_size
    if size < 2048:
        raise ValidationError(f"PDF suspiciously small ({size} bytes)")
    head = pdf.read_bytes()[:5]
    if head != b"%PDF-":
        raise ValidationError("File is not a valid PDF (bad header)")

    pages = _count_pages(pdf)
    if pages is not None and (pages < 1 or pages > 6):
        raise ValidationError(f"Unexpected page count: {pages}")

    if candidate_name and candidate_name.strip():
        # name should appear in the tex source (escaped form may differ, so
        # check the first token of the name)
        first = candidate_name.strip().split()[0]
        if first.lower() not in tex_source.lower():
            raise ValidationError(
                f"Candidate name '{first}' not found in generated resume")

    if "UNDEFINED" in tex_source or "None" in tex_source.split("%", 1)[0][:200]:
        raise ValidationError("Generated tex contains placeholder artifacts")

    return {"pages": pages, "bytes": size}


def _count_pages(pdf: Path) -> int | None:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf)).pages)
    except Exception:
        return None
