# PROJECT_CONTEXT.md — Current Status & Remaining Work

Last updated: April 2026

---

## What Currently Exists

### Repo 1: `resume-latex/` — LaTeX Design Project

**Status: Functional. Compiles to a 3-page PDF.**

The original, manually-curated Data Scientist resume. Produces a polished PDF via XeLaTeX.

| File / Component         | Status       | Notes                                                      |
|--------------------------|--------------|------------------------------------------------------------|
| `cv-style.cls`           | ✅ Done       | Custom class. `longtable` fix applied (page-safe entries). Font paths updated to use system Roboto (no local `fonts/` dir needed). |
| `main.tex`               | ✅ Done       | 3-page layout. DS-oriented. References modular section files. |
| `info.tex`               | ✅ Done       | Personal contact info. Being superseded by `personal.yaml` in builder. |
| `sections/experience/`   | ✅ Done       | kano, kix_sfg, kixeye, ea, pretio, tinymob — all present and compiling. |
| `sections/asides/`       | ✅ Done       | skills-ds.tex, skills-de.tex, experience-breakdown, achievements. `\leavevmode` fix applied to aside vspace issue. |
| `sections/education.tex` | ✅ Done       | Full education history with links and styling. |
| Directory structure      | ✅ Done       | `sections/experience/`, `sections/asides/`, `icons/logos/`, `icons/main/` all properly set up. |
| PDF output               | ✅ Compiling  | 3-page PDF. Clean compile, no errors. Two-pass XeLaTeX required. |

**What this repo currently accomplishes**: Produces a high-quality, visually distinctive 
3-page Data Scientist resume PDF on demand. Layout is stable. Content is manually 
curated and DS-targeted. Not yet automated or family-aware.

---

### Repo 2: `resume-builder/` — Python Build Pipeline

**Status: Content layer complete. Pipeline scaffolded. Not yet end-to-end runnable.**

#### Content Layer (YAML) — ✅ Complete

All source-of-truth content has been written and tagged:

| File                              | Status    | Notes                                             |
|-----------------------------------|-----------|---------------------------------------------------|
| `content/experience/kano.yaml`    | ✅ Done    | All bullets tagged with families, tier, keywords  |
| `content/experience/kixeye_sfg.yaml` | ✅ Done | Includes Stillfront-era bullets + new infra bullets added (kix_sfg_analytics_infra, kix_sfg_data_quality_dbt) |
| `content/experience/kixeye.yaml`  | ✅ Done    | War Commander era bullets                         |
| `content/experience/ea.yaml`      | ✅ Done    | Updated ea_churn_reacquisition_models with "pack spend conversion" |
| `content/experience/pretio.yaml`  | ✅ Done    | Ad tech / MAB bullets                             |
| `content/experience/tinymob.yaml` | ✅ Done    | Early career analytics bullets                    |
| `content/skills.yaml`             | ✅ Done    | Full skills inventory, categorized, family-tagged |
| `content/education.yaml`          | ✅ Done    | Degrees + certifications, family-tagged           |
| `content/summaries.yaml`          | ✅ Done    | 6 summaries (DS, DA, AE, DE, MLE, ECON) each with `revoicing_persona` |
| `content/personal.yaml`           | ✅ Done    | Contact info schema to replace info.tex           |

#### Family Rules Layer — ✅ Complete

| File                              | Status    | Notes                                             |
|-----------------------------------|-----------|---------------------------------------------------|
| `families/data_scientist.yaml`    | ✅ Done    | Priority bullets, exclude lists, skills order     |
| `families/data_analyst.yaml`      | ✅ Done    |                                                   |
| `families/analytics_engineer.yaml`| ✅ Done    |                                                   |
| `families/data_engineer.yaml`     | ✅ Done    |                                                   |
| `families/ml_engineer.yaml`       | ✅ Done    |                                                   |
| `families/economist.yaml`         | ✅ Done    |                                                   |

#### Pipeline Modules — 🔶 Scaffolded, Not Fully Tested

| Module                    | Status          | Notes                                                       |
|---------------------------|-----------------|-------------------------------------------------------------|
| `builder/loader.py`       | ✅ Written       | Loads + normalizes all YAML. Includes `load_personal()`.    |
| `builder/selector.py`     | ✅ Written       | Filters bullets by family, tier, exclude; orders by priority |
| `builder/resolver.py`     | ✅ Written       | Resolves `variants.<FAMILY_ID>` to final bullet text        |
| `builder/ranker.py`       | ✅ Written       | Claude API integration: Stage 1 score, Stage 2 revoice      |
| `builder/renderer.py`     | ✅ Written       | Jinja2 → .tex. Includes `latex_escape` filter.              |
| `builder/validator.py`    | ✅ Written       | Referential integrity checks across all YAML layers         |
| `build.py`                | ✅ Written       | CLI entry point. Orchestrates the full pipeline.            |
| `Makefile`                | ✅ Written       | `make ds`, `make all`, `make posting`, `make pdf`, `make validate` |
| `SCHEMA.md`               | ✅ Written       | Full field documentation. Explains `variants` contract.     |

#### Templates — 🔴 Incomplete

