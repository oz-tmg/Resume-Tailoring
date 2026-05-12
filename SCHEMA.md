# Resume Builder — YAML Content Schema

## Overview

The content layer uses three file types:

| File | Purpose |
|---|---|
| `content/experience/*.yaml` | Source of truth for all work experience |
| `content/skills.yaml` | Master skills inventory |
| `content/education.yaml` | Degrees, certifications |
| `content/summaries.yaml` | Base summary paragraphs per family |
| `families/*.yaml` | Selection rules, ordering, and revoicing instructions |

---

## Bullet Schema

Every bullet inside an experience YAML follows this structure:

```yaml
- id: unique_snake_case_id          # REQUIRED. Referenced by family files.
  text: >                           # REQUIRED. The default/base text.
    Bullet text written in a neutral,
    factually complete voice.
  families: [DA, AE, DE, DS, MLE, ECON]  # REQUIRED. Which families see this bullet.
  keywords: [keyword1, keyword2]    # REQUIRED. ATS terms this bullet covers.
  tier: 1                           # REQUIRED. 1=headline, 2=supporting, 3=contextual.
  exclude_from: [ECON]              # OPTIONAL. Override families list to suppress.
  variants:                         # OPTIONAL. Pre-written rewrites per family or mode.
    DA: > DA-specific rewrite
    DS: > DS-specific rewrite
    ECON: > ECON-specific rewrite
    GAMES: > Games-industry rewrite (used when --industry games and no family variant)
  sub_bullets:                      # OPTIONAL. Nested evidence or outcomes.
    - id: unique_sub_id             # REQUIRED on sub-bullets.
      text: > Sub-bullet text.
      families: [DA, DS]            # REQUIRED. Can be a subset of parent families.
```

### Sub-bullets — when to use them

Sub-bullets create a parent claim → child evidence structure. Use them when:
- The parent bullet makes a bold assertion that needs quantified proof beneath it
- There are 2-3 distinct outcomes from a single piece of work (revenue impact,
  organisational influence, conference presentation — all stemming from one analysis)
- The relationship between items is *consequence*, not just a list of equal facts

Avoid sub-bullets when:
- You're already tight on page space (each sub-bullet costs roughly 1.5 lines)
- The items are parallel and equally weighted (use separate top-level bullets instead)
- The sub-bullet would stand alone fine without the parent context

**Currently used on:** `ea_companion_app` (the propensity score matching story).
Consider adding to `kix_sfg_forecasting_model` if the $14M correction story needs
more supporting detail in future.

### Sub-bullet family filtering

Sub-bullets have their own `families` list, which can be a **subset** of the
parent bullet's families. The resolver filters sub-bullets by family independently
of the parent — so a sub-bullet tagged `[DA, ECON]` will only appear when building
a DA or ECON resume, even if the parent bullet appears in DS builds too.

---

## The `variants` Field — When and Why

### The Problem It Solves

Many accomplishments span multiple job families but speak to each audience
differently. The same causal inference story is told three ways:

| Family | Framing | Vocabulary |
|---|---|---|
| DA | "I found evidence that changed a decision" | insight, stakeholder, evidence |
| DS | "I built a model that estimated causal impact" | propensity matching, AUC, cohort |
| ECON | "I estimated a treatment effect using a quasi-experiment" | consumer surplus, mechanism, welfare |

Without variants, you either: (a) leave the rewriting entirely to Claude every
time, risking inconsistency, or (b) maintain separate bullet files per family,
which creates duplication.

### How the Build Script Uses Variants

```python
# Pseudocode for bullet resolution (with industry support)
def resolve_bullet(bullet, family_id, industry="agnostic"):
    if "variants" in bullet and family_id in bullet["variants"]:
        return bullet["variants"][family_id]   # Family variant wins
    elif industry == "games" and "GAMES" in bullet.get("variants", {}):
        return bullet["variants"]["GAMES"]     # Games variant fallback
    else:
        return bullet["text"]                  # Base text; Claude revoices
```

### Valid Variant Keys

| Key | Usage |
|---|---|
| `DA`, `DS`, `AE`, `DE`, `MLE`, `ECON` | Family-specific rewrites — resolved when building that family |
| `GAMES` | Games-industry framing — used as a fallback when `--industry games` and no family-specific variant exists |
| `AM` | Analytics Manager variant — manually selected, not via a family ID |

### Authoring Guidelines

- Write `text` (the base) in the most neutral, complete framing — typically
  the DA or DS voice, since those are most transferable.
- Only write `variants` for bullets where the framing meaningfully changes
  across families, not just the tone. If it's the same sentence with different
  adjectives, let Claude handle it.
