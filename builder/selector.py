"""
builder/selector.py
===================
Applies family rules to select and order bullets and skills.
Pure Python — no I/O, no API calls.

Returns a structured list of companies → roles → selected bullets,
preserving the ordering defined in the family file's
`experience_roles_order`.

Two modes:

  Base resume mode  (posting_text=None)
    ─────────────────────────────────────
    Hard family rules. Bullets are kept only if they satisfy ALL of:
      role in experience_roles_order
      family in bullet.families  OR  bullet in promote_bullets
      bullet not in exclude_bullets
      bullet.tier <= min_tier
    Per-role cap is applied with priority_bullets sorted to the front.
    This produces the final selection (no candidate pool — selector
    output goes straight to the renderer).

  Posting-tailored mode  (posting_text=<job posting string>)
    ──────────────────────────────────────────────────────────
    Soft family rules — a bullet is admitted if EITHER it satisfies the
    family fit (family in bullet.families OR bullet in promote_bullets)
    OR the posting fit (token overlap between (bullet.text +
    bullet.keywords) and the posting >= posting_fit_threshold). The
    exclude_bullets list is still hard (curated suppression). The tier
    floor is relaxed by 1 (so a min_tier=1 family will admit tier 2 in
    posting mode). Per-role candidate count is widened by
    posting_pool_multiplier (default 2.0).

    The result is a CANDIDATE POOL, not a final selection. The ranker
    (builder/ranker.py) scores each pool entry against the posting via
    Claude, then calls apply_diversity_and_cap() to trim each role's
    pool down to max_bullets_per_role[role_id], preferring (in order):
      1. higher posting score
      2. priority_bullets membership
      3. lower tier
      4. greater keyword-Jaccard distance from already-selected bullets
         in the same role (diversity preference; threshold-controlled)

Configuration knobs — all on family["bullet_selection"], all optional:

  posting_min_tier            int   default = min_tier + 1
  posting_pool_multiplier     float default = 2.0
  posting_fit_threshold       float default = 0.08
  redundancy_threshold        float default = 0.55
  diversity_pref              bool  default = true
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Posting-fit scoring (local, deterministic, no API call)
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.#-]{1,}")
_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "this", "that", "into", "have",
    "has", "had", "are", "was", "were", "been", "being", "but", "not",
    "you", "your", "our", "their", "they", "them", "its", "his", "her",
    "will", "can", "may", "any", "all", "every", "each", "some", "most",
    "more", "less", "than", "then", "when", "while", "where", "what",
    "who", "whom", "whose", "which", "such", "very", "much", "also",
    "well", "etc", "ie", "eg", "we", "us", "as", "at", "by", "of", "or",
    "on", "in", "is", "it", "to", "be", "an", "a",
})


def _tokenize(text: str) -> set[str]:
    """
    Lowercase token-bag with stopwords removed. Used for both posting
    and bullet text. Hyphenated tech terms (e.g. multi-armed, scikit-learn)
    are kept whole; pure punctuation is dropped.
    """
    if not text:
        return set()
    return {
        t.lower() for t in _TOKEN_RE.findall(text)
        if t.lower() not in _STOPWORDS and len(t) > 2
    }


def _bullet_tokens(bullet: dict) -> set[str]:
    """All searchable tokens for a bullet: text + keywords + variants."""
    parts: list[str] = [bullet.get("text", "") or ""]
    parts.extend(bullet.get("keywords", []) or [])
    for v in (bullet.get("variants") or {}).values():
        parts.append(v or "")
    for sub in bullet.get("sub_bullets", []) or []:
        parts.append(sub.get("text", "") or "")
        parts.extend(sub.get("keywords", []) or [])
    return _tokenize(" ".join(parts))


def _posting_fit(bullet: dict, posting_tokens: set[str]) -> float:
    """
    Posting fit score in [0, 1]. Token overlap of (bullet.tokens) ∩
    (posting.tokens), normalized by the smaller side. Using the
    smaller-side denominator avoids penalizing concise bullets when the
    posting is long.
    """
    bt = _bullet_tokens(bullet)
    if not bt or not posting_tokens:
        return 0.0
    overlap = bt & posting_tokens
    denom   = min(len(bt), len(posting_tokens))
    return len(overlap) / denom if denom else 0.0


def _jaccard_keywords(a: dict, b: dict) -> float:
    """
    Jaccard similarity of two bullets' keyword sets, lowercased.
    Used by the diversity pass. Returns 1.0 for identical sets, 0.0 for
    disjoint sets.
    """
    ka = {k.lower() for k in a.get("keywords", []) or []}
    kb = {k.lower() for k in b.get("keywords", []) or []}
    if not ka and not kb:
        return 0.0
    union = ka | kb
    return len(ka & kb) / len(union) if union else 0.0


# ---------------------------------------------------------------------------
# Bullet selection
# ---------------------------------------------------------------------------

def select_bullets(experience: dict,
                   family: dict,
                   *,
                   posting_text: str | None = None) -> list[dict]:
    """
    Apply family rules to produce an ordered list of role dicts, each
    containing only the bullets selected (or pooled) for this family.

    See module docstring for the two modes (base vs posting-tailored).

    Cross-family promotion (`promote_bullets`):
      DS and MLE work overlaps heavily with DA/DE/AE work — BI dashboards,
      ETLs, data modelling, exploratory analysis. When a role has thin
      in-family signal but useful sibling-family bullets, list those
      bullet ids in `promote_bullets` to surface them anyway. Tier and
      exclude filters still apply; promotion only bypasses the family-tag
      check. Promoted bullets that are also in `priority_bullets` keep
      their priority placement.
    """
    fam_id       = family["id"]
    rules        = family["bullet_selection"]
    base_min_tier = rules.get("min_tier", 2)
    max_per_role = rules.get("max_bullets_per_role", {})
    priority_ids = set(rules.get("priority_bullets", []))
    exclude_ids  = set(rules.get("exclude_bullets", []))
    promote_ids  = set(rules.get("promote_bullets", []))
    role_order   = family["experience_roles_order"]

    posting_mode = posting_text is not None
    if posting_mode:
        # Posting mode: relax the tier floor by 1, widen the per-role
        # candidate pool, and admit posting-fit bullets that fail the
        # family-tag check.
        min_tier_eff      = rules.get("posting_min_tier",
                                      base_min_tier + 1)
        pool_multiplier   = float(rules.get("posting_pool_multiplier", 2.0))
        posting_threshold = float(rules.get("posting_fit_threshold", 0.08))
        posting_tokens    = _tokenize(posting_text)
    else:
        min_tier_eff      = base_min_tier
        pool_multiplier   = 1.0
        posting_threshold = None
        posting_tokens    = None

    # Build a lookup: role_id → (company_meta, role_dict)
    role_lookup: dict[str, tuple[dict, dict]] = {}
    for company in experience["companies"]:
        for role in company["roles"]:
            role_lookup[role["id"]] = (company, role)

    selected_companies: list[dict] = []
    company_map: dict[str, dict] = {}

    for role_id in role_order:
        if role_id not in role_lookup:
            print(f"  ⚠  Warning: role '{role_id}' in family config "
                  f"not found in experience files — skipping.")
            continue

        company_meta, role = role_lookup[role_id]
        base_cap = max_per_role.get(role_id, 4)

        if base_cap == 0:
            continue  # Entire role suppressed for this family

        effective_cap = (
            max(base_cap, int(round(base_cap * pool_multiplier)))
            if posting_mode else base_cap
        )

        # Filter bullets — annotate each survivor with its admission reason
        # so the ranker / diversity pass can break ties.
        passing: list[dict] = []
        for bullet in role["bullets"]:
            bid = bullet["id"]

            if bid in exclude_ids:
                continue
            if bullet.get("tier", 99) > min_tier_eff:
                continue

            in_family   = fam_id in bullet.get("families", [])
            is_promoted = bid in promote_ids
            posting_fit = (
                _posting_fit(bullet, posting_tokens)
                if posting_mode else 0.0
            )
            passes_posting_fit = (
                posting_mode and posting_fit >= posting_threshold
            )

            if not (in_family or is_promoted or passes_posting_fit):
                continue

            # Annotate the bullet (shallow copy so we don't mutate the
            # loaded experience structure).
            annotated = {
                **bullet,
                "_in_family":   in_family,
                "_is_promoted": is_promoted,
                "_posting_fit": posting_fit,
                "_admitted_via_posting": (
                    not in_family and not is_promoted and passes_posting_fit
                ),
            }
            passing.append(annotated)

        if not passing:
            continue

        # Initial ordering: priority bullets first (in declared order),
        # then remaining bullets by tier ascending. In posting mode this
        # is just the candidate pool's stable order before scoring.
        priority   = [b for b in passing if b["id"] in priority_ids]
        remaining  = [b for b in passing if b["id"] not in priority_ids]
        remaining.sort(key=lambda b: b.get("tier", 99))
        ordered    = priority + remaining

        # Cap to (base_cap in base mode) or (pool size in posting mode).
        capped = ordered[:effective_cap]

        # Attach to correct company entry
        cname = company_meta["company"]
        if cname not in company_map:
            entry = {
                "company":  cname,
                "division": company_meta.get("division", ""),
                "logo":     company_meta.get("logo", ""),
                "roles":    [],
            }
            company_map[cname] = entry
            selected_companies.append(entry)

        company_map[cname]["roles"].append({
            **role,
            "bullets":   capped,
            "_role_cap": base_cap,   # carried forward for the ranker
        })

    return selected_companies


# ---------------------------------------------------------------------------
# Diversity-aware final cap (called by ranker after Stage 1 scoring)
# ---------------------------------------------------------------------------

def apply_diversity_and_cap(selected_companies: list[dict],
                            family: dict,
                            *,
                            scores: dict[str, int] | None = None
                            ) -> list[dict]:
    """
    Trim each role's candidate pool to its base cap
    (max_bullets_per_role[role_id]) using a diversity-aware greedy pick.

    Pick order, per role, walking until the cap is reached:
      1. Sort remaining candidates by composite score:
           +10 * posting_score (when scores provided)
           +5  if bullet in priority_bullets
           -1  * tier
           -redundancy_weight * max(jaccard_keywords(bullet, picked))
                  for picked already in this role's selection.
      2. Pick the highest-scoring candidate. Append. Repeat.

    If `diversity_pref` is False on the family, the redundancy term is
    skipped (back to score-only ordering).

    Returns the same nested list with bullets re-ordered & trimmed.
    """
    rules                = family["bullet_selection"]
    priority_ids         = set(rules.get("priority_bullets", []))
    redundancy_threshold = float(rules.get("redundancy_threshold", 0.55))
    diversity_pref       = bool(rules.get("diversity_pref", True))
    # Redundancy weight maps "max similarity above threshold" to a score
    # penalty. A bullet whose closest selected sibling has Jaccard >=
    # threshold loses ~3 score points; below threshold it loses none.
    redundancy_weight    = 6.0

    scores = scores or {}

    out_companies: list[dict] = []
    for company in selected_companies:
        company_copy = {**company, "roles": []}
        for role in company["roles"]:
            cap = role.get("_role_cap")
            if cap is None:
                # Selector wasn't run in posting mode — pool already capped.
                # Pass through.
                company_copy["roles"].append({**role,
                                              "bullets": role["bullets"]})
                continue

            pool = list(role["bullets"])
            picked: list[dict] = []

            while pool and len(picked) < cap:
                def composite(b: dict) -> float:
                    score = float(scores.get(b["id"], 0)) * 10.0
                    if b["id"] in priority_ids:
                        score += 5.0
                    score -= float(b.get("tier", 99))
                    if diversity_pref and picked:
                        max_sim = max(_jaccard_keywords(b, p) for p in picked)
                        if max_sim >= redundancy_threshold:
                            # Scaled penalty: stronger overlap → bigger hit
                            score -= redundancy_weight * max_sim
                    return score

                pool.sort(key=composite, reverse=True)
                picked.append(pool.pop(0))

            company_copy["roles"].append({**role, "bullets": picked})
        out_companies.append(company_copy)
    return out_companies


# ---------------------------------------------------------------------------
# Skills selection and ordering
# ---------------------------------------------------------------------------

def select_skills(skills: dict, family: dict) -> dict:
    """
    Filter and order skills according to the family's skills_order config.

    The family file lists which skill names to include and in what order,
    grouped by category. We pull the full skill metadata from the master
    skills.yaml and return an ordered structure for the renderer.

    Returns:
        {
          "programming": [ {name, tier, families, keywords}, ... ],
          "data_science": [...],
          "data_engineering": {
              "storage_and_warehousing": [...],
              "orchestration": [...],
              ...
          }
        }
    """
    fam_id      = family["id"]
    order_rules = family["skills_order"]

    # Build flat name→skill lookup from master skills
    skill_lookup: dict[str, dict] = {}
    for cat_key, cat_val in skills.items():
        if isinstance(cat_val, list):
            for s in cat_val:
                skill_lookup[s["name"]] = s
        elif isinstance(cat_val, dict):
            for subcat_val in cat_val.values():
                if isinstance(subcat_val, list):
                    for s in subcat_val:
                        skill_lookup[s["name"]] = s

    def _pick(names: list[str]) -> list[dict]:
        result = []
        for name in names:
            s = skill_lookup.get(name)
            if s is None:
                print(f"  ⚠  Warning: skill '{name}' in family order "
                      f"not found in skills.yaml — skipping.")
                continue
            if fam_id not in s.get("families", []):
                continue
            result.append(s)
        return result

    output: dict[str, Any] = {}

    for section, val in order_rules.items():
        if isinstance(val, list):
            # Flat section (programming, data_science)
            output[section] = _pick(val)
        elif isinstance(val, dict):
            # Nested section (data_engineering with subcategories)
            output[section] = {}
            for subcat, names in val.items():
                picked = _pick(names)
                if picked:
                    output[section][subcat] = picked

    return output


# ---------------------------------------------------------------------------
# Gaming domain knowledge selection
# ---------------------------------------------------------------------------

def select_domain_knowledge(skills: dict, family: dict,
                            gaming: bool) -> list[dict]:
    """
    Return the gaming-specific `domain_knowledge` groups for this family,
    but ONLY when gaming=True (i.e. the build targets a video-games posting).

    Each returned item is {"name": str, "detail": str}. Groups are filtered
    by family membership and ordered by the family file's optional
    `domain_knowledge_order` (a list of group names); otherwise file order
    is preserved.

    For non-gaming builds this returns [] so the section is omitted entirely.
    """
    if not gaming:
        return []

    fam_id  = family["id"]
    groups  = skills.get("domain_knowledge", [])
    by_name = {g["name"]: g for g in groups}

    order = family.get("domain_knowledge_order")
    ordered_names = order if order else [g["name"] for g in groups]

    result: list[dict] = []
    for name in ordered_names:
        g = by_name.get(name)
        if g is None:
            print(f"  ⚠  Warning: domain_knowledge '{name}' in family order "
                  f"not found in skills.yaml — skipping.")
            continue
        if not g.get("gaming", False):
            continue
        if fam_id not in g.get("families", []):
            continue
        result.append({
            "name":   g["name"],
            "detail": " ".join(g["detail"].split()),
        })

    return result


# ---------------------------------------------------------------------------
# Aside-skills selection and ordering (pg2 sidebar)
# ---------------------------------------------------------------------------

def select_aside_skills(aside_config: dict | None,
                        posting_text: str | None = None) -> dict | None:
    """
    Return the aside_skills config with page2 sections reordered by posting
    relevance when a posting is provided.

    `aside_config` is the `aside_skills` block from the family file:

        page2:
          title: "Data Science Skillset"
          sections:
            - id: experimentation
              label: "Experimentation & Measurement"
              keywords: [experimentation, A/B testing, ...]
              text: >
                Designed and evaluated experiments...
          programming_latex: 'R, {\\color{red} $\\varheartsuit$} Python, SQL, Bash'

    When no posting is provided the sections are returned in their
    original (curated) order. When a posting is provided, each section
    is scored by the fraction of its keywords that appear in the posting,
    and sections are sorted descending. Ties preserve original order.
    Sections with zero overlap are kept but placed at the end.

    Returns a copy of the config with sections reordered (or the original
    if no posting / no aside_config).
    """
    if not aside_config:
        return aside_config

    if not posting_text:
        return aside_config

    posting_tokens = _tokenize(posting_text)
    page2 = aside_config.get("page2")
    if not page2:
        return aside_config

    sections = list(page2.get("sections") or [])
    if not sections:
        return aside_config

    # Score each section: token overlap between the section's keywords
    # and the posting token-bag.
    def _section_score(section: dict) -> float:
        kws = [k.lower() for k in (section.get("keywords") or [])]
        if not kws:
            return 0.0
        kw_tokens = _tokenize(" ".join(kws))
        if not kw_tokens:
            return 0.0
        overlap = kw_tokens & posting_tokens
        return len(overlap) / len(kw_tokens)

    scored = [(i, s, _section_score(s)) for i, s in enumerate(sections)]
    # Sort by score descending, preserve original index as tiebreak
    scored.sort(key=lambda x: (-x[2], x[0]))
    reordered = [s for _, s, _ in scored]

    return {
        **aside_config,
        "page2": {**page2, "sections": reordered},
    }
