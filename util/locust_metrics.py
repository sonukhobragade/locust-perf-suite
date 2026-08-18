"""
Shared Prometheus metrics for Locust load tests.

Single source of truth for `locust_endpoint_requests` (Counter) and
`locust_endpoint_latency_seconds` (Histogram). Tests import these — never
redefine. Service label distinguishes which test (e.g. `demo_orders`,
`payments`).

Usage:
    from util.locust_metrics import EP_REQUESTS, EP_LATENCY, record_endpoint

    record_endpoint(service="demo_orders", endpoint="/orders", method="GET",
                    status_code=200, latency_ms=87.4)
"""
from prometheus_client import Counter, Gauge, Histogram

# All supported Accept-Language tags — must match translation_<code> columns in translations table.
# hi=Hindi, mr=Marathi, kn=Kannada, bn=Bengali, te=Telugu, ta=Tamil, gu=Gujarati,
# pa=Punjabi, ml=Malayalam, ur=Urdu, as=Assamese, or=Odia. Plus en-IN baseline.
ACCEPT_LANGUAGES = [
    "en-IN", "hi-IN", "mr-IN", "kn-IN", "bn-IN", "te-IN", "ta-IN",
    "gu-IN", "pa-IN", "ml-IN", "ur-IN", "as-IN", "or-IN",
]

# Locale is randomised per request so a load run exercises the translation path
# rather than always hitting whatever is cached for the default language. If a
# service caches translated objects, varying this is what makes that cache work
# for its living -- and a locale-dependent slowdown here is a real finding.
def pick_locale(path):
    """Random Accept-Language for a request. `path` is accepted so a caller can
    pin specific endpoints to one locale if a service misbehaves under mixed
    ones."""
    import random
    return random.choice(ACCEPT_LANGUAGES)


EP_REQUESTS = Counter(
    "locust_endpoint_requests",
    "Per-endpoint request counter",
    ["service", "endpoint", "method", "result"],
)

EP_LATENCY = Histogram(
    "locust_endpoint_latency_seconds",
    "Per-endpoint latency",
    ["service", "endpoint", "method"],
    buckets=[0.025, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0],
)


ACTIVE_USERS = Gauge(
    "locust_active_users",
    "Currently spawned Locust virtual users",
    ["service"],
)

JWT_MINT = Counter(
    "locust_jwt_mint_total",
    "JWT mint events",
    ["service", "result"],   # result: success | failure | refresh
)


def record_endpoint(service, endpoint, method, status_code, latency_ms):
    result = "success" if 200 <= status_code < 300 else "failure"
    EP_REQUESTS.labels(service=service, endpoint=endpoint, method=method, result=result).inc()
    EP_LATENCY.labels(service=service, endpoint=endpoint, method=method).observe(latency_ms / 1000.0)


def register_rpm_tab(service):
    """Register custom Locust UI tab showing per-endpoint RPM (RPS*60).

    Locust UI exposes RPS only. Prod comparisons use RPM, so add a tab that
    pulls live `runner.stats.entries` and renders RPM. Idempotent across tests.
    """
    from locust import events as _events

    @_events.init.add_listener
    def _on_init(environment, **_):
        web_ui = getattr(environment, "web_ui", None)
        if web_ui is None:
            return  # worker / headless without UI

        # Idempotent: in multi-file runs first registration wins, others skip.
        if "_rpm_view" in web_ui.app.view_functions:
            return

        from flask import jsonify, render_template_string

        @web_ui.app.route("/rpm")
        def _rpm_view():
            rows = []
            for (name, method), entry in environment.runner.stats.entries.items():
                rows.append({
                    "method": method or "",
                    "name": name,
                    "num_requests": entry.num_requests,
                    "num_failures": entry.num_failures,
                    "rps": round(entry.total_rps, 2),
                    "rpm": round(entry.total_rps * 60, 1),
                    "current_rpm": round(entry.current_rps * 60, 1),
                })
            rows.sort(key=lambda r: r["rpm"], reverse=True)
            agg_rps = environment.runner.stats.total.total_rps
            return jsonify({
                "service": service,
                "total_rpm": round(agg_rps * 60, 1),
                "total_current_rpm": round(environment.runner.stats.total.current_rps * 60, 1),
                "endpoints": rows,
            })

        @web_ui.app.route("/rpm/view")
        def _rpm_html():
            return render_template_string(_RPM_HTML, service=service)

        # Add tab to top nav
        try:
            web_ui.template_args.setdefault("extra_tabs", []).append(
                ("RPM", "/rpm/view")
            )
        except Exception:
            pass


_RPM_HTML = """
<!doctype html>
<html><head><title>RPM — {{ service }}</title>
<style>
body{font-family:-apple-system,sans-serif;margin:20px;background:#1a1a1a;color:#eee}
h1{margin:0 0 6px}.muted{color:#888;font-size:12px;margin-bottom:14px}
table{border-collapse:collapse;width:100%}
th,td{padding:6px 10px;border-bottom:1px solid #333;text-align:right;font-variant-numeric:tabular-nums}
th:nth-child(1),th:nth-child(2),td:nth-child(1),td:nth-child(2){text-align:left}
th{background:#222;position:sticky;top:0}
tr:hover{background:#222}
.tot{background:#0d3b66;font-weight:bold}
</style></head><body>
<h1>RPM — {{ service }}</h1>
<div class=muted>Auto-refresh 2s. RPM = total_rps*60. Current RPM = last 10s window.</div>
<table id=t><thead><tr>
<th>Method</th><th>Name</th><th>#Req</th><th>#Fail</th><th>RPS</th><th>RPM</th><th>Current RPM</th>
</tr></thead><tbody></tbody></table>
<script>
async function tick(){
  const r = await fetch('/rpm'); const j = await r.json();
  const tb = document.querySelector('#t tbody');
  let h = '';
  h += `<tr class=tot><td></td><td>TOTAL</td><td></td><td></td><td></td><td>${j.total_rpm}</td><td>${j.total_current_rpm}</td></tr>`;
  for (const e of j.endpoints){
    h += `<tr><td>${e.method}</td><td>${e.name}</td><td>${e.num_requests}</td><td>${e.num_failures}</td><td>${e.rps}</td><td>${e.rpm}</td><td>${e.current_rpm}</td></tr>`;
  }
  tb.innerHTML = h;
}
tick(); setInterval(tick, 2000);
</script></body></html>
"""


def attach_user_count(environment, service):
    """Hook locust spawning/stopping events to update ACTIVE_USERS gauge.
    Also registers the /rpm custom UI tab for this service."""
    register_rpm_tab(service)
    from locust import events as _events

    @_events.spawning_complete.add_listener
    def _on_spawn_complete(user_count, **_):
        ACTIVE_USERS.labels(service=service).set(user_count)

    @_events.test_start.add_listener
    def _on_test_start(**_):
        ACTIVE_USERS.labels(service=service).set(0)

    @_events.test_stop.add_listener
    def _on_test_stop(**_):
        ACTIVE_USERS.labels(service=service).set(0)
