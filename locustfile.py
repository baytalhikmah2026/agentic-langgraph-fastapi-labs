"""Lab 20: a load test of the Research Desk API with Locust.

Each simulated analyst signs in once with its own load-test account (load-01, load-02 ...),
then keeps using the desk: health checks, client look-ups, research questions that are
already in the Redis cache, and now and then a fresh sign-in.
"""

import itertools
import json
import os
import random
from pathlib import Path

from locust import HttpUser, between, task

PASSWORD = os.environ.get("SB_LOAD_TEST_PASSWORD", "")
ACCOUNTS = int(os.environ.get("SB_LOAD_TEST_ACCOUNTS", "30"))
RESEARCH = json.loads(Path("requests/research_ok.json").read_text(encoding="utf-8"))
CLIENT_IDS = ["C-1042", "C-2077", "C-3105"]
numbers = itertools.count()


class Analyst(HttpUser):
    """One analyst at Crescent Ledger Bank, working at a normal pace."""

    wait_time = between(2, 4)

    def on_start(self) -> None:
        self.username = f"load-{next(numbers) % ACCOUNTS + 1:02d}"
        self.sign_in()

    def sign_in(self) -> None:
        response = self.client.post(
            "/v1/auth/token",
            data={"username": self.username, "password": PASSWORD},
            name="/v1/auth/token",
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(4)
    def health(self) -> None:
        self.client.get("/health", name="/health")

    @task(3)
    def look_up_client(self) -> None:
        client_id = random.choice(CLIENT_IDS)
        self.client.get(f"/v1/clients/{client_id}", name="/v1/clients/[id]")

    @task(1)
    def cached_research(self) -> None:
        with self.client.post(
            "/v1/research", json=RESEARCH, name="/v1/research (cached)", catch_response=True
        ) as response:
            if response.status_code == 200 and not response.json()["cached"]:
                response.failure("answered by the model, not the cache: warm the cache first")

    @task(1)
    def sign_in_again(self) -> None:
        self.sign_in()
