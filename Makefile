# ---------------------------------------------------------------------------
# robo_assess — developer convenience targets
# ---------------------------------------------------------------------------
PY ?= python

.PHONY: help install dev datasets examples generate test eval calibrate docker-build docker-run clean

help:
	@echo "Targets:"
	@echo "  install      Install runtime dependencies"
	@echo "  dev          Install dev dependencies (+pytest)"
	@echo "  datasets     Generate the 12 evaluation datasets"
	@echo "  examples     Build the 3 example assessment packages"
	@echo "  generate     Run a sample offline assessment generation"
	@echo "  test         Run the pytest suite"
	@echo "  eval         Run the benchmark suite + enforce regression gates (CI)"
	@echo "  calibrate    Refit the confidence calibrator from grading outcomes"
	@echo "  docker-build Build the Docker image"
	@echo "  docker-run   Generate inside the container"
	@echo "  clean        Remove caches and generated runtime artefacts"

install:
	$(PY) -m pip install --break-system-packages -r requirements.txt

dev:
	$(PY) -m pip install --break-system-packages -r requirements-dev.txt

datasets:
	$(PY) tools/generate_datasets.py

examples:
	PYTHONPATH=. $(PY) tools/build_examples.py

generate:
	$(PY) -m robo_assess.cli generate --request configs/ros2_fundamentals.yaml

test:
	PYTHONPATH=. $(PY) -m pytest

eval:
	PYTHONPATH=. $(PY) -m robo_assess.cli eval

calibrate:
	PYTHONPATH=. $(PY) -m robo_assess.cli calibrate --write

docker-build:
	docker build -t robo-assess:latest .

docker-run:
	docker run --rm -v $$(pwd)/outputs:/app/outputs robo-assess:latest \
		generate --request configs/ros2_fundamentals.yaml

clean:
	rm -rf .pytest_cache **/__pycache__ *.egg-info build dist
	rm -f logs/*.db memory/*.db vectorstore/*.json
