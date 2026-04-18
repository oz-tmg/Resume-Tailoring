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

    Mutates a copy — does not modify the original loader output.

    Returns the same nested structure with each bullet enriched by:
      - "resolved_text":  str   — the text to use downstream
      - "resolved":       bool  — True if a variant was found
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

                role_copy["bullets"].append({
                    **bullet,
                    "resolved_text": resolved_text,
                    "resolved":      resolved,
                })

            company_copy["roles"].append(role_copy)

        result.append(company_copy)

    return result