| File                      | Status          | Notes                                                       |
|---------------------------|-----------------|-------------------------------------------------------------|
| `templates/resume.tex.j2` | 🔶 Partial       | Jinja2 template exists but needs validation against `cv-style.cls` layout. `\leavevmode` fix needs to be in template (not in generated output). `\input{info}` needs to be removed and replaced with `personal` context variables. |

---

## What the Project Currently Accomplishes

1. **Produces a polished DS resume PDF** from the LaTeX project — ready to send today.
2. **Has a complete content layer** — all experience, skills, education, and summaries 
   are authored, tagged, and organized in YAML.
3. **Has a complete family rules layer** — selection logic for all 6 families is defined.
4. **Has a full pipeline scaffold** — every module is written, the CLI is wired up, 
   and the Makefile targets exist.
5. **Has a complete schema and documentation** — `SCHEMA.md`, `CLAUDE.md`, 
   `COMPANY_CONTEXT.md`, and this file provide full project context for any session.

---

## What Remains

### High Priority — Needed to Make the Pipeline Runnable

| Task | Details |
|------|---------|
| **Ensure `\aside{}` for page 1 and 2** | There are already templated tex files for each job family in /sections that need to be tested to ensure they work, look alright, and optimized with the best criteria |
| **Rank Achievements** | There are already templated tex files for each job family in /sections that need to be tested to ensure they work, look alright, and optimized with the best criteria |
| **Fix `resume.tex.j2`** | Validate the Jinja2 template produces `.tex` that compiles cleanly. Remove `\input{info}`. Inject `personal` context. Apply `\leavevmode` fix to aside vspace openings. Test that each family produces a valid, clean PDF. |
| **End-to-end test: `make ds`** | Run the full pipeline for the DS family. Verify selector, resolver, renderer output. Compile the output `.tex` and check the PDF looks right. |
| **End-to-end test: all families** | Run `make all`. Fix any per-family layout issues (bullet count, page overflow, section ordering). |
| **Validate YAML integrity** | Run `make validate`. Fix any referential integrity errors (missing bullet IDs, undefined family references, etc.). |
| **Validate `resume_bullet_manager.py`** | Ensure the script is capable of taking a resume and uses the same logic used to vet, score, and rank the experience bullet points founded within it while also capable of adding new listed bulleted points of experience for a matched job title within the proper experience .yaml file while also ensuring that it doesn't duplicate experience already documented. |

### Medium Priority — Quality and Completeness

| Task | Details |
|------|---------|
| **Test `ranker.py` (Claude API posting flow)** | Run `make posting` with a real job description. Verify scoring output, revoicing quality, and that re-ranked bullets still compile. |
| **`interests.tex` / `references.tex`** | Decide whether these belong in a YAML layer or are omitted from the builder entirely (they're currently sidebar/optional content). |
| **Cover letter template** | `personal.yaml` has a `cover_letter` block stubbed out. A `cover_letter.tex.j2` template + `make cover F=... P=...` target needs building. |
| **README.md for resume-builder** | The README scaffold was produced (see prior chat) but may need refinement once end-to-end tests pass. |

### Lower Priority — Nice to Have

| Task | Details |
|------|---------|
| **GitHub setup** | Two separate repos: `resume-latex` and `resume-builder`. Both need `git init`, `.gitignore`, and initial push. The `postings/` directory should have entries gitignored (they're job-application-specific). |
| **`postings/` gitignore strategy** | Decide whether to gitignore posting content entirely, gitignore just PDFs, or keep all of it. |
| **Automated PDF output naming** | Currently output goes to `output/data_scientist/resume.pdf`. Consider `output/alex_oswald_DS_2026.pdf` naming convention for easier file management when sending applications. |
| **Side-by-side diff view** | A utility to visually compare two family outputs side-by-side to sanity-check that tailoring is actually happening. |
| **Certifications in content layer** | `certificates.tex` has Coursera/Udacity certs (2026). These need to be in `education.yaml` with family tags and rendered in the template. |

---

## Known Issues / Technical Debt

| Issue | Details |
|-------|---------|
| `skills-ds.tex` and `skills-de.tex` in `resume-latex/`| These are static `.tex` files in the design repo but are generated files in the builder context. The `\leavevmode` fix applied to them in the design repo needs to be replicated in the Jinja2 template, not just those files. |
| `resume.tex.j2` — `\input{info}` dependency | The Jinja2 template may still reference `\input{info}`. This should be removed; personal info should come from `personal` context variables. |
| No integration tests | The pipeline modules are unit-written but haven't been run as a full pipeline. The first `make ds` run will likely surface issues. |
| Font path assumption | `cv-style.cls` assumes Roboto is system-installed (Ubuntu: `fonts-roboto` package). The Jinja2 template's compile step needs the same assumption documented and enforced. |

---

## Session Quick-Start Checklist

When starting a new session on this project:
1. Read `CLAUDE.md` (you likely already have — it auto-loads)
2. Read `PROJECT_CONTEXT.md` (this file) to understand current state
3. Check which "High Priority" items remain and confirm with Alex what to work on
4. Run `make validate` first if working on the builder pipeline
5. Never edit generated output files — fix YAML or templates instead
