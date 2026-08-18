#!/bin/bash

# =============================================================================
# Grafana Dashboard Manager
# =============================================================================
# Utility script to manually manage Grafana dashboards
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GRAFANA_URL="http://localhost:3000"
# No defaults: admin/admin here pushes dashboards to a Grafana anyone can
# log into. Must match docker-compose.monitoring.yml.
GRAFANA_USER="${GRAFANA_ADMIN_USER:?set GRAFANA_ADMIN_USER (see .env.example)}"
GRAFANA_PASS="${GRAFANA_ADMIN_PASSWORD:?set GRAFANA_ADMIN_PASSWORD (see .env.example)}"
DASHBOARD_JSON="$PROJECT_ROOT/config/grafana/dashboards/locust-load-test.json"

# Helper functions
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_header() {
    echo ""
    echo -e "${BLUE}=========================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=========================================================================${NC}"
    echo ""
}

# Check if Grafana is running
check_grafana() {
    if ! curl -s -f "$GRAFANA_URL/api/health" > /dev/null 2>&1; then
        print_error "Grafana is not running at $GRAFANA_URL"
        print_info "Start it with: docker-compose -f docker-compose.monitoring.yml up -d"
        exit 1
    fi
    print_success "Grafana is running"
}

# List all dashboards
list_dashboards() {
    print_header "📊 Listing Grafana Dashboards"

    check_grafana

    local response=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
        "$GRAFANA_URL/api/search?type=dash-db")

    if [ -z "$response" ] || [ "$response" == "[]" ]; then
        print_warning "No dashboards found in Grafana"
        return
    fi

    echo "$response" | jq -r '.[] | "  • \(.title) (ID: \(.id), UID: \(.uid))"'
}

# Verify dashboard provisioning
verify_provisioning() {
    print_header "🔍 Verifying Dashboard Provisioning"

    check_grafana

    # Check if dashboard files exist in container
    print_info "Checking dashboard files in Grafana container..."

    if docker exec grafana ls /etc/grafana/provisioning/dashboards/*.json > /dev/null 2>&1; then
        print_success "Dashboard files found in provisioning directory"
        docker exec grafana ls -lh /etc/grafana/provisioning/dashboards/*.json
    else
        print_error "Dashboard files not found in provisioning directory"
        print_info "Check volume mounts in docker-compose.monitoring.yml"
        return 1
    fi

    # Check if dashboard appears in Grafana
    print_info "Checking if dashboard is loaded in Grafana..."

    local response=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
        "$GRAFANA_URL/api/search?type=dash-db")

    if echo "$response" | grep -q "Locust Load Test"; then
        print_success "Dashboard 'Locust Load Test' is loaded!"

        # Get dashboard details
        local uid=$(echo "$response" | jq -r '.[] | select(.title | contains("Locust Load Test")) | .uid')
        print_info "Dashboard UID: $uid"
        print_info "Access at: $GRAFANA_URL/d/$uid"
    else
        print_warning "Dashboard not found in Grafana"
        print_info "It may take a few moments for provisioning to complete"
    fi
}

# Force reload provisioning
force_reload() {
    print_header "🔄 Force Reloading Dashboard Provisioning"

    check_grafana

    print_info "Restarting Grafana to reload provisioning..."

    docker restart grafana

    print_info "Waiting for Grafana to be ready..."
    local attempts=0
    local max_attempts=30

    while [ $attempts -lt $max_attempts ]; do
        if curl -s -f "$GRAFANA_URL/api/health" > /dev/null 2>&1; then
            print_success "Grafana is ready!"
            sleep 5  # Give provisioning time to complete
            verify_provisioning
            return 0
        fi
        echo -n "."
        sleep 1
        attempts=$((attempts + 1))
    done

    echo ""
    print_error "Grafana failed to restart within ${max_attempts} seconds"
    return 1
}

# Import dashboard via API (alternative method)
import_via_api() {
    print_header "📥 Importing Dashboard via API"

    check_grafana

    if [ ! -f "$DASHBOARD_JSON" ]; then
        print_error "Dashboard JSON not found at: $DASHBOARD_JSON"
        return 1
    fi

    print_info "Reading dashboard JSON..."

    # Read dashboard JSON and prepare for import
    local dashboard_content=$(cat "$DASHBOARD_JSON" | jq '{dashboard: ., overwrite: true, folderId: 0}')

    print_info "Importing dashboard via Grafana API..."

    local response=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
        -H "Content-Type: application/json" \
        -X POST \
        -d "$dashboard_content" \
        "$GRAFANA_URL/api/dashboards/db")

    if echo "$response" | grep -q '"status":"success"'; then
        print_success "Dashboard imported successfully!"
        local uid=$(echo "$response" | jq -r '.uid')
        print_info "Dashboard UID: $uid"
        print_info "Access at: $GRAFANA_URL/d/$uid"
    else
        print_error "Failed to import dashboard"
        echo "$response" | jq '.'
        return 1
    fi
}

# Export dashboard
export_dashboard() {
    print_header "📤 Exporting Dashboard"

    check_grafana

    local uid=$1
    if [ -z "$uid" ]; then
        print_error "Please provide dashboard UID"
        print_info "Usage: $0 export <uid>"
        print_info "List dashboards to get UIDs: $0 list"
        return 1
    fi

    print_info "Exporting dashboard with UID: $uid"

    local response=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
        "$GRAFANA_URL/api/dashboards/uid/$uid")

    if echo "$response" | grep -q '"dashboard"'; then
        local output_file="$PROJECT_ROOT/dashboard-export-$(date +%Y%m%d-%H%M%S).json"
        echo "$response" | jq '.dashboard' > "$output_file"
        print_success "Dashboard exported to: $output_file"
    else
        print_error "Failed to export dashboard"
        echo "$response" | jq '.'
        return 1
    fi
}

# Check dashboard status
status() {
    print_header "📊 Dashboard Status"

    check_grafana
    verify_provisioning
    echo ""
    list_dashboards
}

# Show help
show_help() {
    cat << EOF

${BLUE}Grafana Dashboard Manager${NC}

${GREEN}Usage:${NC}
  $0 <command> [options]

${GREEN}Commands:${NC}
  ${YELLOW}list${NC}          List all dashboards in Grafana
  ${YELLOW}verify${NC}        Verify dashboard provisioning is working
  ${YELLOW}reload${NC}        Force reload provisioning by restarting Grafana
  ${YELLOW}import${NC}        Import dashboard via API (alternative method)
  ${YELLOW}export${NC} <uid>  Export dashboard by UID to JSON file
  ${YELLOW}status${NC}        Show complete dashboard status
  ${YELLOW}help${NC}          Show this help message

${GREEN}Examples:${NC}
  $0 list                    # List all dashboards
  $0 verify                  # Check if provisioning works
  $0 reload                  # Force reload dashboards
  $0 import                  # Import via API
  $0 export abc123           # Export dashboard with UID abc123
  $0 status                  # Show complete status

${GREEN}Troubleshooting:${NC}
  If dashboard is not loading:
    1. Run: $0 verify
    2. Check volume mounts in docker-compose.monitoring.yml
    3. Try: $0 reload
    4. As last resort: $0 import

EOF
}

# Main execution
main() {
    local command=${1:-help}

    case "$command" in
        list)
            list_dashboards
            ;;
        verify)
            verify_provisioning
            ;;
        reload)
            force_reload
            ;;
        import)
            import_via_api
            ;;
        export)
            export_dashboard "$2"
            ;;
        status)
            status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Check dependencies
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed"
    print_info "Install with: brew install jq (macOS) or apt install jq (Linux)"
    exit 1
fi

main "$@"
