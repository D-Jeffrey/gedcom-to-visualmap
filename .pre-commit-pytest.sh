#!/usr/bin/env bash
# Portable pytest runner for pre-commit hooks
# Tries to find Python with pytest in common locations

set -e

# Try to find Python with pytest installed, in order of preference:
# 1. .venv (local virtualenv)
# 2. python3 in PATH
# 3. python in PATH

if [ -x ".venv/bin/python" ] && .venv/bin/python -c "import pytest" 2>/dev/null; then
    exec .venv/bin/python -m pytest "$@"
elif command -v python3 &>/dev/null && python3 -c "import pytest" 2>/dev/null; then
    exec python3 -m pytest "$@"
elif command -v python &>/dev/null && python -c "import pytest" 2>/dev/null; then
    exec python -m pytest "$@"
else
    echo "Error: Could not find Python with pytest installed." >&2
    echo "Please ensure pytest is installed in one of:" >&2
    echo "  - .venv/bin/python" >&2
    echo "  - python3 (in PATH)" >&2
    echo "  - python (in PATH)" >&2
    exit 1
fi
