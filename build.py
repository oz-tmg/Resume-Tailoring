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
          output_dir: Path | None = None, gaming: bool = False,
          education_mode: str | None = None,
          certs_placement: str | None = None,
          industry: str = "agnostic",
          template: str = "standard",
          location_mode: str = "default",
          relocation_city: str | None = None) -> Path:
    """
    Full build pipeline for one family + optional posting.

    gaming=True surfaces the gaming-specific domain_knowledge skill groups
    (Game Systems Analytics, Product & Monetization Analytics, ML Modeling &
    Personalization, and the detailed A/B testing list) for DA/DS/AE builds.

    Returns the path of the generated .tex file.

    industry — "games" | "agnostic" (default).
      "games"    : uses games-industry vernacular in summaries, bullet
                   variants (variants.GAMES), and Claude revoicing persona.
      "agnostic" : neutral language suitable for non-games employers.

    template — "standard" | "ats" (default: "standard").
      "standard" : two-column layout via cv-style.cls + resume.tex.j2
                   (navy header, left sidebar with skills/key victories).
      "ats"      : single-column ATS-friendly layout via cv-style-ats.cls
                   + resume-ats.tex.j2 (navy header, no sidebar, technical-
                   skills table, key-impact-metrics callout). Modeled after
                   the recruiter-prepared resume Alex received in May 2026.
    """
    label_bits = [f"Building: {family_name}"]
    if posting_path:
        label_bits.append(f"Posting: {posting_path.name}")
    else:
        label_bits.append("Base resume")
    if industry != "agnostic":
        label_bits.append(f"Industry: {industry}")
    if template != "standard":
        label_bits.append(f"Template: {template}")
    if location_mode != "default":
        bit = f"Location: {location_mode}"
        if relocation_city:
            bit += f" ({relocation_city})"
        label_bits.append(bit)

    print(f"\n{'='*60}")
    print("  " + "  |  ".join(label_bits))
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
    #    When a posting is provided, the selector switches to
    #    posting-tailored mode: looser tier floor, wider per-role pool,
    #    and bullets that miss the family tag but match posting keywords
    #    are admitted to the candidate pool. The ranker (step 4) trims
    #    the pool to the final cap with a diversity-aware pass.
    # ------------------------------------------------------------------
    print("  [2/5] Selecting bullets...")
    posting_text = posting_path.read_text() if posting_path else None
    selected = select_bullets(experience, family, posting_text=posting_text)

    # ------------------------------------------------------------------
    # 3. Resolve variants — swap base text for pre-written family variant
    #    where one exists. This happens before Claude revoicing so Claude
    #    only revoices bullets that don't already have a curated variant.
    # ------------------------------------------------------------------
    print("  [3/5] Resolving variants...")
    split_section_ids = set(
        family.get("bullet_selection", {}).get("split_sections", [])
    )
    resolved = resolve_bullets(selected, family["id"], industry=industry,
                               split_section_ids=split_section_ids)

    # ------------------------------------------------------------------
    # 4. Posting-specific ranking and revoicing (Claude API)
    # ------------------------------------------------------------------
    if posting_text is not None:
        print("  [4/5] Ranking and revoicing against posting...")
        resolved = rank_and_revoice(resolved, posting_text, family,
                                    industry=industry)
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
        repo_root=ROOT,
        gaming=gaming,
        education_mode=education_mode,
        certs_placement=certs_placement,
        industry=industry,
        posting_text=posting_text,
        template=template,
        location_mode=location_mode,
        relocation_city=relocation_city
    )

    print(f"\n  ✓ Generated: {tex_path}")
    return tex_path


