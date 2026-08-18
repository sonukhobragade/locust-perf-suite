# 📊 Prometheus + Grafana Monitoring Setup

Complete guide for setting up time-series monitoring and visualization for your Locust load tests.

---

## 🎯 What You Get

With this setup, you'll have:

✅ **Real-time Graphs** - Beautiful time-series charts updating every 5 seconds
✅ **TTFC Metrics** - Time to First Chunk (P50, P95, P99)
✅ **Full Response Time** - Complete response metrics
✅ **Success/Failure Rates** - Request validation tracking
✅ **Chunks & Bytes** - Streaming data statistics
✅ **Historical Data** - 7 days of retention
✅ **Zero Code Changes** - Works with existing tests
✅ **Auto-Import Dashboards** - No manual import needed! 🎉
✅ **Health Checks** - Services verify readiness automatically
✅ **Management Tools** - CLI utilities for troubleshooting

---

## 📖 Documentation Guide

- **This document** - Core setup and usage
- **[GRAFANA_AUTO_IMPORT_GUIDE.md](./GRAFANA_AUTO_IMPORT_GUIDE.md)** - Automated import details
- **[util/PROMETHEUS_UTIL_USAGE.md](./util/PROMETHEUS_UTIL_USAGE.md)** - Python utility guide

---

## 🚀 Quick Start (5 Minutes)

### 🎯 Automated Setup (Recommended)

```bash
# One-command automated setup with verification
./util/setup_monitoring.sh
```

**This script automatically:**
- ✅ Checks prerequisites
- ✅ Starts Prometheus and Grafana
- ✅ Waits for services to be healthy
- ✅ Verifies dashboard import
- ✅ Shows you next steps

**For complete automated import documentation, see:** [GRAFANA_AUTO_IMPORT_GUIDE.md](./GRAFANA_AUTO_IMPORT_GUIDE.md)

### Manual Setup (Alternative)

```bash
# From project root
docker-compose -f docker-compose.monitoring.yml up -d
```

**This starts:**
- Prometheus on `http://localhost:9091`
- Grafana on `http://localhost:3000`
- **Dashboards auto-import on startup!**

### Step 2: Start Your Locust Test

```bash
cd tests/SampleService
source ../../venv/bin/activate
locust -f sample_http_load.py
```

**You'll see:**
```
📊 Prometheus metrics server started on http://localhost:9090/metrics
📊 CUSTOM STREAMING METRICS DASHBOARD AVAILABLE
================================================================================
🌐 Custom UI:       http://localhost:8089/streaming-metrics
📡 JSON API:        http://localhost:8089/stats/custom
📈 Prometheus:      http://localhost:9090/metrics
```

### Step 3: Start Load Test

1. Open `http://localhost:8089`
2. Configure users and spawn rate
3. Click "Start swarming"

### Step 4: View Grafana Dashboard

1. Open `http://localhost:3000`
2. Login: `admin` / `admin`
3. Dashboard → **"Locust Load Test"**
   - Dashboard is **automatically imported** - no manual import needed!

**You should see beautiful graphs! 📊**

**💡 Tip:** Use `./util/grafana_dashboard_manager.sh status` to verify everything is working

---

## 📈 Grafana Dashboard Overview

Your dashboard includes **7 panels**:

### 1. ⚡ Time to First Chunk (TTFC)
- **What**: Time until first token arrives
- **Shows**: P50, P95, P99 percentiles
- **Good**: P95 < 1 second, P99 < 2 seconds

### 2. 📦 Full Response Time
- **What**: Total time to receive all tokens
- **Shows**: P50, P95, P99 percentiles
- **Watch**: Trends over time, spikes during load

### 3. ✅ Success Rate (Gauge)
- **What**: Percentage of successful requests
- **Target**: > 95%
- **Colors**: Green (good), Yellow (warning), Red (critical)

### 4. 📊 Request Rate (Success vs Failed)
- **What**: Rate of successful vs failed requests per second
- **Shows**: Success (green), Failed (red)
- **Use**: Identify when failures start occurring

