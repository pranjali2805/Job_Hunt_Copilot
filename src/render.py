import yaml
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


def render_pdf(data, kb, profile, path):
    by_id = {i["id"]: i for i in kb}

    groups = {
        "experience": [],
        "project": [],
        "leadership": []
    }

    for e in data["entries"]:
        item = by_id[e["id"]].copy()
        item["bullets"] = e["bullets"]
        groups.setdefault(item["type"], []).append(item)

    env = Environment(
        loader=FileSystemLoader("templates")
    )

    tpl = env.get_template("resume.html")

    html = tpl.render(
        p=profile,
        summary=data["summary"],
        skills=data["skills"],
        groups=groups
    )

    HTML(string=html).write_pdf(path)