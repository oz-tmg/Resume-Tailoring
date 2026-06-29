"""
builder/resolver.py
===================
Resolves bullet text and role summaries before they reach the renderer
or Claude revoicing.

Priority order for a bullet's final text:
  1. Pre-written variant for this family (variants.<FAMILY_ID> in YAML)
  2. Game-industry variant (variants.GAMES) — only when industry="games"
  3. Base text (bullet["text"])

Bullets with a pre-written variant (family or GAMES) are marked
resolved=True so the ranker/revoicer knows not to rewrite them
(though it may still re-rank them for posting relevance).

Bullets without a variant get resolved=False, signalling to the revoicer
that Claude should apply the family's revoicing_persona to them.

Multi-variant bullets
---------------------
A family entry under `variants` can take two shapes:

  # 1. Single variant (string) — the original, still supported:
  variants:
    DA: >
      One pre-written DA phrasing.

  # 2. Multiple alternates (list of dicts) — pick the best per context:
  variants:
    DA:
      - id: concise
        default: true            # used for base (no-posting) builds
        text: >
          A tight, general-purpose DA phrasing.
      - id: gaming_detailed
        text: >
          A richer, gaming-specific DA phrasing.
        sub_bullets:             # optional, overrides bullet-level subs
          - id: da_detail_1
            text: > ...
            families: [DA, DS]

For base builds the resolver picks the `default: true` alternate (or the
first one if none is flagged). It also attaches `variant_options` — the
full, resolved list of alternates — so the posting-stage ranker can score
each one against the job description and swap in the best fit
(see builder/ranker.py::_select_variants).

Role summaries
--------------
Priority order for a role's resolved_summary:
  1. summary_variants.<FAMILY_ID> — family-specific role description
  2. base summary field

This allows role summaries to emphasise different angles of the same role
(e.g. DS framing vs DE framing) while staying factually honest.
"""

GAMES_KEY = "GAMES"


def _resolve_subs(raw_subs: list[dict], family_id: str) -> list[dict]:
    """Filter sub_bullets by family and attach resolved_text."""
    resolved_subs = []
    for sub in raw_subs:
        if family_id in sub.get("families", [family_id]):
            resolved_subs.append({
                **sub,
                "resolved_text": sub["text"].strip(),
            })
    return resolved_subs


def _resolve_variant_options(family_entry,
                             bullet: dict,
                             family_id: str) -> tuple[str, list[dict], list[dict]]:
    """
    Normalise a family's `variants[family_id]` entry (string OR list) into:
      - default_text:    str         — text to use for base builds
      - default_subs:    list[dict]  — resolved sub-bullets for that text
      - options:         list[dict]  — every alternate, each as
                                       {id, text, resolved_subs}
                                       (empty when there is only one variant)

    Sub-bullet precedence per alternate:
      - if the alternate defines its own `sub_bullets`, those are used
        (filtered by family);
      - otherwise it inherits the bullet-level `sub_bullets`.
    """
    bullet_subs = bullet.get("sub_bullets", [])

    # --- Shape 1: plain string (the original single-variant form) ---------
    if isinstance(family_entry, str):
        text = family_entry.strip()
        subs = _resolve_subs(bullet_subs, family_id)
        return text, subs, []

    # --- Shape 2: list of alternate dicts ---------------------------------
    options: list[dict] = []
    default_idx = 0
    for i, alt in enumerate(family_entry):
        alt_subs_raw = alt["sub_bullets"] if "sub_bullets" in alt else bullet_subs
        options.append({
            "id":            alt.get("id", f"variant_{i}"),
            "text":          alt["text"].strip(),
            "resolved_subs": _resolve_subs(alt_subs_raw, family_id),
        })
        if alt.get("default"):
            default_idx = i

    default = options[default_idx]
    return default["text"], default["resolved_subs"], options


def resolve_bullets(selected_companies: list[dict],
                    family_id: str,
                    industry: str = "agnostic",
                    split_section_ids: set | None = None) -> list[dict]:
    """
    Walk the selected company/role/bullet structure and swap in
    pre-written variants where available.

    Variant lookup priority:
      1. variants[family_id]         — family-specific rewrite
      2. variants[GAMES_KEY]         — games-industry rewrite (only if
                                       industry == "games" and no family
                                       variant exists)
      3. bullet["text"]              — neutral base text

    Also:
    - Filters sub_bullets by family_id so only relevant sub-bullets
      reach the renderer.
    - Resolves role summaries: picks summary_variants[family_id] when
      present, falls back to role["summary"].
    - Annotates each role with _split_sections=True when its id appears
      in split_section_ids, enabling the two-section "Responsibilities /
      Outcomes" layout in the template.
    - Carries each bullet's category field through ("work" by default).

    Returns the same nested structure with each bullet enriched by:
      - "resolved_text":   str        — the text to use downstream
      - "resolved":        bool       — True if a curated variant was found
      - "resolved_subs":   list[dict] — filtered, resolved sub-bullets
      - "variant_options": list[dict] — alternates available to the ranker
                                        (empty unless >1 variant exists)
      - "category":        str        — "work" (default) or "outcome"
    And each role enriched by:
      - "resolved_summary":  str     — the summary to use in the template
      - "_split_sections":   bool    — True when two-section layout applies
    """
    use_games = (industry == "games")
    split_ids = split_section_ids or set()
    result = []

    for company in selected_companies:
        company_copy = {**company, "roles": []}

        for role in company["roles"]:
            # ------------------------------------------------------------------
            # Resolve role summary
            # ------------------------------------------------------------------
            summary_variants = role.get("summary_variants") or {}
            if family_id in summary_variants:
                resolved_summary = summary_variants[family_id].strip()
            else:
                resolved_summary = (role.get("summary") or "").strip()

            role_copy = {
                **role,
                "bullets": [],
                "resolved_summary": resolved_summary,
                "_split_sections": role["id"] in split_ids,
            }

            # ------------------------------------------------------------------
            # Resolve bullets
            # ------------------------------------------------------------------
            for bullet in role["bullets"]:
                variants = bullet.get("variants") or {}

                if family_id in variants:
                    # Family-specific variant — highest priority
                    # (string OR multi-alternate list, normalised by helper)
                    resolved_text, resolved_subs, options = \
                        _resolve_variant_options(
                            variants[family_id], bullet, family_id)
                    resolved = True
                elif use_games and GAMES_KEY in variants:
                    # Games-industry variant — used when no family variant exists
                    resolved_text, resolved_subs, options = \
                        _resolve_variant_options(
                            variants[GAMES_KEY], bullet, family_id)
                    resolved = True
                else:
                    resolved_text = bullet["text"].strip()
                    resolved_subs = _resolve_subs(
                        bullet.get("sub_bullets", []), family_id)
                    options       = []
                    resolved      = False

                role_copy["bullets"].append({
                    **bullet,
                    "resolved_text":   resolved_text,
                    "resolved":        resolved,
                    "resolved_subs":   resolved_subs,
                    "variant_options": options,
                    "category":        bullet.get("category", "work"),
                })

            company_copy["roles"].append(role_copy)

        result.append(company_copy)

    return result
