# COMPANY_CONTEXT.md — Strategic Purpose & Project Background

## The Problem This Project Solves

Alex Oswald has ~10 years of genuinely multifaceted experience: experimentation, 
causal inference, predictive modelling, recommendation systems, analytics engineering, 
data engineering, team leadership, and a graduate background in economics. This is 
an asset — but also a challenge.

**The core tension**: A hiring manager for a Data Engineering role and a hiring manager 
for an Economist role are looking at fundamentally different things. The same resume 
sent to both will feel like a mismatch to at least one of them. Generic resumes that 
try to be everything to everyone end up resonating with no one.

**The solution**: A pipeline that maintains a single authoritative source of content 
(YAML), and tailors what gets shown and how it's framed based on (a) the job family 
being targeted, and (b) optionally the specific job posting being applied to.

---

## Primary Objective

**Get interviews** across the target job families by presenting the same underlying 
experience in the voice and framing that resonates with each specific audience — without 
creating and maintaining six separate resumes manually.

---

## Target Job Families

The six families represent realistic application targets given Alex's background:

| Family           | Why It's Viable                                                  |
|------------------|------------------------------------------------------------------|
| Data Scientist   | 10-year core identity. Experimentation, modelling, RecSys.       |
| Data Analyst     | Strong BI, product analytics, and stakeholder communication history. |
| Analytics Engineer | Significant dbt, pipeline, and reporting modernization experience. |
| Data Engineer    | 4 years hands-on: Snowflake, Airflow, Prefect, Spark, AWS stack. |
| ML Engineer      | Churn models, recommendation engines, MAB systems in production. |
| Economist        | M.A. Economics (UVic), published research, causal inference throughout career. |

Each family gets its own tailored resume built from the same content pool, with:
- Different bullets selected (and de-selected)
- Different bullet ordering and emphasis
- Different summary paragraph and professional framing
- Skills sections reordered to lead with what matters to that audience

---

## Secondary Objectives

### 1. Posting-Level Tailoring
Beyond family-level tailoring, when applying to a specific job, the pipeline can take 
a raw job description and use the Claude API to:
- Score each bullet 0–3 for posting relevance
- Re-rank bullets within roles by posting score
- Revoice bullets that score ≥ 2 to better mirror the language and priorities in the 
  posting (without fabricating or misrepresenting)

This produces a posting-specific `.tex` + PDF in `postings/<company_role>/`.

### 2. One Source of Truth for All Content
Never manage multiple copies of bullet text. Every achievement, responsibility, and 
skill is written once in YAML with metadata, and the build pipeline handles the rest. 
Updating a bullet updates it everywhere automatically.

### 3. Honest, Non-Inflated Representation
The `variants` field and Claude revoicing are tools for *framing* — adjusting emphasis, 
vocabulary, and context for the audience. They are not tools for fabrication. The 
underlying facts, metrics, and claims must remain accurate in all variants. The test: 
if a hiring manager asked Alex to explain the bullet in an interview, he could do so 
truthfully in any variant.

### 4. Maintainability Over Time
New job? Add a `postings/` folder and run `make posting`. New role to add to resume? 
Add a YAML entry with family tags. Nothing in the output layer is hand-edited, so 
content updates don't cascade into reformatting work.

### 5. Cover Letter Support (Planned)
The `content/personal.yaml` schema and `cover_letter` block are placeholders for a 
future cover letter generation pipeline. The Jinja2 infrastructure will extend naturally 
to cover letter templates once the resume pipeline is stable.

---

## The Two Repos

### `resume-latex/` — The Design Substrate
The original LaTeX resume project. Uses a custom `cv-style.cls` with:
- Roboto font family (XeLaTeX required)
- Navy header band with circular portrait
- Three-page layout with alternating main column + sidebar
- TikZ-based elements, `longtable` entrylist for page-safe entry rendering

This repo is the visual source of truth. It produces a hand-curated DS-oriented resume 
and serves as the design reference that the Jinja2 template in the builder mirrors.

### `resume-builder/` — The Pipeline
A Python-based build system where content lives in YAML and output is generated, 
never manually edited. Key components:
- **loader.py** — reads and normalizes all YAML
- **selector.py** — filters bullets by family, tier, and exclude lists; orders by priority
- **resolver.py** — swaps base text for pre-written `variants` where they exist
- **ranker.py** — calls Claude API to score and revoice bullets against a posting
- **renderer.py** — Jinja2 → `.tex` rendering
- **validator.py** — referential integrity checks across YAML layers

---

## Key Design Decisions

**YAML as source of truth, not `.tex`**: Bullets written in LaTeX are hard to 
programmatically filter and tag. YAML is machine-readable, human-editable, and 
version-controllable without fighting LaTeX syntax.

**Family ID system (DS, DA, AE, DE, MLE, ECON)**: Short, stable identifiers used 
consistently across all YAML keys, Python logic, and Makefile targets. Adding a new 
family is an additive change — existing content doesn't need rewriting.

**Tier system (1/2/3)**: Separates "always show this" from "show if space allows" from 
"background context only." Tier 1 bullets are the ones with concrete metrics and 
impact; tier 2 are technical depth and supporting evidence.

**`variants` field for concept-level rewrites only**: Tone adjustment (more technical, 
more strategic, more academic) is handled by Claude's revoicing instructions in 
`summaries.yaml`. The `variants` field is reserved for cases where the *concept* of 
a bullet changes across families — not just the language.

**Personal info in YAML, not `info.tex`**: `content/personal.yaml` replaces `info.tex` 
so personal details have a single home and the Jinja2 template can render everything 
without depending on a separate LaTeX input file.

---

## Background on the Candidate

**Alex Oswald** — Senior Data Scientist based in Victoria, BC, Canada.

Career arc: TinyMob Games (2014) → Pretio Interactive (2015) → EA Sports (2016–2019) 
→ Kixeye/Stillfront Group (2019–2025) → Kano Apps (2025–2026).

Headline strengths:
- Experimentation design and automation in live digital products
- Recommendation systems and targeting (RecSys, MAB, Alliance rec engine, LTO systems)
- Predictive modelling: churn, LTV, spend conversion, reacquisition, revenue forecasting
- Causal inference: propensity score matching, quasi-experimental methods, interaction effects
- Analytics engineering: dbt, Airflow, Prefect, Snowflake, Athena, Iceberg/Parquet
- Forecasting: identified $14M overestimation in a game acquisition model
- Team leadership: led Core Analytics team, mentored junior/senior analysts

Education: M.A. Economics, University of Victoria (auction theory, game theory, 
experimental economics, published research). B.Sc. Economics, Illinois State University.

GitHub: github.com/oz-tmg  
Blog: alexoswald.wordpress.com  
LinkedIn: linkedin.com/in/alex-oswald-0648a657
