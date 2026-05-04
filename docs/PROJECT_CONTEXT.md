# PROJECT_CONTEXT.md — Current Status & Remaining Work

Last updated: May 2026

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

### High Priority — ✅ Completed (April 2026)

| Task | Status | Notes |
|------|--------|-------|
| **Ensure `\aside{}` for page 1 and 2** | ✅ Done | All 6 families have aside-pg1 + aside-pg2 files; MLE variants authored; `\leavevmode` fix applied via template. |
| **Rank Achievements** | ✅ Done | Structural parity across all 6 families (3 Key Victory gems each on pg1). DA swapped $14M forecasting (belonged to ECON) for licensing-automation win; ECON added a third gem surfacing the published CIRANO thesis; AE traded abstract "Scalable Analytics" for concrete Domino→Jenkins modernisation; DE collapsed Infra subsection into Storage & Warehouse for count parity. |
| **Fix `resume.tex.j2`** | ✅ Done | `\input{info}` removed; `personal` context injected; `\leavevmode` fix applied to both aside openings; template uses `<< assets_root >>` for portable aside `\input` paths. |
| **End-to-end test: `make ds`** | ✅ Done | DS pipeline runs clean end-to-end. |
| **End-to-end test: all families** | ✅ Done | `make all` generates all 6 family .tex outputs with correct family-specific aside references. |
| **Validate YAML integrity** | ✅ Done | `make validate` runs clean. Fixed: `ea_analyticon`→`ea_companion_app_analyticon` rename across family files; removed dead `kix_product_analyst` exclude reference; extended validator to index sub_bullet IDs. |
| **Validate `resume_bullet_manager.py`** | ✅ Done | (a) Lazy-loaded the Anthropic client (was breaking imports at module load when SOCKS proxy was active / API key unset). (b) Added new `--add-pipeline` mode that writes directly to `content/experience/*.yaml` with full schema (id, families, keywords, tier) and dedupes against every bullet + sub_bullet + variant in the target role. (c) Text-preserving append so folded scalars (`text: >`), flow-style lists (`[DS, DA]`), and blank lines in Alex's hand-maintained YAML survive edits. End-to-end test confirms reload + validate are clean. |

### Known Content Gap — ✅ Resolved (April 2026)

Two new bullets added to `content/experience/kano.yaml`:
- `kano_anomaly_detection` (tier 1; DS, MLE, AE, DE) — anomaly detection
  framework migrated off RShiny onto Python/DBT/Prefect/Athena/Quicksight,
  with irregular-cadence events folded in via cadence-aware standard errors.
  Promoted to top of DS and MLE priority lists.
- `kano_legacy_dsm_review` (tier 3; DS, MLE) — audit of inherited
  decision-tree / random-forest assets, recommended against migration.
  Stays out of base resumes (DS/MLE `min_tier: 1`) but available for
  posting-tailored builds when the role asks for governance/judgement signal.

In addition, **cross-family promotion** lets DS and MLE surface
`kano_etl_performance` (the Parquet/Iceberg ETL win) even though it isn't
tagged DS/MLE. The mechanism is general-purpose — see "Cross-family
promotion" below.

### Build Options Added (April 2026)

| Option | CLI | YAML default | Effect |
|--------|-----|--------------|--------|
| **Cross-family bullet promotion** | n/a | `families/<f>.yaml: bullet_selection.promote_bullets: [bullet_id, ...]` | Force-includes a bullet on this family even when its `families` list doesn't include the target family. Tier and exclude filters still apply. Useful where DS/MLE work overlaps with DA/DE/AE (BI viz, ETLs, modelling). |
| **Education condensed mode** | `--education-mode {full,condensed}` | `families/<f>.yaml: education.mode: condensed` | Drops education entries whose `relevant_families` excludes this family, then trims accomplishments per `entry.condensed.<FAMILY>` (`"all"` keeps all; list of indices keeps a subset; missing/empty drops them). Focus, thesis_url, dates, institution, degree always preserved. |
| **Certifications placement** | `--certs-placement {education,aside,omit}` | `families/<f>.yaml: education.certifications_placement: aside` | `education` (default) renders certs inline under Education. `aside` routes them to the page-3 sidebar (below Data Engineering Toolkit). `omit` drops them entirely. |

---

## Selection Logic — Posting-Aware Mode + Diversity (May 2026)

### The Bug We Fixed

Until May 2026 the selector applied family rules as a **hard cut before
the posting was ever read**. A bullet whose `families:` list didn't
include the target family was dropped at step 2 of the pipeline; the
ranker (step 4, the only stage that ever sees the posting) never got a
chance to score it. This meant a Data Scientist posting that cared
deeply about, say, "ETL performance optimization on Parquet/Iceberg"
would silently exclude the Kano Parquet ETL bullet because that bullet
is tagged `[DE, AE]` — even though the posting itself was begging for
exactly that signal.

