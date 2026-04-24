# CLAUDE.md — Persistent Instructions for This Project

> This file loads automatically with every Claude Code session.
> It defines the project, the working conventions, and how Claude should behave.

---

## What This Project Is

This is **Alex Oswald's resume builder** — a two-repo system for producing tailored,
interview-ready resumes across multiple job families from a single source of truth.

- **Repo 1: `resume-latex/`** — The LaTeX project that defines visual design and styling.
  Built using a custom `cv-style.cls` (Roboto fonts, navy header, sidebar layout, TikZ).
  This is the design substrate. It compiles to PDF via XeLaTeX.

- **Repo 2: `resume-builder/`** — A Python pipeline that reads YAML content, selects and
  tailors bullets per job family (and optionally per job posting via Claude API), renders
  a Jinja2 LaTeX template, and compiles to PDF. YAML is the source of truth. The `.tex`
  files in `output/` are generated artifacts — never manually edited.

Read `COMPANY_CONTEXT.md` for the full strategic picture.
Read `PROJECT_CONTEXT.md` for current status and remaining work.

---

## Directory Layout

```
resume-builder/          ← Python pipeline repo (primary active repo)
├── content/
│   ├── experience/      ← One YAML file per company (source of truth for all bullets)
│   │   ├── kano.yaml
│   │   ├── kixeye_sfg.yaml
│   │   ├── kixeye.yaml
│   │   ├── ea.yaml
│   │   ├── pretio.yaml
│   │   └── tinymob.yaml
│   ├── skills.yaml      ← Master skills inventory, tagged by family
│   ├── education.yaml   ← Degrees + certifications
│   ├── summaries.yaml   ← Base summary per family + revoicing persona
│   └── personal.yaml    ← Contact info (replaces info.tex)
├── families/            ← One YAML per job family — selection + ordering rules
│   ├── data_scientist.yaml
│   ├── data_analyst.yaml
│   ├── analytics_engineer.yaml
│   ├── data_engineer.yaml
│   ├── ml_engineer.yaml
│   └── economist.yaml
├── builder/             ← Python pipeline modules
│   ├── loader.py        ← YAML loading and normalisation
│   ├── selector.py      ← Bullet + skill selection per family rules
│   ├── resolver.py      ← Pre-written variant resolution
│   ├── ranker.py        ← Claude API: posting scoring + revoicing
│   ├── renderer.py      ← Jinja2 → .tex rendering
│   └── validator.py     ← YAML integrity checks
├── templates/
│   └── resume.tex.j2    ← Jinja2 LaTeX template (mirrors cv-style.cls design)
├── postings/            ← One subfolder per job application
│   └── <company_role>/
│       ├── posting.txt  ← Raw job description
│       └── resume.tex   ← Generated output (do not manually edit)
├── output/              ← Compiled PDFs
├── build.py             ← CLI entry point
├── Makefile             ← Convenience targets
└── SCHEMA.md            ← Full YAML field documentation

resume-latex/            ← Design/style repo
├── main.tex             ← Master document (currently DS-oriented, manual)
├── cv-style.cls         ← Custom LaTeX class (do not edit lightly)
├── info.tex             ← Personal info (being replaced by personal.yaml)
├── sections/            ← Modular .tex content files
│   ├── experience/      ← One .tex per company
│   ├── asides/          ← Sidebar content (.tex)
│   └── ...
└── icons/               ← Logos and images
```

---

## The Six Job Families

| ID   | Label                | Make Target  | Primary Audience                        |
|------|----------------------|--------------|-----------------------------------------|
| DS   | Data Scientist       | `make ds`    | DS/ML roles, product science teams      |
| DA   | Data Analyst         | `make da`    | Analytics, BI, insights roles           |
| AE   | Analytics Engineer   | `make ae`    | dbt/pipeline/data modeling focused      |
| DE   | Data Engineer        | `make de`    | Infrastructure, pipelines, warehousing  |
| MLE  | ML Engineer          | `make mle`   | Production ML systems, MLOps            |
| ECON | Economist            | `make econ`  | Research, causal inference, policy      |

---

## Key Conventions

### YAML bullet schema (always follow)
```yaml
- id: unique_snake_case_id      # referenced by families/*.yaml
  text: >                        # neutral base text
    Bullet content here.
  families: [DS, DA, AE]         # which families include this
  keywords: [keyword1, kw2]      # ATS terms
  tier: 1                        # 1=headline, 2=supporting, 3=contextual
  exclude_from: [ECON]           # optional override suppression
  variants:                      # only when framing concept changes per family
    DA: > DA-specific rewrite
    ECON: > ECON-specific rewrite
```

### Tier rules
- **Tier 1** — Headline achievements. Always included. Quantified outcomes preferred.
- **Tier 2** — Strong supporting context. Include if space/relevance allows.
- **Tier 3** — Background detail. Include only when space is generous or highly relevant to posting.

### The variants field — use sparingly
Write the base `text` neutrally. Only add a `variants` block when the **framing concept** 
changes across families — not just the tone. Claude's revoicing handles tone; `variants` 
handles concept shifts (e.g., a causal inference bullet that reads as "model evaluation" 
for DS but "quasi-experimental study design" for ECON).

### Generated files — never manually edit
Everything under `output/` and any `.tex` in `postings/` is generated. Edit the YAML 
instead and re-run the build.

---

## Build Commands

```bash
# Validate YAML integrity
make validate

# Build base resume for a family
make ds          # → output/data_scientist/resume.tex
make da
make ae
make de
make mle
make econ

# Build posting-tailored resume (calls Claude API for ranking + revoicing)
make posting F=data_scientist P=postings/acme_ds/posting.txt

# Build + compile to PDF
make pdf F=data_scientist

# Build all six base resumes
make all
```

---

## LaTeX Compile Notes

The LaTeX project requires XeLaTeX (not pdflatex). Roboto fonts must be available 
system-wide. The `cv-style.cls` uses `\begin{aside}` via `textpos`, and `entrylist` 
uses `longtable` (updated from `tabular*` to support page breaks within entries).

To compile manually:
```bash
cd resume-latex/
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex  # second pass for cross-references
```

---

## Working in This Project — Reminders for Claude

1. **Read `SCHEMA.md` before editing any YAML** — it defines all required fields and 
   the `variants` contract precisely.

2. **Read `PROJECT_CONTEXT.md` before starting new work** — it tracks what's done 
   and what isn't so work isn't duplicated or contradicted.

3. **Never edit generated files** — if something in `output/` looks wrong, fix the 
   YAML or the template, not the output.

4. **When adding bullets**, assign `families`, `keywords`, and `tier` — all three are 
   required. Run `make validate` after.

5. **When changing `cv-style.cls`**, test with a full XeLaTeX compile. The class has 
   interdependencies between the sidebar, header, and `longtable` entrylist.

6. **The Jinja2 template (`resume.tex.j2`) mirrors `cv-style.cls` layout** — changes 
   to one may need to be reflected in the other.

7. **Content lives in YAML, not `.tex`** — if you find yourself wanting to edit a 
   `.tex` content file in `resume-builder/`, you should be editing a YAML file instead.
