#!/usr/bin/env python3
"""
resume-builder/build.py
=======================
Orchestrates resume generation for a given job family and optional
job posting. Produces a tailored .tex file ready to compile.

Usage
-----
  # Generate a base family resume (no posting)
  python build.py --family data_scientist

  # Generate a posting-tailored resume
  python build.py --family data_scientist --posting postings/acme_ds/posting.txt

  # Generate all six family base resumes at once
  python build.py --all

  # Validate YAML content without building
  python build.py --validate
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Load .env before anything else so ANTHROPIC_API_KEY is available
# to the anthropic client in ranker.py
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed — env vars must be set manually

from builder.loader   import load_family, load_all_experience, load_skills, \
                             load_education, load_summaries, load_personal
from builder.selector import select_bullets
from builder.resolver import resolve_bullets
from builder.ranker   import rank_and_revoice
from builder.renderer import render_tex
from builder.validator import validate_all


ROOT     = Path(__file__).parent
FAMILIES = ["data_analyst", "analytics_engineer", "data_engineer",
            "data_scientist", "ml_engineer", "economist"]


def build(family_name: str, posting_path: Path | None = None,
          output_dir: Path | None = None) -> Path:
    """
    Full build pipeline for one family + optional posting.
    Returns the path of the generated .tex file.
    """
    print(f"\n{'='*60}")
    print(f"  Building: {family_name}" +
          (f"  |  Posting: {posting_path.name}" if posting_path else "  |  Base resume"))
    print(f"{'='*60}")

    # ------------------------------------------------------------------
    # 1. Load all source data
    # ------------------------------------------------------------------
    print("  [1/5] Loading content...")
    family     = load_family(ROOT / "families" / f"{family_name}.yaml")
    experience = load_all_experience(ROOT / "content" / "experience")
    skills     = load_skills(ROOT / "content" / "skills.yaml")
    education  = load_education(ROOT / "content" / "education.yaml")
    summaries  = load_summaries(ROOT / "content" / "summaries.yaml")
    personal   = load_personal(ROOT / "content" / "personal.yaml")
    summary    = summaries[family["summary_ref"]]

    # ------------------------------------------------------------------
    # 2. Select bullets per family rules
    # ------------------------------------------------------------------
    print("  [2/5] Selecting bullets...")
    selected = select_bullets(experience, family)

    # ------------------------------------------------------------------
    # 3. Resolve variants — swap base text for pre-written family variant
    #    where one exists. This happens before Claude revoicing so Claude
    #    only revoices bullets that don't already have a curated variant.
    # ------------------------------------------------------------------
    print("  [3/5] Resolving variants...")
    resolved = resolve_bullets(selected, family["id"])

    # ------------------------------------------------------------------
    # 4. Posting-specific ranking and revoicing (Claude API)
    # ------------------------------------------------------------------
    if posting_path:
        print("  [4/5] Ranking and revoicing against posting...")
        posting_text = posting_path.read_text()
        resolved = rank_and_revoice(resolved, posting_text, family)
    else:
        print("  [4/5] Skipping posting tailoring (no posting provided).")

    # ------------------------------------------------------------------
    # 5. Render to .tex
    # ------------------------------------------------------------------
    print("  [5/5] Rendering .tex...")
    if output_dir is None:
        if posting_path:
            output_dir = posting_path.parent / "output"
        else:
            output_dir = ROOT / "output" / family_name
    output_dir.mkdir(parents=True, exist_ok=True)

    tex_path = render_tex(
        family=family,
        resolved_experience=resolved,
        skills=skills,
        education=education,
        summary=summary,
        personal=personal,
        output_dir=output_dir,
        template_dir=ROOT / "templates",
    )

    print(f"\n  ✓ Generated: {tex_path}")
    return tex_path


def compile_pdf(tex_path: Path) -> Path:
    """Run latexmk to compile .tex → PDF."""
    pdf_path = tex_path.with_suffix(".pdf")
    print(f"  Compiling PDF: {pdf_path.name}...")
    result = subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", str(tex_path)],
        cwd=tex_path.parent,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("  ✗ LaTeX compilation failed. Log:")
        print(result.stdout[-3000:])   # tail of log is most useful
        sys.exit(1)
    print(f"  ✓ PDF ready: {pdf_path}")
    return pdf_path


def main():
    parser = argparse.ArgumentParser(description="Resume builder")
    parser.add_argument("--family",  choices=FAMILIES,
                        help="Job family to build")
    parser.add_argument("--posting", type=Path,
                        help="Path to job posting .txt file")
    parser.add_argument("--output",  type=Path,
                        help="Override output directory")
    parser.add_argument("--pdf",     action="store_true",
                        help="Compile .tex to PDF after generation")
    parser.add_argument("--all",     action="store_true",
                        help="Build base resumes for all six families")
    parser.add_argument("--validate", action="store_true",
                        help="Validate YAML content only, do not build")
    args = parser.parse_args()

    if args.validate:
        validate_all(ROOT)
        return

    # Guard: personal.yaml must exist (it's gitignored — easy to forget)
    personal_path = ROOT / "content" / "personal.yaml"
    if not personal_path.exists():
        print("\n  ✗ content/personal.yaml not found.")
        print("    Copy content/personal.yaml.example → content/personal.yaml")
        print("    and fill in your details.\n")
        sys.exit(1)

    if args.all:
        for fam in FAMILIES:
            tex = build(fam)
            if args.pdf:
                compile_pdf(tex)
        return

    if not args.family:
        parser.error("--family is required unless using --all or --validate")

    posting = Path(args.posting) if args.posting else None
    tex = build(args.family, posting_path=posting, output_dir=args.output)

    if args.pdf:
        compile_pdf(tex)


if __name__ == "__main__":
    main()
