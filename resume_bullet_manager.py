#!/usr/bin/env python3
"""
Resume Bullet Manager
=====================
Parses LaTeX resume experience files, scores/ranks bullet points using Claude,
stores them in YAML, and lets you add new bullets with deduplication.

Usage:
  python resume_bullet_manager.py --init          # Parse all .tex files → YAML
  python resume_bullet_manager.py --score         # Score & rank all bullets
  python resume_bullet_manager.py --show          # Print ranked bullets per role
  python resume_bullet_manager.py --add           # Interactive: add new bullet
  python resume_bullet_manager.py --report        # Full scored report to stdout
"""

import os
import re
import sys
import json
import yaml
import argparse
import textwrap
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

# Where to write / read scoring-workbench YAML (separate from pipeline content)
YAML_DIR = Path("experience_yaml")

# Pipeline's authoritative content directory — the "proper experience .yaml"
# that downstream renderer.py / selector.py read from.
PIPELINE_EXPERIENCE_DIR = Path("content/experience")

# Valid family IDs for the pipeline schema
VALID_FAMILIES = {"DS", "DA", "AE", "DE", "MLE", "ECON"}

# Map of LaTeX source files → (company, logo hint)
TEX_SOURCES = {
    "kano.tex":    "Kano Apps",
    "kix_sfg.tex": "Kixeye / Stillfront Group",
    "kixeye.tex":  "Kixeye Inc",
    "ea.tex":      "Electronic Arts",
    "pretio.tex":  "Pretio Interactive",
    "tinymob.tex": "TinyMob Games",
}

# Scoring rubric weights (must sum to 1.0)
SCORE_WEIGHTS = {
    "quantifiable_impact": 0.30,   # $, %, numbers, timelines
    "action_strength":     0.20,   # strong verbs, specificity
    "technical_depth":     0.20,   # tools, methods named
    "business_relevance":  0.15,   # ties to revenue/retention/etc.
    "uniqueness":          0.15,   # differentiation / unusual insight
}

# Fuzzy-match threshold for deduplication (0–1, lower = stricter)
DEDUP_THRESHOLD = 0.72

MODEL  = "claude-sonnet-4-6"

# Lazy-loaded Anthropic client. Module-level instantiation was breaking
# imports when ANTHROPIC_API_KEY wasn't set or when the sandbox SOCKS
# proxy config was triggered at import time. Matches builder/ranker.py.
_CLIENT = None

def _get_client():
    global _CLIENT
    if _CLIENT is None:
        import anthropic
        _CLIENT = anthropic.Anthropic()
    return _CLIENT


# ---------------------------------------------------------------------------
# LATEX PARSER
# ---------------------------------------------------------------------------

def strip_latex(text: str) -> str:
    """Remove common LaTeX markup, returning readable plain text."""
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\textit\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\emph\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\color\{[^}]*\}", "", text)
    text = re.sub(r"\\[a-zA-Z]+\*?\{([^}]*)\}", r"\1", text)  # generic \cmd{x}
    text = re.sub(r"\\[a-zA-Z]+\*?", "", text)                 # bare \cmd
    text = re.sub(r"\{|\}", "", text)
    text = text.replace(r"\%", "%").replace(r"\$", "$").replace(r"\&", "&")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_tex_file(tex_path: Path) -> list[dict]:
    """
    Parse a LaTeX experience file and return a list of role dicts:
    {
      company, title, period, location, summary, bullets: [str]
    }
    """
    raw = tex_path.read_text(encoding="utf-8")

    # Strip line-level comments (but keep the line itself as empty)
    lines = []
    for line in raw.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("%"):
            lines.append("")
        else:
            # remove inline comments (not inside \url or \href)
            line = re.sub(r"(?<!\\)%.*$", "", line)
            lines.append(line)
    raw = "\n".join(lines)

    roles = []

    # Find each \entry{period}{title}{location}{body}
    # Entries can span multiple lines; match balanced braces manually
    entry_starts = [m.start() for m in re.finditer(r"\\entry\s*\{", raw)]

    def extract_brace_content(s: str, start: int) -> tuple[str, int]:
        """Return (content between outermost braces, index after closing brace)."""
        # Skip whitespace / newlines to find opening brace
        while start < len(s) and s[start] in " \t\n\r":
            start += 1
        if start >= len(s) or s[start] != "{":
            raise ValueError(f"Expected '{{' at pos {start}, got {s[start:start+10]!r}")
        depth = 0
        i = start
        buf = []
        while i < len(s):
            c = s[i]
            if c == "{":
                depth += 1
                if depth > 1:
                    buf.append(c)
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return "".join(buf), i + 1
                else:
                    buf.append(c)
            else:
                buf.append(c)
            i += 1
        raise ValueError("Unbalanced braces")

    for start in entry_starts:
        # Advance past \entry to the first {
        pos = raw.index("{", start)
        try:
            period, pos   = extract_brace_content(raw, pos)
            title,  pos   = extract_brace_content(raw, pos)
            location, pos = extract_brace_content(raw, pos)
            body, _       = extract_brace_content(raw, pos)
        except (ValueError, IndexError):
            continue

        # Extract summary (text before \begin{itemize})
        summary_match = re.split(r"\\begin\{itemize\}", body, maxsplit=1)
        summary = strip_latex(summary_match[0]).strip()

        # Extract bullet items
        bullets = []
        items_block = body
        # Find all \item ... content up to next \item or \end{itemize}
        item_texts = re.split(r"\\item\b", items_block)
        for item in item_texts[1:]:  # skip text before first \item
            # Flatten nested sub-bullets into parent
            sub = re.sub(r"\\begin\{itemize\}(.*?)\\end\{itemize\}", r" \1", item, flags=re.DOTALL)
            sub = re.sub(r"\\item\b", "; ", sub)
            # Remove residual LaTeX env tags that can leak into the last item
            sub = re.sub(r"\\end\{[^}]+\}", " ", sub)
            sub = re.sub(r"\\begin\{[^}]+\}", " ", sub)
            bullet_text = strip_latex(sub).strip().rstrip(";").strip()
            # Strip dangling LaTeX environment names that can leak into the last item
            bullet_text = re.sub(r"\s+\b(itemize|enumerate|document|entrylist|tabular)\b\s*$", "", bullet_text).strip()
            if bullet_text and len(bullet_text) > 10:
                bullets.append(bullet_text)

        roles.append({
            "company":   TEX_SOURCES.get(tex_path.name, tex_path.stem),
            "title":     strip_latex(title).strip(),
            "period":    strip_latex(period).strip(),
            "location":  strip_latex(location).strip(),
            "summary":   summary,
            "bullets":   bullets,
            "source":    tex_path.name,
        })

    return roles


