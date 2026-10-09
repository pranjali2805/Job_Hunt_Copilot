import os
import requests


def _api(method):
    return (
        f"https://api.telegram.org/"
        f"bot{os.environ['TELEGRAM_TOKEN']}/{method}"
    )


CHAT = lambda: os.environ["TELEGRAM_CHAT_ID"]


def send(text):
    requests.post(
        _api("sendMessage"),
        data={
            "chat_id": CHAT(),
            "text": text[:4000],
            "disable_web_page_preview": True,
        },
        timeout=30,
    )


def send_file(path, caption=""):
    with open(path, "rb") as f:
        requests.post(
            _api("sendDocument"),
            data={
                "chat_id": CHAT(),
                "caption": caption[:900],
            },
            files={"document": f},
            timeout=60,
        )