# 🚀 Grafana Automated Dashboard Import Guide

Complete guide for automatically importing and managing Grafana dashboards with zero manual steps.

---

## ✨ What's Automated?

This setup provides **fully automated** Grafana dashboard provisioning:

✅ **Automatic Import** - Dashboards load on Grafana startup
✅ **Health Checks** - Services verify they're ready before accepting traffic
✅ **Smart Dependencies** - Grafana waits for Prometheus to be healthy
✅ **Verification Scripts** - Automated checks to confirm everything works
✅ **Recovery Tools** - Utilities to fix issues if they occur
✅ **Zero Configuration** - Works out of the box

---

## 🎯 Quick Start - Fully Automated

### Option 1: One-Command Setup (Recommended)

```bash
# Run the automated setup script
./util/setup_monitoring.sh
```

**This script will:**
1. ✅ Check all prerequisites
2. ✅ Start Prometheus and Grafana with Docker Compose
3. ✅ Wait for services to be healthy
4. ✅ Verify dashboard is provisioned
5. ✅ Display access URLs and next steps

**Expected output:**
```
=========================================================================
🚀 Automated Monitoring Setup
=========================================================================

=========================================================================
Checking Prerequisites
=========================================================================
✅ Docker is installed
✅ docker-compose is installed
✅ docker-compose.monitoring.yml found
✅ Prometheus config found
✅ Grafana datasource config found
✅ Grafana dashboard JSON found

=========================================================================
Starting Monitoring Services
=========================================================================
ℹ️  Starting Prometheus and Grafana...
✅ Services started successfully

=========================================================================
Verifying Services
=========================================================================
ℹ️  Waiting for Prometheus to be ready...
✅ Prometheus is healthy and ready
ℹ️  Waiting for Grafana to be ready...
✅ Grafana is healthy and ready
ℹ️  Verifying Grafana dashboard provisioning...
✅ Dashboard 'Locust Load Test' found!
✅ Dashboard provisioning verified

=========================================================================
Setup Complete! 🎉
=========================================================================

✅ Monitoring stack is running and ready!

📊 Access Your Dashboards:
  • Grafana:    http://localhost:3000
  • Prometheus: http://localhost:9091

🔐 Grafana Login:
  • Username: admin
  • Password: admin

📈 Dashboard:
  • Go to: Dashboards → Locust Load Test

🚀 Next Steps:
  1. Start your Locust test:
     cd tests/Sample service && locust -f sample_http_load.py
  2. Begin load testing at http://localhost:8089
  3. Watch the graphs in Grafana!
```

### Option 2: Manual Docker Compose (Also Automated!)

```bash
# Start services with health checks
docker-compose -f docker-compose.monitoring.yml up -d

# Services will auto-import dashboards!
# Access Grafana at http://localhost:3000
```

---

## 🔧 How It Works

### 1. Docker Compose Health Checks

The `docker-compose.monitoring.yml` includes health checks:

```yaml
services:
  prometheus:
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:9090/-/ready"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

  grafana:
    depends_on:
      prometheus:
        condition: service_healthy  # Waits for Prometheus!
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 20s
```

**Benefits:**
- Grafana waits for Prometheus to be ready
- Services report health status
- Setup script knows when to proceed
- Prevents race conditions

### 2. Grafana Provisioning

Grafana automatically loads dashboards from mounted directories:

```yaml
volumes:
  - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
  - ./config/grafana/datasources:/etc/grafana/provisioning/datasources
```

**What gets loaded:**
- `config/grafana/dashboards/dashboard.yml` - Provisioning config
- `config/grafana/dashboards/locust-load-test.json` - Dashboard definition
- `config/grafana/datasources/prometheus.yml` - Prometheus datasource

### 3. Auto-Import on Startup

When Grafana starts, it:
1. Reads provisioning configs from `/etc/grafana/provisioning/`
2. Loads datasources (Prometheus)
3. Imports all JSON dashboards
4. Makes them available immediately

**No manual import needed!**

---

## 🛠️ Management Tools

### Dashboard Manager CLI

Use `grafana_dashboard_manager.sh` for manual operations:

