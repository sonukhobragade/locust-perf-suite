#!/bin/bash
# Quick runner script for JWT Authentication Load Test

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}JWT Authentication Load Test Runner${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
    echo -e "Attempting to activate venv..."
    if [ -f "../../venv/bin/activate" ]; then
        source ../../venv/bin/activate
        echo -e "${GREEN}✅ Virtual environment activated${NC}"
    else
        echo -e "${YELLOW}⚠️  Run this from project root or activate venv manually${NC}"
        exit 1
    fi
fi

# Load environment variables
if [ -f "../../.env" ]; then
    export $(cat ../../.env | grep -v '^#' | xargs)
    echo -e "${GREEN}✅ Environment variables loaded${NC}"
else
    echo -e "${YELLOW}⚠️  .env file not found, using defaults${NC}"
fi

# Parse command line arguments
MODE=${1:-web}
USERS=${LOCUST_USERS:-100}
SPAWN_RATE=${LOCUST_SPAWN_RATE:-10}
RUN_TIME=${LOCUST_RUN_TIME:-5m}
HOST=${TARGET_HOST:-https://qa-api.example.com}

echo ""
echo -e "${BLUE}Test Configuration:${NC}"
echo "  Mode: $MODE"
echo "  Users: $USERS"
echo "  Spawn Rate: $SPAWN_RATE/sec"
echo "  Duration: $RUN_TIME"
echo "  Target: $HOST"
echo ""

# Test endpoint connectivity
echo -e "${BLUE}Testing endpoint connectivity...${NC}"
if curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "userId: 662" \
    -H "phoneNumber: 5550000001" \
    "$HOST/auth/token" | grep -q "200\|201\|401\|403"; then
    echo -e "${GREEN}✅ Endpoint is reachable${NC}"
else
    echo -e "${YELLOW}⚠️  Endpoint may be unreachable${NC}"
fi

echo ""
echo -e "${BLUE}Starting load test...${NC}"
echo ""

# Run based on mode
case $MODE in
    web)
        echo -e "${GREEN}Opening Web UI at http://localhost:8089${NC}"
        locust -f jwt_auth_load.py --host="$HOST"
        ;;
    headless)
        echo -e "${GREEN}Running in headless mode${NC}"
        locust -f jwt_auth_load.py \
            --headless \
            --users "$USERS" \
            --spawn-rate "$SPAWN_RATE" \
            --run-time "$RUN_TIME" \
            --host="$HOST" \
            --html ../../reports/jwt_auth_$(date +%Y%m%d_%H%M%S).html \
            --csv ../../reports/jwt_auth_$(date +%Y%m%d_%H%M%S)
        ;;
    quick)
        echo -e "${GREEN}Running quick test (10 users, 1 minute)${NC}"
        locust -f jwt_auth_load.py \
            --headless \
            --users 10 \
            --spawn-rate 2 \
            --run-time 1m \
            --host="$HOST"
        ;;
    *)
        echo -e "${YELLOW}Usage: $0 [web|headless|quick]${NC}"
        echo "  web      - Start with Web UI (default)"
        echo "  headless - Run in headless mode"
        echo "  quick    - Quick test (10 users, 1 min)"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Test Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
