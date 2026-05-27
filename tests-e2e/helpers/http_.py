import time

import requests


def wait_for_http(url, max_wait=60, interval=1):
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(interval)
    raise TimeoutError(f"Timed out waiting for {url}")