- Variants should convey the same underlying facts — never add claims not
  present in the base text, and never remove the quantified outcome.
- ECON variants are the most distinct and most worth pre-writing. They require
  economic vocabulary (externality, mechanism design, surplus, counterfactual)
  that Claude may not apply consistently without explicit guidance.
- `GAMES` variants use live-games vernacular: DAU/WAU, live ops, LTO systems,
  engagement loops, churn win-back, meta progression, matchmaking, F2P
  monetization funnels. Write them when a bullet's business context changes
  meaningfully in a games framing (not just terminology).

### Bullets With Pre-Written Variants (Current)

| Bullet ID | Families with variants | Why pre-written |
|---|---|---|
| `kix_sfg_forecasting_model` | DA, DS, ECON | Valuation story reads very differently per audience |
| `kix_sfg_matchmaking_churn` | DA, DS, ECON | Platform design externality is a specific ECON reframe |
| `kix_sfg_content_cadence` | DA, DS, ECON | Incentive design framing requires ECON vocabulary |
| `ea_companion_app` | DA, DS, ECON | Strongest causal inference story — ECON version is highest-value |
| `ea_licensing_models` | DA, DS, ECON | Two-sided market framing is non-obvious |
| `pretio_thompson_sampling` | DS, MLE, ECON | Mechanism design framing requires specific vocabulary |
| `pretio_conversion_model` | DS, ECON | Demand response framing is distinct from ML framing |
| `tinymob_paywall_cannibalisation` | DA, DS, ECON | Price discrimination / substitution framing |
| `tinymob_free_rider` | DA, ECON | Public goods framing is entirely different register |
| `kano_rshiny_migration` | GAMES | Player-facing BI framing |
| `kano_etl_performance` | GAMES | Live ops visibility framing |
| `kano_anomaly_detection` | GAMES | Irregular-cadence game events framing |
| `kix_forecasting_model` | GAMES | Player LTV / live ops framing |
| `kix_matchmaking_churn` | GAMES | Matchmaking + F2P churn framing |
| `ea_ab_test_design` | GAMES | Live game experimentation framing |
| `ea_mab_recsys` | GAMES | LTO recommendation engine framing |
| + many more | GAMES | See individual company YAML files |

---

## Role-Level `summary_variants`

Each role entry can carry a `summary_variants` block to tailor the role description
per job family. When building for a family, the resolver picks `summary_variants[FAMILY_ID]`
if present; otherwise falls back to the base `summary`.

```yaml
roles:
  - id: kano_senior_de_bi
    title: Senior Game Data Engineer & BI Analyst
    start: 2025-05
    end: 2026-02
    location: Victoria, BC Canada
    summary: >
      Hired to modernize the studio's analytics stack by migrating reporting
      and transformation workflows from RShiny to a scalable Python- and
      AWS-based platform.
    summary_variants:
      DS: >
        Brought in to rebuild Kano's analytics platform and restore data science
        capability, including migrating anomaly detection and inherited ML assets
        to a modern Python, DBT, and AWS stack.
      DE: >
        Hired to architect and build Kano's next-generation analytics platform,
        migrating from RShiny-based ETLs to a scalable DBT-Athena pipeline on
        partitioned Parquet and Iceberg tables.
```

- The `summary` field is the neutral base — always required.
- `summary_variants` keys are family IDs (same set as `variants` keys above).
- Resolved text is exposed to the template as `role.resolved_summary`.
- Authoring intent: summaries should be factually honest — adjust emphasis and
  vocabulary, not claims.

---

## Tier Definitions

| Tier | Meaning | Default behavior |
|---|---|---|
| 1 | Headline achievement. Quantified outcome. Always include. | Included for all families that list the bullet |
| 2 | Strong supporting detail. Include when space allows. | Included unless `min_tier: 1` is set in family file |
| 3 | Contextual or minor. Include only when posting specifically matches. | Excluded by default; posting tailoring can override |

---

## Family IDs

| ID | Label |
|---|---|
| DA | Data Analyst |
| AE | Analytics Engineer |
| DE | Data Engineer |
| DS | Data Scientist |
| MLE | ML Engineer |
| ECON | Economist |

---

## `content/summaries.yaml` Schema

Each entry in `summaries.yaml` is keyed by the family's `summary_ref` value:

```yaml
data_scientist:
  text: >
    Neutral base summary paragraph for this family.
  revoicing_persona: >
    Instructions for Claude when revoicing bullets in agnostic (default) mode.
  games_text: >                        # OPTIONAL. Summary for --industry games builds.
    Games-industry-focused summary paragraph.
  games_revoicing_persona: >           # OPTIONAL. Revoicing persona for --industry games.
    Instructions for Claude in live-games context.
```

