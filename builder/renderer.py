"""
builder/renderer.py
===================
Renders the Jinja2 LaTeX template using the fully resolved, selected,
and (optionally) revoiced data from the pipeline.

The renderer is deliberately thin — it passes clean data to the template,
writes the output .tex file, and stages any LaTeX assets (cv-style.cls,
fonts/) that XeLaTeX needs to find when compiling from the output directory.
"""

import shutil
from pathlib import Path
import re

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from builder.selector import select_skills, select_aside_skills


# ---------------------------------------------------------------------------
# LaTeX special-character escaping
# ---------------------------------------------------------------------------

_LATEX_SPECIAL = {
    "&":  r"\&",
    "%":  r"\%",
    "$":  r"\$",
    "#":  r"\#",
    "_":  r"\_",
    "{":  r"\{",
    "}":  r"\}",
    "~":  r"\textasciitilde{}",
    "^":  r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}


def _latex_escape(text: str) -> str:
    """
    Escape LaTeX special characters in user-supplied text fields.
    Applied via Jinja2 filter: << bullet.resolved_text | latex_escape >>
    """
    pattern = re.compile(
        "|".join(re.escape(k) for k in sorted(_LATEX_SPECIAL, key=len, reverse=True))
    )
    return pattern.sub(lambda m: _LATEX_SPECIAL[m.group()], text)


# ---------------------------------------------------------------------------
# Asset staging
# ---------------------------------------------------------------------------

def _stage_assets(output_dir: Path, repo_root: Path,
                  cls_names: tuple[str, ...] = ("cv-style.cls",)) -> None:
    """
    Copy the requested LaTeX class file(s) into the output directory so XeLaTeX
    can find them regardless of how the .tex file is compiled (build.py, IDE,
    direct xelatex invocation). The fonts/ directory is also symlinked/copied
    for the same reason.

    This is intentionally belt-and-suspenders: build.py also sets
    TEXINPUTS, but any editor or manual xelatex call will work too.

    cls_names — which .cls file(s) to stage. Defaults to ("cv-style.cls",)
                for backwards compatibility. The ATS template uses
                ("cv-style-ats.cls",).
    """
    for cls_name in cls_names:
        cls_src = repo_root / cls_name
        cls_dst = output_dir / cls_name
        if cls_src.exists() and not cls_dst.exists():
            shutil.copy2(cls_src, cls_dst)

    # fonts/ — required by \newfontfamily calls in cv-style.cls
    fonts_src = repo_root / "fonts"
    fonts_dst = output_dir / "fonts"
    if fonts_src.exists():
        # Skip if destination already exists and resolves correctly.
        if fonts_dst.exists():
            pass  # Already in place (real dir or working symlink)
        else:
            # A broken symlink has .exists() == False but .is_symlink() == True.
            # Try to unlink it so we can lay down a fresh link or copy.
            if fonts_dst.is_symlink():
                try:
                    fonts_dst.unlink()
                except (OSError, PermissionError):
                    pass  # Some environments (sandboxes) disallow unlink
            # Only proceed if the destination still doesn't exist after cleanup
            if not fonts_dst.exists() and not fonts_dst.is_symlink():
                try:
                    fonts_dst.symlink_to(fonts_src.resolve())
                except (OSError, NotImplementedError):
                    # Symlinks unavailable (e.g. Windows, sandboxes) — copy
                    shutil.copytree(fonts_src, fonts_dst)


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def _apply_education_mode(education_entries: list[dict],
                          family: dict,
                          mode: str) -> list[dict]:
    """
    Apply education display mode to the education entries.

    Modes:
      "full"      — return entries unchanged (current behaviour).
      "condensed" — drop entries whose relevant_families doesn't include
                    this family, then trim each remaining entry's
                    `accomplishments` to the indices listed in
                    `entry["condensed"][FAMILY_ID]`. Special value "all"
                    keeps every accomplishment. Missing/empty list = no
                    accomplishments shown (focus, thesis_url, dates,
                    institution, degree are always preserved).
    """
    if mode == "full":
        return education_entries

    fam_id = family["id"]
    out: list[dict] = []
    for entry in education_entries:
        rel = entry.get("relevant_families")
        # If relevant_families is set and excludes this family, drop entry
        if rel and fam_id not in rel:
            continue

        condensed_map = entry.get("condensed", {}) or {}
        keep = condensed_map.get(fam_id, [])  # default = drop all accomplishments

        accomplishments = entry.get("accomplishments", []) or []
        if keep == "all":
            kept = accomplishments
        elif isinstance(keep, list):
            kept = [accomplishments[i] for i in keep if 0 <= i < len(accomplishments)]
        else:
            kept = []

        # Shallow copy so we don't mutate the loaded data
        new_entry = {**entry, "accomplishments": kept}
        out.append(new_entry)
    return out


