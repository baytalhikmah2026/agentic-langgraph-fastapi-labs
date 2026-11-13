"""Lab 17: send seven research requests in a row and show where the rate limit starts."""

import httpx
from auth_helper import login

API = "http://127.0.0.1:8000"
# An unknown client: the request is refused after the rate-limit check, without model time
REQUEST = {"client_id": "C-9999", "question": "Summarise the exposure to energy stocks."}


def main() -> None:
    headers = {"Authorization": f"Bearer {login(API, 'amina')}"}
    with httpx.Client(headers=headers) as client:
        for n in range(1, 8):
            response = client.post(f"{API}/v1/research", json=REQUEST)
            print(f"request {n}: {response.status_code} {response.json()['error']}")


if __name__ == "__main__":
    main()