- `text` and `revoicing_persona` are required.
- `games_text` and `games_revoicing_persona` are used when `--industry games` is passed.
  Falls back to `text` / `revoicing_persona` if missing.

---

## `content/personal.yaml` Schema

```yaml
personal:
  first_name: Alex
  last_name: Oswald
  phone: "..."
  email: "..."
  linkedin_handle: "..."
  linkedin_url: "..."
  github_handle: "..."
  github_url: "..."
  blog_url: "..."
  blog_display: "..."
  location: "Victoria, BC"
  work_authorization:                  # OPTIONAL. Work auth note rendered on pg1 sidebar.
    show_on_resume: true
    note: "Authorized to work in Canada and United States"
```

- `work_authorization` is optional. When `show_on_resume: true`, the note appears below
  the page-1 aside content, separated by a rule.

---

## Family File `aside_skills` Block

Each family file can define `aside_skills.page2` to drive the page-2 sidebar
content dynamically from YAML instead of a static `.tex` file. When present,
the template generates the sidebar inline; otherwise it falls back to
`sections/aside-pg2/aside-pg2-<family_id>.tex`.

```yaml
aside_skills:
  page2:
    title: "Data Science Skillset"       # Section heading rendered with \LARGE
    sections:
      - id: experimentation              # Internal identifier (unique within page)
        label: "Experimentation & Measurement"  # Bold heading rendered with \large
        keywords: [experimentation, A/B testing, hypothesis, measurement]
          # Keywords used to score this section's relevance against a job posting
          # (when --posting is provided). Higher overlap → section sorts earlier.
        text: >
          Prose description of this skill area. Rendered under the label.
    programming_latex: 'R, Python, SQL'  # OPTIONAL. Raw LaTeX for a Programming section.
                                          # NOT passed through latex_escape — may contain
                                          # LaTeX commands like {\color{red} $\varheartsuit$}.
```

### Posting-aware reordering

When `--posting` is provided, `select_aside_skills()` in `selector.py` scores each
section by token overlap between its `keywords` and the posting text. Sections with
higher overlap sort to the top. Ties preserve the curated family order. This is a
deterministic, no-API operation — same posting always produces the same order.

---

## Family File ATS-Template Fields

When `--template ats` is passed, the family file may also carry three
optional fields that drive the single-column ATS layout. All three are
ignored by the standard two-column template and all three have sensible
fallbacks derived from existing fields, so adding ATS support to a new
family is opt-in.

```yaml
# OPTIONAL. Keyword tagline rendered under the subtitle in the navy header.
# Passed to LaTeX verbatim (NOT latex-escaped) — use single-quoted YAML so
# backslashes are preserved. Default: first 6 entries of
# ats_keyword_watchlist joined with \textbullet.
ats_tagline: 'dbt \textbullet\ Snowflake \textbullet\ Python \textbullet\ Airflow'

# OPTIONAL. Drives the Technical Skills key/value table. Items are
# latex-escaped on render, so write plain prose (NOT LaTeX). Items don't
# have to match entries in skills.yaml — they can be human-readable phrases.
# Default: derive from skills_order via _compose_ats_skills_groups().
ats_skills_groups:
  - label: "Pipeline & Orchestration"
    items: ["Apache Airflow", "Prefect", "AWS Lambda", "Glue"]
  - label: "Languages"
    items: ["Python (4+ yrs)", "SQL (advanced)", "R (expert)"]

# OPTIONAL. 3 or 4 entries render the Key Impact Metrics callout. Both
# fields are latex-escaped, so write `$14M` not `\$14M`. Unicode arrows
# and em-dashes render natively via XeLaTeX. Section is omitted when
# the field is absent.
impact_metrics:
  - value: "13x"
    label: "Report latency improvement (14 hrs → <1 hr)"
  - value: "$220K+/yr"
    label: "Annual cloud cost savings across Snowflake, EC2, Athena"
```

---

## Adding New Experience

1. Create or edit the relevant `content/experience/<company>.yaml`
2. Add bullet(s) with all required fields
3. Assign `families`, `tier`, and `keywords`
4. If the bullet spans DS + ECON or DA + ECON with meaningfully different
   framing, add a `variants` block
5. Update any affected `families/*.yaml` files:
   - Add the bullet id to `priority_bullets` if tier 1
   - Add to `exclude_bullets` in families where it would read as noise
6. Run `make validate` to check for missing family references and schema errors
