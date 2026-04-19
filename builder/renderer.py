"""
builder/renderer.py
===================
Renders the Jinja2 LaTeX template using the fully resolved, selected,
and (optionally) revoiced data from the pipeline.

The renderer is deliberately thin — it just passes clean data to the
template and writes the output file. All logic lives upstream.
"""

from pathlib import Path
import re

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from builder.selector import select_skills


def render_tex(family: dict,
               resolved_experience: list[dict],
               skills: dict,
               education: dict,
               summary: dict,
               personal: dict,
               output_dir: Path,
               template_dir: Path) -> Path:
    """
    Render resume.tex.j2 with all pipeline data and write to output_dir.
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
        # Keep LaTeX-native {{ }} free for use in LaTeX source
    )

    # Register a helper to escape special LaTeX characters in text fields
    env.filters["latex_escape"] = _latex_escape

    ordered_skills = select_skills(skills, family)

    # Determine which education entries and certs to show
    edu_config   = family.get("education", {})
    show_certs   = edu_config.get("certifications_to_show", None)  # None = show all
    all_certs    = education["certifications"]
    certs_to_show = (
        [c for c in all_certs if c["id"] in show_certs]
        if show_certs is not None else all_certs
    )

    context = {
        "family":          family,
        "personal":        personal["personal"],
        "summary_text":    summary["text"],
        "experience":      resolved_experience,
        "skills":          ordered_skills,
        "education":       education["education"],
        "certifications":  certs_to_show,
        "header_title":    family["header_title"],
    }

    template = env.get_template("resume.tex.j2")
    rendered = template.render(**context)

    # Output filename: resume_<family_id>.tex
    out_path = output_dir / f"resume_{family['id'].lower()}.tex"
    out_path.write_text(rendered, encoding="utf-8")

    return out_path


# ---------------------------------------------------------------------------
# LaTeX escaping
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
    Escape special LaTeX characters in dynamic text fields.
    Applied via Jinja2 filter: << bullet.resolved_text | latex_escape >>
    """
    pattern = re.compile(
        "|".join(re.escape(k) for k in sorted(_LATEX_SPECIAL, key=len, reverse=True))
    )
    return pattern.sub(lambda m: _LATEX_SPECIAL[m.group()], text)
