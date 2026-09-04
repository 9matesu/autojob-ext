r"""Resume extraction and normalization from PDF / DOCX / TXT / MD / LaTeX.

Two paths:
- parse_tex(): structured parse of LaTeX source (\section, \cventry, \item).
- parse_resume_text(): line-based parse for flattened text (PDF/DOCX/TXT/MD),
  block-oriented: consecutive non-bullet lines form an entry header block,
  bullets attach to the entry.
"""
from __future__ import annotations

import io
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from ...models.profile import EMPTY_PROFILE

SECTION_ALIASES = {
    "leadership": ("leadership", "leadership activities", "volunteer",
                   "volunteering", "volunteer experience", "lideranca",
                   "atividades de lideranca", "voluntariado",
                   "trabalho voluntario"),
    "experience": ("experience", "work experience", "professional experience",
                   "employment", "experiencia profissional", "experiencia",
                   "historico profissional"),
    "education": ("education", "academic background", "formacao academica",
                  "formacao", "escolaridade", "educacao"),
    "skills": ("skills", "technologies", "tech stack", "habilidades",
               "competencias", "tecnologias", "technical skills"),
    "projects": ("projects", "projetos"),
    "certifications": ("certifications", "certificates", "certificacoes",
                       "certificados"),
    "languages": ("languages", "idiomas"),
    "summary": ("summary", "profile", "about", "objective", "resumo",
                "perfil", "sobre", "objetivo"),
}


def _fold(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).lower()


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


def _classify_section(line: str) -> str | None:
    """Match short header-like lines against section aliases (accent-folded,
    prefix/word containment). Bullets, prose, and lines that look like
    "Company Location" (comma + trailing location) never match."""
    if len(line) > 60 or line.rstrip().endswith("."):
        return None
    if "," in line or "•" in line:
        return None
    h = _fold(re.sub(r"^[\s]*[-•*–—\d.)\s]+", "", line)).strip().rstrip(":").strip()
    if not h or len(h.split()) > 5:
        return None
    for key, aliases in SECTION_ALIASES.items():
        for a in aliases:
            af = _fold(a)
            if h == af or h.startswith(af) or af in h.split():
                return key
    return None


_DATE_PATTERNS = (
    r"\((?:(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|january|february|march|april|may|june|july|august|september|october|november|december)\.?[a-z]*\s+)?(?:\d{4}|\d{2}/\d{4})\s*(?:[-–—toàa/]\s*(?:(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|january|february|march|april|may|june|july|august|september|october|november|december)\.?[a-z]*\s+)?(?:\d{4}|\d{2}/\d{4}|present|presente|atual|current))?\)",
    r"(?:(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|january|february|march|april|may|june|july|august|september|october|november|december)\.?[a-z]*\s+)?(?:\d{4}|\d{2}/\d{4})\s*(?:[-–—toàa/]\s*(?:(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|january|february|march|april|may|june|july|august|september|october|november|december)\.?[a-z]*\s+)?(?:\d{4}|\d{2}/\d{4}|present|presente|atual|current))",
    r"\b\d{4}\s*[-–—toàa]\s*(?:\d{4}|present|presente|atual|current)\b",
    r"\b\d{4}\b",
)


def _extract_dates(line: str) -> tuple[str, str]:
    """Extracts a period ("2021 - Present", "ago. 2024 – ago. 2027") from a
    line. Returns (cleaned_line, period)."""
    for pat in _DATE_PATTERNS:
        m = re.search(pat, line, re.IGNORECASE)
        if m:
            period = m.group(0).strip("()")
            rest = line[:m.start()].strip() + " " + line[m.end():].strip()
            cleaned = rest.strip(" •–—-\t")
            return cleaned, period
    return line, ""


_REMOTE_WORDS = ("remot", "remote", "híbrido", "hybrid", "presencial", "on-site", "onsite")

# Right-anchored: a trailing location chunk at the end of a header line.
# The lookbehind rejects matches starting mid-token (e.g. "Pat" in "digiPat").
_LOCATION_RE = re.compile(
    r"(?<![A-Za-zÀ-ú0-9])[A-ZÀ-Ú][\wà-ú.]+(?:\s+[A-ZÀ-Ú][\wà-ú.]+){0,3}\s*,\s*(?:[A-Z]{2}|[A-ZÀ-Ú][a-zà-ú]+)\s*$"
)
_GLUE_RE = re.compile(r"[a-zà-ú][A-ZÀ-Ú]")