# ---------------------------------------------------------------------------
# ATS template helpers — skills-table grouping + keyword tagline
# ---------------------------------------------------------------------------

# Default-grouping labels for when a family doesn't define ats_skills_groups.
# Keys match keys in skills.yaml::data_engineering.<subcategory>.
_ATS_DE_LABELS = {
    "modelling_and_transformation":  "Data Modeling & Transformation",
    "storage_and_warehousing":       "Storage & Warehousing",
    "orchestration":                 "Pipeline & Orchestration",
    "streaming_and_ingestion":       "Streaming & Ingestion",
    "data_processing":               "Data Processing",
    "bi_tools":                      "BI & Delivery",
    "hosting_and_infrastructure":    "DevOps / Infrastructure",
    "file_formats":                  "File Formats",
}


def _compose_ats_skills_groups(skills: dict, family: dict,
                                ordered_skills: dict) -> list[dict]:
    """
    Build the list of `{label, items_text}` rows that populate the ATS
    "Technical Skills" table.

    Precedence:
      1. `family.ats_skills_groups` — explicit override, used as-is. Each
         entry is `{label, items: [...skill display names...]}`. Items are
         passed through verbatim — they're treated as display strings, not
         lookups, so family files can include human-readable phrases that
         aren't strict skills.yaml entries (e.g. "LTV forecasting,
         AppsFlyer, A/B experimentation" for a Marketing Analytics group).
      2. Derived from `ordered_skills` (output of select_skills) — grouped
         by skills.yaml category. Programming → "Languages",
         data_engineering subcats → human labels via _ATS_DE_LABELS,
         data_science → "Data Science".

    The renderer never silently drops a non-empty override group — an
    empty `items` list is still rendered as a row, in case the family
    wants the label present for ATS keyword density even without items.
    """
    explicit = family.get("ats_skills_groups")
    if explicit:
        out: list[dict] = []
        for grp in explicit:
            items = grp.get("items", []) or []
            out.append({
                "label":      grp["label"],
                "items_text": ", ".join(items),
            })
        return out

    out = []
    if ordered_skills.get("programming"):
        out.append({
            "label":      "Languages",
            "items_text": ", ".join(s["name"] for s in ordered_skills["programming"]),
        })
    if ordered_skills.get("data_science"):
        out.append({
            "label":      "Data Science",
            "items_text": ", ".join(s["name"] for s in ordered_skills["data_science"]),
        })
    de = ordered_skills.get("data_engineering") or {}
    for cat_key, items in de.items():
        if not items:
            continue
        label = _ATS_DE_LABELS.get(cat_key, cat_key.replace("_", " ").title())
        out.append({
            "label":      label,
            "items_text": ", ".join(s["name"] for s in items),
        })
    return out


# ---------------------------------------------------------------------------
# Header-location composer — encodes work-eligibility + relocation context
# into the location field of the header (used by both templates).
# ---------------------------------------------------------------------------

# Default cities per location mode. The recruiter's first-instinct relocation
# guess from Victoria, BC is Vancouver for Canadian roles and Seattle for US
# roles (closest major tech hubs + Alex's relocation comfort zones).
_DEFAULT_RELOCATION_CITY: dict[str, str] = {
    "relocate": "Vancouver",
    "us":       "Seattle",
}

# Unicode middle dot — renders natively under XeLaTeX with the Roboto fonts
# included in this repo. Kept as a constant so the separator is consistent
# across both templates and easy to swap later (e.g. to "•" or "|").
_LOC_SEP = " · "  # " · "


def _compose_header_location(personal: dict,
                              location_mode: str = "default",
                              relocation_city: str | None = None) -> str:
    """
    Build the location string that drops into the header's location slot.

    Modes:
      "default"  — `Victoria, BC.`
                   The base `personal.location` with a trailing period (if
                   not already present). Used for jobs at or near the home
                   base — no relocation or work-eligibility signal needed.
      "relocate" — `Victoria, BC · Open to Relocation (Vancouver)`
                   Adds an explicit relocation clause. City defaults to
                   "Vancouver" — typical recruiter shorthand for "this
                   candidate would move within Canada." Override via
                   `--relocation-city`.
      "us"       — `Victoria, BC · US Citizen & Canadian PR · Open to Relocation (Seattle)`
                   Adds work-eligibility signal for US recruiters scanning
                   resumes from non-US locations. City defaults to "Seattle"
                   — closest major US tech hub.

    The returned string is plain text. The template applies `latex_escape`
    so `&` and other LaTeX specials are handled at render time.
    """
    if location_mode not in ("default", "relocate", "us"):
        raise ValueError(
            f"Invalid location_mode: {location_mode!r}. "
            f"Valid options: default, relocate, us"
        )

    base = (personal.get("location") or "").rstrip(".").rstrip()
    if not base:
        return ""

    if location_mode == "default":
        return f"{base}."

    city = relocation_city or _DEFAULT_RELOCATION_CITY[location_mode]
    pieces: list[str] = [base]
    if location_mode == "us":
        pieces.append("US Citizen & Canadian PR")
    pieces.append(f"Open to Relocation ({city})")
    return _LOC_SEP.join(pieces)


