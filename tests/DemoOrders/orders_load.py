"""
Load profile for the demo order service.

Target is the stack shipped with pytest-api-harness -- a FastAPI order service
with Postgres behind it and Redis in front:

    docker compose -f ../pytest-api-harness/demo/docker-compose.yml up -d
    locust -f tests/DemoOrders/orders_load.py --host http://localhost:8000

Running against a local container rather than a hosted API is the point. Load
testing somebody else's public endpoint is abuse, and a rate limiter makes the
numbers meaningless anyway: you end up measuring their throttle, not your
service.

The task weights encode a read-heavy shape, which is what the cache exists for.
Two things worth watching in the results rather than just the totals:

  * GET /orders/[id] should show a bimodal latency distribution. The fast mode
    is a Redis hit, the slow mode is the Postgres read behind a miss. If the
    distribution is flat and slow, the cache is not being populated.
  * PATCH .../status evicts the cached entry, so a workload that writes often
    keeps the hit rate down. Raising the write weight should visibly move read
    latency -- that coupling is the interesting result, not the raw RPS.
"""

import os
import random

from locust import HttpUser, TaskSet, between, task

USERNAME = os.getenv("DEMO_USERNAME", "qa")
PASSWORD = os.getenv("DEMO_PASSWORD", "demo")

SKUS = ["WIDGET-001", "WIDGET-002", "GADGET-100", "GADGET-200", "DOODAD-007"]


class OrderTasks(TaskSet):
    def on_start(self):
        r = self.client.post(
            "/auth/token",
            json={"username": USERNAME, "password": PASSWORD},
            name="POST /auth/token",
        )
        if r.status_code != 200:
            self.interrupt()
        self.client.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
        # Orders this user created, so reads and writes target rows that exist.
        self.own_orders: list[int] = []
        self._create_order()

    def _create_order(self):
        with self.client.post(
            "/orders",
            json={
                "sku": random.choice(SKUS),
                "quantity": random.randint(1, 100),
                "unit_price_cents": random.randint(1, 10_000),
            },
            name="POST /orders",
            catch_response=True,
        ) as r:
            if r.status_code == 201:
                self.own_orders.append(r.json()["id"])
                r.success()
            else:
                r.failure(f"create failed: {r.status_code}")

    @task(6)
    def read_order(self):
        """Read-heavy by design: this is the path the cache serves."""
        if not self.own_orders:
            self._create_order()
            return
        oid = random.choice(self.own_orders)
        with self.client.get(f"/orders/{oid}", name="GET /orders/[id]", catch_response=True) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"read failed: {r.status_code}")

    @task(3)
    def read_catalog(self):
        """Pure cache path -- no database behind a hit."""
        sku = random.choice(SKUS)
        with self.client.get(f"/catalog/{sku}", name="GET /catalog/[sku]", catch_response=True) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"catalog failed: {r.status_code}")

    @task(2)
    def create_order(self):
        self._create_order()

    @task(1)
    def advance_status(self):
        """Writes that evict cache entries, so read latency and write rate couple."""
        if not self.own_orders:
            return
        oid = random.choice(self.own_orders)
        with self.client.patch(
            f"/orders/{oid}/status",
            json={"status": "paid"},
            name="PATCH /orders/[id]/status",
            catch_response=True,
        ) as r:
            # 409 is a correct refusal (the order already moved on), not an error.
            # Counting it as a failure would make the run look broken at high
            # concurrency purely because the state machine is doing its job.
            if r.status_code in (200, 409):
                r.success()
            else:
                r.failure(f"status change failed: {r.status_code}")


class OrderUser(HttpUser):
    tasks = [OrderTasks]
    wait_time = between(0.1, 0.5)
