# 📊 Prometheus Metrics Utility - Usage Guide

Reusable Prometheus metrics utility for **any** Locust test.

---

## 🚀 Quick Start

### 1. Import and Initialize

```python
from util.prometheus_metrics import PrometheusMetrics

# Initialize metrics for your service
metrics = PrometheusMetrics(
    service_name="my-service",  # Will prefix all metrics
    port=9090                    # Prometheus scrape port
)
```

### 2. Use in Your Locust Test

```python
import time
from locust import HttpUser, TaskSet, task, between
from util.prometheus_metrics import PrometheusMetrics

# Initialize once at module level
metrics = PrometheusMetrics("my-api", port=9090)

class MyAPITasks(TaskSet):

    @task
    def my_request(self):
        start_time = time.time()
        first_chunk_time = None
        chunks = 0
        bytes_received = 0

        with self.client.get("/api/endpoint", stream=True) as response:
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        if chunks == 0:
                            # Record TTFC
                            first_chunk_time = time.time()
                            ttfc_ms = (first_chunk_time - start_time) * 1000
                            metrics.record_ttfc(ttfc_ms / 1000.0)

                        chunks += 1
                        bytes_received += len(chunk)

                # Record full response
                full_time_ms = (time.time() - start_time) * 1000
                metrics.record_full_response(full_time_ms / 1000.0)
                metrics.record_chunks(chunks)
                metrics.record_bytes(bytes_received)
                metrics.increment_success()
            else:
                metrics.increment_failed()

class MyAPIUser(HttpUser):
    tasks = [MyAPITasks]
    wait_time = between(1, 3)
```

---

## 📖 API Reference

### Initialization

```python
PrometheusMetrics(service_name: str, port: int = 9090)
```

**Parameters:**
- `service_name`: Prefix for all metrics (e.g., "payments", "auth", "sample_service")
- `port`: Port to expose metrics (default: 9090)

**Example:**
```python
metrics = PrometheusMetrics("payments-api", port=9090)
```

---

### Recording Metrics

#### `record_ttfc(seconds: float)`
Record Time to First Chunk/Token.

```python
ttfc_seconds = (first_chunk_time - request_start)
metrics.record_ttfc(ttfc_seconds)
```

#### `record_full_response(seconds: float)`
Record total response time.

```python
response_seconds = (response_end - request_start)
metrics.record_full_response(response_seconds)
```

#### `increment_total()`
Increment total requests counter.

```python
metrics.increment_total()
```

#### `increment_success()`
Increment successful requests counter.

```python
metrics.increment_success()
```

#### `increment_failed()`
Increment failed requests counter.

```python
metrics.increment_failed()
```

#### `record_chunks(count: int)`
Record number of streaming chunks.

```python
metrics.record_chunks(45)  # 45 chunks received
```

#### `record_bytes(bytes_count: int)`
Record bytes received.

```python
metrics.record_bytes(2048)  # 2048 bytes
```

#### `set_active_users(count: int)`
Set current active users.

```python
metrics.set_active_users(10)  # 10 active users
```

---

### Convenience Method

#### `record_request(...)`
Record all metrics for a single request in one call.

```python
metrics.record_request(
    ttfc_ms=456.0,           # Time to first chunk (ms)
    full_response_ms=3421.0, # Full response time (ms)
    chunks=45,                # Number of chunks
    bytes_count=2048,         # Bytes received
    success=True              # Request successful?
)
```

**This is equivalent to:**
```python
metrics.increment_total()
metrics.increment_success()
metrics.record_ttfc(0.456)
metrics.record_full_response(3.421)
metrics.record_chunks(45)
metrics.record_bytes(2048)
```

---

## 📊 Metrics Exported

Your service will export these Prometheus metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `{service}_ttfc_seconds` | Histogram | Time to first chunk |
| `{service}_full_response_seconds` | Histogram | Full response time |
| `{service}_requests_total` | Counter | Total requests |
| `{service}_requests_success` | Counter | Successful requests |
| `{service}_requests_failed` | Counter | Failed requests |
| `{service}_chunks_received` | Histogram | Chunks per response |
| `{service}_bytes_received` | Histogram | Bytes per response |
| `{service}_current_ttfc_seconds` | Gauge | Latest TTFC |
| `{service}_current_response_seconds` | Gauge | Latest response time |
| `{service}_active_users` | Gauge | Active users count |

**Example with `service_name="payments"`:**
- `payments_ttfc_seconds`
- `payments_requests_total`
- etc.

---

## 🎯 Real-World Examples

### Example 1: REST API Load Test

```python
from locust import HttpUser, task, between
from util.prometheus_metrics import PrometheusMetrics
import time

metrics = PrometheusMetrics("rest-api")

class RestAPIUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def get_users(self):
        start = time.time()

        response = self.client.get("/api/users")

        duration_ms = (time.time() - start) * 1000
        success = response.status_code == 200

        metrics.record_request(
            full_response_ms=duration_ms,
            bytes_count=len(response.content),
            success=success
        )
```

### Example 2: Streaming API Test

```python
from locust import HttpUser, task
from util.prometheus_metrics import PrometheusMetrics
import time

metrics = PrometheusMetrics("streaming-api")

class StreamingAPIUser(HttpUser):

    @task
    def stream_data(self):
        start = time.time()
        first_chunk_time = None
        chunks = 0
        total_bytes = 0

        with self.client.get("/stream", stream=True) as response:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    if chunks == 0:
                        first_chunk_time = time.time()
                    chunks += 1
                    total_bytes += len(chunk)

            ttfc_ms = (first_chunk_time - start) * 1000 if first_chunk_time else 0
            full_ms = (time.time() - start) * 1000

            metrics.record_request(
                ttfc_ms=ttfc_ms,
                full_response_ms=full_ms,
                chunks=chunks,
                bytes_count=total_bytes,
                success=response.status_code == 200
            )
```

