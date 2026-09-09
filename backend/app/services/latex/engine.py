"""LaTeX Engine: structured resume -> .tex -> pdflatex -> .pdf.

Templates live in templates/<name>/resume.tex.j2 (Jinja2). Output is written
per batch item: output/resumes/<batch>/<company-slug>/resume.{tex,pdf}.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ...config import BIN_DIR, OUTPUT_DIR, TEMPLATE_DIR


class LatexError(Exception):
    def __init__(self, message: str, transient: bool = False):
        super().__init__(message)
        self.transient = transient


def list_templates() -> list[str]:
    if not TEMPLATE_DIR.exists():
        return []
    return sorted(d.name for d in TEMPLATE_DIR.iterdir()
                  if d.is_dir() and (d / "resume.tex.j2").exists())


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape([]),
        block_start_string="<%", block_end_string="%>",
        variable_start_string="<<", variable_end_string=">>",
        comment_start_string="<#", comment_end_string="#>",
    )


def esc(s) -> str:
    """Escape LaTeX special characters."""
    if s is None:
        return ""
    s = str(s)
    repl = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
            "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
            "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    out = []
    for ch in s:
        out.append(repl.get(ch, ch))
    return "".join(out)


def esc_url(s) -> str:
    """Escape characters that break \\href{...} arguments (keep / : . -)."""
    if s is None:
        return ""
    s = str(s).strip()
    repl = {"\\": "", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
            "_": r"\_", "{": "", "}": "", "~": "", "^": "", " ": "%20"}
    return "".join(repl.get(ch, ch) for ch in s)


def short_url(s) -> str:
    """Display form of a URL: strip scheme and trailing slash."""
    if s is None:
        return ""
    s = str(s).strip()
    s = re.sub(r"^https?://(www\.)?", "", s)
    return s.rstrip("/")


def _dates(entry: dict) -> str:
    start = (entry.get("start") or entry.get("start_date") or "").strip()
    end = (entry.get("end") or entry.get("end_date") or "").strip()
    if start and end:
        return f"{start} - {end}"
    return start or end or (entry.get("period") or "") or (entry.get("year") or "")


def _bullets(entry: dict) -> list[str]:
    """Experience bullets: explicit list wins, else split description lines."""
    bl = entry.get("bullets")
    if isinstance(bl, list) and bl:
        return [str(b) for b in bl if str(b).strip()]
    desc = entry.get("description") or ""
    if isinstance(desc, list):
        lines = []
        for item in desc:
            lines.extend(str(item).splitlines())
    else:
        lines = str(desc).splitlines()
    lines = [ln.strip(" -*•\t") for ln in lines]
    return [ln for ln in lines if ln.strip()]


def _names(items) -> str:
    """Join a list of skill/language entries as a comma-separated string.
    Language dicts keep their level: "Inglês: fluente"."""
    out = []
    for it in items or []:
        if isinstance(it, dict):
            name = it.get("name") or ""
            level = it.get("level") or ""
            out.append(f"{name}: {level}" if name and level else name)
        else:
            out.append(str(it))
    return ", ".join(x for x in out if x)


# Language detection: Portuguese by default; English when the job text is
# clearly written in English (common trigger words, weighted).
_PT_WORDS = ("requisitos", "responsabilidades", "experiência", "vaga",
             "empresa", "salário", "benefícios", "desejável", "necessário",
             "conhecimentos", "formação", "superior", "diferencial",
             "trabalho", "equipe", "procuramos", "buscamos", "contratação")
_EN_WORDS = ("requirements", "responsibilities", "experience", "salary",
             "benefits", "preferred", "required", "knowledge", "degree",
             "we are looking", "you will", "skills", "team", "location",
             "qualifications", "about the role", "what you'll do")


def build_contact_line(personal: dict) -> str:
    """LaTeX contact line: location • phone • email • linkedin • github."""
    parts = []
    if personal.get("location"):
        parts.append(esc(personal["location"]))
    if personal.get("phone"):
        parts.append(esc(personal["phone"]))
    if personal.get("email"):
        parts.append(r"\href{mailto:" + esc_url(personal["email"]) +
                     r"}{\underline{" + esc(personal["email"]) + r"}}")
    for key in ("linkedin", "github", "website"):
        if personal.get(key):
            parts.append(r"\href{" + esc_url(personal[key]) +
                         r"}{\underline{" + esc(short_url(personal[key])) + r"}}")
    return r" \textbullet{} ".join(parts)


def detect_language(job: dict) -> str:
    """Return 'pt' or 'en' based on the job posting language."""
    text = " ".join([
        job.get("title") or "", job.get("description") or "",
        " ".join(job.get("requirements") or []),
    ]).lower()
    pt = sum(1 for w in _PT_WORDS if w in text)
    en = sum(1 for w in _EN_WORDS if w in text)
    if en > pt and en >= 2:
        return "en"
    return "pt"


def slugify(company: str, title: str) -> str:
    base = f"{company}-{title}".lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base[:60] or "job"


def normalize_resume(resume: dict) -> dict:
    """Coerce entries into the dict shapes the templates expect."""
    r = dict(resume)

    def as_named(items):
        out = []
        for it in items or []:
            if isinstance(it, dict):
                out.append(it)
            elif it:
                out.append({"name": str(it)})
        return out

    for key in ("skills", "languages", "certifications", "projects"):
        r[key] = as_named(r.get(key))
    r["experience"] = [e if isinstance(e, dict) else {"role": str(e)}
                       for e in (r.get("experience") or [])]
    r["leadership"] = [e if isinstance(e, dict) else {"role": str(e)}
                       for e in (r.get("leadership") or [])]
    r["education"] = [e if isinstance(e, dict) else {"institution": str(e)}
                      for e in (r.get("education") or [])]
    r["personal"] = r.get("personal") or {}
    r["summary"] = r.get("summary") or ""
    return r


def render_tex(template: str, resume: dict, job: dict,
               lang: str | None = None) -> str:
    if template.lower() in ("standard", "standard_ats", "ats", "padrao", "padrao_ats"):
        template = "editorial"
    tpl_dir = TEMPLATE_DIR / template

    if not (tpl_dir / "resume.tex.j2").exists():
        raise LatexError(f"Template not found: {template}", transient=False)

    env = _env()
    env.filters["esc"] = esc
    env.filters["esc_url"] = esc_url
    env.filters["short_url"] = short_url
    env.filters["dates"] = _dates
    env.filters["bullets"] = _bullets
    env.filters["names"] = _names
    tpl = env.get_template(f"{template}/resume.tex.j2")
    lang = lang or detect_language(job)
    personal = resume.get("personal", {})
    return tpl.render(resume=normalize_resume(resume), job=job,
                      personal=personal, lang=lang,
                      contact_line=build_contact_line(personal))


def find_compiler() -> tuple[str | None, str | None]:
    """Returns (compiler_type, compiler_path) or (None, None)."""
    bundled_tectonic = BIN_DIR / "tectonic.exe"
    if bundled_tectonic.exists():
        return "tectonic", str(bundled_tectonic)
    w_tectonic = shutil.which("tectonic")
    if w_tectonic:
        return "tectonic", w_tectonic
    w_pdflatex = shutil.which("pdflatex")
    if w_pdflatex:
        return "pdflatex", w_pdflatex
    return None, None


def download_tectonic_if_missing() -> str | None:
    """Auto-download portable standalone Tectonic binary for Windows."""
    target_exe = BIN_DIR / "tectonic.exe"
    if target_exe.exists():
        return str(target_exe)
    import io, zipfile, httpx
    url = "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.15.0/tectonic-0.15.0-x86_64-pc-windows-msvc.zip"
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=60.0)
        if resp.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                z.extract("tectonic.exe", str(BIN_DIR))
            return str(target_exe)
    except Exception as e:
        print(f"Failed to auto-download tectonic: {e}")
    return None


def compile_pdf(tex_source: str, workdir: Path) -> Path:
    """Run Tectonic or pdflatex in an isolated temp dir, copy PDF out.

    Duas tentativas: falhas transitórias de compilador (lock do MiKTeX,
    varredura de antivírus, timeout) não devem derrubar a captura inteira.
    """
    tex_path = workdir / "resume.tex"
    tex_path.write_text(tex_source, encoding="utf-8")
    comp_type, comp_path = find_compiler()
    if not comp_type:
        comp_path = download_tectonic_if_missing()
        if comp_path:
            comp_type = "tectonic"
        else:
            raise LatexError(
                "No LaTeX compiler found (neither Tectonic nor pdflatex). "
                "Please place tectonic.exe in backend/bin or install MiKTeX/TeX Live.",
                transient=False
            )

    last_err: Exception | None = None
    for attempt in (1, 2):
        try:
            with tempfile.TemporaryDirectory(prefix="resume_tex_") as tmp:
                tmp_path = Path(tmp)
                if comp_type == "tectonic":
                    proc = subprocess.run(
                        [comp_path, "-X", "compile", str(tex_path), "--outdir", str(tmp_path)],
                        capture_output=True, text=True, timeout=300
                    )
                    if proc.returncode != 0:
                        log_tail = proc.stdout[-1500:] if proc.stdout else (proc.stderr or "Compilation error")
                        raise LatexError(f"Tectonic failed: {log_tail}", transient=False)
                else:
                    for _pass in (1, 2):
                        proc = subprocess.run(
                            [comp_path, "-interaction=nonstopmode", "-halt-on-error",
                             "-output-directory", str(tmp_path), str(tex_path)],
                            capture_output=True, text=True, timeout=180,
                            cwd=str(tmp_path),
                        )
                        if proc.returncode != 0:
                            log_tail = _extract_errors(proc.stdout) or proc.stdout[-1500:]
                            raise LatexError(f"pdflatex failed (pass {_pass}): {log_tail}", transient=False)
                pdf_src = tmp_path / "resume.pdf"
                if not pdf_src.exists():
                    raise LatexError(f"{comp_type} produced no PDF", transient=False)
                pdf_out = workdir / "resume.pdf"
                shutil.copyfile(pdf_src, pdf_out)
                return pdf_out
        except subprocess.TimeoutExpired as e:
            last_err = LatexError(f"{comp_type} timed out after {e} on attempt {attempt}", transient=True)
        except LatexError as e:
            last_err = e
        if attempt == 1:
            time.sleep(1.5)

    raise last_err if last_err else LatexError("Compilation failed", transient=False)


def _extract_errors(stdout: str) -> str:
    lines = stdout.splitlines()
    errs = [ln for ln in lines if ln.startswith("!") or "Error" in ln]
    return "\n".join(errs[:10])


def generate(template: str, resume: dict, job: dict, batch_label: str) -> dict:
    """Full render+compile for one item. Returns paths + tex source + lang."""
    folder = slugify(job.get("company", "unknown"), job.get("title", "job"))
    out_dir = OUTPUT_DIR / "resumes" / batch_label / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    lang = detect_language(job)
    tex = render_tex(template, resume, job, lang=lang)
    (out_dir / "resume.tex").write_text(tex, encoding="utf-8")
    pdf = compile_pdf(tex, out_dir)
    return {"output_dir": str(out_dir), "pdf_path": str(pdf), "tex": tex,
            "lang": lang}