The architectural rule has been changed from:

> *Role must appear in family.*

to:

> *An experience bullet must align with the posting OR be relevant to
> the job family of the posting.*

### Two Modes

| Mode | Triggered when | Family rule | Tier floor | Per-role pool | Output |
|------|---------------|-------------|------------|---------------|--------|
| **Base** | `--posting` not provided | Hard: `family ∈ bullet.families` OR `bullet ∈ promote_bullets` | `min_tier` | `max_bullets_per_role[role_id]` | Final selection — goes straight to renderer |
| **Posting-tailored** | `--posting <path>` | Soft: `(family ∈ bullet.families)` OR `(bullet ∈ promote_bullets)` OR `(posting_fit ≥ posting_fit_threshold)` | `min_tier + 1` (relaxed by 1) | `max_bullets_per_role[role_id] × posting_pool_multiplier` | Candidate pool — ranker scores it, then `apply_diversity_and_cap` trims to base cap |

In both modes the `exclude_bullets` list and `experience_roles_order` are
honored as hard structural rules. Roles not listed in
`experience_roles_order` are never admitted (this keeps the resume
structurally stable across postings — no surprise roles appearing).

### How `posting_fit` is Scored

A deterministic, no-API token-bag overlap (computed in `selector.py`,
not by Claude):

1. Tokenize the posting: lowercase, drop stopwords and 1–2-char tokens,
   keep hyphenated tech terms whole (so `multi-armed`, `scikit-learn`,
   `A/B`-style terms survive).
2. Tokenize the bullet's full searchable surface — `text` +
   `keywords` + every `variants.<FAM>` body + every `sub_bullets[].text`
   and `sub_bullets[].keywords` — through the same tokenizer.
3. `posting_fit = |bullet_tokens ∩ posting_tokens| / min(|bt|, |pt|)`.
   Smaller-side denominator avoids penalizing concise bullets when the
   posting is long. Returns a value in `[0, 1]`.
4. Admit the bullet to the candidate pool if `posting_fit ≥
   posting_fit_threshold` (default 0.08).

This is intentionally cheap. Stage 1 of the ranker (the Claude API call)
re-scores the surviving pool with semantic understanding 0–3; the local
score is just a gate, not a final ranking signal.

### Diversity-Aware Cap (`apply_diversity_and_cap`)

Once Claude has scored every pool entry, each role's pool is trimmed to
`max_bullets_per_role[role_id]` by a greedy pick that penalizes
redundancy. Composite score for each remaining candidate, recomputed
after every pick:

```
composite = +10 * posting_score              # Claude's 0–3 score
            +5   if bullet in priority_bullets
            -1   * bullet.tier
            -redundancy_weight * max_sim     # only if max_sim ≥ threshold
```

where `max_sim` is the maximum keyword-Jaccard similarity between this
candidate and any bullet already picked in the same role. Bullets whose
closest sibling has Jaccard `< redundancy_threshold` (default 0.55) lose
nothing — the penalty kicks in only for genuine duplicates. Pick the
highest composite, append, repeat until cap reached.

This solves the "two roles, same project" problem: when EA's
`ea_recommendation_engine` and Pretio's `pretio_targeting_engine` both
rank highly for a recsys posting, the diversity pass keeps both (their
keyword sets diverge — Thompson Sampling vs collaborative filtering)
but suppresses near-duplicates within the same role.

### Configurable Knobs

All on `family["bullet_selection"]`, all optional with sensible defaults:

| Knob | Default | Purpose |
|------|---------|---------|
| `min_tier` | 2 | Base-mode tier floor. |
| `posting_min_tier` | `min_tier + 1` | Posting-mode tier floor (relaxed). |
| `posting_pool_multiplier` | 2.0 | Pool widens to `cap × this` in posting mode. |
| `posting_fit_threshold` | 0.08 | Minimum `posting_fit` to admit an out-of-family bullet. |
| `redundancy_threshold` | 0.55 | Jaccard above which redundancy penalty applies. |
| `diversity_pref` | `true` | Toggle the redundancy term off (back to score-only). |

### Bullet Annotations Carried Through the Pipeline

`select_bullets` annotates each surviving bullet with metadata used by
the diversity pass and useful for debugging / future telemetry:

- `_in_family` — true if `family ∈ bullet.families`
- `_is_promoted` — true if bullet id is in `promote_bullets`
- `_posting_fit` — float in `[0, 1]` (0 in base mode)
- `_admitted_via_posting` — true iff the bullet passed only because of
  `posting_fit` (i.e. would have been excluded by base-mode rules)