# ---------------------------------------------------------------------------
# PDF PARSER
# ---------------------------------------------------------------------------

PDF_PARSE_SYSTEM = """\
You are a resume parser. The user will give you the raw text extracted from a PDF resume.
Your job is to identify every distinct work experience entry and return structured data.

Return ONLY a JSON array — no markdown fences, no prose.
Each element represents one role:
{
  "company":  "<company name>",
  "title":    "<job title>",
  "period":   "<date range, e.g. Jun 2016 – Nov 2018>",
  "location": "<city / country if present, else ''>",
  "summary":  "<introductory sentence(s) describing the role, not a bullet>",
  "bullets":  ["<bullet text>", ...]
}

Rules:
- bullets must be plain strings — no leading dashes, bullets, or numbers.
- If a bullet spans multiple lines in the source, join it into one string.
- Omit the Education section and any non-work-experience sections entirely.
- Do not invent content; extract only what is present.
- Return an empty array [] if no work experience is found.
"""


def clean_pdf_text(raw: str) -> str:
    """Normalise common PDF extraction artefacts."""
    # (cid:N) is a missing-glyph placeholder; common for bullet characters
    raw = re.sub(r"\(cid:\d+\)", "•", raw)
    # Merge hyphenated line-breaks (word wrap artefacts)
    raw = re.sub(r"-\n(\w)", r"\1", raw)
    # Collapse runs of whitespace/blank lines to at most two newlines
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r"[ \t]+", " ", raw)
    return raw.strip()


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract plain text from a PDF using pdfplumber (preferred) with
    a pypdf fallback for malformed files.
    """
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            for page in pdf.pages:
                t = page.extract_text(x_tolerance=2, y_tolerance=2)
                if t:
                    pages.append(t)
        if pages:
            return clean_pdf_text("\n\n".join(pages))
    except Exception as e:
        print(f"  ⚠️  pdfplumber failed ({e}), trying pypdf fallback…")

    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        pages = [p.extract_text() or "" for p in reader.pages]
        return clean_pdf_text("\n\n".join(pages))
    except Exception as e:
        raise RuntimeError(f"Could not extract text from {pdf_path}: {e}") from e


def parse_resume_pdf_with_claude(text: str) -> list[dict]:
    """
    Send extracted PDF text to Claude and get back a list of structured
    role dicts matching the same shape produced by parse_tex_file().
    """
    # Trim to ~12 000 chars so we stay well within the context window
    # even for very long resumes.
    if len(text) > 12_000:
        text = text[:12_000] + "\n[truncated]"

    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=4096,
        system=PDF_PARSE_SYSTEM,
        messages=[{"role": "user", "content": f"Resume text:\n\n{text}"}],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()

    roles = json.loads(raw)

    # Normalise to match the shape from parse_tex_file()
    for role in roles:
        role.setdefault("summary", "")
        role.setdefault("location", "")
        role["source"] = "pdf_import"
        # Sanitise bullets: drop empties and leading punctuation
        role["bullets"] = [
            re.sub(r"^[•\-–—*·▪▸►\s]+", "", b).strip()
            for b in role.get("bullets", [])
            if b and b.strip()
        ]

    return roles


def cmd_init_pdf(pdf_path: Path) -> None:
    """Parse a PDF resume and merge the extracted roles into YAML files."""
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        return

    print(f"\n📄  Extracting text from {pdf_path.name}…")
    try:
        text = extract_text_from_pdf(pdf_path)
    except RuntimeError as e:
        print(f"  ✗ {e}")
        return
    print(f"  Extracted {len(text):,} characters across the document.\n")

    print("🤖  Parsing experience sections with Claude…")
    try:
        roles = parse_resume_pdf_with_claude(text)
    except Exception as e:
        print(f"  ✗ Claude parsing failed: {e}")
        return

    if not roles:
        print("  No work-experience entries found in the document.")
        return

    print(f"  Found {len(roles)} role(s).\n")

    total_added = 0
    for role in roles:
        company = role.get("company", "Unknown Company")
        data = load_yaml(company)
        key  = role_key(role.get("title", ""), role.get("period", ""))

        if key not in data:
            data[key] = {
                "company":  company,
                "title":    role.get("title", ""),
                "period":   role.get("period", ""),
                "location": role.get("location", ""),
                "summary":  role.get("summary", ""),
                "source":   "pdf_import",
                "bullets":  [],
            }

        existing_texts = [b["text"] for b in data[key]["bullets"]]
        added = 0
        for bullet in role.get("bullets", []):
            dup, _ = is_duplicate(bullet, existing_texts)
            if not dup:
                data[key]["bullets"].append({
                    "text":   bullet,
                    "scores": None,
                    "added":  str(datetime.today().date()),
                    "source": "pdf_import",
                })
                existing_texts.append(bullet)
                added += 1

        save_yaml(company, data)
        print(f"  ✅  {company} | {role.get('title', '?')} — {added} bullets imported"
              + (f" ({len(role['bullets']) - added} duplicate(s) skipped)"
                 if len(role.get('bullets', [])) > added else ""))
        total_added += added

    print(f"\n✔  Done. {total_added} bullet(s) written to {YAML_DIR}/\n")


# ---------------------------------------------------------------------------
# YAML PERSISTENCE
# ---------------------------------------------------------------------------

def yaml_path_for(company: str) -> Path:
    """Return the YAML file path for a company slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", company.lower()).strip("_")
    return YAML_DIR / f"{slug}.yaml"


