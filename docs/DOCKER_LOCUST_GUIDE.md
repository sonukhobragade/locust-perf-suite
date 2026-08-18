# Locust Docker - Run Load Tests While PC is Locked

## ✅ Why Docker?

Docker containers run as system services, not as user processes. This means:
- ✅ **Works when PC is locked** - Container keeps running
- ✅ **Survives terminal closure** - Background process
- ✅ **Consistent environment** - Same setup every time
- ❌ **Stops when PC sleeps** - Keep PC awake or use wake-on-LAN
- ❌ **Stops when PC shuts down** - Only shutdown stops it

## 🚀 Quick Start (3 Steps)

### Step 1: Build Docker Image (One-time)

```bash
./run_locust_docker.sh build
```

**This builds the image with:**
- Python 3.11
- All dependencies from `requirements.txt`
- Your test files and utilities
- Prometheus metrics server

### Step 2: Start Locust

```bash
# Web UI mode (interactive)
./run_locust_docker.sh start

# Headless mode (automated)
./run_locust_docker.sh start --headless -u 100 -r 10 -d 1h
```

**Options:**
- `-u, --users NUM` - Number of concurrent users
- `-r, --rate NUM` - Users spawned per second
- `-d, --duration TIME` - Test duration (e.g., `10m`, `1h`, `30s`)
- `--headless` - Run without Web UI (automated)

### Step 3: Monitor & Control

```bash
# Check if running
./run_locust_docker.sh status

# View logs (live)
./run_locust_docker.sh logs

# Stop test
./run_locust_docker.sh stop
```

## 🌐 Access Points

Once started, access these URLs:

| Service | URL | Purpose |
|---------|-----|---------|
| **Locust Web UI** | http://localhost:8089 | Start/stop tests, view real-time stats |
| **Prometheus Metrics** | http://localhost:9090/metrics | Raw metrics for Grafana |
| **Custom Stats API** | http://localhost:8089/stats/custom | JSON API for custom metrics |

## 📊 Common Usage Patterns

### Pattern 1: Interactive Testing (Web UI)

```bash
# Start with Web UI
./run_locust_docker.sh start

# Open browser to http://localhost:8089
# Configure users/spawn rate in UI
# Start test from UI
# Lock your PC - test continues! 🔒

# Come back later, check status
./run_locust_docker.sh status
./run_locust_docker.sh logs
```

### Pattern 2: Automated Testing (Headless)

```bash
# Run 100 users for 30 minutes
./run_locust_docker.sh start --headless -u 100 -r 10 -d 30m

# Lock your PC immediately 🔒
# Test runs for 30 minutes and stops automatically

# Check final results
./run_locust_docker.sh logs
```

### Pattern 3: Long-Running Soak Test

```bash
# Start test without duration (runs forever)
./run_locust_docker.sh start --headless -u 50 -r 5

# Lock PC, go home 🏠
# Test runs overnight

# Next morning - check results
./run_locust_docker.sh status
./run_locust_docker.sh logs
./run_locust_docker.sh stop
```

### Pattern 4: Running Different Tests

```bash
# Run specific test file
./run_locust_docker.sh start -t tests/AuthService/jwt_auth_load.py

# Or edit the script to change default test file
```

## 🔧 Management Commands

### View All Commands

```bash
./run_locust_docker.sh --help
```

### Essential Commands

```bash
# Build/rebuild image
./run_locust_docker.sh build

# Start container
./run_locust_docker.sh start

# Stop container
./run_locust_docker.sh stop

# Restart (stop + start)
./run_locust_docker.sh restart

# View logs (follow mode)
./run_locust_docker.sh logs

# Check if running
./run_locust_docker.sh status

# Open shell inside container (debug)
./run_locust_docker.sh shell

# Remove container and image
./run_locust_docker.sh clean
```

## 🔍 Checking if Container is Running

### Method 1: Using the script

```bash
./run_locust_docker.sh status
```

### Method 2: Using Docker directly

```bash
# List running containers
docker ps

# Check specific container
docker ps --filter "name=locust-load-test"

# View logs
docker logs -f locust-load-test
```

## 🐛 Troubleshooting

### Container Won't Start

```bash
# Check if port is already in use
lsof -i :8089

# View error logs
docker logs locust-load-test

# Remove old container and try again
./run_locust_docker.sh clean
./run_locust_docker.sh build
./run_locust_docker.sh start
```

### Container Stopped Unexpectedly

```bash
# View logs to see what happened
docker logs locust-load-test

# Check Docker daemon status
docker ps

# Restart Docker Desktop if needed
```

### Can't Access Web UI

