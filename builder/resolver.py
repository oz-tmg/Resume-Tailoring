"""
builder/resolver.py
===================
Resolves bullet text before it reaches the renderer or Claude revoicing.

Priority order for a bullet's final text:
  1. Pre-written variant for this family (variants.<FAMILY_ID> in YAML)
  2. Base text (bullet["text"])

Bullets with a pre-written variant are marked resolved=True so the
ranker/revoicer knows not to send them through Claude for rewriting
(though it may still re-rank them for posting relevance).

Bullets without a variant get resolved=False, signalling to the revoicer
that Claude should apply the family's revoicing_persona to them.
"""


def resolve_bullets(selected_companies: list[dict],
                    family_id: str) -> list[dict]:
    """
    Walk the selected company/role/bullet structure and swap in
    pre-written variants where available.

    Also filters sub_bullets by family_id so only relevant sub-bullets
    are passed to the renderer.

    Returns the same nested structure with each bullet enriched by:
      - "resolved_text":  str        — the text to use downstream
      - "resolved":       bool       — True if a variant was found
      - "resolved_subs":  list[dict] — filtered, resolved sub-bullets
    """
    result = []

    for company in selected_companies:
        company_copy = {**company, "roles": []}

        for role in company["roles"]:
            role_copy = {**role, "bullets": []}

            for bullet in role["bullets"]:
                variants = bullet.get("variants", {})
                if family_id in variants:
                    resolved_text = variants[family_id].strip()
                    resolved      = True
                else:
                    resolved_text = bullet["text"].strip()
                    resolved      = False

                # Resolve sub_bullets — filter by family, resolve text
                raw_subs = bullet.get("sub_bullets", [])
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
                })

            company_copy["roles"].append(role_copy)

        result.append(company_copy)

    return result
