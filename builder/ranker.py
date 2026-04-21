"""
builder/ranker.py
=================
Calls the Anthropic API to do two things when a job posting is provided:

  Stage 1 — RANK
    Score each bullet (0-3) for relevance to the posting. Bullets
    with resolved=True (pre-written variants) are ranked but NOT rewritten.
    Bullets with resolved=False are candidates for rewriting.

  Stage 2 — REVOICE
    For unresolved bullets that scored >= 2, rewrite them to mirror the
    posting's specific language and emphasis while preserving the
    underlying facts.

The ranker also rewrites the summary paragraph to reference the specific
role/company from the posting.
"""

import json
import os
import textwrap
from typing import Any

import anthropic


MODEL = "claude-sonnet-4-6"
client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def rank_and_revoice(selected_companies: list[dict],
                     posting_text: str,
                     family: dict) -> list[dict]:
    """
    Run Stage 1 (rank) then Stage 2 (revoice) against the job posting.
    Returns the same nested structure with bullets reordered within roles
    and unresolved bullets potentially rewritten.
    """
    # Flatten to (company_idx, role_idx, bullet_idx, bullet) for easy indexing
    flat: list[tuple[int, int, int, dict]] = []
    for ci, company in enumerate(selected_companies):
        for ri, role in enumerate(company["roles"]):
            for bi, bullet in enumerate(role["bullets"]):
                flat.append((ci, ri, bi, bullet))

    # Stage 1: rank
    print("    → Stage 1: ranking bullets against posting...")
    scores = _rank_bullets(flat, posting_text, family)

    # Stage 2: revoice unresolved bullets that scored well
    print("    → Stage 2: revoicing unresolved bullets...")
    rewrites = _revoice_bullets(flat, scores, posting_text, family)

    # Apply scores + rewrites back into the structure
    result = _apply_results(selected_companies, flat, scores, rewrites)

    return result


# ---------------------------------------------------------------------------
# Stage 1: Rank
# ---------------------------------------------------------------------------

def _rank_bullets(flat: list, posting_text: str, family: dict) -> dict[str, int]:
    """
    Ask Claude to score each bullet 0-3 for relevance to the posting.
    Returns {bullet_id: score}.
    """
    bullet_list = "\n".join(
        f'  "{b["id"]}": {b["resolved_text"]}'
        for _, _, _, b in flat
    )

    prompt = textwrap.dedent(f"""
        You are helping tailor a resume for the following job posting.
        Score each resume bullet 0-3 for how relevant it is to this posting.

        SCORING GUIDE:
          3 = Directly addresses a requirement or keyword in the posting
          2 = Relevant to the role's general responsibilities
          1 = Tangentially related, adds some context
          0 = Not relevant to this posting

        JOB POSTING:
        {posting_text}

        RESUME BULLETS (id: text):
        {bullet_list}

        Return ONLY a JSON object mapping bullet id to score integer.
        Example: {{"bullet_id_1": 3, "bullet_id_2": 1}}
        No explanation, no markdown fences, just the JSON object.
    """).strip()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"    ⚠  Could not parse ranking response — using default scores.")
        return {b["id"]: 2 for _, _, _, b in flat}


# ---------------------------------------------------------------------------
# Stage 2: Revoice
# ---------------------------------------------------------------------------

def _revoice_bullets(flat: list, scores: dict, posting_text: str,
                     family: dict) -> dict[str, str]:
    """
    For unresolved bullets scoring >= 2, ask Claude to rewrite them to
    mirror the posting's language while preserving facts and outcomes.
    Returns {bullet_id: rewritten_text}.
    """
    candidates = [
        b for _, _, _, b in flat
        if not b.get("resolved", False) and scores.get(b["id"], 0) >= 2
    ]

    if not candidates:
        return {}

    bullet_list = "\n".join(
        f'  "{b["id"]}": {b["resolved_text"]}'
        for b in candidates
    )

    prompt = textwrap.dedent(f"""
        You are tailoring resume bullets for a specific job posting.
        Your task: rewrite each bullet to mirror the posting's language
        and emphasis WITHOUT changing the underlying facts or adding claims.

        RULES:
        - Keep all quantified outcomes exactly as stated (%, $, numbers)
        - Do not add skills, tools, or achievements not in the original
        - Match terminology from the posting where it fits naturally
        - Keep each bullet to 1-2 sentences maximum
        - Write in third-person implied (no "I")
        - Tone and persona: {family["revoicing_persona"]}

        JOB POSTING:
        {posting_text}

        BULLETS TO REWRITE (id: current text):
        {bullet_list}

        Return ONLY a JSON object mapping bullet id to rewritten string.
        No explanation, no markdown fences, just the JSON object.
    """).strip()

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"    ⚠  Could not parse revoicing response — using original text.")
        return {}


# ---------------------------------------------------------------------------
# Apply results
# ---------------------------------------------------------------------------

def _apply_results(selected_companies: list[dict],
                   flat: list,
                   scores: dict[str, int],
                   rewrites: dict[str, str]) -> list[dict]:
    """
    Apply scores and rewrites into the nested structure.
    Within each role, bullets are re-sorted by score descending
    (highest relevance to posting first), with ties preserving
    original order.
    """
    result = []

    for ci, company in enumerate(selected_companies):
        company_copy = {**company, "roles": []}

        for ri, role in enumerate(company["roles"]):
            role_copy = {**role, "bullets": []}

            for bullet in role["bullets"]:
                bid          = bullet["id"]
                score        = scores.get(bid, 1)
                final_text   = rewrites.get(bid, bullet["resolved_text"])

                role_copy["bullets"].append({
                    **bullet,
                    "resolved_text": final_text,
                    "posting_score": score,
                })

            # Re-sort by posting score descending within the role
            role_copy["bullets"].sort(
                key=lambda b: b.get("posting_score", 1),
                reverse=True,
            )
            company_copy["roles"].append(role_copy)

        result.append(company_copy)

    return result


# ---------------------------------------------------------------------------
# Summary revoicing (called separately from build.py if needed)
# ---------------------------------------------------------------------------

def revoice_summary(base_summary: str, posting_text: str,
                    family: dict) -> str:
    """
    Rewrite the base summary paragraph for a specific posting.
    Preserves factual claims; mirrors posting's framing and keywords.
    """
    prompt = textwrap.dedent(f"""
        Rewrite the following resume summary paragraph for a specific job
        posting. Mirror the posting's language and emphasis. Keep all
        factual claims. Do not add credentials or experience not present.
        Keep to 3-4 sentences maximum.

        Persona / tone: {family["revoicing_persona"]}

        JOB POSTING:
        {posting_text}

        BASE SUMMARY:
        {base_summary}

        Return ONLY the rewritten summary paragraph. No explanation.
    """).strip()

    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()
