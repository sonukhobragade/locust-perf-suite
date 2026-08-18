# Quick Start - JWT Authentication Load Test

## Prerequisites
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt
```

## Run the Test

### Option 1: Web UI Mode (Recommended for First Run)
```bash
locust -f tests/AuthService/jwt_auth_load.py
```
Then open http://localhost:8089 in your browser and configure:
- Number of users: 100
- Spawn rate: 10
- Host: https://qa-api.example.com

### Option 2: Headless Mode (Command Line)
```bash
locust -f tests/AuthService/jwt_auth_load.py \
    --headless \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --host https://qa-api.example.com
```

### Option 3: Quick Test (10 users, 1 minute)
```bash
locust -f tests/AuthService/jwt_auth_load.py \
    --headless \
    --users 10 \
    --spawn-rate 2 \
    --run-time 1m \
    --host https://qa-api.example.com
```

## Test the Endpoint Manually First
```bash
curl -X POST 'https://qa-api.example.com/auth/token' \
  -H 'userId: 662' \
  -H 'phoneNumber: 5550000001' \
  -v
```

## View Results
- Live stats available at: http://localhost:8089 (Web UI mode)
- CSV reports: `reports/` directory
- HTML report: Generated with `--html` flag

## Troubleshooting

### Test won't start
```bash
# Check if locust is installed
locust --version

# Check if dependencies are installed
pip list | grep locust
```

### Connection errors
```bash
# Verify endpoint is accessible
curl -I https://qa-api.example.com/auth/token
```

### Module import errors
```bash
# Ensure you're in the project root
cd /path/to/projects/locust-perf

# Ensure virtual environment is activated
source venv/bin/activate
```

## Expected Output
```
[2025-11-04 17:00:00,000] INFO/locust.main: Starting web interface at http://0.0.0.0:8089
[2025-11-04 17:00:00,001] INFO/locust.main: Starting Locust 2.31.8
============================================================
JWT Authentication Load Test Starting
Target Host: https://qa-api.example.com
Test Users: Dynamic
============================================================
```

## Stop the Test
- Web UI: Click "Stop" button
- Headless: Ctrl+C (will generate report)

## Next Steps
1. Analyze performance metrics (response times, failure rate)
2. Adjust load parameters based on results
3. Customize test users in `jwt_auth_load.py`
4. Integrate with CI/CD pipeline

For detailed documentation, see [README.md](./README.md)
