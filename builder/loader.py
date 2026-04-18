"""
builder/loader.py
=================
Loads and normalises all YAML source files into plain Python dicts/lists.
No filtering or business logic here — just clean, validated data structures
that the rest of the pipeline can consume.
"""

from pathlib import Path
from typing import Any
import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _require(obj: dict, keys: list[str], context: str):
    for k in keys:
        if k not in obj:
            raise ValueError(f"Missing required field '{k}' in {context}")


# ---------------------------------------------------------------------------
# Family loader
# ---------------------------------------------------------------------------

def load_family(path: Path) -> dict:
    """
    Load a families/*.yaml file and return a normalised dict.
    Validates required top-level keys.
    """
    data = _load(path)
    _require(data, ["id", "label", "summary_ref", "bullet_selection",
                    "skills_order", "experience_roles_order",
                    "header_title", "revoicing_persona"], str(path))
    return data


# ---------------------------------------------------------------------------
# Experience loader
# ---------------------------------------------------------------------------

def load_all_experience(experience_dir: Path) -> dict[str, dict]:
    """
    Load all company YAML files from content/experience/.
    Returns a flat dict keyed by bullet id for O(1) lookup:

        {
          "kix_sfg_forecasting_model": {
            "id":        "kix_sfg_forecasting_model",
            "text":      "...",
            "families":  ["DS", "DA", "ECON"],
            "keywords":  [...],
            "tier":      1,
            "variants":  {"DA": "...", "DS": "...", "ECON": "..."},
            "_role_id":  "kix_sfg_lead",
            "_company":  "Kixeye & Stillfront Group AB",
            "_role":     { full role dict }
          },
          ...
        }

    Also returns a separate structure preserving company → role → bullets
    order for the renderer:

        [
          {
            "company":  "Kixeye & Stillfront Group AB",
            "division": "Mobile Games",
            "logo":     "...",
            "roles": [
              {
                "id":      "kix_sfg_lead",
                "title":   "Lead Data Analyst...",
                "start":   "2022-02",
                ...
                "bullets": [ bullet_dict, ... ]
              }
            ]
          }
        ]
    """
    bullet_index: dict[str, dict] = {}
    companies: list[dict] = []

    for yaml_file in sorted(experience_dir.glob("*.yaml")):
        data = _load(yaml_file)
        company_entry = {
            "company":  data["company"],
            "division": data.get("division", ""),
            "logo":     data.get("logo", ""),
            "roles":    [],
        }

        for role in data.get("roles", []):
            _require(role, ["id", "title", "start", "end", "bullets"],
                     f"{yaml_file}:{role.get('id','?')}")

            role_entry = {**role, "bullets": []}

            for bullet in role.get("bullets", []):
                _require(bullet, ["id", "text", "families", "keywords", "tier"],
                         f"{yaml_file}:{role['id']}:{bullet.get('id','?')}")

                enriched = {
                    **bullet,
                    "_role_id":  role["id"],
                    "_company":  data["company"],
                    "_role":     role,
                }
                bullet_index[bullet["id"]] = enriched
                role_entry["bullets"].append(enriched)

            company_entry["roles"].append(role_entry)

        companies.append(company_entry)

    return {"by_id": bullet_index, "companies": companies}


# ---------------------------------------------------------------------------
# Skills loader
# ---------------------------------------------------------------------------

def load_skills(path: Path) -> dict:
    """
    Load content/skills.yaml.
    Returns the raw nested dict — the selector handles ordering per family.
    """
    return _load(path)


# ---------------------------------------------------------------------------
# Education loader
# ---------------------------------------------------------------------------

def load_education(path: Path) -> dict:
    """
    Load content/education.yaml.
    Returns {"education": [...], "certifications": [...]}.
    """
    data = _load(path)
    return {
        "education":      data.get("education", []),
        "certifications": data.get("certifications", []),
    }


# ---------------------------------------------------------------------------
# Summaries loader
# ---------------------------------------------------------------------------

def load_summaries(path: Path) -> dict[str, dict]:
    """
    Load content/summaries.yaml.
    Returns a dict keyed by summary id (e.g. "data_scientist").
    Each value is the full summary block including text and revoicing_persona.
    """
    data = _load(path)
    return data.get("summaries", {})
