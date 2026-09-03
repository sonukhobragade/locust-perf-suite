# Locust load-test suite
.PHONY: help install lint format type-check verify test headless web docker monitoring clean

.DEFAULT_GOAL := help

# Every recipe runs in its own shell, so activating a venv in one target does
# not carry to the next. Resolve the interpreter once and call tools through it,
# so `make install && make headless` uses what install just put in venv/.
VENV       ?= venv
PY         := $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)

# Override on the command line: make headless LOCUSTFILE=tests/Payments/payments_load.py
LOCUSTFILE ?= tests/SampleService/sample_http_load.py
HOST       ?= http://localhost:8000
USERS      ?= 10
SPAWN_RATE ?= 2
RUN_TIME   ?= 1m

help: ## Show this help message
	@echo "Locust load-test suite"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36mmake %-14s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables: LOCUSTFILE HOST USERS SPAWN_RATE RUN_TIME VENV"

install: ## Create a venv and install dependencies
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/pip install -r requirements-dev.txt

verify: ## Check dependencies are present and every locustfile still resolves
	$(PY) verify_imports.py

web: ## Start Locust with the web UI
	$(PY) -m locust -f $(LOCUSTFILE) --host $(HOST)

headless: ## Run a load test headless and write results CSVs
	$(PY) -m locust -f $(LOCUSTFILE) --host $(HOST) --headless \
		--users $(USERS) --spawn-rate $(SPAWN_RATE) --run-time $(RUN_TIME) \
		--csv reports/results

docker: ## Build the image and start the suite in Docker
	./run_locust_docker.sh build
	./run_locust_docker.sh start

monitoring: ## Bring up Prometheus and Grafana
	docker compose -f docker-compose.monitoring.yml up -d

deps: ## Check requirements.txt against what the source imports
	$(PY) tools/check_deps.py

imports: ## Import every module the suite needs, using requirements.txt alone
	$(PY) tools/check_runtime_imports.py

test: deps ## Run the unit tests
	$(PY) -m pytest tests/unit -q

lint: ## Run ruff linting
	$(PY) -m ruff check tests/ util/ tools/ LocustHelpers/

format: ## Format with ruff
	$(PY) -m ruff format tests/ util/ tools/ LocustHelpers/

type-check: ## Run pyright
	$(PY) -m pyright

clean: ## Remove caches and generated results
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
	rm -f reports/*_stats.csv reports/*_failures.csv reports/*_stats_history.csv \
	      reports/*_exceptions.csv