def load_yaml(company: str) -> dict:
    """Load existing YAML data or return blank structure."""
    path = yaml_path_for(company)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    return data


def save_yaml(company: str, data: dict) -> None:
    """Write data to the company YAML file."""
    YAML_DIR.mkdir(parents=True, exist_ok=True)
    path = yaml_path_for(company)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=100)


def role_key(title: str, period: str) -> str:
    """Stable dict key for a role."""
    return f"{title} | {period}"


# ---------------------------------------------------------------------------
# DEDUPLICATION
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def is_duplicate(new_bullet: str, existing_bullets: list[str],
                 threshold: float = DEDUP_THRESHOLD) -> tuple[bool, str | None]:
    """Return (is_dup, most_similar_existing_or_None)."""
    for existing in existing_bullets:
        score = similarity(new_bullet, existing)
        if score >= threshold:
            return True, existing
    return False, None


# ---------------------------------------------------------------------------
# CLAUDE-POWERED SCORING
# ---------------------------------------------------------------------------

SCORE_SYSTEM = """\
You are an expert resume coach specializing in data science and analytics roles.
You evaluate résumé bullet points across five dimensions and return ONLY a JSON object.

Scoring dimensions (0–100 each):
- quantifiable_impact: Does it include $, %, numbers, before/after, time savings?
- action_strength: Does it start with a strong verb and remain specific throughout?
- technical_depth: Are specific tools, methods, or frameworks named?
- business_relevance: Does it link to revenue, retention, efficiency, or strategic value?
- uniqueness: Is the insight non-obvious, or does it demonstrate unusual thinking?

Return EXACTLY this JSON (no markdown, no prose):
{
  "quantifiable_impact": <0-100>,
  "action_strength": <0-100>,
  "technical_depth": <0-100>,
  "business_relevance": <0-100>,
  "uniqueness": <0-100>,
  "composite": <weighted average to 1 decimal>,
  "rationale": "<one sentence>",
  "suggested_improvement": "<one sentence rewrite or 'None needed'>"
}
"""


def score_bullet(bullet: str) -> dict:
    """Call Claude to score a single bullet. Returns the parsed score dict."""
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=400,
        system=SCORE_SYSTEM,
        messages=[{"role": "user", "content": f"Bullet: {bullet}"}],
    )
    raw = response.content[0].text.strip()
    # Strip possible ```json fences
    raw = re.sub(r"^```json\s*|```$", "", raw, flags=re.MULTILINE).strip()
    data = json.loads(raw)

    # Recompute composite from weights to be authoritative
    composite = sum(
        data[k] * w for k, w in SCORE_WEIGHTS.items() if k in data
    )
    data["composite"] = round(composite, 1)
    return data


def score_bullets_batch(bullets: list[str]) -> list[dict]:
    """Score a list of bullets, returning one score dict per bullet."""
    system = """\
You are an expert resume coach specializing in data science and analytics roles.
Score each bullet in the input array. Return ONLY a JSON array, one object per bullet,
same order as input.

Each object:
{
  "quantifiable_impact": <0-100>,
  "action_strength": <0-100>,
  "technical_depth": <0-100>,
  "business_relevance": <0-100>,
  "uniqueness": <0-100>,
  "rationale": "<one sentence>",
  "suggested_improvement": "<rewrite or 'None needed'>"
}
No markdown fences, no prose — only the JSON array.
"""
    payload = json.dumps(bullets, ensure_ascii=False)
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": f"Bullets:\n{payload}"}],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*|```$", "", raw, flags=re.MULTILINE).strip()
    scores = json.loads(raw)

    # Attach composite
    for s in scores:
        composite = sum(s[k] * w for k, w in SCORE_WEIGHTS.items() if k in s)
        s["composite"] = round(composite, 1)
    return scores


# ---------------------------------------------------------------------------
# INIT: parse all tex → YAML
# ---------------------------------------------------------------------------

