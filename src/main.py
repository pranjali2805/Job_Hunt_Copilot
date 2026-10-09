
import os
import re
import yaml
import datetime as dt

from src import fetch, match, tailor, render, tracker, notify
from src.filters import filter_job


def load_yaml(path):
    """Load a YAML file safely using UTF-8."""
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def slug(text):
    """Convert text into a filename-friendly slug."""
    return re.sub(
        r"[^a-z0-9]+",
        "-",
        (text or "").lower()
    ).strip("-")[:50]


def main():
    # --------------------------------------------------
    # 1. Load configuration and personal data
    # --------------------------------------------------
    cfg = load_yaml("config.yaml")
    kb = load_yaml("knowledge_base.yaml")
    profile = load_yaml("profile.yaml")

    profile_text = str(profile)

    if not isinstance(cfg, dict):
        raise ValueError("config.yaml must contain a YAML mapping.")

    if not isinstance(kb, list) or not kb:
        raise ValueError("knowledge_base.yaml must contain a non-empty list.")

    if not isinstance(profile, dict):
        raise ValueError("profile.yaml must contain a YAML mapping.")

    # --------------------------------------------------
    # 2. Connect to Google Sheets
    # --------------------------------------------------
    ws = tracker.get_sheet()
    seen = {
        link.strip()
        for link in tracker.existing_links(ws)
        if link and link.strip()
    }

    # --------------------------------------------------
    # 3. Fetch jobs and apply shared eligibility filters
    # --------------------------------------------------
    raw_jobs = fetch.fetch_all()

    jobs = []
    rejection_counts = {}
    skipped_duplicates = 0
    checked_urls = set()

    for job in raw_jobs:
        url = (job.get("url") or "").strip()

        if not url:
            rejection_counts["missing_url"] = (
                rejection_counts.get("missing_url", 0) + 1
            )
            continue

        # Prevent both historical duplicates and duplicates
        # occurring within the same fetch.
        if url in seen or url in checked_urls:
            skipped_duplicates += 1
            continue

        checked_urls.add(url)

        accepted, reason = filter_job(job, cfg)

        if accepted:
            jobs.append(job)
        else:
            rejection_counts[reason] = (
                rejection_counts.get(reason, 0) + 1
            )

    print(f"\nFetched raw jobs: {len(raw_jobs)}")
    print(f"Skipped duplicates: {skipped_duplicates}")
    print(f"New eligible jobs: {len(jobs)}")

    if rejection_counts:
        print("\nFiltering breakdown:")

        for reason, count in sorted(rejection_counts.items()):
            print(f"  {reason}: {count}")

    # --------------------------------------------------
    # 4. Score eligible jobs
    # --------------------------------------------------
    for job in jobs:
        top_items, semantic_score = match.rank(
            job["jd"],
            kb
        )

        job["top"] = top_items
        job["sem"] = semantic_score

        job["score"], job["gaps"] = match.score(
            job,
            semantic_score,
            kb,
            cfg,
            profile_text
        )

    # Highest-scoring eligible jobs first.
    jobs.sort(
        key=lambda job: job["score"],
        reverse=True
    )

    # --------------------------------------------------
    # 5. Print the top five BEFORE generating any PDFs
    # --------------------------------------------------
    print("\nTop 5 eligible jobs:")

    if not jobs:
        print("No new eligible jobs were found.")

    for job in jobs[:5]:
        print(
            f"{job['score']:>3}/100 | "
            f"{job['title']} | "
            f"{job['company']} | "
            f"{job.get('location', '')} | "
            f"{job['url']}"
        )

    # --------------------------------------------------
    # 6. Generate resumes for qualifying jobs
    # --------------------------------------------------
    os.makedirs("output", exist_ok=True)

    today = dt.date.today().isoformat()
    max_resumes = int(cfg["max_resumes_per_day"])
    threshold = float(cfg["threshold"])

    rows = []
    digest = []
    resumes_created = 0

    for job in jobs:
        pdf_path = ""
        cold_message = ""
        review_flag = ""
        status = "Found"

        should_generate = (
            job["score"] >= threshold
            and resumes_created < max_resumes
        )

        if should_generate:
            try:
                # Ask the LLM to tailor content using the
                # selected knowledge-base entries.
                output = tailor.tailor(
                    job,
                    job["top"],
                    profile_text
                )

                # Use deterministic filenames for each
                # company, role, and date.
                filename = (
                    f"{today}_"
                    f"{slug(job['company'])}_"
                    f"{slug(job['title'])}.pdf"
                )

                pdf_path = os.path.join(
                    "output",
                    filename
                ).replace("\\", "/")

                render.render_pdf(
                    output,
                    kb,
                    profile,
                    pdf_path
                )

                cold_message = output.get(
                    "cold_message",
                    ""
                )

                review_flag = output.get(
                    "review_flag",
                    ""
                )

                # A generated resume always requires human
                # review before it is used for an application.
                status = "Review Required"
                resumes_created += 1

                print(f"\nPDF generated: {pdf_path}")
                print(f"Review status: {status}")

                if review_flag:
                    print(f"Review flag: {review_flag}")

            except Exception as error:
                # Keep the job in the tracker even when
                # tailoring or rendering fails.
                pdf_path = ""
                cold_message = ""
                review_flag = (
                    f"Generation failed: "
                    f"{type(error).__name__}: {error}"
                )
                status = "Generation Failed"

                print(
                    f"\n[error] Resume generation failed for "
                    f"{job['company']} - {job['title']}: {error}"
                )

        # Record every new eligible job, even when its score
        # is below the resume-generation threshold.
        rows.append([
            today,
            job["company"],
            job["title"],
            job.get("location", ""),
            job["url"],
            job["score"],
            pdf_path,
            status,
            "",
            "",
            cold_message,
            review_flag,
            "",
        ])

        digest.append(
            f"{job['score']}% | "
            f"{job['title']} | "
            f"{job['company']}"
        )

    # --------------------------------------------------
    # 7. Update Google Sheets
    # --------------------------------------------------
    tracker.add_rows(ws, rows)

    print(f"\nNew eligible jobs recorded: {len(rows)}")
    print(f"Resumes generated: {resumes_created}")

    # --------------------------------------------------
    # 8. Check follow-ups
    # --------------------------------------------------
    due = tracker.due_followups(
        ws,
        int(cfg["followup_days"])
    )

    # --------------------------------------------------
    # 9. Send the Telegram digest
    # --------------------------------------------------
    message = (
        f"Job digest {today}\n"
        f"New eligible jobs: {len(jobs)}\n"
        f"Resumes generated: {resumes_created}\n\n"
        + "\n".join(digest[:10])
    )

    if not digest:
        message += "\n\nNothing new today."

    if due:
        message += (
            "\n\nFollow up today:\n"
            + "\n".join(due)
        )

    notify.send(message)

    print("\nJob-Hunt Copilot run completed.")


if __name__ == "__main__":
    main()