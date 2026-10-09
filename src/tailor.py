import re
import json

from .llm import chat_json
from sentence_transformers import SentenceTransformer, util


# Separate model from the matching module so this validator
# can independently check whether an LLM bullet is actually
# similar to the source fact it claims to be based on.
_validator_model = None


def _validator():
    global _validator_model

    if _validator_model is None:
        _validator_model = SentenceTransformer("all-MiniLM-L6-v2")

    return _validator_model


SYSTEM = """
You are a strict resume editor.

You rewrite resume content for ONE job description.

The most important rule:
EVERY CLAIM MUST BE SUPPORTED BY THE PROVIDED SOURCE FACTS.

HARD RULES:
- Use ONLY the facts provided in ENTRIES and PROFILE.
- Never invent employers, tools, responsibilities, numbers, achievements,
  outcomes, customers, teams, business contexts, or impact.
- Never infer an outcome that is not explicitly stated.
- Never turn an activity into an achievement unless the achievement
  is explicitly present in a source fact.
- Every resume bullet MUST identify the exact source fact(s) it was
  derived from.
- A bullet may use 1 or 2 source facts, but must not introduce
  information outside those facts.
- Every number in a bullet must appear in its selected source fact(s).
- You may reorder information, shorten wording, and mirror terminology
  from the job description ONLY when that terminology truthfully
  describes the source fact.
- Do not keyword stuff.
- Bullets should normally start with a strong verb.
- Maximum 22 words per bullet when possible.
- Use 2-3 bullets per selected entry.
- Select the 4-6 most relevant entries.
- Prefer fewer strong claims over impressive-sounding unsupported claims.
- If a claim cannot be supported, OMIT it.

Return ONLY valid JSON in this structure:

{
  "summary": "...",
  "skills": ["skill1", "skill2"],
  "entries": [
    {
      "id": "entry-id",
      "bullets": [
        {
          "text": "...",
          "source_facts": ["entry-id::fact_1"]
        }
      ]
    }
  ],
  "jd_keywords": ["keyword1", "keyword2"],
  "cold_message": "..."
}

IMPORTANT:
source_facts must contain only IDs from the supplied ENTRIES.
Do not invent source-fact IDs.
"""


NUM = re.compile(r"\d+(?:[.,]\d+)*%?")


def nums(text):
    return {
        n.strip(".,")
        for n in NUM.findall(text or "")
    }


def fact_id(entry_id, index):
    return f"{entry_id}::fact_{index + 1}"


def build_fact_map(top_items):
    facts = {}

    for entry in top_items:
        entry_id = entry["id"]

        for index, fact in enumerate(entry.get("facts", [])):
            facts[fact_id(entry_id, index)] = fact

    return facts


def semantic_similarity(text, source_fact):
    model = _validator()

    embeddings = model.encode(
        [text, source_fact],
        convert_to_tensor=True
    )

    return float(
        util.cos_sim(
            embeddings[0],
            embeddings[1]
        ).item()
    )


def validate_bullet(text, source_ids, fact_map):
    problems = []

    if not source_ids:
        return False, ["missing source fact"], text

    valid_sources = [
        fact_map[s]
        for s in source_ids
        if s in fact_map
    ]

    if not valid_sources:
        return False, ["invalid source fact"], text

    # Every number must occur in at least one of the facts
    allowed_numbers = set()

    for fact in valid_sources:
        allowed_numbers.update(nums(fact))

    bad_numbers = nums(text) - allowed_numbers

    if bad_numbers:
        problems.append(
            f"unsupported numbers: {sorted(bad_numbers)}"
        )

    # At least one cited source fact must be semantically close
    similarities = [
        semantic_similarity(text, fact)
        for fact in valid_sources
    ]

    best_similarity = max(similarities)

    if best_similarity < 0.52:
        problems.append(
            f"weak source similarity: {best_similarity:.2f}"
        )

    if problems:
        # Safe fallback: use the strongest cited source fact
        best_fact = valid_sources[
            similarities.index(best_similarity)
        ]

        return False, problems, best_fact

    return True, [], text


def clean_output(raw_output, top_items, profile_text):
    fact_map = build_fact_map(top_items)

    review_flags = []

    cleaned_entries = []

    for entry in raw_output.get("entries", []):
        entry_id = entry.get("id")

        valid_entry_ids = {
            item["id"]
            for item in top_items
        }

        if entry_id not in valid_entry_ids:
            review_flags.append(
                f"Unknown entry ID: {entry_id}"
            )
            continue

        cleaned_bullets = []

        for bullet in entry.get("bullets", []):
            if isinstance(bullet, str):
                text = bullet
                source_ids = []
            else:
                text = bullet.get("text", "")
                source_ids = bullet.get(
                    "source_facts",
                    []
                )

            ok, problems, safe_text = validate_bullet(
                text,
                source_ids,
                fact_map
            )

            if not ok:
                review_flags.append(
                    f"{entry_id}: {'; '.join(problems)}"
                )

            cleaned_bullets.append(safe_text)

        if cleaned_bullets:
            cleaned_entries.append({
                "id": entry_id,
                "bullets": cleaned_bullets
            })

    # Skills are limited to skills already present
    allowed_skills = set()

    for item in top_items:
        for skill in item.get("skills", []):
            allowed_skills.add(skill)

    cleaned_skills = [
        skill
        for skill in raw_output.get("skills", [])
        if skill in allowed_skills
    ]

    # Ensure numbers cannot sneak into summary/cold message
    allowed_profile_numbers = nums(profile_text)

    summary = raw_output.get("summary", "")
    cold_message = raw_output.get("cold_message", "")

    unsupported_summary_numbers = (
        nums(summary) - allowed_profile_numbers
    )

    unsupported_cold_numbers = (
        nums(cold_message) - allowed_profile_numbers
    )

    if unsupported_summary_numbers:
        review_flags.append(
            f"Summary unsupported numbers: "
            f"{sorted(unsupported_summary_numbers)}"
        )

    if unsupported_cold_numbers:
        review_flags.append(
            f"Cold message unsupported numbers: "
            f"{sorted(unsupported_cold_numbers)}"
        )

    return {
        "summary": summary,
        "skills": cleaned_skills,
        "entries": cleaned_entries,
        "jd_keywords": raw_output.get(
            "jd_keywords",
            []
        )[:10],
        "cold_message": cold_message,
        "review_flag": " | ".join(review_flags)
    }


def tailor(job, top_items, profile_text):
    entries = []

    for item in top_items:
        entry = {
            "id": item["id"],
            "title": item["title"],
            "org": item.get("org", ""),
            "facts": [],
            "skills": item.get("skills", [])
        }

        for index, fact in enumerate(
            item.get("facts", [])
        ):
            entry["facts"].append({
                "id": fact_id(
                    item["id"],
                    index
                ),
                "text": fact
            })

        entries.append(entry)

    user = (
        f"JOB TITLE: {job['title']}\n"
        f"COMPANY: {job['company']}\n"
        f"JOB DESCRIPTION:\n{job['jd'][:5000]}\n\n"
        f"ENTRIES:\n"
        f"{json.dumps(entries, ensure_ascii=False)}\n\n"
        f"PROFILE:\n"
        f"{profile_text}"
    )

    raw_output = chat_json(
        SYSTEM,
        user
    )

    return clean_output(
        raw_output,
        top_items,
        profile_text
    )