def _looks_like_location(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    low = t.lower()
    if any(w in low for w in _REMOTE_WORDS):
        return True
    return bool(_LOCATION_RE.search(t))


def _extract_location(line: str) -> tuple[str, str]:
    """Removes a trailing location chunk ("São Paulo, SP", "Remoto") from a
    header line. Handles PDF column gluing ("Waldomiro MayCruzeiro, SP") by
    cutting at the first within-token lowercase→uppercase boundary. When the
    whole line is consumed by the match, the first token is given back as the
    entity name ("Objective Cruzeiro, SP" -> company "Objective").
    Returns (rest, location)."""
    m = _LOCATION_RE.search(line)
    if m:
        matched = m.group(0).rstrip()
        gm = _GLUE_RE.search(matched)
        if gm:
            cut = m.start() + gm.start() + 1
            loc = line[cut:].strip(" ,|•–—-\t")
            rest = line[:cut].strip(" ,|•–—-\t")
            return rest, loc
        rest = line[:m.start()].strip(" ,|•–—-\t")
        if not rest and " " in matched:
            first, _, tail = matched.partition(" ")
            if "," in tail:
                return first.strip(), tail.strip(" ,|•–—-\t")
        return rest, matched.strip(" ,|•–—-\t")
    for w in _REMOTE_WORDS:
        m2 = re.search(r"\b" + w + r"\w*\s*$", line, re.IGNORECASE)
        if m2:
            loc = m2.group(0).strip()
            rest = line[:m2.start()].strip(" ,|•–—-\t")
            return rest, loc
    return line, ""


_BULLET_RE = re.compile(r"^\s*(?:[-–—]\s+|\d+[.)]\s+)")


def _bullet(line: str) -> tuple[bool, str]:
    if line.lstrip().startswith("•"):
        return True, line.lstrip()[1:].strip()
    m = _BULLET_RE.match(line)
    if m:
        return True, line[m.end():].strip()
    return False, line.strip()


_SENTENCE_END_RE = re.compile(r"[.!?…\"')\]]\s*$")


def _split_blocks(lines: list[str]) -> list[tuple[list[str], list[str]]]:
    """Group a section's lines into entries: consecutive non-bullet lines form
    a header block; bullets attach to the current entry. A non-bullet line
    right after an unterminated bullet is a wrapped continuation (PDF line
    breaks), not a new header."""
    entries: list[tuple[list[str], list[str]]] = []
    cur_h: list[str] = []
    cur_b: list[str] = []
    for line in lines:
        is_b, text = _bullet(line)
        if is_b:
            cur_b.append(text)
        elif (
            cur_b and cur_b[-1] and not _SENTENCE_END_RE.search(cur_b[-1])
            and not any(d in line for d in _DELIMS)
            and not _extract_dates(line)[1]
        ):
            cur_b[-1] = (cur_b[-1] + " " + text).strip()
        else:
            if cur_b:
                entries.append((cur_h, cur_b))
                cur_h, cur_b = [], []
            cur_h.append(line)
    if cur_h or cur_b:
        entries.append((cur_h, cur_b))
    return entries


_DELIMS = (" | ", " - ", " – ", " — ", " at ", " @ ")


def _parse_entry_block(header_lines: list[str], bullets: list[str], role_first: bool = True) -> dict:
    """Parse an entry header block into company/title/location/period plus a
    description list (subtitle line first, then bullets). Handles both the
    PDF two-line layout ("Objective Cruzeiro, SP" + "Designer Gráfico 2025")
    and the delimited one-line layout ("Tech Lead | Org | Remote | 2021 -").
    role_first=True (experience/leadership): first segment is the role;
    role_first=False (education/projects): first segment is the entity."""
    lines = [l.strip() for l in header_lines if l.strip()]
    period = ""
    date_remainder = ""
    rest: list[str] = []
    for l in lines:
        cleaned, p = _extract_dates(l)
        if p and not period:
            note = cleaned.strip()
            if note.startswith("(") and note.endswith(")"):
                p = f"{p} {note}"
                note = ""
            period = p
            date_remainder = note
        else:
            rest.append(l)

    location = ""
    parts: list[str] = []

    def push(p: str, is_first: bool) -> None:
        nonlocal location
        p = p.strip(" ,|•–—-\t")
        if not p:
            return
        if not is_first:
            ml = _LOCATION_RE.match(p)
            if ml and ml.group(0).strip() == p:
                if not location:
                    location = p
                return
        remainder, loc = _extract_location(p)
        if loc:
            if not location:
                location = loc
            p = remainder.strip()
            if not p:
                return
        if _looks_like_location(p):
            if not location:
                location = p
            return
        parts.append(p)

    def add(text: str) -> None:
        for d in _DELIMS:
            if d in text:
                for i, piece in enumerate([x.strip() for x in text.split(d) if x.strip()]):
                    push(piece, i == 0)
                return
        push(text, True)

    if date_remainder:
        add(date_remainder)
    if rest:
        add(rest[0])
        extras = [r.strip() for r in rest[1:] if r.strip()]
    else:
        extras = []

    company = ""
    title = ""
    if len(parts) >= 2:
        if role_first:
            title, company = parts[0], parts[1]
        else:
            company, title = parts[0], parts[1]
    elif len(parts) == 1:
        if location and not date_remainder:
            company = parts[0]
        else:
            title = parts[0]

    subtitle = " ".join(extras).strip().strip("—-– ").strip()
    description = ([subtitle] if subtitle else []) + [b for b in bullets if b]
    return {
        "company": company,
        "title": title,
        "location": location,
        "period": period,
        "description": description,
    }


def _parse_section_entries(lines: list[str], role_first: bool = True) -> list[dict]:
    return [_parse_entry_block(h, b, role_first) for h, b in _split_blocks(lines)]


def _parse_skills(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        _, text = _bullet(line)
        # strip "Categoria:" label at line start (Front-end:, Cloud e DevOps:)
        text = re.sub(r"^[A-Za-zÀ-ú][^:]{0,39}:\s*", "", text)
        parts = re.split(r"[,;•|]|\s/\s", text)
        for p in parts:
            s = p.strip().strip("-•*").strip()
            if 1 < len(s) < 40 and _fold(s) not in seen:
                seen.add(_fold(s))
                out.append(s)
    return out[:40]


def _parse_languages(lines: list[str]) -> list[dict]:
    out: list[dict] = []
    for line in lines:
        _, text = _bullet(line)
        for part in re.split(r"[;,]", text):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                name, level = [x.strip() for x in part.split(":", 1)]
            else:
                name, level = part, ""
            if name:
                out.append({"name": name, "level": level})
    return out


def _parse_certifications(lines: list[str]) -> list[dict]:
    out: list[dict] = []
    for line in lines:
        _, text = _bullet(line)
        if text:
            out.append({"name": text})
    return out


def _parse_projects(lines: list[str]) -> list[dict]:
    out = []
    for e in _parse_section_entries(lines, role_first=False):
        out.append({
            "name": e["company"] or e["title"],
            "role": e["title"] if e["company"] else "",
            "location": e["location"],
            "period": e["period"],
            "description": e["description"],
        })
    return [p for p in out if p["name"]]


_DEGREE_WORDS = ("bacharel", "licenci", "tecnolog", "engenh", "mestr", "doutor",
                 "pos-grad", "pos grad", "b.s", "m.s", "b.a", "m.a", "bsc", "msc")


def _parse_education(lines: list[str]) -> list[dict]:
    out = []
    for e in _parse_section_entries(lines, role_first=False):
        inst = e["company"] or e["title"]
        deg = " ".join(x for x in ([e["title"]] if e["company"] else []) + e["description"]).strip()
        if not e["company"] and e["title"] and any(w in _fold(e["title"]) for w in _DEGREE_WORDS):
            deg, inst = e["title"], ""
        out.append({
            "institution": inst,
            "degree": deg,
            "location": e["location"],
            "year": e["period"],
        })
    return [x for x in out if x["institution"] or x["degree"]]


def _parse_experience_like(lines: list[str]) -> list[dict]:
    out = []
    for e in _parse_section_entries(lines):
        out.append({
            "title": e["title"],
            "company": e["company"],
            "location": e["location"],
            "period": e["period"],
            "description": e["description"],
        })
    return [x for x in out if x["title"] or x["company"] or x["description"]]


def _parse_contact(lines: list[str], profile: dict) -> None:
    head = "\n".join(lines[:12])
    email_m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", head)
    if email_m:
        profile["personal"]["email"] = email_m.group(0)
    phone_m = re.search(r"((?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4}[-\s]?\d{4}))", head)
    if phone_m:
        profile["personal"]["phone"] = phone_m.group(0).strip()
    linkedin_m = re.search(r"(linkedin\.com/in/[\w\-]+)", head, re.I)
    if linkedin_m:
        profile["personal"]["linkedin"] = "https://" + linkedin_m.group(0)
    github_m = re.search(r"(github\.com/[\w\-]+)", head, re.I)
    if github_m:
        profile["personal"]["github"] = "https://" + github_m.group(0)
    portfolio_m = re.search(r"https?://(?!linkedin|github)[\w./?=&%-]+\.\w{2,}", head)
    if portfolio_m:
        profile["personal"]["portfolio"] = portfolio_m.group(0)
    loc_m = re.search(
        r"([A-ZÀ-Ú][a-zà-ú]+(?:\s[A-ZÀ-Ú][a-zà-ú]+)*\s*,\s*(?:[A-Z]{2}|Brasil|Brazil|Remote|Remoto))",
        head,
    )
    if loc_m:
        profile["personal"]["location"] = loc_m.group(0).strip()
    for l in lines[:5]:
        if len(l.split()) in (2, 3, 4) and "@" not in l and "http" not in l and not re.search(r"\d", l):
            if not profile["personal"].get("name"):
                profile["personal"]["name"] = l
            break


def parse_resume_text(text: str) -> dict:
    if _is_tex(text):
        return parse_tex(text)

    profile = {k: (list(v) if isinstance(v, list) else (dict(v) if isinstance(v, dict) else v))
               for k, v in EMPTY_PROFILE.items()}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return profile

    _parse_contact(lines, profile)

    # Segment by section. Lines before the first header are pre-header:
    # only prose-like long lines count as summary (short taglines like
    # "Estágio | Desenvolvimento" are dropped).
    current_sec: str | None = None
    buckets: dict[str, list[str]] = {k: [] for k in SECTION_ALIASES}
    for line in lines[1:]:
        cls = _classify_section(line)
        if cls:
            current_sec = cls
            continue
        if current_sec is None:
            is_prose = (
                len(line) > 80
                and "@" not in line
                and "http" not in line
                and not re.search(r"\(\d{2}\)\s?\d", line)
            )
            if is_prose:
                buckets["summary"].append(line)
        else:
            buckets[current_sec].append(line)

    profile["summary"] = " ".join(buckets["summary"]).strip()
    profile["skills"] = _parse_skills(buckets["skills"])
    profile["experience"] = _parse_experience_like(buckets["experience"])
    profile["leadership"] = _parse_experience_like(buckets["leadership"])
    profile["education"] = _parse_education(buckets["education"])
    profile["projects"] = _parse_projects(buckets["projects"])
    profile["languages"] = _parse_languages(buckets["languages"])
    profile["certifications"] = _parse_certifications(buckets["certifications"])
    return profile


# ---------------------------------------------------------------- LaTeX path

def _is_tex(text: str) -> bool:
    t = text.lstrip()
    return t.startswith("%") or "\\documentclass" in text or ("\\section{" in text and "\\item" in text)


def _tex_args(s: str, i: int) -> tuple[list[str], int]:
    """Read consecutive balanced-brace arguments starting at s[i] (a '{').
    Returns (args, index after them)."""
    args: list[str] = []
    n = len(s)
    while i < n:
        while i < n and s[i] in " \t\n":
            i += 1
        if i >= n or s[i] != "{":
            break
        depth = 0
        start = i + 1
        while i < n:
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        args.append(s[start:i])
        i += 1
    return args, i


def _tex_strip_cmds(s: str) -> str:
    s = re.sub(r"\\\\", " ", s)
    s = re.sub(r"\\(?:textbf|textit|emph|underline|href)\{[^{}]*\}\{", "", s)
    s = re.sub(r"\\(?:textbullet|and|quad|qquad|hspace|vspace)\{?[^}]*\}?", " ", s)
    s = re.sub(r"\\[a-zA-Z@]+\*?", " ", s)
    s = re.sub(r"[{}]", " ", s)
    s = re.sub(r"\\([%&_#$])", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_tex(text: str) -> dict:
    profile = {k: (list(v) if isinstance(v, list) else (dict(v) if isinstance(v, dict) else v))
               for k, v in EMPTY_PROFILE.items()}

    name_m = re.search(r"\\begin\{center\}(.*?)\\end\{center\}", text, re.S)
    header_block = name_m.group(1) if name_m else ""
    if header_block:
        tb = re.search(r"\\textbf\{([^{}]*)\}", header_block)
        if tb:
            profile["personal"]["name"] = _tex_strip_cmds(tb.group(1))
        contact = re.sub(r"\\(?:LARGE|l?href|textbullet|textbf)\{[^{}]*\}\{?|\\\\|\[.*?\]", " ", header_block)
        contact = _tex_strip_cmds(contact)
        _parse_contact(contact.split(" "), profile)
        # name line may hold location/phone too; re-scan whole header text
        _parse_contact(header_block.replace("\\\\", "\n").splitlines(), profile)
        if not profile["personal"]["name"]:
            first = [l for l in header_block.splitlines() if l.strip()]
            if first:
                profile["personal"]["name"] = _tex_strip_cmds(first[0])

    sections = re.split(r"\\section\{", text)
    for chunk in sections[1:]:
        title, _, body = chunk.partition("}")
        title = _tex_strip_cmds(title)
        bucket = _classify_section(title)
        if bucket is None:
            folded = _fold(title)
            if "resumo" in folded or "summary" in folded:
                bucket = "summary"
            elif "lideranca" in folded or "leadership" in folded or "voluntar" in folded:
                bucket = "leadership"
            elif "experiencia" in folded or "experience" in folded or "employment" in folded:
                bucket = "experience"
            elif "competencia" in folded or "habilidade" in folded or "skill" in folded or "tecnologia" in folded:
                bucket = "skills"
            elif "formacao" in folded or "educacao" in folded or "education" in folded:
                bucket = "education"
            elif "projeto" in folded or "project" in folded:
                bucket = "projects"
            elif "certificacao" in folded or "certification" in folded:
                bucket = "certifications"
            elif "idioma" in folded or "language" in folded:
                bucket = "languages"
        if bucket is None:
            continue
        body = body.split("\\section{")[0]

        if bucket == "skills":
            lines = [_tex_strip_cmds(l) for l in re.findall(r"\\item\s+(.*)", body)]
            skill_lines: list[str] = []
            lang_lines: list[str] = []
            for l in lines:
                head = _fold(l.split(":", 1)[0]) if ":" in l else ""
                if any(w in head for w in ("idioma", "language", "lingua")):
                    lang_lines.append(l.split(":", 1)[1])
                else:
                    skill_lines.append(l)
            profile["skills"] = _parse_skills(skill_lines)
            if lang_lines and not profile["languages"]:
                profile["languages"] = _parse_languages(lang_lines)
            continue
        if bucket == "languages":
            lines = re.findall(r"\\item\s+(.*)", body)
            profile["languages"] = _parse_languages([_tex_strip_cmds(l) for l in lines])
            continue
        if bucket == "certifications":
            lines = re.findall(r"\\item\s+(.*)", body)
            profile["certifications"] = _parse_certifications([_tex_strip_cmds(l) for l in lines])
            continue
        if bucket == "summary":
            prose = re.sub(r"\\item.*", "", body)
            profile["summary"] = _tex_strip_cmds(prose)[:1500]
            continue

        # cventry-based sections
        entries: list[dict] = []
        pos = 0
        while True:
            m = re.compile(r"\\cventry\{").search(body, pos)
            if not m:
                break
            args, after = _tex_args(body, m.end() - 1)
            nxt = re.compile(r"\\cventry\{|\\section\{").search(body, after)
            end = nxt.start() if nxt else len(body)
            bullets = [_tex_strip_cmds(b) for b in re.findall(r"\\item\s+(.*)", body[after:end])]
            args = [_tex_strip_cmds(a) for a in args]
            a1 = args[0] if len(args) > 0 else ""
            a2 = args[1] if len(args) > 1 else ""
            a3 = args[2] if len(args) > 2 else ""
            a4 = args[3] if len(args) > 3 else ""
            if bucket == "education":
                entries.append({"institution": a1, "location": a2, "degree": a3, "year": a4})
            elif bucket == "projects":
                entries.append({"name": a1, "location": a2, "role": a3, "period": a4,
                                "description": bullets})
            else:
                entries.append({"company": a1, "location": a2, "title": a3, "period": a4,
                                "description": bullets})
            pos = after

        if bucket == "education":
            profile["education"] = entries
        elif bucket == "projects":
            profile["projects"] = entries
        elif bucket == "leadership":
            profile["leadership"] = entries
        else:
            profile["experience"] = entries

    return profile