Roles also carry `_role_cap` (the base cap from
`max_bullets_per_role`) so the ranker's `apply_diversity_and_cap` step
knows what to trim down to.

### Future Evolution — Concept Tags + Per-Concept Caps

The current diversity pass works on raw keyword Jaccard. That's good
enough for the "same role, same project" case but blunt for the
**cross-role same-concept** case (EA recsys + Pretio recsys + Kano
behavioural targeting all hit the same hiring signal — does the resume
need three of them?).

Proposed schema evolution — **concept tags**, an opt-in second
classification layer on bullets:

```yaml
# content/experience/<file>.yaml
- id: ea_recommendation_engine
  text: ...
  families: [DS, MLE, DA]
  keywords: [recommendation systems, collaborative filtering, ranking]
  concepts: [recsys, personalization]
  tier: 1
```

With a starter taxonomy:

| Concept id | Examples |
|------------|----------|
| `etl_optimization` | Parquet/Iceberg migrations, partition tuning, cost reduction |
| `recsys` | recommendation engines, ranking, collaborative filtering |
| `ab_testing` | experimentation infra, hypothesis testing, lift analysis |
| `causal_inference` | propensity matching, DiD, CEM, kernel matching |
| `churn_modelling` | survival analysis, retention modelling, win-back |
| `mlops` | model deployment, CI/CD for models, monitoring |
| `bi_modernisation` | dashboard rebuilds, BI tool migrations, semantic layers |
| `experimentation_infra` | A/B platforms, ramp-up frameworks, MAB systems |
| `cost_reduction` | infra cost wins, query cost wins, compute right-sizing |
| `forecasting` | time series, revenue forecasting, LTV modelling |

Family files would gain optional caps and floors:

```yaml
# families/data_scientist.yaml
bullet_selection:
  concept_caps:
    recsys: 2          # at most 2 recsys bullets across the whole resume
    ab_testing: 3
  concept_floors:
    causal_inference: 1  # ensure at least 1 causal_inference bullet if any
                         #   pass selection (otherwise no-op)
```

The diversity pass would then:
1. Apply `concept_caps` as hard global limits before per-role greedy
   pick (drop the lowest-scoring duplicates first).
2. Apply `concept_floors` as soft preferences: if a role has any
   floor-concept candidate at all, bias the composite score for it
   regardless of redundancy.

This keeps the scoring math local and deterministic, doesn't require an
API call, and gives Alex a single knob to tune resume "shape" per
posting style.

**Status: not implemented.** The current Jaccard-on-keywords pass is
the operational implementation; concept tags are a planned evolution
when the keyword-only approach proves too coarse on real postings.

---

### Medium Priority — Quality and Completeness

| Task | Details |
|------|---------|
| **Test `ranker.py` (Claude API posting flow)** | Run `make posting` with a real job description. Verify scoring output, revoicing quality, and that re-ranked bullets still compile. |
| **`interests.tex` / `references.tex`** | Decide whether these belong in a YAML layer or are omitted from the builder entirely (they're currently sidebar/optional content). |
| **Cover letter template** | `personal.yaml` has a `cover_letter` block stubbed out. A `cover_letter.tex.j2` template + `make cover F=... P=...` target needs building. |
| **README.md for resume-builder** | The README scaffold was produced (see prior chat) but may need refinement once end-to-end tests pass. |
| **Family-level defaults for new build options** | The new `education.mode` and `education.certifications_placement` family-level defaults aren't set anywhere yet — every family currently uses CLI defaults (`full` + `education`). Decide per-family whether condensed should be the default for non-ECON families. |

### Lower Priority — Nice to Have

| Task | Details |
|------|---------|
| **GitHub setup** | Two separate repos: `resume-latex` and `resume-builder`. Both need `git init`, `.gitignore`, and initial push. The `postings/` directory should have entries gitignored (they're job-application-specific). |
| **`postings/` gitignore strategy** | Decide whether to gitignore posting content entirely, gitignore just PDFs, or keep all of it. |
| **Automated PDF output naming** | Currently output goes to `output/data_scientist/resume.pdf`. Consider `output/alex_oswald_DS_2026.pdf` naming convention for easier file management when sending applications. |
| **Side-by-side diff view** | A utility to visually compare two family outputs side-by-side to sanity-check that tailoring is actually happening. |
| **Certifications in content layer** | ✅ Done. `education.yaml` carries `certifications:` with `relevant_families` per entry, and the renderer now filters by family. Placement is configurable (`--certs-placement education|aside|omit`). |

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