```bash
# List all dashboards
./util/grafana_dashboard_manager.sh list

# Verify provisioning is working
./util/grafana_dashboard_manager.sh verify

# Force reload dashboards
./util/grafana_dashboard_manager.sh reload

# Import via API (alternative method)
./util/grafana_dashboard_manager.sh import

# Export dashboard for backup
./util/grafana_dashboard_manager.sh export <uid>

# Complete status check
./util/grafana_dashboard_manager.sh status

# Show help
./util/grafana_dashboard_manager.sh help
```

### Common Commands

**Check if everything is working:**
```bash
./util/grafana_dashboard_manager.sh status
```

**Force reload if dashboard not showing:**
```bash
./util/grafana_dashboard_manager.sh reload
```

**Backup current dashboard:**
```bash
# Get UID from list command
./util/grafana_dashboard_manager.sh list

# Export using UID
./util/grafana_dashboard_manager.sh export abc123
```

---

## 🔍 Verification

### 1. Check Services Are Running

```bash
# View container status
docker-compose -f docker-compose.monitoring.yml ps

# Should show:
# prometheus    Up (healthy)
# grafana       Up (healthy)
```

### 2. Verify Dashboard Exists

**Option A: Use the manager script:**
```bash
./util/grafana_dashboard_manager.sh verify
```

**Option B: Manual verification:**
```bash
# Check Grafana API
curl -s -u admin:admin http://localhost:3000/api/search?type=dash-db | jq

# Should show dashboard with title containing "Locust Load Test"
```

**Option C: Use Grafana UI:**
1. Open http://localhost:3000
2. Login (admin/admin)
3. Click "Dashboards" icon (left sidebar)
4. Should see "Locust Load Test"

### 3. Check Provisioning Directory

```bash
# Check files are mounted in Grafana container
docker exec grafana ls -lh /etc/grafana/provisioning/dashboards/

# Should show:
# dashboard.yml
# locust-load-test.json
```

---

## 🚨 Troubleshooting

### Dashboard Not Loading?

**Step 1: Run status check**
```bash
./util/grafana_dashboard_manager.sh status
```

**Step 2: Check logs**
```bash
# Grafana logs
docker logs grafana

# Look for provisioning messages:
# "Provisioning dashboards"
# "provisioning.dashboard: Started provisioning"
```

**Step 3: Verify files**
```bash
# Check host files exist
ls -lh config/grafana/dashboards/

# Check container can access files
docker exec grafana ls -lh /etc/grafana/provisioning/dashboards/
```

**Step 4: Force reload**
```bash
./util/grafana_dashboard_manager.sh reload
```

**Step 5: Import via API (last resort)**
```bash
./util/grafana_dashboard_manager.sh import
```

### Services Not Starting?

**Check Docker:**
```bash
docker ps -a
docker-compose -f docker-compose.monitoring.yml logs
```

**Common issues:**
- Port conflicts (3000 or 9091 already in use)
- Docker not running
- Insufficient permissions

**Solutions:**
```bash
# Stop conflicting services
lsof -ti:3000 | xargs kill
lsof -ti:9091 | xargs kill

# Restart Docker
# macOS: Docker Desktop → Restart
# Linux: sudo systemctl restart docker

# Fix permissions
sudo chown -R $USER:$USER ./config
```

### Health Checks Failing?

**Check health status:**
```bash
docker inspect prometheus | jq '.[0].State.Health'
docker inspect grafana | jq '.[0].State.Health'
```

**If unhealthy:**
```bash
# Restart services
docker-compose -f docker-compose.monitoring.yml restart

# Or recreate
docker-compose -f docker-compose.monitoring.yml down
docker-compose -f docker-compose.monitoring.yml up -d
```

### Provisioning Takes Too Long?

**Normal timing:**
- Prometheus ready: ~10 seconds
- Grafana ready: ~20 seconds
- Dashboard visible: ~30 seconds total

**If taking longer:**
```bash
# Watch Grafana logs live
docker logs -f grafana

# Look for errors or warnings
docker logs grafana | grep -i error
docker logs grafana | grep -i warning
```

---

## 📁 File Structure

```
locust-perf/
├── docker-compose.monitoring.yml     # Docker services with health checks
├── config/
│   ├── prometheus.yml                # Prometheus config
│   └── grafana/
│       ├── datasources/
│       │   └── prometheus.yml        # Auto-imported datasource
│       └── dashboards/
│           ├── dashboard.yml         # Provisioning config
│           └── locust-load-test.json  # Dashboard JSON
└── util/
    ├── setup_monitoring.sh           # Automated setup script
    └── grafana_dashboard_manager.sh  # Dashboard management CLI
```