def compile_pdf(tex_path: Path) -> Path:
    """
    Compile a .tex file to PDF using xelatex (two passes for cross-refs).

    TEXINPUTS is extended to include the repo root so cv-style.cls is found
    even if _stage_assets hasn't run (e.g. manual invocation). The renderer
    also copies cv-style.cls into the output dir, so this is belt-and-suspenders.
    """
    import os

    pdf_path = tex_path.with_suffix(".pdf")
    print(f"  [compile] {tex_path.name} → {pdf_path.name}")

    # Build TEXINPUTS: current dir + output dir + repo root + original value
    env = os.environ.copy()
    existing = env.get("TEXINPUTS", "")
    # Colon-separated on macOS/Linux; semicolon on Windows
    sep = ";" if os.name == "nt" else ":"
    env["TEXINPUTS"] = sep.join(filter(None, [
        ".",
        str(tex_path.parent),   # output/data_analyst/
        str(ROOT),              # repo root — cv-style.cls lives here
        str(ROOT / "fonts"),    # fonts/ for fontspec
        existing,
    ])) + sep                   # trailing separator = also search TeX defaults

    xelatex_cmd = [
        "/Library/TeX/texbin/xelatex",   # explicit path avoids PATH issues
        "-file-line-error",
        "-interaction=nonstopmode",
        "-synctex=1",
        str(tex_path),
    ]

    # Two passes: first builds .aux, second resolves cross-references
    for pass_num in (1, 2):
        result = subprocess.run(
            xelatex_cmd,
            cwd=tex_path.parent,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  ✗ xelatex pass {pass_num} failed. Log tail:\n")
            # Print last 60 lines — the error is almost always at the end
            lines = (result.stdout + result.stderr).splitlines()
            print("\n".join(lines[-60:]))
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
    parser.add_argument("--gaming",  action="store_true",
                        help="Surface gaming-specific domain_knowledge skill "
                             "groups (DA/DS/AE) for video-games postings")
    parser.add_argument("--validate", action="store_true",
                        help="Validate YAML content only, do not build")
    parser.add_argument("--education-mode",
                        choices=["full", "condensed"],
                        help=("Override education display mode. "
                              "Defaults to family.education.mode (or 'full')."))
    parser.add_argument("--certs-placement",
                        choices=["education", "aside", "omit"],
                        help=("Where to render certifications. "
                              "Defaults to family.education.certifications_placement "
                              "(or 'education')."))
    parser.add_argument("--industry",
                        choices=["games", "agnostic"],
                        default="agnostic",
                        help=("Industry framing: 'games' uses game-industry "
                              "vernacular in summaries, bullet variants "
                              "(variants.GAMES), and Claude revoicing. "
                              "Default: 'agnostic'."))
    parser.add_argument("--template",
                        choices=["standard", "ats"],
                        default="standard",
                        help=("Output layout: 'standard' (default) renders "
                              "the two-column resume with sidebar via "
                              "cv-style.cls. 'ats' renders an ATS-friendly "
                              "single-column layout via cv-style-ats.cls "
                              "with a technical-skills table and "
                              "key-impact-metrics callout (modeled after the "
                              "recruiter-prepared resume)."))
    parser.add_argument("--location-mode",
                        choices=["default", "relocate", "us"],
                        default="default",
                        help=("Header location mode. 'default' shows just "
                              "the base location ('Victoria, BC.'). "
                              "'relocate' appends an 'Open to Relocation "
                              "(<city>)' clause — default city: Vancouver. "
                              "'us' additionally inserts 'US Citizen & "
                              "Canadian PR' to signal work eligibility — "
                              "default city: Seattle. Override the city "
                              "with --relocation-city."))
    parser.add_argument("--relocation-city",
                        help=("City for the 'Open to Relocation' clause "
                              "when --location-mode is 'relocate' or 'us'. "
                              "Defaults to Vancouver (relocate) or Seattle "
                              "(us). Ignored when --location-mode=default."))
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
            tex = build(fam,
                        gaming=args.gaming,
                        education_mode=args.education_mode,
                        certs_placement=args.certs_placement,
                        industry=args.industry,
                        template=args.template,
                        location_mode=args.location_mode,
                        relocation_city=args.relocation_city)
            if args.pdf:
                compile_pdf(tex)
        return

    if not args.family:
        parser.error("--family is required unless using --all or --validate")

    posting = Path(args.posting) if args.posting else None
    tex = build(args.family,
                posting_path=posting,
                output_dir=args.output,
                gaming=args.gaming,
                education_mode=args.education_mode,
                certs_placement=args.certs_placement,
                industry=args.industry,
                template=args.template,
                location_mode=args.location_mode,
                relocation_city=args.relocation_city)

    if args.pdf:
        compile_pdf(tex)


if __name__ == "__main__":
    main()
