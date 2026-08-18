# Quick Start Guide

## 1. Activate Virtual Environment

```bash
# Navigate to project
cd /path/to/locust-perf-suite

# Activate virtual environment
source venv/bin/activate

# You should see (venv) in your terminal prompt
```

## 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

## 4. Run Sample HTTP Test

```bash
# Run with Locust web UI
locust -f tests/SampleService/sample_http_load.py \
    --host http://localhost:8080

# Open browser to http://localhost:8089
# Configure users and spawn rate
# Start test
```

## 5. Run Headless Test

```bash
locust -f tests/SampleService/sample_http_load.py \
    --host http://localhost:8080 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 1m \
    --headless \
    --csv reports/test_results \
    --html reports/test_results.html
```

## 6. View Results

```bash
# Open HTML report
open reports/test_results.html

# Or view CSV files
cat reports/test_results_stats.csv
```

## 7. Create Your First Test

```bash
# Create new test directory
mkdir -p tests/MyService

# Copy sample as template
cp tests/SampleService/sample_http_load.py tests/MyService/my_load_test.py

# Edit the test file
nano tests/MyService/my_load_test.py

# Run your test
locust -f tests/MyService/my_load_test.py --host http://your-api.com
```

## 8. Working with gRPC

```bash
# Place your .proto files in proto/ directory (create it first)
mkdir proto

# Generate Python code from proto files
python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./proto_generated \
    --grpc_python_out=./proto_generated \
    ./proto/your_service.proto

# Update tests/SampleService/sample_grpc_load.py with your service
# Then run
locust -f tests/SampleService/sample_grpc_load.py --host grpc://localhost:50051
```

## Common Commands

```bash
# Deactivate virtual environment
deactivate

# Update dependencies
pip freeze > requirements.txt

# Run with custom SLA thresholds
locust -f tests/SampleService/sample_http_load.py \
    --host http://localhost:8080 \
    --check-p99-response-time 800 \
    --check-p95-response-time 400 \
    --max-fail-ratio 0.005

# Distributed load testing (master)
locust -f tests/SampleService/sample_http_load.py \
    --master \
    --expect-workers 4

# Distributed load testing (worker)
locust -f tests/SampleService/sample_http_load.py \
    --worker \
    --master-host 127.0.0.1
```

## Project Structure Overview

```
load-test-framework/
├── LocustHelpers/          # Command line parser, custom helpers
├── util/                   # Data loaders, gRPC helpers
├── proto_generated/        # Generated protobuf files
├── tests/                  # Your load test scenarios
│   ├── SampleService/      # Example tests
│   ├── Accounts/           # Add your tests here
│   └── Payments/           # Organize by service
├── config/                 # Configuration files
├── data/                   # Test data (CSV, JSON)
├── reports/                # Test results
├── venv/                   # Virtual environment
├── requirements.txt        # Dependencies
├── .env.example           # Environment template
└── README.md              # Full documentation
```

## Troubleshooting

### Virtual environment not activating
```bash
# Recreate it
rm -rf venv
python3 -m venv venv
source venv/bin/activate
```

### Module not found errors
```bash
# Ensure you're in venv
which python  # Should show path in venv directory

# Reinstall dependencies
pip install -r requirements.txt
```

### Permission denied on venv/bin/activate
```bash
chmod +x venv/bin/activate
```

## Next Steps

1. Read the full README.md for detailed documentation
2. Customize tests/SampleService templates for your use case
3. Add your test data to data/ directory
4. Configure .env with your endpoints
5. Start testing!