### Example 3: gRPC Streaming Test

```python
from locust import User, task
from util.prometheus_metrics import PrometheusMetrics
import time
import grpc

metrics = PrometheusMetrics("grpc-service")

class GRPCUser(User):

    @task
    def streaming_rpc(self):
        start = time.time()
        first_chunk_time = None
        chunks = 0

        try:
            for response in self.stub.StreamingMethod(request):
                if chunks == 0:
                    first_chunk_time = time.time()
                chunks += 1

            ttfc_ms = (first_chunk_time - start) * 1000 if first_chunk_time else 0
            full_ms = (time.time() - start) * 1000

            metrics.record_request(
                ttfc_ms=ttfc_ms,
                full_response_ms=full_ms,
                chunks=chunks,
                success=True
            )
        except grpc.RpcError:
            metrics.record_request(success=False)
```

---

## 🔧 Advanced Usage

### Multiple Services in One Test

```python
from util.prometheus_metrics import PrometheusMetrics

# Each service gets its own metrics with unique names
auth_metrics = PrometheusMetrics("auth-service", port=9090)
payment_metrics = PrometheusMetrics("payment-service", port=9091)

class MyUser(HttpUser):

    @task
    def auth_and_pay(self):
        # Auth request
        start = time.time()
        auth_response = self.client.post("/auth")
        auth_metrics.record_request(
            full_response_ms=(time.time() - start) * 1000,
            success=auth_response.status_code == 200
        )

        # Payment request
        start = time.time()
        payment_response = self.client.post("/payment")
        payment_metrics.record_request(
            full_response_ms=(time.time() - start) * 1000,
            success=payment_response.status_code == 200
        )
```

### Using Singleton Pattern

```python
from util.prometheus_metrics import get_default_metrics

# Get singleton instance (auto-created on first call)
metrics = get_default_metrics("my-service", port=9090)

# Anywhere else in your code
from util.prometheus_metrics import get_default_metrics
metrics = get_default_metrics()  # Returns same instance
```

### Custom Histogram Buckets

```python
# Edit util/prometheus_metrics.py to customize buckets:

self.ttfc_histogram = Histogram(
    f'{service_name}_ttfc_seconds',
    'Time to First Chunk in seconds',
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0]  # Your custom buckets
)
```

---

## 🐳 Integration with Docker

### Prometheus Configuration

Add your test to `config/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'my-service'
    static_configs:
      - targets: ['host.docker.internal:9090']
        labels:
          service: 'my-service'
```

### Start Monitoring Stack

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

### View Metrics

1. **Prometheus**: http://localhost:9091
2. **Grafana**: http://localhost:3000
3. **Raw Metrics**: http://localhost:9090/metrics

---

## 📈 Creating Grafana Dashboards

Use these PromQL queries for your service:

### TTFC P95
```promql
histogram_quantile(0.95, rate(my_service_ttfc_seconds_bucket[1m]))
```

### Success Rate
```promql
rate(my_service_requests_success_total[1m]) / rate(my_service_requests_total[1m])
```

### Request Rate
```promql
rate(my_service_requests_total[1m])
```

### Average Response Time
```promql
rate(my_service_full_response_seconds_sum[1m]) / rate(my_service_full_response_seconds_count[1m])
```

---

## ✅ Best Practices

1. **Service Naming**: Use descriptive service names:
   - ✅ `"payment-api"`, `"user-service"`, `"checkout-api"`
   - ❌ `"test"`, `"api"`, `"service"`

2. **Port Assignment**: Use different ports for different services:
   - Service A: 9090
   - Service B: 9091
   - Service C: 9092

3. **Metrics Granularity**: Record what matters:
   - Always: TTFC, response time, success/failure
   - Streaming: chunks, bytes
   - Optional: active users (if relevant)

4. **Error Handling**: Always record failures:
   ```python
   try:
       # ... make request ...
       metrics.increment_success()
   except Exception as e:
       metrics.increment_failed()
       raise
   ```

5. **Performance**: The utility is lightweight, but:
   - Don't call metrics inside tight loops
   - Batch updates when possible
   - Use `record_request()` for convenience

---

## 🔍 Troubleshooting

### "OSError: [Errno 48] Address already in use"

**Cause**: Port 9090 already in use

**Solution**: Use a different port or stop the conflicting process
```python
metrics = PrometheusMetrics("my-service", port=9091)
```

### Metrics not appearing in Prometheus

**Check:**
1. Metrics server started? Look for log: `"Prometheus metrics server started..."`
2. Endpoint accessible? `curl http://localhost:9090/metrics`
3. Prometheus scraping? Check http://localhost:9091/targets

### Values always zero

**Cause**: Not calling metrics recording methods

**Solution**: Ensure you're calling:
```python
metrics.record_request(...)  # or individual metrics methods
```

---

## 📚 Additional Resources

- [Prometheus Python Client Docs](https://github.com/prometheus/client_python)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboard Guide](https://grafana.com/docs/grafana/latest/dashboards/)

---

**Ready to use? Just import and start tracking metrics!** 📊

```python
from util.prometheus_metrics import PrometheusMetrics

metrics = PrometheusMetrics("your-service")
# Start testing!
```

---

**Last Updated:** 2025-11-04
**Version:** 1.0.0