def cmd_init(tex_dir: Path) -> None:
    """Parse all .tex experience files and write initial YAML databases."""
    print(f"\n📂  Scanning {tex_dir} for experience .tex files...\n")
    created = 0
    for tex_name in TEX_SOURCES:
        tex_path = tex_dir / tex_name
        if not tex_path.exists():
            print(f"  ⚠️  Not found: {tex_path}")
            continue

        roles = parse_tex_file(tex_path)
        if not roles:
            print(f"  ⚠️  No entries parsed from {tex_name}")
            continue

        company = roles[0]["company"]
        data = load_yaml(company)

        for role in roles:
            key = role_key(role["title"], role["period"])
            if key not in data:
                data[key] = {
                    "company":  role["company"],
                    "title":    role["title"],
                    "period":   role["period"],
                    "location": role["location"],
                    "summary":  role["summary"],
                    "source":   role["source"],
                    "bullets":  [],
                }
            existing_texts = [b["text"] for b in data[key]["bullets"]]
            added = 0
            for bullet in role["bullets"]:
                dup, _ = is_duplicate(bullet, existing_texts)
                if not dup:
                    data[key]["bullets"].append({
                        "text":    bullet,
                        "scores":  None,
                        "added":   str(datetime.today().date()),
                        "source":  "tex_import",
                    })
                    existing_texts.append(bullet)
                    added += 1

            print(f"  ✅  {company} | {role['title']} — {added} bullets imported")

        save_yaml(company, data)
        created += 1

    print(f"\n✔  Done. {created} YAML files written to {YAML_DIR}/\n")


# ---------------------------------------------------------------------------
# SCORE: score all un-scored bullets in YAML
# ---------------------------------------------------------------------------

def cmd_score(tex_dir: Path) -> None:
    """Score any un-scored bullets across all YAML files."""
    YAML_DIR.mkdir(parents=True, exist_ok=True)
    yaml_files = list(YAML_DIR.glob("*.yaml"))
    if not yaml_files:
        print("No YAML files found. Run --init first.")
        return

    total_scored = 0
    for yf in yaml_files:
        with open(yf) as f:
            data = yaml.safe_load(f) or {}

        changed = False
        for key, role in data.items():
            unscored = [b for b in role["bullets"] if not b.get("scores")]
            if not unscored:
                continue

            bullets_text = [b["text"] for b in unscored]
            print(f"\n  Scoring {len(bullets_text)} bullet(s) for:"
                  f"\n    {role['company']} | {role['title']}")

            # Batch in chunks of 10 to stay within token limits
            chunk_size = 10
            all_scores = []
            for i in range(0, len(bullets_text), chunk_size):
                chunk = bullets_text[i : i + chunk_size]
                try:
                    scores = score_bullets_batch(chunk)
                    all_scores.extend(scores)
                except Exception as e:
                    print(f"    ⚠️  Scoring error: {e}")
                    all_scores.extend([None] * len(chunk))

            for bullet, score in zip(unscored, all_scores):
                bullet["scores"] = score
                if score:
                    print(f"    [{score['composite']:5.1f}] {bullet['text'][:80]}…")
                total_scored += 1

            changed = True

        if changed:
            company = next(iter(data.values()))["company"]
            save_yaml(company, data)

    print(f"\n✔  Scored {total_scored} bullet(s) total.\n")


# ---------------------------------------------------------------------------
# SHOW: print ranked bullets
# ---------------------------------------------------------------------------

def cmd_show() -> None:
    """Print all bullets ranked by composite score."""
    yaml_files = sorted(YAML_DIR.glob("*.yaml"))
    if not yaml_files:
        print("No YAML files found. Run --init first.")
        return

    for yf in yaml_files:
        with open(yf) as f:
            data = yaml.safe_load(f) or {}

        for key, role in data.items():
            bullets = sorted(
                role["bullets"],
                key=lambda b: (b.get("scores") or {}).get("composite", 0),
                reverse=True,
            )
            print(f"\n{'='*80}")
            print(f"  {role['company']}  ·  {role['title']}  ·  {role['period']}")
            print(f"{'='*80}")
            for i, b in enumerate(bullets, 1):
                score = b.get("scores")
                composite = score["composite"] if score else "?"
                flag = "★" if score and score["composite"] >= 80 else " "
                print(f"\n  {flag} #{i}  [{composite}]")
                print(textwrap.fill(f"     {b['text']}", width=90,
                                    subsequent_indent="     "))
                if score and score.get("rationale"):
                    print(f"     → {score['rationale']}")
                if score and score.get("suggested_improvement", "None needed") != "None needed":
                    print(f"     💡 {score['suggested_improvement']}")


# ---------------------------------------------------------------------------
# ADD: interactively add a new bullet to a role
# ---------------------------------------------------------------------------

