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

Priority order for a role's resolved_summary:
  1. summary_variants.<FAMILY_ID> — family-specific role description
  2. base summary field

This allows role summaries to emphasise different angles of the same role
(e.g. DS framing vs DE framing) while staying factually honest.
"""

GAMES_KEY = "GAMES"


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
      - "resolved_text":  str        — the text to use downstream
      - "resolved":       bool       — True if a curated variant was found
      - "resolved_subs":  list[dict] — filtered, resolved sub-bullets
      - "category":       str        — "work" (default) or "outcome"
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
                    resolved_text = variants[family_id].strip()
                    resolved = True
                elif use_games and GAMES_KEY in variants:
                    # Games-industry variant — used when no family variant exists
                    resolved_text = variants[GAMES_KEY].strip()
                    resolved = True
                else:
                    resolved_text = bullet["text"].strip()
                    resolved = False

                # Resolve sub_bullets — filter by family, resolve text
                raw_subs = bullet.get("sub_bullets") or []
                resolved_subs = []
                for sub in raw_subs:
                    if family_id in sub.get("families", [family_id]):
                        resolved_subs.append({
                            **sub,
                            "resolved_text": sub["text"].strip(),
                        })

                role_copy["bullets"].append({
                    **bullet,
                    "resolved_text": resolved_text,
                    "resolved":      resolved,
                    "resolved_subs": resolved_subs,
                    "category":      bullet.get("category", "work"),
                })

            company_copy["roles"].append(role_copy)

        result.append(company_copy)

    return result
