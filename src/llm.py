import os
import json
import time
import requests


URL = "https://api.groq.com/openai/v1/chat/completions"

# Keep this configurable so we can change models later without editing the code.
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")


def chat_json(system, user, retries=4):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add your Groq API key as an environment variable."
        )

    for i in range(retries):
        r = requests.post(
            URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=90,
        )

        if r.status_code == 429:
            time.sleep(20 * (i + 1))
            continue

        r.raise_for_status()

        return json.loads(
            r.json()["choices"][0]["message"]["content"]
        )

    raise RuntimeError("LLM rate-limited")