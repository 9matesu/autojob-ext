"""Resume extraction and normalization from PDF / DOCX / TXT / MD."""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from ...models.profile import EMPTY_PROFILE

SECTION_ALIASES = {
    "experience": ("experience", "work experience", "professional experience",
                   "employment", "experiência profissional", "experiência",
                   "histórico profissional"),
    "education": ("education", "academic background", "formação acadêmica",
                  "formação", "formacao", "escolaridade", "educação", "educacao"),
    "skills": ("skills", "technologies", "tech stack", "habilidades",
               "competências", "tecnologias"),
    "projects": ("projects", "projetos"),
    "certifications": ("certifications", "certificates", "certificações",
                       "certificados"),
    "languages": ("languages", "idiomas"),
    "summary": ("summary", "profile", "about", "objective", "resumo",
                "perfil", "sobre", "objetivo"),
}

def extract_text(filename: str, raw_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw_bytes))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if suffix == ".docx":
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
            xml = z.read("word/document.xml")
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        root = ET.fromstring(xml)
        lines = []
        for p in root.iter(f"{{{ns['w']}}}p"):
            text = "".join(t.text or "" for t in p.iter(f"{{{ns['w']}}}t"))
            if text.strip():
                lines.append(text.strip())
        return "\n".join(lines)
    return raw_bytes.decode("utf-8", errors="replace")

def _classify_section(header: str) -> str | None:
    h = header.strip().lower().rstrip(":")
    for key, aliases in SECTION_ALIASES.items():
        if h in aliases:
            return key
    return None

def _extract_dates(line: str) -> tuple[str, str]:
    """Extracts date/period strings like '2021 - Present', '(2022 - Atual)' from line.
    Returns (cleaned_line, period).
    """
    date_patterns = [
        r"\((?:(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|january|february|march|april|may|june|july|august|september|october|november|december)\.?[a-z]*\s+)?(?:\d{4}|\d{2}/\d{4})\s*(?:[-–—toàa/]\s*(?:(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|january|february|march|april|may|june|july|august|september|october|november|december)\.?[a-z]*\s+)?(?:\d{4}|\d{2}/\d{4}|present|presente|atual|current))?\)",
        r"(?:(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|january|february|march|april|may|june|july|august|september|october|november|december)\.?[a-z]*\s+)?(?:\d{4}|\d{2}/\d{4})\s*(?:[-–—toàa/]\s*(?:(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|january|february|march|april|may|june|july|august|september|october|november|december)\.?[a-z]*\s+)?(?:\d{4}|\d{2}/\d{4}|present|presente|atual|current))",
        r"\b\d{4}\s*[-–—toàa]\s*(?:\d{4}|present|presente|atual|current)\b",
        r"\b\d{4}\b",
    ]
    for pat in date_patterns:
        m = re.search(pat, line, re.IGNORECASE)
        if m:
            period = m.group(0).strip("()")
            rest = line[:m.start()].strip() + " " + line[m.end():].strip()
            cleaned = rest.strip(" ()|•–—-\t")
            return cleaned, period
    return line, ""

def _parse_job_header(line: str) -> tuple[str, str, str]:
    """Parses a candidate job header into (title, company, period)."""
    cleaned_line, period = _extract_dates(line)

    delims = [" | ", " - ", " – ", " — ", " at ", " em ", " @ "]
    for d in delims:
        if d in cleaned_line:
            parts = [p.strip() for p in cleaned_line.split(d) if p.strip()]
            if len(parts) >= 2:
                return parts[0], parts[1], period

    if "," in cleaned_line:
        parts = [p.strip() for p in cleaned_line.split(",") if p.strip()]
        if len(parts) >= 2:
            return parts[0], parts[1], period

    return cleaned_line.strip(), "", period