def _compose_ats_tagline(family: dict) -> str:
    """
    Return the keyword tagline that renders directly under the subtitle line
    in the navy header band.

    Precedence:
      1. `family.ats_tagline` — explicit LaTeX-ready string from the family file.
         Treated as raw LaTeX (not escaped) so the family can include macros.
      2. Derived from `family.ats_keyword_watchlist[:6]`, joined with
         `\\textbullet`. Each keyword is latex-escaped individually.
      3. Empty string when neither is defined.
    """
    if family.get("ats_tagline"):
        return family["ats_tagline"]

    keywords = (family.get("ats_keyword_watchlist") or [])[:6]
    if not keywords:
        return ""
    escaped = [_latex_escape(k) for k in keywords]
    return r" \textbullet\ ".join(escaped)


def _select_certifications(certifications: list[dict],
                           family: dict,
                           edu_config: dict) -> list[dict]:
    """
    Filter the certifications list according to family rules.

    Precedence:
      1. Explicit allowlist `family.education.certifications_to_show: [id, ...]`
         picks specific cert ids in order.
      2. Else, drop any cert whose `relevant_families` doesn't include this
         family (or has no `relevant_families` field — fall through unchanged).
    """
    show_certs = edu_config.get("certifications_to_show", None)
    if show_certs is not None:
        # Preserve the order specified by the family file
        cert_by_id = {c["id"]: c for c in certifications}
        return [cert_by_id[cid] for cid in show_certs if cid in cert_by_id]

    fam_id = family["id"]
    out: list[dict] = []
    for c in certifications:
        rel = c.get("relevant_families")
        if rel and fam_id not in rel:
            continue
        out.append(c)
    return out


# ---------------------------------------------------------------------------
# Template registry — maps the --template flag to (jinja file, .cls staged)
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, dict[str, str]] = {
    "standard": {
        "jinja":  "resume.tex.j2",
        "cls":    "cv-style.cls",
    },
    "ats": {
        "jinja":  "resume-ats.tex.j2",
        "cls":    "cv-style-ats.cls",
    },
}


