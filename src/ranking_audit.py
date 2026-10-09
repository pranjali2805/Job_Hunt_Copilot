import csv
from pathlib import Path

import yaml

from src.fetch import fetch_all
from src.filters import filter_job
from src.match import rank, score


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def main():
    cfg = load_yaml("config.yaml")
    kb = load_yaml("knowledge_base.yaml")
    profile = load_yaml("profile.yaml")
    profile_text = str(profile)

    print("Fetching current job listings...")
    raw_jobs = fetch_all()

    # Keep one copy of each URL.
    unique_jobs = []
    seen_urls = set()

    for job in raw_jobs:
        url = (job.get("url") or "").strip()

        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        unique_jobs.append(job)

    print(f"\nRaw listings fetched: {len(raw_jobs)}")
    print(f"Unique jobs to audit: {len(unique_jobs)}")

    scored_jobs = []
    rejection_counts = {}

    print("\nScoring all unique jobs...")

    for index, job in enumerate(unique_jobs, start=1):
        accepted, reason = filter_job(job, cfg)

        if not accepted:
            rejection_counts[reason] = (
                rejection_counts.get(reason, 0) + 1
            )

        _, semantic_score = rank(
            job.get("jd", ""),
            kb,
        )

        final_score, keyword_gaps = score(
            job,
            semantic_score,
            kb,
            cfg,
            profile_text,
        )

        scored_jobs.append({
            "score": final_score,
            "semantic_score": round(semantic_score, 3),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "passes_filters": "yes" if accepted else "no",
            "filter_reason": reason,
            "keyword_gaps": "; ".join(keyword_gaps),
            "description_excerpt": " ".join(
                (job.get("jd") or "").split()
            )[:1000],
        })

        if index % 20 == 0:
            print(f"  Scored {index}/{len(unique_jobs)} jobs")

    scored_jobs.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    print("\nTop 20 scored jobs:")

    for position, job in enumerate(scored_jobs[:20], start=1):
        print(
            f"{position:>2}. {job['score']:>3}/100 | "
            f"sem={job['semantic_score']:.3f} | "
            f"filters={job['passes_filters']} | "
            f"{job['title']} | {job['company']}"
        )

        if job["passes_filters"] == "no":
            print(f"    Rejected: {job['filter_reason']}")

        print(f"    {job['url']}")

    if rejection_counts:
        print("\nFilter rejection breakdown:")

        for reason, count in sorted(rejection_counts.items()):
            print(f"  {reason}: {count}")

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "ranking_audit.csv"

    fields = [
        "rank",
        "score",
        "semantic_score",
        "title",
        "company",
        "location",
        "url",
        "passes_filters",
        "filter_reason",
        "keyword_gaps",
        "description_excerpt",
        "relevance_label",
        "notes",
    ]

    # Export all scored jobs; the first 20 are the initial
    # hand-labeling sample.
    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for position, job in enumerate(scored_jobs, start=1):
            writer.writerow({
                "rank": position,
                **job,
                "relevance_label": "",
                "notes": "",
            })

    print(f"\nAudit exported: {csv_path}")
    print(f"Total audited jobs: {len(scored_jobs)}")
    print("Hand-label the first 20 rows before changing weights.")


if __name__ == "__main__":
    main()