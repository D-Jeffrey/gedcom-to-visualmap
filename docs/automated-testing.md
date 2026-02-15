# Automated Testing Guide

This project includes multiple levels of automated testing to catch issues early and ensure code quality.

## 1. GitHub Actions (CI/CD)

### What it does
- Runs automatically on every push and pull request
- Tests across multiple OS platforms (Ubuntu, Windows, macOS)
- Tests across Python versions (3.10, 3.11, 3.12, 3.13)
- Generates coverage reports

### Configuration
See [.github/workflows/tests.yml](../.github/workflows/tests.yml)

### Viewing Results
- Check the "Actions" tab in GitHub
- Green checkmark = all tests passed
- Red X = tests failed (click for details)

### Badge (optional)
Add to README.md:
```markdown
[![Tests](https://github.com/YOUR_USERNAME/gedcom-to-visualmap/workflows/Tests/badge.svg)](https://github.com/YOUR_USERNAME/gedcom-to-visualmap/actions)
```

## 2. Pre-commit Hooks (Local)

### What it does
- Runs automatically before each git commit
- Fast tests only (skips slow tests)
- Code formatting checks
- Catches common issues before they reach GitHub

### Installation

**Step 1: Install pre-commit package**
```bash
pip install pre-commit
```

Or use the Makefile:
```bash
make install-dev  # Installs all dev dependencies including pre-commit
```

**Step 2: Install git hooks**
```bash
pre-commit install
```

**Step 3: Environments auto-install on first use**

The first time pre-commit runs (either on first commit or manual run), it will automatically download and install all tool environments (black, flake8, etc.). This takes a few minutes but only happens once - environments are cached and reused.

```bash
# Test the setup - will auto-install environments
pre-commit run --all-files
```

### For New Users Cloning the Repo

New users need to:
1. Clone the repository (includes `.pre-commit-config.yaml` and `.pre-commit-pytest.sh`)
2. Install dependencies: `pip install -r requirements-dev.txt`
3. Set up hooks: `pre-commit install`
4. Environments auto-install on first commit or test run

The `.pre-commit-config.yaml` file is version-controlled, but the actual environments are **not** - they're installed locally and cached in `~/.cache/pre-commit/`.

### Portable Python Detection

The pytest hooks use `.pre-commit-pytest.sh` wrapper script that automatically finds Python with pytest installed in this order:
1. `.venv/bin/python` (local virtualenv)
2. `python3` (in PATH)
3. `python` (in PATH)

This ensures pre-commit works across different development environments (macOS, Linux, Windows WSL, CI/CD) without hardcoded paths or virtualenv activation requirements.

### Usage
Once installed, tests run automatically when you commit:
```bash
git add .
git commit -m "Your message"
# Tests run automatically here
```

To run manually without committing:
```bash
pre-commit run --all-files
```

To skip pre-commit hooks (not recommended):
```bash
git commit --no-verify -m "Your message"
```

### Configuration
See [.pre-commit-config.yaml](../.pre-commit-config.yaml)

## 3. Makefile Commands (Local)

### Quick Commands
```bash
# Run all tests
make test

# Run fast tests only
make test-fast

# Run GUI consistency tests
make test-gui

# Run tests with coverage report
make test-cov

# Clean test artifacts
make clean

# Install dependencies
make install

# Install dev tools (pre-commit, coverage, etc)
make install-dev
```

### See all commands
```bash
make help
```

## 4. Manual Testing

### Run all tests
```bash
python -m pytest --quiet
```

### Run specific test file
```bash
python -m pytest gedcom-to-map/gui/tests/test_visual_map_frame_services.py -v
```

### Run with coverage
```bash
python -m pytest --cov=gedcom-to-map --cov-report=html
# Open htmlcov/index.html in browser
```

### Skip slow tests
```bash
python -m pytest -m "not slow"
```

## 5. VS Code Integration

### Recommended settings
Add to `.vscode/settings.json` (local, not committed):
```json
{
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": [
    "--quiet"
  ],
  "python.testing.autoTestDiscoverOnSaveEnabled": true
}
```

### Using the Test Explorer
1. Open Test Explorer (beaker icon in sidebar)
2. Tests auto-discover when you save files
3. Click play button to run tests
4. Green = pass, Red = fail

## Testing Strategy

### Fast vs Slow Tests
- **Fast tests** (<1s each): Unit tests, service layer tests
- **Slow tests** (>1s each): Integration tests, file I/O tests

Mark slow tests with:
```python
@pytest.mark.slow
def test_large_gedcom_file():
    ...
```

### What Gets Tested Where

**Pre-commit (local)**:
- Fast unit tests only
- Code formatting
- GUI attribute consistency tests

**GitHub Actions (CI)**:
- All tests (fast + slow)
- Multiple OS platforms
- Multiple Python versions
- Coverage reporting

### Test Organization
```
gedcom-to-map/
├── services/tests/          # Service layer tests
├── gui/tests/               # GUI integration tests
├── render/tests/            # Rendering tests
└── tests/                   # General/cross-cutting tests
```

## Troubleshooting

### Pre-commit hooks fail
```bash
# See what failed
pre-commit run --all-files

# Update hook versions
pre-commit autoupdate

# Reinstall hooks
pre-commit uninstall
pre-commit install
```

### GitHub Actions fail but local tests pass
- Check Python version differences
- Check OS-specific issues (paths, line endings)
- Run locally with same Python version: `pyenv install 3.13`

### Tests are slow
```bash
# Run fast tests only
make test-fast

# Or with pytest directly
python -m pytest -m "not slow"
```

## Best Practices

1. **Run tests before committing** (automatic with pre-commit)
2. **Write tests for bug fixes** (like the `selectedpeople` attribute test)
3. **Mark slow tests** with `@pytest.mark.slow`
4. **Keep tests fast** - use mocks for complex dependencies
5. **Test attribute consistency** - prevent AttributeError bugs
6. **Check GitHub Actions** before merging PRs

## Coverage Goals

Current: **~95%** coverage (581 tests)

Focus areas:
- Service layer: High coverage ✅
- GUI attribute consistency: Good ✅
- GUI event handlers: Limited (wxPython dependency)
- Rendering: Good ✅

## Adding New Tests

### For GUI code
Place in `gedcom-to-map/gui/tests/`:
```python
# Test service layer attributes, not full GUI
def test_gui_service_integration():
    state = GVState()
    assert hasattr(state, 'expected_attribute')
```

### For service code
Place in `gedcom-to-map/services/tests/`:
```python
def test_service_behavior():
    service = MyService()
    result = service.do_something()
    assert result == expected
```

## Further Resources

- [pytest documentation](https://docs.pytest.org/)
- [pre-commit documentation](https://pre-commit.com/)
- [GitHub Actions documentation](https://docs.github.com/en/actions)