def cmd_add() -> None:
    """Interactive flow: pick a role, enter a bullet, deduplicate, score, save."""
    yaml_files = sorted(YAML_DIR.glob("*.yaml"))
    if not yaml_files:
        print("No YAML files found. Run --init first.")
        return

    # Build flat list of roles for selection
    all_roles = []
    for yf in yaml_files:
        with open(yf) as f:
            data = yaml.safe_load(f) or {}
        for key, role in data.items():
            all_roles.append((yf, key, role))

    # Display menu
    print("\n📋  Available roles:\n")
    for i, (_, key, role) in enumerate(all_roles, 1):
        print(f"  {i:2d}. {role['company']:35s} | {role['title']:40s} | {role['period']}")

    try:
        choice = int(input("\nSelect role number: ").strip()) - 1
        assert 0 <= choice < len(all_roles)
    except (ValueError, AssertionError):
        print("Invalid selection.")
        return

    yf, key, role = all_roles[choice]

    print(f"\n✏️   Adding bullet to: {role['title']} @ {role['company']}\n")
    new_bullet = input("Enter new bullet text:\n> ").strip()
    if not new_bullet:
        print("Empty input — aborting.")
        return

    # Deduplication check
    existing_texts = [b["text"] for b in role["bullets"]]
    dup, matched = is_duplicate(new_bullet, existing_texts)
    if dup:
        print(f"\n⚠️   This bullet is too similar to an existing one:\n")
        print(f"     Existing: {matched}")
        print(f"     New:      {new_bullet}")
        confirm = input("\nAdd anyway? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted — bullet not added.")
            return

    # Score the new bullet
    print("\n⏳  Scoring with Claude…")
    try:
        score = score_bullet(new_bullet)
        print(f"\n  Composite score: {score['composite']}")
        for dim, w in SCORE_WEIGHTS.items():
            print(f"    {dim:28s} {score.get(dim, '?'):5.0f}  (weight {w:.0%})")
        print(f"\n  Rationale: {score.get('rationale', '')}")
        suggestion = score.get("suggested_improvement", "None needed")
        if suggestion and suggestion != "None needed":
            print(f"  💡 Suggested: {suggestion}")
    except Exception as e:
        print(f"  ⚠️  Scoring failed: {e}")
        score = None

    # Confirm save
    save = input("\nSave this bullet? [Y/n] ").strip().lower()
    if save in ("", "y"):
        with open(yf) as f:
            data = yaml.safe_load(f) or {}

        data[key]["bullets"].append({
            "text":   new_bullet,
            "scores": score,
            "added":  str(datetime.today().date()),
            "source": "manual",
        })

        company = role["company"]
        save_yaml(company, data)
        print(f"\n✅  Bullet added to {yf.name}\n")
    else:
        print("Discarded.")


# ---------------------------------------------------------------------------
# PIPELINE INTEGRATION — read/write content/experience/*.yaml (the proper
# experience .yaml files that renderer.py and selector.py actually use).
#
# Pipeline schema (per company file):
#   company, division, logo, roles: [ { id, title, start, end, location,
#     summary, bullets: [ { id, text, families, keywords, tier,
#       [variants], [exclude_from], [sub_bullets] } ] } ]
# ---------------------------------------------------------------------------

def load_pipeline_experience(pipeline_dir: Path | None = None) -> list[dict]:
    """
    Load every content/experience/*.yaml and return a flat list of
    (file_path, company_data, role_index, role_data) tuples, useful for
    menu-style role selection across all companies.

    Uses PIPELINE_EXPERIENCE_DIR at call time (not def time), so tests
    and CLI --pipeline-dir overrides take effect.
    """
    if pipeline_dir is None:
        pipeline_dir = PIPELINE_EXPERIENCE_DIR
    if not pipeline_dir.exists():
        return []
    entries = []
    for yf in sorted(pipeline_dir.glob("*.yaml")):
        with open(yf) as f:
            data = yaml.safe_load(f) or {}
        roles = data.get("roles", []) or []
        for idx, role in enumerate(roles):
            entries.append((yf, data, idx, role))
    return entries


def collect_pipeline_bullet_texts(role: dict) -> list[str]:
    """
    Gather every bullet text (and sub_bullet text) under a pipeline role,
    so dedup sees the whole surface — not just top-level bullets.
    """
    texts: list[str] = []
    for b in role.get("bullets", []) or []:
        t = b.get("text")
        if t:
            texts.append(str(t).strip())
        for sub in b.get("sub_bullets", []) or []:
            st = sub.get("text")
            if st:
                texts.append(str(st).strip())
        # Include variants too — rewording guards
        for v in (b.get("variants") or {}).values():
            if v:
                texts.append(str(v).strip())
    return texts


def slugify_id(text: str, prefix: str | None = None, existing: set | None = None) -> str:
    """
    Turn a bullet text into a snake_case id suitable for the pipeline schema.
    Collisions get _2, _3, ... appended. A prefix (e.g. company short-name)
    is prepended when supplied — matches the pattern used across the repo
    (kano_dbt, kix_wcra_alliance_rec, ea_companion_app_analyticon, …).
    """
    base = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    # Keep it short — first 4 meaningful words
    words = [w for w in base.split("_") if len(w) > 2][:4]
    slug = "_".join(words) or "bullet"
    if prefix:
        slug = f"{prefix}_{slug}"
    existing = existing or set()
    candidate, n = slug, 2
    while candidate in existing:
        candidate = f"{slug}_{n}"
        n += 1
    return candidate


def collect_all_pipeline_ids(pipeline_dir: Path | None = None) -> set[str]:
    """All bullet + sub_bullet ids across the pipeline, for uniqueness."""
    if pipeline_dir is None:
        pipeline_dir = PIPELINE_EXPERIENCE_DIR
    ids: set[str] = set()
    for yf in pipeline_dir.glob("*.yaml"):
        with open(yf) as f:
            data = yaml.safe_load(f) or {}
        for role in data.get("roles", []) or []:
            for b in role.get("bullets", []) or []:
                if "id" in b:
                    ids.add(b["id"])
                for sub in b.get("sub_bullets", []) or []:
                    if "id" in sub:
                        ids.add(sub["id"])
    return ids


