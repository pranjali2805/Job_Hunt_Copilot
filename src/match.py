import re
from sentence_transformers import SentenceTransformer, util


_model, _kb_emb = None, None


def _m():
    global _model

    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")

    return _model


def kb_text(i):
    return (
        f"{i['title']} {i.get('org', '')}. "
        + " ".join(i["facts"])
        + " "
        + " ".join(i.get("skills", []))
    )


def rank(jd, kb, k=7):
    """
    Return top-k knowledge-base items
    and the mean similarity of the top 3.
    """
    global _kb_emb

    if _kb_emb is None:
        _kb_emb = _m().encode(
            [kb_text(i) for i in kb],
            convert_to_tensor=True
        )

    jd_e = _m().encode(
        [jd[:2500]],
        convert_to_tensor=True
    )

    sims = util.cos_sim(jd_e, _kb_emb)[0].tolist()

    order = sorted(
        range(len(kb)),
        key=lambda i: sims[i],
        reverse=True
    )[:k]

    return (
        [kb[i] for i in order],
        sum(sims[i] for i in order[:3]) / min(3, len(order))
    )


def has_kw(text, kw):
    return re.search(
        rf"(?<![a-z]){re.escape(kw)}(?![a-z])",
        text
    ) is not None


def score(job, sem, kb, cfg, profile_text=""):
    blob = (
        " ".join(kb_text(i) for i in kb)
        + " "
        + profile_text.lower()
    )

    jd = job["jd"].lower()

    # Keywords from config that appear in the job description
    jd_kw = [
        k for k in cfg["keywords"]
        if has_kw(jd, k)
    ]

    covered = [
        k for k in jd_kw
        if has_kw(blob, k)
    ]

    gaps = [
        k for k in jd_kw
        if not has_kw(blob, k)
    ]

    cov = len(covered) / max(len(jd_kw), 1)

    t = job["title"].lower()

    # First matching title weight wins
    tfit = next(
        (w for k, w in cfg["title_weights"].items() if k in t),
        0.4
    )

    # Normalize semantic similarity from roughly 0.15–0.60 to 0–1
    sem_n = min(
        max((sem - 0.15) / 0.45, 0),
        1
    )

    final_score = round(
        100 * (
            0.5 * sem_n
            + 0.3 * cov
            + 0.2 * tfit
        )
    )

    return final_score, gaps