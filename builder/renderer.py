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

from builder.selector import select_skills, select_domain_knowledge


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

def render_tex(family: dict,
               resolved_experience: list[dict],
               skills: dict,
               education: dict,
               summary: dict,
               personal: dict,
               output_dir: Path,
               template_dir: Path,
               repo_root: Path,
               gaming: bool = False) -> Path:
    """
    Render resume.tex.j2 with all pipeline data and write to output_dir.
    Stages cv-style.cls and fonts/ alongside the .tex so any compiler works.

    gaming=True injects the gaming-specific domain_knowledge skill groups
    (DA/DS/AE only); otherwise that section is omitted.

    Returns the path to the generated .tex file.
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

    ordered_skills    = select_skills(skills, family)
    domain_knowledge  = select_domain_knowledge(skills, family, gaming)

    edu_config   = family.get("education", {})
    show_certs   = edu_config.get("certifications_to_show", None)
    all_certs    = education["certifications"]
    certs_to_show = (
        [c for c in all_certs if c["id"] in show_certs]
        if show_certs is not None else all_certs
    )
    # "detailed" (default) shows focus + accomplishments; "compact" emits a
    # tight degree/institution strip. Set per family via education.layout.
    education_layout = edu_config.get("layout", "detailed")

    context = {
        "family":          family,
        "personal":        personal["personal"],
        "summary_text":    summary["text"],
        "experience":      resolved_experience,
        "skills":          ordered_skills,
        "domain_knowledge": domain_knowledge,
        "education":       education["education"],
        "education_layout": education_layout,
        "certifications":  certs_to_show,
        "header_title":    family["header_title"],
        # Forward-slash path for LaTeX compatibility on all platforms
        "assets_root":     str(repo_root).replace("\\", "/"),
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