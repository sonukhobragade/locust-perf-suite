"""
Command Line Parser for Locust Tests
Adds custom command line arguments and event listeners
"""
import logging
import locust.stats
from locust import events

# Configure CSV stats output
locust.stats.CSV_STATS_INTERVAL_SEC = 5
locust.stats.CSV_STATS_FLUSH_INTERVAL_SEC = 60

# Global variables for runtime configuration
test_host = None
custom_config = {}


@events.init_command_line_parser.add_listener
def _(parser):
    """Add custom command line arguments"""
    parser.add_argument(
        "--check-p99-response-time",
        type=int,
        env_var="LOCUST_P99",
        include_in_web_ui=True,
        default=1000,
        help="P99 response time threshold in ms"
    )
    parser.add_argument(
        "--check-p95-response-time",
        type=int,
        env_var="LOCUST_P95",
        include_in_web_ui=True,
        default=500,
        help="P95 response time threshold in ms"
    )
    parser.add_argument(
        "--max-fail-ratio",
        type=float,
        env_var="LOCUST_MAX_FAIL_RATIO",
        include_in_web_ui=True,
        default=0.01,
        help="Maximum allowed failure ratio (0.01 = 1%)"
    )
    parser.add_argument(
        "--custom-config",
        type=str,
        env_var="LOCUST_CUSTOM_CONFIG",
        include_in_web_ui=False,
        default="",
        help="Custom configuration JSON string"
    )


@events.test_start.add_listener
def _(environment, **kwargs):
    """Test start event handler"""
    opts = environment.parsed_options

    logging.info(f"Test starting with host: {opts.host}")
    logging.info(f"P99 threshold: {opts.check_p99_response_time}ms")
    logging.info(f"P95 threshold: {opts.check_p95_response_time}ms")
    logging.info(f"Max fail ratio: {opts.max_fail_ratio}")

    global test_host, custom_config
    test_host = opts.host
    if opts.custom_config:
        import json
        try:
            custom_config = json.loads(opts.custom_config)
        except json.JSONDecodeError:
            logging.warning("Failed to parse custom config JSON")


@events.test_stop.add_listener
def _(environment, **kwargs):
    """Test stop event handler"""
    logging.info("Test stopped")


@events.quitting.add_listener
def _(environment, **kwargs):
    """Test quitting event handler - validates SLA metrics"""
    opts = environment.parsed_options
    stats = environment.stats.total

    # Check P99 response time
    p99 = stats.get_response_time_percentile(0.99)
    if p99 > opts.check_p99_response_time:
        logging.error(
            f"Test failed: P99 response time ({p99}ms) exceeded threshold "
            f"({opts.check_p99_response_time}ms)"
        )
        environment.process_exit_code = 3
        return

    # Check P95 response time
    p95 = stats.get_response_time_percentile(0.95)
    if p95 > opts.check_p95_response_time:
        logging.error(
            f"Test failed: P95 response time ({p95}ms) exceeded threshold "
            f"({opts.check_p95_response_time}ms)"
        )
        environment.process_exit_code = 3
        return

    # Check failure ratio
    if stats.num_requests > 0:
        fail_ratio = stats.num_failures / stats.num_requests
        if fail_ratio > opts.max_fail_ratio:
            logging.error(
                f"Test failed: Failure ratio ({fail_ratio:.4f}) exceeded threshold "
                f"({opts.max_fail_ratio:.4f})"
            )
            environment.process_exit_code = 3
            return

    logging.info("Test passed all SLA checks")
    environment.process_exit_code = 0