def company_id_prefix(yaml_file: Path) -> str:
    """kano.yaml → 'kano', kixeye_sfg.yaml → 'kix_sfg', ea.yaml → 'ea'."""
    stem = yaml_file.stem
    # Common abbreviations the repo already uses
    aliases = {
        "kixeye_sfg": "kix_sfg",
        "kixeye":     "kix",
        "tinymob":    "tmg",
    }
    return aliases.get(stem, stem)


def _format_pipeline_bullet(entry: dict, bullet_indent: str = "      ") -> str:
    """
    Render a new bullet block as text, matching repo conventions:
      - 6-space indent for '- id:'
      - 8-space indent for bullet fields
      - 10-space indent for '> folded scalar' body
      - flow-style sequences for families and keywords
    """
    body = bullet_indent + "  "       # +2 spaces
    fold = body + "  "                 # +4 spaces (folded-scalar content)

    # Wrap the text body to ~65-chars so folded scalars read well in the file
    wrapped = textwrap.wrap(entry["text"], width=65,
                            break_long_words=False, break_on_hyphens=False)
    wrapped_lines = "\n".join(f"{fold}{w}" for w in wrapped)

    fams_flow = "[" + ", ".join(entry["families"]) + "]"

    # Keywords flow-style, wrapped at ~88 chars with continuation-indent
    kw_prefix = f"{body}keywords: ["
    cont = " " * len(kw_prefix)
    kw_line = kw_prefix
    kw_out = []
    for i, k in enumerate(entry["keywords"]):
        token = k + ("," if i < len(entry["keywords"]) - 1 else "")
        candidate = kw_line + (" " if kw_line != kw_prefix else "") + token
        if len(candidate) > 88 and kw_line != kw_prefix:
            kw_out.append(kw_line)
            kw_line = cont + token
        else:
            kw_line = candidate if kw_line == kw_prefix else kw_line + " " + token
    kw_out.append(kw_line + "]")
    kw_block = "\n".join(kw_out)

    lines = [
        f"{bullet_indent}- id: {entry['id']}",
        f"{body}text: >",
        wrapped_lines,
        f"{body}families: {fams_flow}",
        kw_block,
        f"{body}tier: {entry['tier']}",
    ]
    return "\n".join(lines) + "\n"


def _detect_bullet_indent(file_text: str) -> str:
    """
    Infer the bullet-item indent used by this file (usually '      ', 6 spaces).
    Scans for the first line that looks like a bullet entry under a bullets: key.
    """
    for m in re.finditer(r"^(\s+)-\s+id:\s+\w+", file_text, flags=re.MULTILINE):
        indent = m.group(1)
        # Skip role-level ids (shorter indent) — we want bullet-level (>=4 spaces)
        if len(indent) >= 4:
            return indent
    return "      "  # sensible default


def append_bullet_to_pipeline_yaml(yaml_path: Path, role_id: str, entry: dict) -> None:
    """
    Append a new bullet to the named role inside a content/experience/*.yaml
    without round-tripping through yaml.dump (which destroys folded scalars,
    flow-style lists, and blank lines). Pure-text operation that preserves
    the handcrafted style of the surrounding file.
    """
    content = yaml_path.read_text()
    lines = content.splitlines(keepends=True)

    # Find the target role's '- id: <role_id>' line
    role_line_pat = re.compile(rf"^(\s*)-\s+id:\s*{re.escape(role_id)}\b")
    role_start = None
    role_indent = ""
    for i, ln in enumerate(lines):
        m = role_line_pat.match(ln)
        if m:
            role_start = i
            role_indent = m.group(1)
            break
    if role_start is None:
        raise ValueError(f"Role id {role_id!r} not found in {yaml_path}")

    # Find the next role at the same indent (or EOF)
    next_role_pat = re.compile(rf"^{re.escape(role_indent)}-\s+id:")
    role_end = len(lines)
    for i in range(role_start + 1, len(lines)):
        if next_role_pat.match(lines[i]):
            role_end = i
            break

    # Insertion point: last non-blank line within the role block + 1
    insert_at = role_end
    while insert_at > role_start + 1 and lines[insert_at - 1].strip() == "":
        insert_at -= 1

    bullet_indent = _detect_bullet_indent(content)
    block = _format_pipeline_bullet(entry, bullet_indent=bullet_indent)

    # Build the new file content: prior lines, blank separator, new block,
    # then everything that was after insert_at (preserves separators).
    head = lines[:insert_at]
    tail = lines[insert_at:]
    # Ensure head ends with a newline
    if head and not head[-1].endswith("\n"):
        head[-1] = head[-1] + "\n"
    # Blank separator between prior last bullet and the new one
    if head and head[-1].strip() != "":
        head.append("\n")
    new_content = "".join(head) + block
    # Ensure a blank line between new block and the next role (if any tail)
    if tail:
        if not new_content.endswith("\n"):
            new_content += "\n"
        if tail[0].strip() != "":
            new_content += "\n"
        new_content += "".join(tail)

    yaml_path.write_text(new_content)


