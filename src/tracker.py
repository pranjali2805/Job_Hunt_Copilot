import os
import datetime as dt

import gspread


HEADERS = [
    "Date found",
    "Company",
    "Role",
    "Location",
    "Link",
    "Match %",
    "Resume file",
    "Status",
    "Applied date",
    "Follow-up sent",
    "Cold message",
    "Review flag",
    "Notes",
]


def get_sheet():
    gc = gspread.service_account(
        filename=os.environ["GOOGLE_CREDS_FILE"]
    )

    ws = gc.open_by_key(
        os.environ["SHEET_ID"]
    ).sheet1

    if ws.row_values(1) != HEADERS:
        ws.update("A1", [HEADERS])

    return ws


def existing_links(ws):
    return set(
        ws.col_values(HEADERS.index("Link") + 1)[1:]
    )


def add_rows(ws, rows):
    if rows:
        ws.append_rows(
            rows,
            value_input_option="USER_ENTERED"
        )


def due_followups(ws, days):
    due = []

    for r in ws.get_all_records():
        if (
            r["Status"] == "Applied"
            and r["Applied date"]
            and not r["Follow-up sent"]
        ):
            try:
                d = dt.date.fromisoformat(
                    str(r["Applied date"])
                )
            except ValueError:
                continue

            if (dt.date.today() - d).days >= days:
                due.append(
                    f"{r['Company']} - {r['Role']}"
                )

    return due