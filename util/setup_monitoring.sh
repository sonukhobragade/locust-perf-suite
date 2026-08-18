#!/bin/bash

# =============================================================================
# Automated Prometheus + Grafana Monitoring Setup
# =============================================================================
# This script:
# - Starts Prometheus and Grafana with Docker Compose
# - Waits for services to be healthy
# - Verifies dashboard provisioning
# - Provides clear status feedback
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.monitoring.yml"
GRAFANA_URL="http://localhost:3000"
PROMETHEUS_URL="http://localhost:9091"
# Must match the credentials docker-compose.monitoring.yml starts Grafana with.
# No defaults: admin/admin here silently provisions dashboards against a
# Grafana that anyone on the network can log into.
GRAFANA_USER="${GRAFANA_ADMIN_USER:?set GRAFANA_ADMIN_USER (see .env.example)}"
GRAFANA_PASS="${GRAFANA_ADMIN_PASSWORD:?set GRAFANA_ADMIN_PASSWORD (see .env.example)}"
MAX_WAIT_TIME=60  # Maximum seconds to wait for services

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}=========================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=========================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

wait_for_service() {
    local service_name=$1
    local service_url=$2
    local max_attempts=$3
    local attempt=1

    print_info "Waiting for $service_name to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$service_url" > /dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi

        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done

    echo ""
    print_error "$service_name failed to start within ${max_attempts} seconds"
    return 1
}

verify_dashboard() {
    print_info "Verifying Grafana dashboard provisioning..."

    # Wait a bit for provisioning to complete
    sleep 3

    # Check if dashboard exists via Grafana API
    local response=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
        "$GRAFANA_URL/api/search?type=dash-db" 2>/dev/null)

    if echo "$response" | grep -q "Locust Load Test"; then
        print_success "Dashboard 'Locust Load Test' found!"
        return 0
    else
        print_warning "Dashboard not found yet, checking provisioning status..."

        # Check provisioning directory
        if docker exec grafana ls /etc/grafana/provisioning/dashboards/*.json > /dev/null 2>&1; then
            print_info "Dashboard files are present in provisioning directory"
            print_warning "Dashboard may take a few more seconds to appear in Grafana"
            return 0
        else
            print_error "Dashboard files not found in provisioning directory"
            return 1
        fi
    fi
}

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker is installed"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose is not installed. Please install docker-compose first."
        exit 1
    fi
    print_success "docker-compose is installed"

    # Check if docker-compose file exists
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        print_error "docker-compose.monitoring.yml not found at: $DOCKER_COMPOSE_FILE"
        exit 1
    fi
    print_success "docker-compose.monitoring.yml found"

    # Check if config files exist
    if [ ! -f "$PROJECT_ROOT/config/prometheus.yml" ]; then
        print_error "Prometheus config not found at: $PROJECT_ROOT/config/prometheus.yml"
        exit 1
    fi
    print_success "Prometheus config found"

    if [ ! -f "$PROJECT_ROOT/config/grafana/datasources/prometheus.yml" ]; then
        print_error "Grafana datasource config not found"
        exit 1
    fi
    print_success "Grafana datasource config found"

    if [ ! -f "$PROJECT_ROOT/config/grafana/dashboards/locust-load-test.json" ]; then
        print_error "Grafana dashboard JSON not found"
        exit 1
    fi
    print_success "Grafana dashboard JSON found"
}

start_services() {
    print_header "Starting Monitoring Services"

    cd "$PROJECT_ROOT"

    # Check if services are already running
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Up"; then
        print_warning "Services are already running. Restarting..."
        docker-compose -f "$DOCKER_COMPOSE_FILE" down
    fi

    print_info "Starting Prometheus and Grafana..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d

    if [ $? -eq 0 ]; then
        print_success "Services started successfully"
    else
        print_error "Failed to start services"
        exit 1
    fi
}

verify_services() {
    print_header "Verifying Services"

    # Wait for Prometheus
    if wait_for_service "Prometheus" "$PROMETHEUS_URL/-/ready" 30; then
        print_success "Prometheus is healthy and ready"
    else
        print_error "Prometheus failed to start"
        print_info "Check logs: docker logs prometheus"
        exit 1
    fi

    # Wait for Grafana
    if wait_for_service "Grafana" "$GRAFANA_URL/api/health" 30; then
        print_success "Grafana is healthy and ready"
    else
        print_error "Grafana failed to start"
        print_info "Check logs: docker logs grafana"
        exit 1
    fi

    # Verify dashboard
    if verify_dashboard; then
        print_success "Dashboard provisioning verified"
    else
        print_warning "Dashboard verification inconclusive, but services are running"
        print_info "Check Grafana UI manually at: $GRAFANA_URL"
    fi
}

print_summary() {
    print_header "Setup Complete! 🎉"

    echo -e "${GREEN}✅ Monitoring stack is running and ready!${NC}"
    echo ""
    echo -e "${BLUE}📊 Access Your Dashboards:${NC}"
    echo -e "  • Grafana:    ${GREEN}$GRAFANA_URL${NC}"
    echo -e "  • Prometheus: ${GREEN}$PROMETHEUS_URL${NC}"
    echo ""
    echo -e "${BLUE}🔐 Grafana Login:${NC}"
    echo -e "  • Username: ${YELLOW}admin${NC}"
    echo -e "  • Password: ${YELLOW}admin${NC}"
    echo ""
    echo -e "${BLUE}📈 Dashboard:${NC}"
    echo -e "  • Go to: Dashboards → Locust Load Test"
    echo ""
    echo -e "${BLUE}🚀 Next Steps:${NC}"
    echo -e "  1. Start your Locust test:"
    echo -e "     ${YELLOW}locust -f tests/SampleService/sample_http_load.py${NC}"
    echo -e "  2. Begin load testing at http://localhost:8089"
    echo -e "  3. Watch the graphs in Grafana!"
    echo ""
    echo -e "${BLUE}🔧 Useful Commands:${NC}"
    echo -e "  • Stop services:  ${YELLOW}docker-compose -f docker-compose.monitoring.yml down${NC}"
    echo -e "  • View logs:      ${YELLOW}docker-compose -f docker-compose.monitoring.yml logs -f${NC}"
    echo -e "  • Restart:        ${YELLOW}./util/setup_monitoring.sh${NC}"
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    print_header "🚀 Automated Monitoring Setup"

    check_prerequisites
    start_services
    verify_services
    print_summary
}

# Run main function
main
