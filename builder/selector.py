"""
builder/selector.py
===================
Applies family rules to select and order bullets and skills.
Pure Python — no I/O, no API calls.

Returns a structured list of companies → roles → selected bullets,
preserving the ordering defined in the family file's
`experience_roles_order`.
"""

from typing import Any


# ---------------------------------------------------------------------------
# Bullet selection
# ---------------------------------------------------------------------------

def select_bullets(experience: dict, family: dict) -> list[dict]:
    """
    Apply family rules to produce an ordered list of role dicts, each
    containing only the bullets selected for this family.

    Selection logic (in order of precedence):
      1. Role must appear in family["experience_roles_order"]
      2. Bullet must list this family in its "families" field
      3. Bullet must NOT be in family["bullet_selection"]["exclude_bullets"]
      4. Bullet tier must be <= family["bullet_selection"]["min_tier"]
         (lower number = more important, so tier 1 passes min_tier 2,
          but tier 3 does NOT pass min_tier 2)
      5. Count of selected bullets per role is capped by
         family["bullet_selection"]["max_bullets_per_role"]
      6. Priority bullets (listed in family config) are moved to the front
         within each role before the cap is applied.
    """
    fam_id       = family["id"]
    rules        = family["bullet_selection"]
    min_tier     = rules.get("min_tier", 2)
    max_per_role = rules.get("max_bullets_per_role", {})
    priority_ids = set(rules.get("priority_bullets", []))
    exclude_ids  = set(rules.get("exclude_bullets", []))
    role_order   = family["experience_roles_order"]

    # Build a lookup: role_id → (company_meta, role_dict)
    role_lookup: dict[str, tuple[dict, dict]] = {}
    for company in experience["companies"]:
        for role in company["roles"]:
            role_lookup[role["id"]] = (company, role)

    selected_companies: list[dict] = []
    # Track which companies we've already started building
    company_map: dict[str, dict] = {}

    for role_id in role_order:
        if role_id not in role_lookup:
            print(f"  ⚠  Warning: role '{role_id}' in family config "
                  f"not found in experience files — skipping.")
            continue

        company_meta, role = role_lookup[role_id]
        cap = max_per_role.get(role_id, 4)

        if cap == 0:
            continue  # Entire role suppressed for this family

        # Filter bullets
        passing = []
        for bullet in role["bullets"]:
            bid = bullet["id"]

            if bid in exclude_ids:
                continue
            if fam_id not in bullet.get("families", []):
                continue
            if bullet.get("tier", 99) > min_tier:
                continue

            passing.append(bullet)

        if not passing:
            continue  # No bullets survived — omit role entirely

        # Sort: priority bullets first (preserving relative order within
        # each group), then remaining bullets by tier ascending
        priority   = [b for b in passing if b["id"] in priority_ids]
        remaining  = [b for b in passing if b["id"] not in priority_ids]
        remaining.sort(key=lambda b: b.get("tier", 99))
        ordered    = priority + remaining

        # Apply cap
        capped = ordered[:cap]

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
            "bullets": capped,
        })

    return selected_companies


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
