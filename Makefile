# ---------------------------------------------------------------------------
# coding_agent — developer convenience targets
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
	@echo "  docker-build Build the generator Docker image"
	@echo "  docker-run   Generate inside the container"
	@echo "  clean        Remove caches and generated runtime artefacts"

install:
	$(PY) -m pip install --user --no-build-isolation .

dev:
	$(PY) -m pip install --user --no-build-isolation .

datasets:
	$(PY) tools/generate_datasets.py

examples:
	PYTHONPATH=. $(PY) tools/build_examples.py

generate:
	$(PY) -m coding_agent.cli generate --md "syllabus/Linux_ROS2_Fundamentals.md"

test:
	PYTHONPATH=. $(PY) -m pytest

eval:
	PYTHONPATH=. $(PY) -m coding_agent.cli eval

calibrate:
	PYTHONPATH=. $(PY) -m coding_agent.cli calibrate --write

docker-build:
	docker build -t coding-agent:latest .

docker-run:
	docker run --rm \
		-e OPENROUTER_API_KEY -e ANTHROPIC_API_KEY -e CODING_PROVIDER \
		-v $$(pwd)/outputs:/app/outputs \
		-v $$(pwd)/memory:/app/memory \
		-v $$(pwd)/vectorstore:/app/vectorstore \
		coding-agent:latest \
		generate --md "syllabus/Linux_ROS2_Fundamentals.md"

clean:
	rm -rf .pytest_cache **/__pycache__ *.egg-info build dist
	rm -f logs/*.db memory/*.db vectorstore/*.json
