import os
import re
import yaml
import datetime as dt

from src import fetch, match, tailor, render, tracker, notify


# Load configuration and personal data
cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
kb = yaml.safe_load(open("knowledge_base.yaml", encoding="utf-8"))
profile = yaml.safe_load(open("profile.yaml", encoding="utf-8"))

profile_text = str(profile)


def word(text, keyword):
    return re.search(
        rf"(?<![a-z]){re.escape(keyword)}(?![a-z])",
        text.lower()
    ) is not None


def keep(job):
    title = job["title"].lower()

    # Must match at least one target title
    if not any(
        word(title, k)
        for k in cfg["titles_include"]
    ):
        return False

    # Must not contain excluded seniority/title terms
    if any(
        word(title, k)
        for k in cfg["titles_exclude"]
    ):
        return False

    # Location filter
    loc = job["location"].lower()

    if loc and not any(
        word(loc, x)
        for x in cfg["locations"]
    ):
        return False

    # Experience filter
    years = re.findall(
        r"\b(\d+)\s*(?:-\s*\d+)?\s*(?:years?|yrs?)\b",
        job["jd"].lower()
    )

    if years and min(int(y) for y in years) > cfg["max_years"]:
        return False

    return True


def slug(text):
    return re.sub(
        r"[^a-z0-9]+",
        "-",
        text.lower()
    ).strip("-")[:50]


def main():
    # Connect to Google Sheet
    ws = tracker.get_sheet()

    # Avoid adding the same job repeatedly
    seen = tracker.existing_links(ws)

    # Fetch and filter jobs
    jobs = [
        j
        for j in fetch.fetch_all()
        if j["url"]
        and j["url"] not in seen
        and keep(j)
    ]

    print(f"{len(jobs)} new matching jobs")

    # Score every matching job
    for j in jobs:
        top, sem = match.rank(
            j["jd"],
            kb
        )

        j["top"] = top
        j["sem"] = sem

        j["score"], j["gaps"] = match.score(
            j,
            sem,
            kb,
            cfg,
            profile_text
        )

    # Highest scores first
    jobs.sort(
        key=lambda j: j["score"],
        reverse=True
    )

    repo = os.getenv(
        "GITHUB_REPOSITORY",
        ""
    )

    rows = []
    digest = []
    resumes_created = 0

    os.makedirs("output", exist_ok=True)

    for j in jobs:
        pdf = ""
        cold = ""
        flag = ""

        # Only tailor resumes for jobs above threshold
        # and within daily resume limit
        if (
            j["score"] >= cfg["threshold"]
            and resumes_created < cfg["max_resumes_per_day"]
        ):
            try:
                out = tailor.tailor(
                    j,
                    j["top"],
                    profile_text
                )

                path = (
                    f"output/"
                    f"{dt.date.today()}_"
                    f"{slug(j['company'])}_"
                    f"{slug(j['title'])}.pdf"
                )

                render.render_pdf(
                    out,
                    kb,
                    profile,
                    path
                )

                if repo:
                    pdf = (
                        f"https://github.com/"
                        f"{repo}/blob/main/{path}"
                    )
                else:
                    pdf = path

                cold = out.get(
                    "cold_message",
                    ""
                )

                flag = out.get(
                    "review_flag",
                    ""
                )

                resumes_created += 1

            except Exception as e:
                flag = f"tailor failed: {e}"

        rows.append([
            str(dt.date.today()),
            j["company"],
            j["title"],
            j["location"],
            j["url"],
            j["score"],
            pdf,
            "Found",
            "",
            "",
            cold,
            flag,
            "",
        ])

        digest.append(
            f"{j['score']}% | "
            f"{j['title']} | "
            f"{j['company']}"
        )

    # Add jobs to Google Sheet
    tracker.add_rows(ws, rows)

    # Get follow-ups that are due
    due = tracker.due_followups(
        ws,
        cfg["followup_days"]
    )

    msg = (
        f"Job digest {dt.date.today()}\n"
        f"New matches: {len(jobs)} | "
        f"Resumes made: {resumes_created}\n\n"
        + "\n".join(digest[:10])
    )

    if not digest:
        msg += "\nNothing new today."

    if due:
        msg += (
            "\n\nFollow up today:\n"
            + "\n".join(due)
        )

    notify.send(msg)


if __name__ == "__main__":
    main()