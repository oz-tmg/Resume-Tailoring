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
"""


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
                    family_id: str) -> list[dict]:
    """
    Walk the selected company/role/bullet structure and swap in
    pre-written variants where available.

    Also filters sub_bullets by family_id so only relevant sub-bullets
    are passed to the renderer.

    Returns the same nested structure with each bullet enriched by:
      - "resolved_text":   str        — the text to use downstream
      - "resolved":        bool       — True if a variant was found
      - "resolved_subs":   list[dict] — filtered, resolved sub-bullets
      - "variant_options": list[dict] — alternates available to the ranker
                                        (empty unless >1 variant exists)
    """
    result = []

    for company in selected_companies:
        company_copy = {**company, "roles": []}

        for role in company["roles"]:
            role_copy = {**role, "bullets": []}

            for bullet in role["bullets"]:
                variants = bullet.get("variants", {})

                if family_id in variants:
                    resolved_text, resolved_subs, options = \
                        _resolve_variant_options(
                            variants[family_id], bullet, family_id)
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
                })

            company_copy["roles"].append(role_copy)

        result.append(company_copy)

    return result
