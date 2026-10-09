import re
import html
import requests
import yaml
from bs4 import BeautifulSoup


H = {"User-Agent": "Mozilla/5.0 (job-copilot personal project)"}


def clean(raw: str) -> str:
    raw = html.unescape(raw or "")
    return re.sub(r"\s+", " ", BeautifulSoup(raw, "html.parser").get_text(" ")).strip()


def greenhouse(slug):
    r = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
        headers=H,
        timeout=30,
    )
    r.raise_for_status()

    for j in r.json().get("jobs", []):
        yield {
            "company": slug,
            "title": j["title"],
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "jd": clean(j.get("content", "")),
        }


def lever(slug):
    r = requests.get(
        f"https://api.lever.co/v0/postings/{slug}?mode=json",
        headers=H,
        timeout=30,
    )
    r.raise_for_status()

    for j in r.json():
        yield {
            "company": slug,
            "title": j["text"],
            "location": (j.get("categories") or {}).get("location", ""),
            "url": j.get("hostedUrl", ""),
            "jd": clean(j.get("descriptionPlain") or j.get("description", "")),
        }


def ashby(slug):
    r = requests.get(
        f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
        headers=H,
        timeout=30,
    )
    r.raise_for_status()

    for j in r.json().get("jobs", []):
        yield {
            "company": slug,
            "title": j["title"],
            "location": j.get("location", "") or "",
            "url": j.get("jobUrl", ""),
            "jd": clean(
                j.get("descriptionPlain") or j.get("description", "")
            ),
        }


SOURCES = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
}


def fetch_all(path="companies.yaml"):
    cfg = yaml.safe_load(open(path))
    out = []

    for ats, slugs in cfg.items():
        for slug in slugs or []:
            try:
                out.extend(SOURCES[ats](slug))
            except Exception as e:
                print(f"[skip] {ats}/{slug}: {e}")

    return out