def render_tex(family: dict,
               resolved_experience: list[dict],
               skills: dict,
               education: dict,
               summary: dict,
               personal: dict,
               output_dir: Path,
               template_dir: Path,
               repo_root: Path,
               education_mode: str | None = None,
               certs_placement: str | None = None,
               industry: str = "agnostic",
               posting_text: str | None = None,
               template: str = "standard",
               location_mode: str = "default",
               relocation_city: str | None = None) -> Path:
    """
    Render resume.tex.j2 with all pipeline data and write to output_dir.
    Stages cv-style.cls and fonts/ alongside the .tex so any compiler works.
    Returns the path to the generated .tex file.

    education_mode  — "full" | "condensed". If None, fall back to
                      family.education.mode (default: "full").
    certs_placement — "education" | "aside" | "omit". If None, fall back to
                      family.education.certifications_placement (default:
                      "education"). "aside" passes certifications into a
                      separate `certifications_aside` template variable so
                      they can render in the page-3 sidebar instead.
    industry        — "games" | "agnostic". When "games", the games_text
                      summary variant is used if available, and aside skills
                      are rendered with games-friendly framing.
    posting_text    — Job posting text used to reorder aside skill sections
                      by posting relevance.
    template        — "standard" | "ats". "standard" renders the
                      two-column layout via templates/resume.tex.j2 +
                      cv-style.cls (default). "ats" renders the single-
                      column ATS-friendly layout via
                      templates/resume-ats.tex.j2 + cv-style-ats.cls.
                      The ATS layout adds new context variables
                      `ats_skills_groups`, `ats_tagline`, and
                      `impact_metrics` (all optional, with sensible
                      fallbacks derived from existing family fields).
    location_mode   — "default" | "relocate" | "us". Controls what goes in
                      the header's location slot. "default" shows just
                      `personal.location` with a trailing period; "relocate"
                      appends an "Open to Relocation (<city>)" clause;
                      "us" additionally inserts "US Citizen & Canadian PR"
                      to signal work eligibility to US recruiters. See
                      _compose_header_location for the exact format.
    relocation_city — City name for the "Open to Relocation" clause when
                      location_mode is "relocate" or "us". Defaults to
                      "Vancouver" (relocate) or "Seattle" (us) when None.
                      Ignored when location_mode is "default".
    """
    if template not in _TEMPLATES:
        raise ValueError(
            f"Invalid template: {template!r}. "
            f"Valid options: {sorted(_TEMPLATES)}"
        )
    tmpl_cfg = _TEMPLATES[template]
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<#",
        comment_end_string="#>",
    )

    env.filters["latex_escape"] = _latex_escape

    ordered_skills = select_skills(skills, family)

    # Resolve aside skills for pg2 sidebar — reordered by posting relevance
    # when a posting is provided.
    raw_aside_skills = family.get("aside_skills")
    aside_skills = select_aside_skills(raw_aside_skills, posting_text)

    # Choose summary text: games variant when industry="games" and available.
    if industry == "games" and summary.get("games_text"):
        summary_text = summary["games_text"]
    else:
        summary_text = summary["text"]

    edu_config = family.get("education", {})

    # Resolve education_mode and certs_placement: CLI argument wins, family
    # default is the fallback, then the hard-coded default.
    if education_mode is None:
        education_mode = edu_config.get("mode", "full")
    if certs_placement is None:
        certs_placement = edu_config.get("certifications_placement", "education")

    if education_mode not in ("full", "condensed"):
        raise ValueError(f"Invalid education_mode: {education_mode!r}")
    if certs_placement not in ("education", "aside", "omit"):
        raise ValueError(f"Invalid certs_placement: {certs_placement!r}")

    education_to_show = _apply_education_mode(
        education["education"], family, education_mode
    )
    selected_certs    = _select_certifications(
        education["certifications"], family, edu_config
    )

    # Route certs to the right template slot based on placement.
    if certs_placement == "omit":
        certs_inline = []
        certs_aside  = []
    elif certs_placement == "aside":
        certs_inline = []
        certs_aside  = selected_certs
    else:  # "education"
        certs_inline = selected_certs
        certs_aside  = []

    # ATS-template-only context: composed here so they're cheap no-ops when
    # the standard template renders (Jinja2 ignores unused keys).
    ats_skills_groups = _compose_ats_skills_groups(skills, family, ordered_skills)
    ats_tagline       = _compose_ats_tagline(family)
    impact_metrics    = family.get("impact_metrics") or []

    # Header location — applied to both templates. Encodes work-eligibility
    # and relocation context (defaults to a plain "Victoria, BC.").
    header_location   = _compose_header_location(
        personal["personal"], location_mode, relocation_city,
    )

    context = {
        "family":               family,
        "personal":             personal["personal"],
        "summary_text":         summary_text,
        "experience":           resolved_experience,
        "skills":               ordered_skills,
        "aside_skills":         aside_skills,
        "education":            education_to_show,
        "education_mode":       education_mode,
        "certifications":       certs_inline,
        "certifications_aside": certs_aside,
        "certs_placement":      certs_placement,
        "header_title":         family["header_title"],
        "header_location":      header_location,
        "location_mode":        location_mode,
        "industry":             industry,
        "template":             template,
        # ATS-template context (harmless to the standard template)
        "ats_skills_groups":    ats_skills_groups,
        "ats_tagline":          ats_tagline,
        "impact_metrics":       impact_metrics,
        # Forward-slash path for LaTeX compatibility on all platforms
        "assets_root":          str(repo_root).replace("\\", "/"),
    }

    jinja_tmpl = env.get_template(tmpl_cfg["jinja"])
    rendered   = jinja_tmpl.render(**context)

    # Per-template output filename suffix — keeps both layouts side-by-side
    # in the same output directory rather than overwriting each other.
    family_id = family["id"].lower()
    if template == "ats":
        tex_path = output_dir / f"resume_{family_id}_ats.tex"
    else:
        tex_path = output_dir / f"resume_{family_id}.tex"

    output_dir.mkdir(parents=True, exist_ok=True)
    tex_path.write_text(rendered, encoding="utf-8")

    # Stage the right .cls file (and fonts/) next to the .tex so any compiler
    # finds them. We stage both classes when the standard template is used so
    # an ATS build that lands in the same directory later doesn't need a
    # re-stage; conversely, for an ATS build only the ATS class is needed.
    cls_files: tuple[str, ...] = (tmpl_cfg["cls"],)
    if template == "standard":
        cls_files = ("cv-style.cls",)
    _stage_assets(output_dir, repo_root, cls_names=cls_files)

    return tex_path