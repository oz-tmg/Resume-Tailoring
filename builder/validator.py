"""
builder/validator.py
====================
Validates the full content + families layer for referential integrity
and schema correctness. Run via:  python build.py --validate

Checks:
  - All bullet ids referenced in family files exist in experience YAMLs
  - All role ids in experience_roles_order exist in experience YAMLs
  - All bullets have required fields
  - All variants reference valid family IDs
  - No duplicate bullet ids across experience files
  - Summary refs in family files exist in summaries.yaml
  - Skills referenced in family order files exist in skills.yaml
"""

from pathlib import Path
from builder.loader import (load_family, load_all_experience,
                            load_skills, load_summaries)

FAMILY_IDS = {"DA", "AE", "DE", "DS", "MLE", "ECON"}
FAMILIES   = ["data_analyst", "analytics_engineer", "data_engineer",
              "data_scientist", "ml_engineer", "economist"]


def validate_all(root: Path) -> bool:
    errors:   list[str] = []
    warnings: list[str] = []

    print("\n  Validating content layer...")

    # Load raw data
    experience = load_all_experience(root / "content" / "experience")
    skills     = load_skills(root / "content" / "skills.yaml")
    summaries  = load_summaries(root / "content" / "summaries.yaml")

    bullet_ids = set(experience["by_id"].keys())
    role_ids   = {
        role["id"]
        for company in experience["companies"]
        for role in company["roles"]
    }

    # Build flat skill name set
    skill_names: set[str] = set()
    for cat_val in skills.values():
        if isinstance(cat_val, list):
            for s in cat_val:
                skill_names.add(s["name"])
        elif isinstance(cat_val, dict):
            for subcat_val in cat_val.values():
                if isinstance(subcat_val, list):
                    for s in subcat_val:
                        skill_names.add(s["name"])

    # Check for duplicate bullet ids
    seen_ids: dict[str, str] = {}
    for company in experience["companies"]:
        for role in company["roles"]:
            for bullet in role["bullets"]:
                bid = bullet["id"]
                if bid in seen_ids:
                    errors.append(
                        f"Duplicate bullet id '{bid}' — "
                        f"found in both '{seen_ids[bid]}' and '{role['id']}'"
                    )
                else:
                    seen_ids[bid] = role["id"]

    # Validate variants use legal family IDs and well-formed alternates
    for bid, bullet in experience["by_id"].items():
        for vfam, ventry in bullet.get("variants", {}).items():
            if vfam not in FAMILY_IDS:
                errors.append(
                    f"Bullet '{bid}' has variant for unknown family '{vfam}'"
                )
            # Multi-variant (list) form: each alternate needs id + text,
            # ids must be unique, and at most one may be flagged default.
            if isinstance(ventry, list):
                if not ventry:
                    errors.append(
                        f"Bullet '{bid}' variant '{vfam}' is an empty list"
                    )
                alt_ids: list[str] = []
                default_count = 0
                for i, alt in enumerate(ventry):
                    if not isinstance(alt, dict):
                        errors.append(
                            f"Bullet '{bid}' variant '{vfam}' alternate #{i} "
                            f"must be a mapping with 'id' and 'text'"
                        )
                        continue
                    if "text" not in alt:
                        errors.append(
                            f"Bullet '{bid}' variant '{vfam}' alternate "
                            f"'{alt.get('id', i)}' is missing 'text'"
                        )
                    if "id" not in alt:
                        warnings.append(
                            f"Bullet '{bid}' variant '{vfam}' alternate #{i} "
                            f"has no 'id' (a positional id will be used)"
                        )
                    else:
                        alt_ids.append(alt["id"])
                    if alt.get("default"):
                        default_count += 1
                if len(alt_ids) != len(set(alt_ids)):
                    errors.append(
                        f"Bullet '{bid}' variant '{vfam}' has duplicate "
                        f"alternate ids"
                    )
                if default_count == 0:
                    warnings.append(
                        f"Bullet '{bid}' variant '{vfam}' has no alternate "
                        f"flagged default — first will be used for base builds"
                    )
                elif default_count > 1:
                    errors.append(
                        f"Bullet '{bid}' variant '{vfam}' has {default_count} "
                        f"alternates flagged default — only one is allowed"
                    )

    # Validate each family file
    for fam_name in FAMILIES:
        fam_path = root / "families" / f"{fam_name}.yaml"
        if not fam_path.exists():
            errors.append(f"Missing family file: {fam_path}")
            continue

        fam = load_family(fam_path)
        label = fam["label"]

        # summary_ref exists
        if fam["summary_ref"] not in summaries:
            errors.append(
                f"[{label}] summary_ref '{fam['summary_ref']}' "
                f"not found in summaries.yaml"
            )

        # role ids in experience_roles_order exist
        for rid in fam.get("experience_roles_order", []):
            if rid not in role_ids:
                errors.append(
                    f"[{label}] experience_roles_order references "
                    f"unknown role '{rid}'"
                )

        # bullet ids in priority_bullets exist
        bs = fam.get("bullet_selection", {})
        for bid in bs.get("priority_bullets", []):
            if bid not in bullet_ids:
                warnings.append(
                    f"[{label}] priority_bullets references "
                    f"unknown bullet '{bid}'"
                )

        # bullet ids in exclude_bullets exist
        for bid in bs.get("exclude_bullets", []):
            if bid not in bullet_ids:
                warnings.append(
                    f"[{label}] exclude_bullets references "
                    f"unknown bullet '{bid}'"
                )

        # Skills in skills_order exist in master skills.yaml
        def _check_skills(order_node, path=""):
            if isinstance(order_node, list):
                for name in order_node:
                    if name not in skill_names:
                        warnings.append(
                            f"[{label}] skills_order{path} references "
                            f"unknown skill '{name}'"
                        )
            elif isinstance(order_node, dict):
                for k, v in order_node.items():
                    _check_skills(v, f".{k}")

        _check_skills(fam.get("skills_order", {}))

    # Report
    print(f"\n  {'─'*50}")
    if errors:
        print(f"  ✗ {len(errors)} ERROR(S) found:\n")
        for e in errors:
            print(f"    • {e}")
    if warnings:
        print(f"  ⚠  {len(warnings)} WARNING(S):\n")
        for w in warnings:
            print(f"    • {w}")
    if not errors and not warnings:
        print("  ✓ All checks passed.")
    elif not errors:
        print("\n  ✓ No errors — build can proceed (review warnings).")

    print(f"  {'─'*50}\n")
    return len(errors) == 0
