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
  variants:                         # OPTIONAL. Pre-written rewrites per family.
    DA: > DA-specific rewrite
    DS: > DS-specific rewrite
    ECON: > ECON-specific rewrite
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
# Pseudocode for bullet resolution
def resolve_bullet(bullet, family_id):
    if "variants" in bullet and family_id in bullet["variants"]:
        return bullet["variants"][family_id]   # Use pre-written variant
    else:
        return bullet["text"]                  # Fall back to base text
        # Claude then revoices this per the family's revoicing_persona
```

### Multiple Alternates Per Family (multi-variant)

A family entry under `variants` can be **either** a single string (the
classic form above) **or** a list of alternates when you have written more
than one phrasing of the same accomplishment for the same family and want
the build to choose the best fit per context:

```yaml
variants:
  DA:
    - id: concise
      default: true          # used for base (no-posting) builds
      text: >
        A tight, general-purpose DA phrasing — the safe primary.
    - id: gaming_detailed
      text: >
        A richer, gaming-specific DA phrasing with system detail.
      sub_bullets:           # OPTIONAL — overrides the bullet-level subs
        - id: da_pvp_models
          text: > Built and cross-validated three logistic models ...
          families: [DA, DS]
```

Rules:
- Exactly one alternate should carry `default: true`. It is used for base
  (`make da`) builds. If none is flagged, the first is used (validator warns).
- `id` must be unique within the family's alternate list.
- An alternate may define its own `sub_bullets`; if it does, those replace
  the bullet-level `sub_bullets` when that alternate is selected. Omit the
  key to inherit the bullet-level subs.
- **Posting builds** (`--posting`) auto-select: the Claude ranker scores each
  alternate against the job description and swaps in the best match
  (gaming-detailed for gaming postings, concise for generic ones). See
  `builder/ranker.py::_select_variants`. No `--posting` ⇒ the `default` wins.
- The single-string form and the list form can coexist across families on the
  same bullet (e.g. `DA` as a list, `ECON` as a string).

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

---

## Education Schema

Each `content/education.yaml` entry supports:

| Field | Required | Notes |
|---|---|---|
| `degree` | yes | e.g. `M.A. in Economics` |
| `specialization` | no | Rendered after the degree with an em-dash, e.g. `Auctions & Experimental Economics` |
| `minor` | no | Rendered as `, Minor in <minor>` |
| `focus` | no | One-line focus statement shown above the accomplishments |
| `accomplishments` | no | Bullet list (hidden in `compact` layout) |
| `thesis_url` | no | Rendered as a linked sub-item under accomplishments |

### Education layout (detailed vs compact)

The education section has two layouts, selected per family in the family file:

```yaml
# families/<family>.yaml
education:
  layout: compact      # or "detailed" (the default)
  certifications_to_show: [gcp_ml, udacity_de]   # optional cert filter
```

- **`detailed`** (default) — shows `focus` and the full `accomplishments`
  list (plus the thesis link). Mirrors the hand-tailored EA resume's
  education section.
- **`compact`** — emits a tight degree / institution / dates strip with no
  body, for resumes that need education kept to a single line each.

---

## Gaming Domain Knowledge (`domain_knowledge`)

`content/skills.yaml` has a top-level `domain_knowledge` section: gaming-
specific descriptive skill groups (not single tools), each with a `name`
label and a `detail` comma-list. They mirror the hand-tailored EA resume's
**Game Systems Analytics**, **Product & Monetization Analytics**, **ML
Modeling & Personalization** blocks and the detailed **A/B Testing** list.

```yaml
domain_knowledge:
  - name: Game Systems Analytics
    gaming: true
    families: [DA, DS, AE]
    detail: > matchmaking quality, player progression, ...
    keywords: [matchmaking, progression, ...]
```

These are **gaming-gated**: they only render when a build is run with
`--gaming` (or `build(..., gaming=True)`), and only for the families listed.
Base, non-gaming builds omit the section entirely. Optionally control order
per family with `domain_knowledge_order: [<group name>, ...]` in the family
file. See `builder/selector.py::select_domain_knowledge`.

```bash
# Surface the gaming domain-knowledge blocks for a games posting:
python build.py --family data_analyst --gaming
python build.py --family data_analyst --gaming \
    --posting postings/Electronic_Arts/Advanced_Analyst_Apex.txt
```
