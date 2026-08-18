#!/bin/bash
# Locust Docker Runner - Runs independently of your desktop session
# Your PC can be locked and Locust will continue running

set -e  # Exit on error

CONTAINER_NAME="locust-load-test"
IMAGE_NAME="locust-perf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_FILE="tests/SampleService/sample_http_load.py"
USERS=8
SPAWN_RATE=2
RUN_TIME=""

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

print_success() {
    echo -e "${GREEN}✓${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC}  $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

# Function to display usage
usage() {
    cat << EOF
${GREEN}Locust Docker Runner${NC}

Usage: $0 [COMMAND] [OPTIONS]

${BLUE}Commands:${NC}
  build       Build the Docker image
  start       Start Locust container (runs in background)
  stop        Stop the running container
  restart     Restart the container
  logs        View container logs
  status      Check container status
  shell       Open bash shell in container
  clean       Remove container and image

${BLUE}Start Options:${NC}
  -t, --test FILE       Test file to run (default: $TEST_FILE)
  -u, --users NUM       Number of users (default: $USERS)
  -r, --rate NUM        Spawn rate (default: $SPAWN_RATE)
  -d, --duration TIME   Run time (e.g., 10m, 1h, default: infinite)
  --headless            Run without Web UI (automated mode)

${BLUE}Examples:${NC}
  # Build image
  $0 build

  # Start with Web UI (default)
  $0 start

  # Start with custom settings
  $0 start -u 50 -r 5 -d 30m

  # Run headless (automated)
  $0 start --headless -u 100 -r 10 -d 1h

  # View logs (follow mode)
  $0 logs

  # Check status
  $0 status

  # Stop container
  $0 stop

${BLUE}Access Points (when running):${NC}
  • Locust Web UI:        http://localhost:8089
  • Prometheus Metrics:   http://localhost:9090/metrics
  • Custom Stats:         http://localhost:8089/stats/custom

${BLUE}Important Notes:${NC}
  ✓ Container runs independently - you can lock your PC
  ✓ Container persists until you explicitly stop it
  ✓ Use 'docker ps' to see if it's running
  ✓ Use '$0 logs' to monitor progress

EOF
    exit 0
}

# Build Docker image
build_image() {
    print_info "Building Docker image: $IMAGE_NAME"

    if ! docker build -f Dockerfile.locust -t $IMAGE_NAME .; then
        print_error "Failed to build Docker image"
        exit 1
    fi

    print_success "Docker image built successfully: $IMAGE_NAME"
}

# Start Locust container
start_container() {
    # Check if container is already running
    if docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_warning "Container '$CONTAINER_NAME' is already running"
        print_info "Run '$0 logs' to view logs or '$0 restart' to restart"
        exit 1
    fi

    # Check if container exists but is stopped
    if docker ps -a --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Removing stopped container '$CONTAINER_NAME'"
        docker rm $CONTAINER_NAME > /dev/null 2>&1
    fi

    # Build command
    LOCUST_CMD="locust -f $TEST_FILE --web-host=0.0.0.0 --web-port=8089"

    # Add options
    if [ -n "$HEADLESS" ]; then
        LOCUST_CMD="$LOCUST_CMD --headless --users=$USERS --spawn-rate=$SPAWN_RATE"
        if [ -n "$RUN_TIME" ]; then
            LOCUST_CMD="$LOCUST_CMD --run-time=$RUN_TIME"
        fi
    fi

    print_info "Starting Locust container: $CONTAINER_NAME"

    # Start container
    docker run -d \
        --name $CONTAINER_NAME \
        --env-file .env \
        -p 8089:8089 \
        -p 9090:9090 \
        -p 5557:5557 \
        --restart unless-stopped \
        $IMAGE_NAME \
        sh -c "$LOCUST_CMD"

    # Wait a moment for container to start
    sleep 2

    # Check if container is running
    if docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_success "Container started successfully!"
        echo
        print_info "Container is running in the background"
        print_info "You can now lock your PC - Docker will keep running"
        echo
        echo -e "${GREEN}Access Points:${NC}"
        echo "  • Locust Web UI:        http://localhost:8089"
        echo "  • Prometheus Metrics:   http://localhost:9090/metrics"
        echo "  • Custom Stats:         http://localhost:8089/stats/custom"
        echo
        echo -e "${BLUE}Monitoring:${NC}"
        echo "  • View logs:   $0 logs"
        echo "  • Check status: $0 status"
        echo "  • Stop test:    $0 stop"
    else
        print_error "Container failed to start. Check logs with: docker logs $CONTAINER_NAME"
        exit 1
    fi
}

# Stop container
stop_container() {
    if ! docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_warning "Container '$CONTAINER_NAME' is not running"
        exit 0
    fi

    print_info "Stopping container: $CONTAINER_NAME"
    docker stop $CONTAINER_NAME > /dev/null
    print_success "Container stopped"
}

# View logs
view_logs() {
    if ! docker ps -a --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_error "Container '$CONTAINER_NAME' does not exist"
        exit 1
    fi

    print_info "Viewing logs for: $CONTAINER_NAME (Ctrl+C to exit)"
    docker logs -f --tail 100 $CONTAINER_NAME
}

# Check status
check_status() {
    if docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_success "Container '$CONTAINER_NAME' is RUNNING"
        echo
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo
        print_info "Access Locust UI at: http://localhost:8089"
    elif docker ps -a --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_warning "Container '$CONTAINER_NAME' exists but is STOPPED"
        echo
        docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}"
    else
        print_error "Container '$CONTAINER_NAME' does not exist"
        print_info "Run '$0 start' to create and start the container"
    fi
}

# Restart container
restart_container() {
    stop_container
    sleep 2
    start_container
}

# Open shell in container
open_shell() {
    if ! docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_error "Container '$CONTAINER_NAME' is not running"
        exit 1
    fi

    print_info "Opening shell in container: $CONTAINER_NAME"
    docker exec -it $CONTAINER_NAME /bin/bash
}

# Clean up
clean_up() {
    print_warning "This will remove the container and image"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cancelled"
        exit 0
    fi

    if docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Stopping container"
        docker stop $CONTAINER_NAME > /dev/null
    fi

    if docker ps -a --filter "name=$CONTAINER_NAME" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Removing container"
        docker rm $CONTAINER_NAME > /dev/null
    fi

    if docker images --format "{{.Repository}}" | grep -q "^${IMAGE_NAME}$"; then
        print_info "Removing image"
        docker rmi $IMAGE_NAME > /dev/null
    fi

    print_success "Cleanup complete"
}

# Parse arguments
COMMAND=""
HEADLESS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        build|start|stop|restart|logs|status|shell|clean)
            COMMAND=$1
            shift
            ;;
        -t|--test)
            TEST_FILE="$2"
            shift 2
            ;;
        -u|--users)
            USERS="$2"
            shift 2
            ;;
        -r|--rate)
            SPAWN_RATE="$2"
            shift 2
            ;;
        -d|--duration)
            RUN_TIME="$2"
            shift 2
            ;;
        --headless)
            HEADLESS="yes"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Run '$0 --help' for usage"
            exit 1
            ;;
    esac
done

# Execute command
case $COMMAND in
    build)
        build_image
        ;;
    start)
        start_container
        ;;
    stop)
        stop_container
        ;;
    restart)
        restart_container
        ;;
    logs)
        view_logs
        ;;
    status)
        check_status
        ;;
    shell)
        open_shell
        ;;
    clean)
        clean_up
        ;;
    *)
        usage
        ;;
esac
