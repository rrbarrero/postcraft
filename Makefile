.PHONY: help lint typecheck format test test-full analyze draft

help:
	@echo "Available targets:"
	@echo "  lint       - Run ruff linter"
	@echo "  typecheck  - Run ty type checker"
	@echo "  format     - Run ruff formatter"
	@echo "  test       - Run pytest (skips LLM tests)"
	@echo "  test-full  - Run pytest including LLM tests"
	@echo "  all        - Run all checks (lint, typecheck, format, test)"
	@echo "  analyze    - Run scan and analyze on a path (Usage: make analyze PATH=/path/to/repo)"
	@echo "  draft      - Generate local portfolio draft (Usage: make draft PATH=/path/to/repo)"

lint:
	uv run ruff check .

typecheck:
	uv run ty check .

format:
	uv run ruff format .

test:
	uv run pytest -v

test-full:
	uv run pytest -v -o "addopts="

analyze:
ifndef PATH
	@echo "Error: PATH is not defined. Usage: make analyze PATH=/path/to/repo"
	exit 1
endif
	/home/roberto/.local/bin/uv run python -m src.adapters.primary.cli analyze $(PATH)

draft:
ifndef PATH
	@echo "Error: PATH is not defined. Usage: make draft PATH=/path/to/repo"
	exit 1
endif
	/home/roberto/.local/bin/uv run python -m src.adapters.primary.cli draft-project-post $(PATH)

all: lint typecheck format test
