.PHONY: test test-fast test-all test-cov test-gui clean help install

help:
	@echo "Available targets:"
	@echo "  test          - Run all tests (default)"
	@echo "  test-fast     - Run fast tests only (skip slow tests)"
	@echo "  test-gui      - Run GUI attribute consistency tests"
	@echo "  test-cov      - Run tests with coverage report"
	@echo "  test-all      - Run all tests including slow ones"
	@echo "  clean         - Remove test artifacts and cache"
	@echo "  install       - Install dependencies"
	@echo "  install-dev   - Install dependencies + development tools"

test:
	python -m pytest --quiet

test-fast:
	python -m pytest -m "not slow" --quiet

test-gui:
	python -m pytest gedcom-to-map/gui/tests/ -v

test-cov:
	python -m pytest --cov=gedcom-to-map --cov-report=html --cov-report=term

test-all:
	python -m pytest -v

clean:
	rm -rf .pytest_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

install:
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements-dev.txt
	pre-commit install
