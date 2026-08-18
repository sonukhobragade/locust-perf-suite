"""
service-payments mixed load test (read-heavy, NO real money flow).

Per-VU flow:
  on_start:
    - pick row from QA seed CSV (qa_users.csv)
    - POST /auth/token with userId/phoneNumber/countryCode -> store JWT
    - hydrate live ids:
        GET /subscriptions          -> subscription.subscriptionId pool
        POST /payments/deposits     -> order id pool (status=ALL)
    - hydrate-call names match the load-call names (no [hydrate] suffix)
  each task:
    - reuse VU's user_id, phone, country, jwt
    - prefer hydrated ids; fall back to skipping when none
    - on 401: re-mint JWT once, retry

Scope

Read-only endpoints only. Anything that creates or settles a payment, issues a
refund, or overrides an order is deliberately absent: a load test must not move
money or mutate state in a payment system, and one that can do so by accident
is a liability rather than a tool.

Point it at your own service with the host argument; the paths exercised are
the ones defined in the tasks below.

Seed CSV: test_data/qa_users.csv (user_id,phone_number,country_code,...)
"""
import os
import sys
import csv
import random
import time
import logging
from locust import HttpUser, TaskSet, task, constant_throughput, events
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from util.prometheus_metrics import PrometheusMetrics  # noqa: E402

load_dotenv()

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# Port 9096 — one port per suite, so two suites can run side by side.
metrics = PrometheusMetrics(service_name="payments", port=9096)

from util.locust_metrics import EP_REQUESTS, EP_LATENCY, JWT_MINT, attach_user_count, pick_locale  # noqa: E402

SERVICE_LABEL = os.getenv("LOCUST_SERVICE_LABEL", "payments")


