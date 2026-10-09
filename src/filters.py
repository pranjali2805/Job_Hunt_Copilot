
import re


def normalize_phrase(text):
    """Normalize titles and phrases for consistent matching."""
    return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))


def contains_phrase(text, phrase):
    """Match complete words/phrases, not arbitrary substrings."""
    normalized_text = f" {normalize_phrase(text)} "
    normalized_phrase = f" {normalize_phrase(phrase)} "
    return bool(normalized_phrase.strip()) and (
        normalized_phrase in normalized_text
    )


# Job families outside the current target scope.
# These rules take precedence over broad matches such as "growth".
EXCLUDED_TITLE_PHRASES = [
    "sales",
    "account executive",
    "sales development representative",
    "business development representative",
    "software engineer",
    "software developer",
    "backend engineer",
    "frontend engineer",
    "full stack developer",
    "data engineer",
    "qa engineer",
    "executive assistant",
    "recruiter",
    "talent acquisition",
]


def title_rejection_reason(title, cfg):
    """Return a rejection reason, or None when the title passes."""
    title_norm = normalize_phrase(title)

    if not title_norm:
        return "missing_title"

    if any(
        contains_phrase(title_norm, phrase)
        for phrase in EXCLUDED_TITLE_PHRASES
    ):
        return "excluded_job_family"

    excluded_levels = cfg.get("titles_exclude", [])

    # 'staff' is also part of the target title 'Chief of Staff'.
    # Do not reject that target merely because it contains 'staff'.
    is_chief_of_staff = contains_phrase(title_norm, "chief of staff")

    for phrase in excluded_levels:
        phrase_norm = normalize_phrase(phrase)

        if phrase_norm == "staff" and is_chief_of_staff:
            continue

        if contains_phrase(title_norm, phrase_norm):
            return f"excluded_seniority:{phrase_norm}"

    included_titles = cfg.get("titles_include", [])

    if not any(
        contains_phrase(title_norm, phrase)
        for phrase in included_titles
    ):
        return "title_not_in_target_list"

    return None


def location_rejection_reason(location, cfg):
    """Return a rejection reason, or None when the location passes."""
    location_norm = normalize_phrase(location)

    # Preserve the existing behavior: blank locations are not rejected
    # solely because the location is missing.
    if not location_norm:
        return None

    allowed_locations = cfg.get("locations", [])

    if not any(
        contains_phrase(location_norm, allowed)
        for allowed in allowed_locations
    ):
        return "location_not_allowed"

    return None


def experience_rejection_reason(jd, cfg):
    """
    Reject a job when an explicit stated experience requirement
    exceeds max_years. Ranges use their upper bound.
    """
    max_years = cfg.get("max_years")
    if max_years is None:
        return None

    text = (jd or "").lower()

    pattern = re.compile(
        r"\b(?P<first>\d{1,2})\s*"
        r"(?:(?:-|to)\s*(?P<second>\d{1,2}))?\s*\+?\s*"
        r"(?:years?|yrs?)\b"
    )

    required_values = []

    for match in pattern.finditer(text):
        upper = match.group("second") or match.group("first")
        required_values.append(int(upper))

    if required_values and max(required_values) > max_years:
        return "experience_exceeds_max_years"

    return None


def filter_job(job, cfg):
    """
    Return (keep_job, reason).

    Rejections are explicit so the ranking audit can explain
    why a listing was excluded.
    """
    title_reason = title_rejection_reason(job.get("title", ""), cfg)
    if title_reason:
        return False, title_reason

    location_reason = location_rejection_reason(
        job.get("location", ""), cfg
    )
    if location_reason:
        return False, location_reason

    experience_reason = experience_rejection_reason(
        job.get("jd", ""), cfg
    )
    if experience_reason:
        return False, experience_reason

    return True, "passed"