---

## 🎨 Customizing Dashboards

### Modify Existing Dashboard

**Option 1: Edit in Grafana UI (Recommended)**
1. Open dashboard in Grafana
2. Click "Dashboard settings" (gear icon)
3. Make changes
4. Save
5. Export to JSON
6. Save to `config/grafana/dashboards/locust-load-test.json`

**Option 2: Edit JSON directly**
```bash
# Edit the JSON file
vim config/grafana/dashboards/locust-load-test.json

# Reload dashboard
./util/grafana_dashboard_manager.sh reload
```

### Add New Dashboard

1. **Create dashboard in Grafana**
2. **Export to JSON:**
   ```bash
   # Get dashboard UID
   ./util/grafana_dashboard_manager.sh list

   # Export
   ./util/grafana_dashboard_manager.sh export <uid>
   ```
3. **Move to provisioning directory:**
   ```bash
   mv dashboard-export-*.json config/grafana/dashboards/my-new-dashboard.json
   ```
4. **Reload:**
   ```bash
   ./util/grafana_dashboard_manager.sh reload
   ```

### Remove Dashboard

**Option 1: Delete from Grafana UI**
- Dashboard will be re-imported on restart (from provisioning)

**Option 2: Remove from provisioning**
```bash
# Remove JSON file
rm config/grafana/dashboards/unwanted-dashboard.json

# Restart Grafana
docker restart grafana
```

---

## 🔐 Security Best Practices

### Change Default Credentials

**Update docker-compose.monitoring.yml:**
```yaml
environment:
  - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
```

**Create .env file:**
```bash
echo "GRAFANA_PASSWORD=your_secure_password" > .env
```

**Restart services:**
```bash
docker-compose -f docker-compose.monitoring.yml down
docker-compose -f docker-compose.monitoring.yml up -d
```

### Restrict Access

**Docker Compose (development):**
```yaml
ports:
  - "127.0.0.1:3000:3000"  # Only localhost access
```

**Production (use reverse proxy):**
```yaml
# Don't expose ports directly
# Use nginx/traefik with SSL
```

---

## 📊 Advanced Features

### Auto-Refresh Dashboard

**Set in Grafana UI:**
1. Open dashboard
2. Click time picker (top right)
3. Select refresh interval: `5s`, `10s`, `30s`, `1m`

**Or configure in JSON:**
```json
{
  "refresh": "5s",
  ...
}
```

### Alert Configuration

**In Grafana UI:**
1. Dashboard → Panel → Edit
2. Alert tab
3. Create alert rule
4. Configure notification channels

### Multiple Dashboards

**Add more dashboards:**
1. Create JSON file in `config/grafana/dashboards/`
2. Name it descriptively: `my-custom-dashboard.json`
3. Restart Grafana: `docker restart grafana`
4. Dashboard auto-loads!

---

## 🤝 Integration

### CI/CD Pipeline

```yaml
# .github/workflows/monitoring.yml
- name: Start Monitoring Stack
  run: |
    docker-compose -f docker-compose.monitoring.yml up -d
    ./util/setup_monitoring.sh
```

### Kubernetes

```yaml
# Use ConfigMaps for provisioning
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
data:
  locust-load-test.json: |
    {{ .Files.Get "config/grafana/dashboards/locust-load-test.json" }}
```

---

## 📚 Additional Resources

- [Grafana Provisioning Docs](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- [Dashboard JSON Schema](https://grafana.com/docs/grafana/latest/dashboards/json-model/)
- [Prometheus Configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)

---

## ✅ Summary

**What you get with automated import:**

✨ **Zero manual steps** - Everything auto-imports on startup
🔒 **Reliable provisioning** - Health checks ensure proper startup
🛠️ **Management tools** - CLI utilities for troubleshooting
📊 **Instant visibility** - Dashboards ready in ~30 seconds
🔄 **Version control** - Dashboards stored as code in git
🚀 **Reproducible** - Same setup on every machine

**You just run:**
```bash
./util/setup_monitoring.sh
```

**And get:**
- Prometheus running and scraping metrics
- Grafana running with dashboards loaded
- All connections verified and working
- Clear instructions for next steps

**No manual imports. No configuration. No hassle. Just working dashboards! 🎉**
