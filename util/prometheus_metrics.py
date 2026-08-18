"""
Reusable Prometheus Metrics Utility for Locust Load Tests
Provides standardized metrics collection and export for any Locust test.
"""
import logging
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, start_http_server

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """
    Reusable Prometheus metrics exporter for Locust tests.

    Usage:
        from util.prometheus_metrics import PrometheusMetrics

        metrics = PrometheusMetrics(
            service_name="my-service",
            port=9090
        )

        # In your test:
        metrics.record_ttfc(ttfc_seconds)
        metrics.record_full_response(response_seconds)
        metrics.increment_success()
    """

    def __init__(self, service_name: str, port: int = 9090):
        """
        Initialize Prometheus metrics for a service.

        Args:
            service_name: Name of the service being tested (e.g., "checkout", "payments")
            port: Port to expose metrics on (default: 9090)
        """
        self.service_name = service_name
        self.port = port

        # TTFC Metrics
        self.ttfc_histogram = Histogram(
            f'{service_name}_ttfc_seconds',
            'Time to First Chunk/Token in seconds',
            buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
        )

        # Full Response Metrics
        self.full_response_histogram = Histogram(
            f'{service_name}_full_response_seconds',
            'Time for full response in seconds',
            buckets=[0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0]
        )

        # Request Counters
        self.requests_total = Counter(f'{service_name}_requests_total', 'Total requests made')
        self.requests_success = Counter(f'{service_name}_requests_success', 'Successful requests')
        self.requests_failed = Counter(f'{service_name}_requests_failed', 'Failed requests')

        # Response Data Metrics
        self.chunks_histogram = Histogram(
            f'{service_name}_chunks_received',
            'Number of chunks per response',
            buckets=[1, 5, 10, 20, 30, 50, 75, 100, 150, 200]
        )
        self.bytes_histogram = Histogram(
            f'{service_name}_bytes_received',
            'Bytes received per response',
            buckets=[100, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]
        )

        # Latency Gauge (current value)
        self.current_ttfc = Gauge(f'{service_name}_current_ttfc_seconds', 'Current TTFC in seconds')
        self.current_response_time = Gauge(f'{service_name}_current_response_seconds', 'Current response time in seconds')

        # Active Users
        self.active_users = Gauge(f'{service_name}_active_users', 'Number of active users')

        # Start metrics server
        self._start_server()

    def _start_server(self):
        """Start the Prometheus metrics HTTP server."""
        try:
            start_http_server(self.port)
            logger.info(f"📊 Prometheus metrics server started on http://localhost:{self.port}/metrics")
        except OSError as e:
            logger.warning(f"Could not start Prometheus server on port {self.port}: {e}")
            logger.info("Metrics server may already be running or port is in use")

    def record_ttfc(self, seconds: float):
        """
        Record Time to First Chunk/Token.

        Args:
            seconds: Time in seconds until first chunk was received
        """
        self.ttfc_histogram.observe(seconds)
        self.current_ttfc.set(seconds)

    def record_full_response(self, seconds: float):
        """
        Record full response time.

        Args:
            seconds: Total time in seconds for complete response
        """
        self.full_response_histogram.observe(seconds)
        self.current_response_time.set(seconds)

    def increment_total(self):
        """Increment total requests counter."""
        self.requests_total.inc()

    def increment_success(self):
        """Increment successful requests counter."""
        self.requests_success.inc()

    def increment_failed(self):
        """Increment failed requests counter."""
        self.requests_failed.inc()

    def record_chunks(self, count: int):
        """
        Record number of chunks received.

        Args:
            count: Number of chunks in the response
        """
        self.chunks_histogram.observe(count)

    def record_bytes(self, bytes_count: int):
        """
        Record bytes received.

        Args:
            bytes_count: Number of bytes in the response
        """
        self.bytes_histogram.observe(bytes_count)

    def set_active_users(self, count: int):
        """
        Set current active users count.

        Args:
            count: Number of currently active users
        """
        self.active_users.set(count)

    def record_request(self, ttfc_ms: Optional[float] = None, full_response_ms: Optional[float] = None,
                      chunks: Optional[int] = None, bytes_count: Optional[int] = None, success: bool = True):
        """
        Convenience method to record all metrics for a single request.

        Args:
            ttfc_ms: Time to first chunk in milliseconds
            full_response_ms: Full response time in milliseconds
            chunks: Number of chunks received
            bytes_count: Number of bytes received
            success: Whether the request was successful
        """
        self.increment_total()

        if success:
            self.increment_success()
        else:
            self.increment_failed()

        if ttfc_ms is not None:
            self.record_ttfc(ttfc_ms / 1000.0)

        if full_response_ms is not None:
            self.record_full_response(full_response_ms / 1000.0)

        if chunks is not None:
            self.record_chunks(chunks)

        if bytes_count is not None:
            self.record_bytes(bytes_count)


# Singleton instance (optional - use for single-service scenarios)
_default_metrics = None


def get_default_metrics(service_name: str = "locust", port: int = 9090) -> PrometheusMetrics:
    """
    Get or create default PrometheusMetrics instance.

    Args:
        service_name: Service name (only used on first call)
        port: Metrics port (only used on first call)

    Returns:
        PrometheusMetrics instance
    """
    global _default_metrics
    if _default_metrics is None:
        _default_metrics = PrometheusMetrics(service_name, port)
    return _default_metrics