### 5. 🔢 Requests Per Minute (Gauge)
- **What**: Total throughput
- **Shows**: Requests/min
- **Use**: Capacity planning

### 6. 📦 Chunks Received Per Response
- **What**: Number of streaming chunks
- **Shows**: P50, P95 percentiles
- **Use**: Understand response fragmentation

### 7. 💾 Bytes Received Per Response
- **What**: Total bytes per response
- **Shows**: P50, P95 percentiles
- **Use**: Bandwidth analysis

---

## 🔍 How It Works

### Architecture

```
Locust Test (Port 9090)
    ↓ (exports metrics)
Prometheus (Port 9091) ← Health checks enabled!
    ↓ (scrapes every 5s)
Grafana (Port 3000)    ← Auto-imports dashboards!
    ↓ (queries and visualizes)
Your Browser
```

### 🎯 Automated Dashboard Import

**How dashboards are automatically imported:**

1. **Docker Compose** mounts dashboard files:
   ```yaml
   volumes:
     - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
   ```

2. **Grafana Provisioning** reads on startup:
   - `config/grafana/dashboards/dashboard.yml` (config)
   - `config/grafana/dashboards/locust-load-test.json` (dashboard)

3. **Health Checks** ensure proper startup order:
   - Prometheus starts and becomes healthy
   - Grafana waits for Prometheus
   - Grafana loads and provisions dashboards
   - All ready in ~30 seconds!

**No manual import needed! Everything happens automatically.**

**For detailed automation info:** See [GRAFANA_AUTO_IMPORT_GUIDE.md](./GRAFANA_AUTO_IMPORT_GUIDE.md)

### Metrics Flow

1. **Locust Test** exposes Prometheus metrics on `:9090/metrics`
2. **Prometheus** scrapes metrics every 5 seconds
3. **Grafana** queries Prometheus and renders graphs
4. **You** see real-time visualizations!

### Metrics Exported

| Metric Name | Type | Description |
|-------------|------|-------------|
| `sample_service_ttfc_seconds` | Histogram | Time to first chunk |
| `sample_service_full_response_seconds` | Histogram | Full response time |
| `sample_service_requests_total` | Counter | Total requests made |
| `sample_service_requests_success` | Counter | Successful requests |
| `sample_service_requests_failed` | Counter | Failed requests |
| `sample_service_chunks_received` | Histogram | Chunks per response |
| `sample_service_bytes_received` | Histogram | Bytes per response |

---

## 🛠️ Configuration

### Prometheus Scrape Interval

Edit `config/prometheus.yml`:

```yaml
global:
  scrape_interval: 5s      # Change this
  evaluation_interval: 5s
```

**Recommended values:**
- Development: `5s`
- Load Testing: `10s`
- Long-running: `30s`

### Data Retention

Edit `docker-compose.monitoring.yml`:

```yaml
command:
  - '--storage.tsdb.retention.time=7d'  # Change this
```

**Options:**
- `7d` - 7 days
- `30d` - 30 days
- `90d` - 90 days

### Grafana Refresh Rate

In Grafana dashboard:
1. Click ⏰ (time picker) at top-right
2. Select refresh interval: `5s`, `10s`, `30s`, `1m`

---

## 📊 Custom Queries

You can create your own panels in Grafana. Here are useful PromQL queries:

### Average TTFC
```promql
rate(sample_service_ttfc_seconds_sum[1m]) / rate(sample_service_ttfc_seconds_count[1m])
```

### Error Rate
```promql
rate(sample_service_requests_failed_total[1m]) / rate(sample_service_requests_total[1m])
```

### Throughput (requests/sec)
```promql
rate(sample_service_requests_total[1m])
```

### P99 TTFC
```promql
histogram_quantile(0.99, rate(sample_service_ttfc_seconds_bucket[1m]))
```

---

## 🔧 Troubleshooting

### Dashboard Not Auto-Importing?