def parse_resume_text(text: str) -> dict:
    profile = {k: (list(v) if isinstance(v, list) else (dict(v) if isinstance(v, dict) else v))
               for k, v in EMPTY_PROFILE.items()}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return profile

    # 1. Extract contact info from header lines
    head = "\n".join(lines[:12])
    email_m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", head)
    if email_m: profile["personal"]["email"] = email_m.group(0)

    phone_m = re.search(r"((?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4}[-\s]?\d{4}))", head)
    if phone_m: profile["personal"]["phone"] = phone_m.group(0).strip()

    linkedin_m = re.search(r"(linkedin\.com/in/[\w\-]+)", head, re.I)
    if linkedin_m: profile["personal"]["linkedin"] = "https://" + linkedin_m.group(0)

    github_m = re.search(r"(github\.com/[\w\-]+)", head, re.I)
    if github_m: profile["personal"]["github"] = "https://" + github_m.group(0)

    # Detect location (e.g. São Paulo, SP / Remote)
    loc_m = re.search(r"([A-ZÀ-Ú][a-zà-ú]+(?:\s[A-ZÀ-Ú][a-zà-ú]+)*\s*,\s*(?:[A-Z]{2}|Brasil|Brazil|Remote|Remoto))", head)
    if loc_m: profile["personal"]["location"] = loc_m.group(0).strip()

    # First clean non-contact line is the candidate's name
    for l in lines[:5]:
        if len(l.split()) in (2, 3, 4) and "@" not in l and "http" not in l and not re.search(r"\d", l):
            profile["personal"]["name"] = l
            break

    # 2. Segment by section
    current_sec = "summary"
    sec_buckets: dict[str, list[str]] = {k: [] for k in SECTION_ALIASES}
    sec_buckets["summary"] = []

    for line in lines[1:]:
        cls = _classify_section(line)
        if cls:
            current_sec = cls
            continue
        sec_buckets[current_sec].append(line)

    # Summary
    if sec_buckets["summary"]:
        # Filter out lines that look like headers or contact info
        sum_lines = [l for l in sec_buckets["summary"] if "@" not in l and "http" not in l]
        profile["summary"] = " ".join(sum_lines[:5]).strip()

    # Skills
    if sec_buckets["skills"]:
        raw_s = " ".join(sec_buckets["skills"])
        raw_s = re.sub(r"(?:linguagens|languages|ferramentas|tools|frameworks|bancos de dados|outros)\s*:\s*", " ", raw_s, flags=re.I)
        tokens = re.split(r"[,;•|/\n\t]+", raw_s)
        seen = set()
        cleaned_skills = []
        for t in tokens:
            st = t.strip().strip("-•*").strip()
            if 1 < len(st) < 35 and st.lower() not in seen:
                seen.add(st.lower())
                cleaned_skills.append(st)
        profile["skills"] = cleaned_skills[:30]

    # Experience: multi-job boundary detection
    exp_lines = sec_buckets["experience"]
    if exp_lines:
        experiences = []
        current_exp = None

        for line in exp_lines:
            # Check if line is a bullet item
            is_bullet = bool(re.match(r"^[\s]*[-•*–—\d\.]+\s*", line))
            clean_text = re.sub(r"^[\s]*[-•*–—\d\.]+\s*", "", line).strip()

            # Check if line contains dates or role/company header
            _, period = _extract_dates(line)
            is_header = bool(period) or (not is_bullet and any(sep in line for sep in [" | ", " - ", " – ", " at ", " em "]))

            if is_header and not is_bullet:
                if current_exp and (current_exp["title"] or current_exp["description"]):
                    experiences.append(current_exp)
                title, comp, per = _parse_job_header(line)
                current_exp = {
                    "title": title or "Cargo Profissional",
                    "company": comp or "Empresa",
                    "period": per or period,
                    "description": [],
                }
            elif current_exp:
                if clean_text:
                    current_exp["description"].append(clean_text)
            else:
                # First experience item encountered
                title, comp, per = _parse_job_header(line)
                current_exp = {
                    "title": title or "Cargo Profissional",
                    "company": comp or "Empresa",
                    "period": per or period,
                    "description": [clean_text] if is_bullet and clean_text else [],
                }

        if current_exp and (current_exp["title"] or current_exp["description"]):
            experiences.append(current_exp)

        profile["experience"] = experiences

    # Education
    edu_lines = sec_buckets["education"]
    if edu_lines:
        education_items = []
        current_edu = None
        for line in edu_lines:
            _, period = _extract_dates(line)
            is_new_edu = bool(period) or any(deg in line.lower() for deg in ["bacharel", "gradua", "b.s", "m.s", "engenh", "ciência", "faculdade", "universidade", "pós", "tecnólog"])
            if is_new_edu:
                if current_edu:
                    education_items.append(current_edu)
                p1, p2, per = _parse_job_header(line)
                univ_keywords = ["universidade", "faculdade", "usp", "unicamp", "ufrj", "college", "school", "instituto", "fatec", "puc"]
                if any(u in p1.lower() for u in univ_keywords):
                    inst_name = p1
                    deg_name = p2 or "Graduação"
                else:
                    inst_name = p2 or "Instituição de Ensino"
                    deg_name = p1 or "Bacharelado"

                current_edu = {
                    "institution": inst_name,
                    "degree": deg_name,
                    "year": per or period or "2020",
                }
            elif current_edu and not current_edu.get("degree"):
                current_edu["degree"] = line
        if current_edu:
            education_items.append(current_edu)
        profile["education"] = education_items

    return profile
