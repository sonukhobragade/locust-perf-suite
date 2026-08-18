# JWT Authentication Load Test

## Overview
Load test for the  JWT token creation endpoint. This test simulates multiple users requesting JWT tokens with different user credentials.

## Endpoint Details
- **URL**: `POST https://qa-api.example.com/auth/token`
- **Method**: POST
- **Required Headers**:
  - `userId`: User ID (string)
  - `phoneNumber`: Phone number (string)

## Test Configuration

### Environment Variables
Configure these in `.env` file:
```bash
TARGET_HOST=https://qa-api.example.com
LOCUST_USERS=100
LOCUST_SPAWN_RATE=10
LOCUST_RUN_TIME=5m
```

### Test Users
The test uses predefined test user credentials:
- User IDs: 662, 663, 664, 665, 666
- Phone Numbers: 5550000001, 5550000001, 5550000001, 5550000002, 5550000002

## Running the Test

### Basic Run
```bash
# Run with default configuration
locust -f tests/AuthService/jwt_auth_load.py

# Access Web UI at http://localhost:8089
```

### Command Line Mode (Headless)
```bash
# Run with 100 users, spawn rate of 10 users/sec, for 5 minutes
locust -f tests/AuthService/jwt_auth_load.py \
    --headless \
    --users 100 \
    --spawn-rate 10 \
    --run-time 5m \
    --host https://qa-api.example.com
```

### With Custom Configuration
```bash
# Using environment variables
export TARGET_HOST=https://qa-api.example.com
export LOCUST_USERS=50
export LOCUST_SPAWN_RATE=5
export LOCUST_RUN_TIME=2m

locust -f tests/AuthService/jwt_auth_load.py --headless
```

### Using Makefile (if available)
```bash
# Run the JWT auth test
make test-jwt-auth
```

## Test Scenarios

### Scenario 1: Standard JWT Creation (Weight: 5)
- Creates JWT token with fixed user credentials
- Validates response contains token
- Expected Status: 200 or 201

### Scenario 2: JWT Creation with User Rotation (Weight: 1)
- Rotates through different test user credentials
- Simulates multiple users requesting tokens
- Expected Status: 200 or 201

## Success Criteria

### Response Validation
- ✅ Status code: 200 or 201
- ✅ Response body contains JWT token field
- ✅ Response time < 1000ms (P99)
- ✅ Response time < 500ms (P95)

### SLA Thresholds
```bash
LOCUST_P99=1000    # 99th percentile < 1000ms
LOCUST_P95=500     # 95th percentile < 500ms
LOCUST_MAX_FAIL_RATIO=0.01  # Max 1% failure rate
```

## Expected Response Format

### Success Response (200/201)
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "userId": "662",
  "expiresIn": 3600
}
```

### Error Response (4xx/5xx)
```json
{
  "error": "Invalid credentials",
  "message": "User not found or phone number mismatch"
}
```

## Performance Metrics

Monitor these key metrics:
- **Requests per second (RPS)**
- **Response time percentiles** (P50, P95, P99)
- **Failure rate**
- **Concurrent users**

## Troubleshooting

### Common Issues

#### 1. Connection Refused
```bash
# Check if target host is accessible
curl -X POST https://qa-api.example.com/auth/token \
  -H "userId: 662" \
  -H "phoneNumber: 5550000001"
```

#### 2. Authentication Failures
- Verify test user credentials are valid
- Check if users exist in the system
- Verify phone numbers match user IDs

#### 3. Rate Limiting
- Reduce spawn rate if hitting rate limits
- Add wait time between requests
- Configure appropriate wait_time in test

## Customization

### Adding More Test Users
Edit `jwt_auth_load.py`:
```python
self.test_user_ids = [662, 663, 664, 665, 666, 667, 668]  # Add more IDs
self.test_phone_numbers = [
    "5550000001",
    "5550000001",
    # Add corresponding phone numbers
]
```

### Adjusting Task Weights
```python
@task(10)  # Increase weight for more frequent execution
def create_jwt_token(self):
    # ...
```

### Custom Headers
```python
headers = {
    "userId": str(user_id),
    "phoneNumber": phone_number,
    "Content-Type": "application/json",
    "Authorization": "Bearer <token>",  # Add if needed
}
```

## Reports

Test results are saved to:
- HTML Report: `reports/jwt_auth_<timestamp>.html`
- CSV Stats: `reports/jwt_auth_stats.csv`
- Exceptions: `reports/jwt_auth_exceptions.csv`

## Integration with CI/CD

```yaml
# Example GitHub Actions
- name: Run JWT Auth Load Test
  run: |
    source venv/bin/activate
    locust -f tests/AuthService/jwt_auth_load.py \
      --headless \
      --users 50 \
      --spawn-rate 5 \
      --run-time 2m \
      --html reports/jwt_auth_report.html
```

## Related Tests
- `tests/SampleService/sample_http_load.py` - Sample HTTP load test
- `tests/SampleService/sample_grpc_load.py` - Sample gRPC load test

## Resources
- [Locust Documentation](https://docs.locust.io/)
- [Project README](../../README.md)
- [Locust Best Practices](../../APP_RULES.md)
