# Resume Builder

Generates tailored LaTeX resumes from a single YAML content layer,
targeting six job families with optional per-posting Claude API revoicing.

## Job Families

| ID | Label | `make` target |
|---|---|---|
| DA | Data Analyst | `make da` |
| AE | Analytics Engineer | `make ae` |
| DE | Data Engineer | `make de` |
| DS | Data Scientist | `make ds` |
| MLE | ML Engineer | `make mle` |
| ECON | Economist | `make econ` |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up secrets and personal info (both are gitignored — never committed)
cp .env.example .env
# edit .env → add your ANTHROPIC_API_KEY

cp content/personal.yaml.example content/personal.yaml
# edit content/personal.yaml → add your real contact details

# 3. Validate YAML content integrity
make validate

# 4. Build a base resume for a family
make ds

# 5. Build a posting-tailored resume (uses Claude API — requires ANTHROPIC_API_KEY)
make posting F=data_scientist P=postings/acme_ds/posting.txt

# 6. Build + compile to PDF
make pdf F=data_scientist

# 7. Build all six base resumes
make all
```

## Architecture

```
content/
├── experience/     ← YAML source of truth, one file per company
│   ├── kano.yaml
│   ├── kixeye.yaml
│   ├── ea.yaml
│   ├── pretio.yaml
│   └── tinymob.yaml
├── skills.yaml     ← Master skills inventory
├── education.yaml  ← Degrees and certifications
└── summaries.yaml  ← Base summary per family

families/           ← Selection rules per job family
├── data_analyst.yaml
├── analytics_engineer.yaml
├── data_engineer.yaml
├── data_scientist.yaml
├── ml_engineer.yaml
└── economist.yaml

templates/
└── resume.tex.j2   ← Jinja2 LaTeX template (your cv-style.cls design)

builder/            ← Python pipeline
├── loader.py       ← YAML loading and normalisation
├── selector.py     ← Bullet and skills selection per family rules
├── resolver.py     ← Pre-written variant resolution
├── ranker.py       ← Claude API: posting ranking + revoicing
├── renderer.py     ← Jinja2 → .tex rendering
└── validator.py    ← YAML integrity checks

build.py            ← CLI entry point
Makefile            ← Convenience targets
```

## Pipeline

```
YAML content + family rules
        │
        ▼
   loader.py          Load + normalise all YAML
        │
        ▼
   selector.py        Filter bullets by family, tier, exclude lists
                      Order bullets by priority list + tier
        │
        ▼
   resolver.py        Swap base text for pre-written family variant
                      where variants.<FAMILY_ID> exists
        │
        ▼
   ranker.py          (only if --posting provided)
   Claude API         Stage 1: Score each bullet 0-3 for posting relevance
                      Stage 2: Revoice unresolved bullets scoring ≥ 2
                      Re-sort bullets within roles by posting score
        │
        ▼
   renderer.py        Render Jinja2 template → .tex file
        │
        ▼
   latexmk            (only if --pdf) Compile .tex → PDF
```

## Adding a New Job Application

```bash
mkdir postings/company_role
# paste job description into:
echo "..." > postings/company_role/posting.txt
# build:
make posting F=data_scientist P=postings/company_role/posting.txt
```

## Updating Content

See `SCHEMA.md` for full field documentation.

Key things to know:
- **Bullet `tier`**: 1 = always include, 2 = include if space, 3 = posting-specific only
- **Bullet `variants`**: Pre-written rewrites for specific families. Write these for
  any bullet where the framing concept changes (not just the tone) across families.
  Most important for ECON variants, which require specific economic vocabulary.
  A family's variant can be a **single string** or a **list of named alternates**
  (one flagged `default`); posting builds auto-pick the best-fitting alternate.
  See SCHEMA.md → "Multiple Alternates Per Family".
- **Family `exclude_bullets`**: Explicitly suppresses bullets that would signal the
  wrong identity for that family, regardless of the `families` tag on the bullet.
- **Gaming domain knowledge**: `--gaming` (or `make <fam> GAMING=1`) surfaces the
  gaming-specific skill blocks (Game Systems Analytics, Product & Monetization
  Analytics, ML Modeling & Personalization, detailed A/B testing) for DA/DS/AE
  builds — intended for video-games postings only.
- **Education layout**: set `education.layout: compact` in a family file for a tight
  one-line-per-degree strip, or `detailed` (default) for focus + accomplishments.

## Environment Variables

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # Required for --posting builds
```