**Quick fix:**
```bash
# Check status
./util/grafana_dashboard_manager.sh status

# Force reload
./util/grafana_dashboard_manager.sh reload
```

**Detailed troubleshooting:**
See [GRAFANA_AUTO_IMPORT_GUIDE.md - Troubleshooting](./GRAFANA_AUTO_IMPORT_GUIDE.md#-troubleshooting)

### Prometheus Not Scraping

**Check Prometheus targets:**
```bash
open http://localhost:9091/targets
```

Should show: `http://host.docker.internal:9090` as **UP**

**If DOWN:**
1. Verify Locust is running
2. Check `:9090/metrics` is accessible
3. On Linux, use `--network host` in docker-compose

### No Data in Grafana

**Check datasource:**
1. Grafana → Configuration → Data Sources
2. Select "Prometheus"
3. Click "Test" - should say "Data source is working"

**If failing:**
- Check Prometheus is running: `docker ps`
- Verify URL: `http://prometheus:9090`

### Graphs Show "No Data"

**Causes:**
1. No load test running
2. Prometheus not scraping
3. Wrong time range in Grafana

**Fix:**
1. Start Locust test
2. Run load test (start swarming)
3. Set time range to "Last 5 minutes"

### Docker Permission Errors

```bash
# Fix volume permissions
sudo chown -R $USER:$USER ./config
```

---

## 🎨 Customizing Dashboards

### Add New Panel

1. Click "+ Add" → "Visualization"
2. Select "Prometheus" datasource
3. Enter PromQL query
4. Configure visualization type
5. Save

### Export Dashboard

1. Dashboard → Share → Export
2. Save JSON
3. Share with team

### Import Dashboard

1. Dashboards → Import
2. Upload JSON file or paste JSON
3. Select datasource
4. Import

---

## 🚀 Production Best Practices

### 1. Secure Grafana
```yaml
# docker-compose.monitoring.yml
environment:
  - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
  - GF_SERVER_ROOT_URL=https://grafana.yourdomain.com
  - GF_AUTH_ANONYMOUS_ENABLED=false
```

### 2. Add Alerting
Configure alerts in Grafana for:
- TTFC P95 > 2 seconds
- Success rate < 90%
- Request rate drops > 50%

### 3. Persistent Storage
Ensure volumes are backed up:
```bash
docker volume ls
docker volume inspect perf_prometheus_data
docker volume inspect perf_grafana_data
```

### 4. Resource Limits
Add to docker-compose:
```yaml
services:
  prometheus:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1'
```

---

## 📁 File Structure

```
locust-perf/
├── docker-compose.monitoring.yml      # Docker setup
├── config/
│   ├── prometheus.yml                 # Prometheus config
│   └── grafana/
│       ├── datasources/
│       │   └── prometheus.yml         # Grafana datasource
│       └── dashboards/
│           ├── dashboard.yml          # Dashboard provisioning
│           └── locust-load-test.json  # Dashboard definition
└── tests/SampleService/
    └── sample_http_load.py      # Test with Prometheus metrics
```

---

## 🔗 Useful Commands

```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# View logs
docker-compose -f docker-compose.monitoring.yml logs -f

# Stop monitoring stack
docker-compose -f docker-compose.monitoring.yml down

# Stop and remove volumes (clean slate)
docker-compose -f docker-compose.monitoring.yml down -v

# Check Prometheus metrics endpoint
curl http://localhost:9090/metrics | grep sample_service

# Query Prometheus API
curl 'http://localhost:9091/api/v1/query?query=sample_service_ttfc_seconds_count'
```

---

## 📖 Additional Resources

- [Prometheus Docs](https://prometheus.io/docs/)
- [Grafana Docs](https://grafana.com/docs/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)

---

## 🎉 You're All Set!

Your monitoring stack is ready. Start a load test and watch those beautiful graphs! 📊

**Questions?** Check the troubleshooting section or logs.

---

**Last Updated:** 2025-11-04
**Version:** 1.0.0
