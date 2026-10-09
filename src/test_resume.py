import os
import yaml

from src.fetch import fetch_all
from src.match import rank
from src.tailor import tailor
from src.render import render_pdf


def main():
    kb = yaml.safe_load(
        open("knowledge_base.yaml", encoding="utf-8")
    )

    profile = yaml.safe_load(
        open("profile.yaml", encoding="utf-8")
    )

    profile_text = str(profile)

    print("Fetching jobs...")

    jobs = fetch_all()

    if not jobs:
        print("No jobs fetched.")
        return

    # Prefer an entry-level product/growth/strategy-style role
    preferred = [
        j for j in jobs
        if any(
            word in j["title"].lower()
            for word in [
                "product",
                "growth",
                "strategy",
                "founder",
                "chief of staff",
                "apm",
                "associate"
            ]
        )
    ]

    job = preferred[0] if preferred else jobs[0]

    print(f"\nTesting job:")
    print(f"Company : {job['company']}")
    print(f"Role    : {job['title']}")
    print(f"Location: {job['location']}")
    print(f"URL     : {job['url']}")

    print("\nRanking relevant experience...")

    top_items, sem = rank(
        job["jd"],
        kb
    )

    print(f"Semantic similarity: {sem:.3f}")

    print("\nCalling Groq for resume tailoring...")

    output = tailor(
        job,
        top_items,
        profile_text
    )

    print("\nTailoring completed.")

    print("\nGenerated entries:")
    for entry in output.get("entries", []):
        print(f"\n{entry['id']}")
        for bullet in entry.get("bullets", []):
            print(f"  - {bullet}")

    print("\nReview flag:")
    print(output.get("review_flag", ""))

    os.makedirs("output", exist_ok=True)

    pdf_path = "output/test_resume.pdf"

    render_pdf(
        output,
        kb,
        profile,
        pdf_path
    )

    print(f"\nPDF created successfully:")
    print(pdf_path)


if __name__ == "__main__":
    main()