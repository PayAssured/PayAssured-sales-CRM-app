import requests
import os
import json
import time
import sys
from datetime import datetime

SENDINBLUE_API_KEY_PROD = os.getenv("SENDINBLUE_API_KEY_PROD")
GOOGLE_CHAT_WEBHOOK = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")

SENDINBLUE_ACCOUNT_URL = "https://api.brevo.com/v3/account"
STATE_FILE = ".github/monitoring/brevo_state.json"

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"status": "ok"}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def send_google_chat(message):
    payload = {"text": message}
    requests.post(GOOGLE_CHAT_WEBHOOK, json=payload, timeout=10)


def check_api_key():
    headers = {
        "accept": "application/json",
        "api-key": SENDINBLUE_API_KEY_PROD
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                SENDINBLUE_ACCOUNT_URL,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return "ok"

            if response.status_code in (401, 403):
                return "failed"

        except requests.exceptions.RequestException:
            pass

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    return "failed"


def main():
    if not SENDINBLUE_API_KEY_PROD or not GOOGLE_CHAT_WEBHOOK:
        print("Missing required environment variables")
        sys.exit(1)

    previous_state = load_state()["status"]
    current_state = check_api_key()

    # OK → FAILED (expired)
    if previous_state == "ok" and current_state == "failed":
        send_google_chat(
            "🚨 Brevo PROD API Key Expired\n"
            f"Detected at {datetime.utcnow().isoformat()} UTC"
        )

    # FAILED → OK (updated)
    if previous_state == "failed" and current_state == "ok":
        send_google_chat(
            "✅ Brevo PROD API Key Updated & Working\n"
            f"Recovered at {datetime.utcnow().isoformat()} UTC"
        )

    save_state({"status": current_state})

    if current_state == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