def cmd_add_pipeline() -> None:
    """
    Interactive: add a new bullet to the PROPER experience YAML
    (content/experience/<company>.yaml) with full pipeline schema
    (id, families, keywords, tier). Dedupes against all existing
    bullets — including sub_bullets and variants — for that role.
    """
    entries = load_pipeline_experience()
    if not entries:
        print(f"No YAML files found under {PIPELINE_EXPERIENCE_DIR}/. "
              "Are you running from the repo root?")
        return

    # Display menu
    print("\n📋  Pipeline roles (content/experience/):\n")
    for i, (yf, company_data, _, role) in enumerate(entries, 1):
        company = company_data.get("company", yf.stem)
        title   = role.get("title", "?")
        period  = f"{role.get('start','?')} → {role.get('end','?')}"
        print(f"  {i:2d}. {company:35s} | {title:45s} | {period}  [{yf.name}]")

    try:
        choice = int(input("\nSelect role number: ").strip()) - 1
        assert 0 <= choice < len(entries)
    except (ValueError, AssertionError):
        print("Invalid selection.")
        return

    yf, company_data, role_idx, role = entries[choice]

    print(f"\n✏️   Adding bullet to:")
    print(f"     {company_data.get('company')} | {role.get('title')}")
    print(f"     File: {yf}\n")

    new_bullet = input("Enter new bullet text:\n> ").strip()
    if not new_bullet:
        print("Empty input — aborting.")
        return

    # Dedupe against every bullet/sub/variant under this role
    existing_texts = collect_pipeline_bullet_texts(role)
    dup, matched = is_duplicate(new_bullet, existing_texts)
    if dup:
        print(f"\n⚠️   Too similar to an existing bullet under this role:")
        print(f"     Existing : {matched}")
        print(f"     New      : {new_bullet}")
        confirm = input("\nAdd anyway? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted — bullet not added.")
            return

    # Score with Claude (optional — continue even if API fails)
    print("\n⏳  Scoring with Claude…")
    score = None
    try:
        score = score_bullet(new_bullet)
        print(f"\n  Composite score: {score['composite']}")
        for dim, w in SCORE_WEIGHTS.items():
            print(f"    {dim:28s} {score.get(dim, '?'):5.0f}  (weight {w:.0%})")
        print(f"\n  Rationale: {score.get('rationale','')}")
        sug = score.get("suggested_improvement", "None needed")
        if sug and sug != "None needed":
            print(f"  💡 Suggested: {sug}")
    except Exception as e:
        print(f"  ⚠️  Scoring unavailable ({e}). Continuing without score.")

    # Families (required by pipeline schema)
    print(f"\n  Valid families: {sorted(VALID_FAMILIES)}")
    fam_raw = input("  Families (comma-separated, e.g. DS,DA,AE): ").strip().upper()
    families = [f.strip() for f in re.split(r"[,\s]+", fam_raw) if f.strip()]
    bad = [f for f in families if f not in VALID_FAMILIES]
    if bad:
        print(f"  ⚠️  Unknown family id(s): {bad}")
        print(f"  Aborting — fix family ids and retry.")
        return
    if not families:
        print("  ⚠️  At least one family is required by the pipeline schema.")
        return

    # Tier (required)
    try:
        tier = int(input("  Tier [1=headline, 2=supporting, 3=contextual]: ").strip())
        assert tier in (1, 2, 3)
    except (ValueError, AssertionError):
        print("  ⚠️  Tier must be 1, 2, or 3 — aborting.")
        return

    # Keywords (required, ATS terms)
    kw_raw = input("  Keywords (comma-separated): ").strip()
    keywords = [k.strip() for k in kw_raw.split(",") if k.strip()]
    if not keywords:
        print("  ⚠️  At least one keyword is recommended for ATS targeting.")

    # Generate an id that doesn't collide with anything else in the pipeline
    existing_ids = collect_all_pipeline_ids()
    prefix = company_id_prefix(yf)
    new_id = slugify_id(new_bullet, prefix=prefix, existing=existing_ids)

    # Confirm before writing
    print("\n— Preview —")
    print(f"  file:     {yf}")
    print(f"  role:     {role.get('title')} ({role.get('start')} → {role.get('end')})")
    print(f"  id:       {new_id}")
    print(f"  families: {families}")
    print(f"  tier:     {tier}")
    print(f"  keywords: {keywords}")
    print(f"  text:     {new_bullet}")
    go = input("\nWrite to pipeline YAML? [Y/n] ").strip().lower()
    if go not in ("", "y"):
        print("Discarded.")
        return

    # Append the new bullet WITHOUT roundtripping through yaml.dump —
    # that flattens folded scalars, flow-style lists, and blank lines,
    # all of which are load-bearing for Alex's hand-maintained files.
    bullet_entry = {
        "id":       new_id,
        "text":     new_bullet,
        "families": families,
        "keywords": keywords,
        "tier":     tier,
    }
    role_id = role.get("id")
    if not role_id:
        print("  ⚠️  Role missing an 'id' field — cannot locate insert point.")
        return
    try:
        append_bullet_to_pipeline_yaml(yf, role_id, bullet_entry)
    except Exception as e:
        print(f"  ✗ Could not write bullet: {e}")
        return
    print(f"\n✅  Bullet '{new_id}' written to {yf}")
    print(f"   Next step: `make validate` to confirm integrity, then rebuild families.\n")


# ---------------------------------------------------------------------------
# REPORT: export scored summary to stdout (or file)
# ---------------------------------------------------------------------------

