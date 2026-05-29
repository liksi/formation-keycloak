from __future__ import annotations

import time

import requests


def wait_for_message(
    recipient: str, maildev_url: str = "http://localhost:1080", timeout: int = 30
) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(f"{maildev_url}/email", timeout=10)
        response.raise_for_status()
        for message in response.json():
            recipients = [item.get("address", "") for item in message.get("to", [])]
            if recipient in recipients:
                return message
        time.sleep(1)
    raise TimeoutError(f"No message delivered to {recipient} within {timeout}s")
