"""Unit tests for util/locust_metrics.py.

The metric definitions are module-level Prometheus collectors, so importing
this module registers them once for the whole process. The tests read counter
values through the registry rather than resetting anything, which keeps them
independent of import order.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from util import locust_metrics  # noqa: E402


def requests_total(service: str, endpoint: str, method: str, result: str) -> float:
    value = locust_metrics.EP_REQUESTS.labels(
        service=service, endpoint=endpoint, method=method, result=result
    )._value.get()
    return float(value)


class TestRecordEndpoint:
    @pytest.mark.parametrize("status", [200, 201, 204, 299])
    def test_2xx_counts_as_success(self, status):
        before = requests_total("svc", "/ok", "GET", "success")

        locust_metrics.record_endpoint("svc", "/ok", "GET", status, 12.0)

        assert requests_total("svc", "/ok", "GET", "success") == before + 1

    @pytest.mark.parametrize("status", [199, 300, 301, 400, 404, 500, 503])
    def test_everything_outside_2xx_counts_as_failure(self, status):
        # 3xx included on purpose. A redirect during a load test means the
        # scenario is not exercising the endpoint it thinks it is.
        before = requests_total("svc", "/bad", "GET", "failure")

        locust_metrics.record_endpoint("svc", "/bad", "GET", status, 12.0)

        assert requests_total("svc", "/bad", "GET", "failure") == before + 1

    def test_a_failure_does_not_increment_the_success_series(self):
        before = requests_total("svc", "/mixed", "POST", "success")

        locust_metrics.record_endpoint("svc", "/mixed", "POST", 500, 5.0)

        assert requests_total("svc", "/mixed", "POST", "success") == before

    def test_latency_is_recorded_in_seconds_not_milliseconds(self):
        # The caller passes milliseconds; the histogram buckets are in seconds.
        # Getting this wrong puts every observation in the overflow bucket and
        # the dashboards quietly show nothing.
        locust_metrics.record_endpoint("unit-latency", "/t", "GET", 200, 250.0)

        total = locust_metrics.EP_LATENCY.labels(
            service="unit-latency", endpoint="/t", method="GET"
        )._sum.get()

        assert total == pytest.approx(0.25)

    def test_each_endpoint_is_counted_separately(self):
        a = requests_total("svc", "/a", "GET", "success")
        b = requests_total("svc", "/b", "GET", "success")

        locust_metrics.record_endpoint("svc", "/a", "GET", 200, 1.0)

        assert requests_total("svc", "/a", "GET", "success") == a + 1
        assert requests_total("svc", "/b", "GET", "success") == b


class TestPickLocale:
    def test_it_returns_one_of_the_configured_locales(self):
        assert locust_metrics.pick_locale("/anything") in locust_metrics.ACCEPT_LANGUAGES

    def test_the_locale_list_is_not_empty(self):
        # pick_locale calls random.choice, which raises on an empty sequence.
        assert locust_metrics.ACCEPT_LANGUAGES