def cmd_report(output_file: str | None = None) -> None:
    """Write a full ranked report to stdout or a file."""
    lines = ["RESUME BULLET SCORECARD", "=" * 80, ""]
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Scoring weights: { {k: f'{v:.0%}' for k,v in SCORE_WEIGHTS.items()} }")
    lines.append("")

    yaml_files = sorted(YAML_DIR.glob("*.yaml"))
    if not yaml_files:
        print("No YAML files found. Run --init first.")
        return

    for yf in yaml_files:
        with open(yf) as f:
            data = yaml.safe_load(f) or {}

        for key, role in data.items():
            bullets = sorted(
                role["bullets"],
                key=lambda b: (b.get("scores") or {}).get("composite", 0),
                reverse=True,
            )
            scored   = [b for b in bullets if b.get("scores")]
            avg      = (sum(b["scores"]["composite"] for b in scored) / len(scored)
                        if scored else 0)
            top3_avg = (sum(b["scores"]["composite"] for b in scored[:3]) / min(3, len(scored))
                        if scored else 0)

            lines.append(f"\n{'─'*80}")
            lines.append(f"  COMPANY : {role['company']}")
            lines.append(f"  ROLE    : {role['title']}")
            lines.append(f"  PERIOD  : {role['period']}")
            lines.append(f"  STATS   : {len(bullets)} bullets | avg {avg:.1f} | top-3 avg {top3_avg:.1f}")
            lines.append(f"{'─'*80}")

            for rank, b in enumerate(bullets, 1):
                s = b.get("scores") or {}
                c = s.get("composite", "?")
                flag = "★★" if isinstance(c, float) and c >= 85 else (
                       "★ " if isinstance(c, float) and c >= 70 else "  ")
                lines.append(f"\n  {flag} #{rank:2d}  composite={c}")
                if s:
                    dim_line = "  ".join(
                        f"{k[:4].upper()}={s.get(k,'?'):4.0f}"
                        for k in SCORE_WEIGHTS
                    )
                    lines.append(f"       {dim_line}")
                wrapped = textwrap.fill(b["text"], width=88,
                                        initial_indent="       ",
                                        subsequent_indent="       ")
                lines.append(wrapped)
                if s.get("rationale"):
                    lines.append(f"       → {s['rationale']}")
                sug = s.get("suggested_improvement", "None needed")
                if sug and sug != "None needed":
                    lines.append(f"       💡 {sug}")

    text = "\n".join(lines)
    if output_file:
        Path(output_file).write_text(text)
        print(f"Report written to {output_file}")
    else:
        print(text)


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resume Bullet Manager — parse, score, rank, and extend experience bullets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Workflow:
              1a. python resume_bullet_manager.py --init              # Import .tex → scoring workbench
              1b. python resume_bullet_manager.py --pdf resume.pdf    # Import PDF → scoring workbench
              2.  python resume_bullet_manager.py --score             # Score all bullets
              3.  python resume_bullet_manager.py --show              # View ranked bullets
              4.  python resume_bullet_manager.py --add               # Add to scoring workbench
              5.  python resume_bullet_manager.py --add-pipeline      # Add to content/experience/*.yaml
              6.  python resume_bullet_manager.py --report            # Export full report

            --add-pipeline writes directly to the pipeline's 'proper' experience YAML
            (content/experience/*.yaml) with the full schema (id, families, keywords,
            tier), and dedupes against every bullet/sub_bullet/variant under the role.
        """),
    )
    parser.add_argument("--tex-dir",       default=".",        help="Directory containing .tex files (default: .)")
    parser.add_argument("--yaml-dir",      default="experience_yaml", help="Scoring workbench dir (default: experience_yaml)")
    parser.add_argument("--pipeline-dir",  default="content/experience", help="Pipeline experience dir (default: content/experience)")
    parser.add_argument("--init",          action="store_true", help="Parse .tex files and write scoring workbench")
    parser.add_argument("--pdf",           default=None,        metavar="FILE",
                        help="Path to a PDF resume to parse and import into YAML")
    parser.add_argument("--score",         action="store_true", help="Score un-scored bullets via Claude")
    parser.add_argument("--show",          action="store_true", help="Print ranked bullets to terminal")
    parser.add_argument("--add",           action="store_true", help="Interactively add a bullet to the scoring workbench")
    parser.add_argument("--add-pipeline",  action="store_true", help="Interactively add a bullet to content/experience/*.yaml")
    parser.add_argument("--report",        action="store_true", help="Write full scorecard report")
    parser.add_argument("--out",           default=None,        help="Output file for --report")
    args = parser.parse_args()

    global YAML_DIR, PIPELINE_EXPERIENCE_DIR
    YAML_DIR = Path(args.yaml_dir)
    PIPELINE_EXPERIENCE_DIR = Path(args.pipeline_dir)
    tex_dir  = Path(args.tex_dir)

    if not any([args.init, args.pdf, args.score, args.show, args.add,
                args.add_pipeline, args.report]):
        parser.print_help()
        sys.exit(0)

    if args.init:
        cmd_init(tex_dir)
    if args.pdf:
        cmd_init_pdf(Path(args.pdf))
    if args.score:
        cmd_score(tex_dir)
    if args.show:
        cmd_show()
    if args.add:
        cmd_add()
    if args.add_pipeline:
        cmd_add_pipeline()
    if args.report:
        cmd_report(args.out)


if __name__ == "__main__":
    main()