```bash
# Verify container is running
./run_locust_docker.sh status

# Check port mapping
docker ps --filter "name=locust-load-test"

# Should show: 0.0.0.0:8089->8089/tcp
```

### Environment Variables Not Loading

The container automatically loads `.env` file. Check:

```bash
# Verify .env exists
cat .env

# Check what's loaded in container
docker exec locust-load-test env | grep SAMPLE_SERVICE
```

## 📝 Environment Variables

The container loads from `.env` file:

```bash
# .env file content
SAMPLE_SERVICE_TOKEN=your_token_here
SAMPLE_SERVICE_HOST=https://api.example.com
```

Make sure `.env` exists before starting!

## 🔄 Updating Tests

When you modify test files:

```bash
# Rebuild image
./run_locust_docker.sh build

# Restart container with new image
./run_locust_docker.sh restart
```

## 💾 Data Persistence

**Reports and logs:**
- Locust reports are generated inside the container
- Extract them using:

```bash
# Copy reports from container
docker cp locust-load-test:/app/reports ./reports

# Or mount volume when starting (modify script):
# -v $(pwd)/reports:/app/reports
```

## 🎯 Integration with Monitoring

### With Grafana

The container exposes Prometheus metrics on port 9090:

```bash
# Prometheus endpoint
curl http://localhost:9090/metrics
```

Configure Grafana to scrape `localhost:9090` for Locust metrics.

### Docker Compose Integration

To run alongside your monitoring stack:

```yaml
# Add to docker-compose.monitoring.yml
  locust:
    image: locust-perf
    container_name: locust-load-test
    ports:
      - "8089:8089"
      - "9090:9090"
    env_file:
      - .env
    restart: unless-stopped
```

## ⚠️ Important Notes

### PC Power Settings

**For PC to stay running when locked:**

1. **macOS:**
   ```bash
   # Prevent sleep
   caffeinate -d

   # Or: System Settings → Battery → Prevent from sleeping
   ```

2. **Windows:**
   - Settings → System → Power & Sleep
   - Set "When plugged in, PC goes to sleep after" → **Never**

3. **Linux:**
   ```bash
   # Disable sleep
   sudo systemctl mask sleep.target
   ```

### Container Lifecycle

```
docker run → Container RUNNING → You lock PC ✅ → Container still RUNNING
                ↓
         You close terminal ✅ → Container still RUNNING
                ↓
         PC goes to sleep ❌ → Container STOPPED
                ↓
         PC shuts down ❌ → Container STOPPED
```

### Resource Limits

By default, Docker uses up to 50% CPU and 2GB RAM. For heavy tests, increase:

```bash
# Docker Desktop → Settings → Resources
# Increase CPUs and Memory
```

## 🎓 Examples

### Example 1: Overnight Soak Test

```bash
# Friday evening - Start 8-hour test
./run_locust_docker.sh start --headless -u 200 -r 20 -d 8h

# Lock Mac and go home 🏠
# Ensure "Prevent sleep when display is off" is enabled

# Monday morning - Check results
./run_locust_docker.sh status  # Should be stopped (8h complete)
./run_locust_docker.sh logs    # View full test logs
```

### Example 2: Lunch Break Test

```bash
# Start quick test
./run_locust_docker.sh start --headless -u 50 -r 10 -d 30m

# Lock PC, go to lunch 🍕
# Come back 30 min later

# Test automatically stopped
./run_locust_docker.sh logs  # View results
```

### Example 3: Multi-Day Test

```bash
# Start indefinite test
./run_locust_docker.sh start --headless -u 100 -r 10

# Run for days, checking periodically
./run_locust_docker.sh status  # Is it still running?
./run_locust_docker.sh logs    # Check progress

# Stop when ready
./run_locust_docker.sh stop
```

## 🔗 Quick Reference

| Command | Purpose |
|---------|---------|
| `./run_locust_docker.sh build` | Build Docker image |
| `./run_locust_docker.sh start` | Start with Web UI |
| `./run_locust_docker.sh start --headless -u 100 -r 10` | Automated test |
| `./run_locust_docker.sh status` | Check if running |
| `./run_locust_docker.sh logs` | View logs (live) |
| `./run_locust_docker.sh stop` | Stop test |
| `docker ps` | See running containers |
| `docker logs locust-load-test` | View logs |

## 📚 Related Documentation

- [Locust Documentation](https://docs.locust.io/)
- [Docker Documentation](https://docs.docker.com/)
- [QUICKSTART.md](./QUICKSTART.md) - Local venv setup
- [PROMETHEUS_GRAFANA_SETUP.md](./PROMETHEUS_GRAFANA_SETUP.md) - Monitoring setup

---

**Pro Tip:** Bookmark http://localhost:8089 for quick access to Locust UI! 🚀