def _split_name(name):
    parts = name.split(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "GET", name


# --- Config ---
BASE_URL = os.getenv("PAYMENTS_BASE_URL") or os.getenv("BACKEND_API_BASE", "https://qa-api.example.com")
PATH_PREFIX = os.getenv("PAYMENTS_PATH_PREFIX", "")
SLO_P95_MS = int(os.getenv("PAYMENTS_SLO_P95_MS", "400"))
SLO_P99_MS = int(os.getenv("PAYMENTS_SLO_P99_MS", "1000"))
SEED_CSV = os.getenv("PAYMENTS_SEED_CSV", "test_data/qa_users.csv")

# --- Stats ---
stats = {
    "overall": {"count": 0, "total": 0, "min": float('inf'), "max": 0, "values": []},
    "by_endpoint": {},
    "jwt_mint": {"success": 0, "failed": 0, "remint": 0},
}


def record(name, ms):
    o = stats["overall"]
    o["count"] += 1
    o["total"] += ms
    o["min"] = min(o["min"], ms)
    o["max"] = max(o["max"], ms)
    o["values"].append(ms)
    if len(o["values"]) > 2000:
        o["values"].pop(0)
    ep = stats["by_endpoint"].setdefault(name, {"count": 0, "total": 0, "values": []})
    ep["count"] += 1
    ep["total"] += ms
    ep["values"].append(ms)
    if len(ep["values"]) > 2000:
        ep["values"].pop(0)
    metrics.record_full_response(ms / 1000.0)


def pct(values, p):
    if not values:
        return 0
    s = sorted(values)
    return s[min(int(len(s) * p / 100), len(s) - 1)]


def load_user_pool():
    pool = []
    path = os.path.abspath(SEED_CSV)
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                pool.append({
                    "user_id": r["user_id"].strip(),
                    "phone_number": r["phone_number"].strip(),
                    "country_code": (r.get("country_code") or "IN").strip() or "IN",
                })
        print(f"Loaded {len(pool)} users from {path}")
        return pool
    except Exception as e:
        print(f"WARN: cannot load seed CSV {path}: {e} — using env/hardcoded fallback")

    env_uid = os.getenv("PAYMENTS_FALLBACK_USER_ID")
    env_phone = os.getenv("PAYMENTS_FALLBACK_PHONE")
    env_cc = os.getenv("PAYMENTS_FALLBACK_COUNTRY", "IN")
    if env_uid and env_phone:
        pool.append({"user_id": env_uid, "phone_number": env_phone, "country_code": env_cc})
    else:
        pool.append({"user_id": "101", "phone_number": "919900000101", "country_code": "IN"})
        pool.append({"user_id": "102", "phone_number": "919900000102", "country_code": "IN"})
    print(f"Using {len(pool)} fallback payments user(s).")
    return pool


# --- Verified payload values ---
# AllowedPaymentStatus enum: SUCCESS, FAILED, PENDING, REFUNDED.
# "ALL" is the special equalsIgnoreCase branch -> all statuses.
DEPOSIT_STATUS_FILTERS = [
    ["ALL"],
    ["SUCCESS"],
    ["PENDING"],
    ["FAILED"],
    ["SUCCESS", "PENDING"],
    ["SUCCESS", "FAILED", "REFUNDED"],
]

# Sample deposit-suggestions-v2 payloads (all fields optional; backend tolerates nulls).
SUGGESTION_V2_TAGS = [
    ["chat"], ["call"], ["report"], ["recharge"],
    ["chat", "premium"], ["call", "promo"],
]
SUGGESTION_V2_INTERNAL_TAGS = [
    ["new_user"], ["existing_user"], ["premium"],
    ["promo"], ["recharge_flow"],
]
SUGGESTION_V2_COSTS = ["10", "20", "30", "50", "75", "100"]


# --- Events ---
attach_user_count(None, SERVICE_LABEL)


@events.init.add_listener
def on_init(environment, **_kwargs):
    if not environment.web_ui:
        return

    @environment.web_ui.app.route(f"/stats/custom/{SERVICE_LABEL}", endpoint=f"custom_{SERVICE_LABEL}")
    def custom():
        o = stats["overall"]
        return {
            "overall": {
                "count": o["count"],
                "avg": o["total"] / o["count"] if o["count"] else 0,
                "p50": pct(o["values"], 50),
                "p95": pct(o["values"], 95),
                "p99": pct(o["values"], 99),
                "slo_p95_ms": SLO_P95_MS,
                "slo_p99_ms": SLO_P99_MS,
            },
            "jwt_mint": stats["jwt_mint"],
            "by_endpoint": {
                k: {
                    "count": v["count"],
                    "avg": v["total"] / v["count"] if v["count"] else 0,
                    "p95": pct(v["values"], 95),
                    "p99": pct(v["values"], 99),
                }
                for k, v in stats["by_endpoint"].items()
            },
        }

    print("\n" + "=" * 80)
    print("PAYMENTS MIXED LOAD TEST (read-only — no PG writes)")
    print("=" * 80)
    print(f"Target:        {BASE_URL}{PATH_PREFIX}")
    print(f"Seed CSV:      {SEED_CSV}")
    print(f"SLO:           p95<{SLO_P95_MS}ms, p99<{SLO_P99_MS}ms")
    print("Locust UI:     http://localhost:8089")
    print("Custom stats:  http://localhost:8089/stats/custom")
    print("Prometheus:    http://localhost:9096/metrics")
    print("=" * 80 + "\n")


@events.test_stop.add_listener
def on_stop(**_kwargs):
    o = stats["overall"]
    print("\n" + "=" * 80)
    print("PAYMENTS PERFORMANCE STATISTICS")
    print("=" * 80)
    print(f"  JWT mint: success={stats['jwt_mint']['success']} failed={stats['jwt_mint']['failed']} remint={stats['jwt_mint']['remint']}")
    if o["count"] > 0:
        p95 = pct(o["values"], 95)
        p99 = pct(o["values"], 99)
        print(f"  Total Requests:  {o['count']}")
        print(f"  Avg:             {o['total'] / o['count']:.0f} ms")
        print(f"  Min / Max:       {o['min']:.0f} / {o['max']:.0f} ms")
        print(f"  P50 / P95 / P99: {pct(o['values'], 50):.0f} / {p95:.0f} / {p99:.0f} ms")
        print(f"  SLO p95<{SLO_P95_MS}ms: {'PASS' if p95 < SLO_P95_MS else 'FAIL'}")
        print(f"  SLO p99<{SLO_P99_MS}ms: {'PASS' if p99 < SLO_P99_MS else 'FAIL'}")
        print("\n  Per-endpoint:")
        rows = sorted(stats["by_endpoint"].items(), key=lambda kv: -kv[1]["count"])
        for name, d in rows:
            print(f"    {name:<60} n={d['count']:>5}  avg={d['total'] / d['count']:.0f}ms  p95={pct(d['values'], 95):.0f}ms  p99={pct(d['values'], 99):.0f}ms")
    print("=" * 80 + "\n")


USER_POOL = load_user_pool()


class PaymentsTasks(TaskSet):

    def on_start(self):
        if not USER_POOL:
            raise RuntimeError("No payments user pool. Provide seed CSV or fallback env vars.")
        self.row = random.choice(USER_POOL)
        self.user_id = self.row["user_id"]
        self.phone = self.row["phone_number"]
        self.country = self.row["country_code"]
        self.live_subscription_ids = []
        self.live_order_ids = []
        self.jwt = None
        self.jwt_minted_at = 0
        self._mint_jwt()
        self._hydrate_ids()

    # --- Hydrate live ids ---
    def _hydrate_ids(self):
        if not self.jwt:
            return
        # Deposits list -> grab order ids. (no v2 list endpoint exists per controller scan)
        try:
            r = self.client.post(
                f"{PATH_PREFIX}/payments/deposits",
                headers=self._headers(),
                json={"status": ["ALL"]},
                name="POST /payments/deposits",
            )
            if 200 <= r.status_code < 300:
                items = r.json()
                if isinstance(items, list):
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        oid = it.get("id") or it.get("orderId")
                        if oid is not None:
                            self.live_order_ids.append(str(oid))
        except Exception:
            pass

    # --- JWT mint ---
    def _mint_jwt(self, is_remint=False):
        if is_remint:
            stats["jwt_mint"]["remint"] += 1
            JWT_MINT.labels(service=SERVICE_LABEL, result="refresh").inc()
        h = {
            "userId": str(self.user_id),
            "phoneNumber": str(self.phone),
            "countryCode": self.country,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        with self.client.post(
            f"{PATH_PREFIX}/auth/token",
            headers=h,
            catch_response=True,
            name="POST /auth/token [mint]",
        ) as resp:
            if 200 <= resp.status_code < 300:
                try:
                    data = resp.json()
                    self.jwt = data.get("jwtToken") or data.get("jwt") or data.get("token")
                    if not self.jwt:
                        stats["jwt_mint"]["failed"] += 1
                        JWT_MINT.labels(service=SERVICE_LABEL, result="failure").inc()
                        resp.failure(f"mint OK but no jwt field in body: {str(data)[:200]}")
                        return
                    stats["jwt_mint"]["success"] += 1
                    JWT_MINT.labels(service=SERVICE_LABEL, result="success").inc()
                    self.jwt_minted_at = time.time()
                    resp.success()
                except Exception as e:
                    stats["jwt_mint"]["failed"] += 1
                    JWT_MINT.labels(service=SERVICE_LABEL, result="failure").inc()
                    resp.failure(f"jwt parse: {e}")
            else:
                stats["jwt_mint"]["failed"] += 1
                JWT_MINT.labels(service=SERVICE_LABEL, result="failure").inc()
                resp.failure(f"HTTP {resp.status_code} | {(resp.text or '')[:200]}")

    JWT_REFRESH_AFTER_S = 12 * 60

    def _refresh_jwt(self):
        if not self.jwt:
            return self._mint_jwt(is_remint=True)
        h = {
            "auth_token": self.jwt or "",
            "userId": str(self.user_id),
            "phoneNumber": str(self.phone),
            "countryCode": self.country,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        body = {"jwtToken": self.jwt, "jwtExpiry": str(int(time.time() * 1000) + 900_000)}
        with self.client.post(
            f"{PATH_PREFIX}/auth/refreshJWTToken",
            headers=h, json=body,
            catch_response=True,
            name="POST /auth/refreshJWTToken [proactive]",
        ) as resp:
            if 200 <= resp.status_code < 300:
                try:
                    data = resp.json()
                    new_jwt = data.get("jwtToken") or data.get("jwt") or data.get("token")
                    if new_jwt:
                        self.jwt = new_jwt
                        self.jwt_minted_at = time.time()
                        resp.success()
                        return
                except Exception:
                    pass
            resp.failure(f"refresh HTTP {resp.status_code}; falling back to mint")
            self._mint_jwt(is_remint=True)

    def _headers(self, extra=None, path=None):
        h = {
            "auth_token": self.jwt or "",
            "Accept": "application/json",
            "Accept-Language": pick_locale(path),
            "Content-Type": "application/json",
            "userId": str(self.user_id),
            "phoneNumber": str(self.phone),
            "countryCode": self.country,
        }
        if extra:
            h.update({k: str(v) for k, v in extra.items()})
        return h

    def _do(self, method, path, name, headers=None, json_body=None, params=None):
        if not self.jwt:
            return
        if self.jwt_minted_at and (time.time() - self.jwt_minted_at) > self.JWT_REFRESH_AFTER_S:
            self._refresh_jwt()
            if headers and "auth_token" in headers:
                headers["auth_token"] = self.jwt or ""
        url = f"{PATH_PREFIX}{path}"
        h = headers or self._headers(path=path)
        metrics.increment_total()
        start = time.time()
        with self.client.request(
            method, url, headers=h, json=json_body, params=params,
            catch_response=True, name=name,
        ) as resp:
            ms = (time.time() - start) * 1000
            record(name, ms)
            ep_method, ep_path = _split_name(name)
            EP_LATENCY.labels(service=SERVICE_LABEL, endpoint=ep_path, method=ep_method).observe(ms / 1000.0)
            if resp.status_code == 401:
                self._mint_jwt(is_remint=True)
                if self.jwt:
                    h["auth_token"] = self.jwt or ""
                    start2 = time.time()
                    with self.client.request(
                        method, url, headers=h, json=json_body, params=params,
                        catch_response=True, name=name,
                    ) as r2:
                        ms2 = (time.time() - start2) * 1000
                        record(name, ms2)
                        EP_LATENCY.labels(service=SERVICE_LABEL, endpoint=ep_path, method=ep_method).observe(ms2 / 1000.0)
                        if 200 <= r2.status_code < 300:
                            metrics.increment_success()
                            EP_REQUESTS.labels(service=SERVICE_LABEL, endpoint=ep_path, method=ep_method, result="success").inc()
                            r2.success()
                        else:
                            metrics.increment_failed()
                            EP_REQUESTS.labels(service=SERVICE_LABEL, endpoint=ep_path, method=ep_method, result="failure").inc()
                            r2.failure(f"HTTP {r2.status_code} after remint")
                resp.success()
                return
            if 200 <= resp.status_code < 300:
                metrics.increment_success()
                EP_REQUESTS.labels(service=SERVICE_LABEL, endpoint=ep_path, method=ep_method, result="success").inc()
                resp.success()
            else:
                metrics.increment_failed()
                EP_REQUESTS.labels(service=SERVICE_LABEL, endpoint=ep_path, method=ep_method, result="failure").inc()
                body = (resp.text or "")[:200]
                resp.failure(f"HTTP {resp.status_code} | {body}")

    def _pick_subscription(self):
        return random.choice(self.live_subscription_ids) if self.live_subscription_ids else None

    def _pick_order(self):
        return random.choice(self.live_order_ids) if self.live_order_ids else None

    # ---- Tasks: 4 read endpoints (per Postman + prod) ----

    @task(4)
    def get_subscriptions(self):
        self._do("GET", "/subscriptions", "GET /subscriptions")

    @task(3)
    def post_deposits(self):
        body = {"status": random.choice(DEPOSIT_STATUS_FILTERS)}
        self._do("POST", "/payments/deposits", "POST /payments/deposits", json_body=body)

    @task(2)
    def get_payment_methods(self):
        self._do("GET", "/payments/methods", "GET /payments/methods")

    @task(2)
    def post_deposit_suggestions_v2(self):
        body = {
            "providerId": random.choice([1, 2, 3, 7, 11]),
            "tags": random.choice(SUGGESTION_V2_TAGS),
            "costPerChat": random.choice(SUGGESTION_V2_COSTS),
            "internalTags": random.choice(SUGGESTION_V2_INTERNAL_TAGS),
        }
        self._do("POST", "/payments/suggestions",
                 "POST /payments/suggestions", json_body=body)



class PaymentsUser(HttpUser):
    tasks = [PaymentsTasks]
    wait_time = constant_throughput(1)  # 1 RPS per VU
    host = BASE_URL
