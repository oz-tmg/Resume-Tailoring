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

from builder.selector import select_skills


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

def _stage_assets(output_dir: Path, repo_root: Path) -> None:
    """
    Copy cv-style.cls into the output directory so XeLaTeX can find it
    regardless of how the .tex file is compiled (build.py, IDE, direct
    xelatex invocation).  The fonts/ directory is also symlinked/copied
    for the same reason.

    This is intentionally belt-and-suspenders: build.py also sets
    TEXINPUTS, but any editor or manual xelatex call will work too.
    """
    # cv-style.cls — required by \documentclass[]{cv-style}
    cls_src = repo_root / "cv-style.cls"
    cls_dst = output_dir / "cv-style.cls"
    if cls_src.exists() and not cls_dst.exists():
        shutil.copy2(cls_src, cls_dst)

    # fonts/ — required by \newfontfamily calls in cv-style.cls
    fonts_src = repo_root / "fonts"
    fonts_dst = output_dir / "fonts"
    if fonts_src.exists() and not fonts_dst.exists():
        try:
            fonts_dst.symlink_to(fonts_src.resolve())
        except (OSError, NotImplementedError):
            # Symlinks unavailable (e.g. some Windows configs) — copy instead
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
               certs_placement: str | None = None) -> Path:
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
    """
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

    context = {
        "family":               family,
        "personal":             personal["personal"],
        "summary_text":         summary["text"],
        "experience":           resolved_experience,
        "skills":               ordered_skills,
        "education":            education_to_show,
        "education_mode":       education_mode,
        "certifications":       certs_inline,
        "certifications_aside": certs_aside,
        "certs_placement":      certs_placement,
        "header_title":         family["header_title"],
        # Forward-slash path for LaTeX compatibility on all platforms
        "assets_root":          str(repo_root).replace("\\", "/"),
    }

    template  = env.get_template("resume.tex.j2")
    rendered  = template.render(**context)

    family_id = family["id"].lower()
    tex_path  = output_dir / f"resume_{family_id}.tex"

    output_dir.mkdir(parents=True, exist_ok=True)
    tex_path.write_text(rendered, encoding="utf-8")

    # Stage cv-style.cls and fonts/ next to the .tex so any compiler finds them
    _stage_assets(output_dir, repo_root)

    return tex_path