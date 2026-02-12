# Cross-Platform Development Guide

This document outlines best practices for ensuring the gedcom-to-visualmap codebase works consistently across Windows, macOS, and Linux.

## Table of Contents
1. [File Encoding](#file-encoding)
2. [Path Handling](#path-handling)
3. [Line Endings](#line-endings)
4. [Testing](#testing)
5. [Utilities](#utilities)

---

## File Encoding

### The Problem
Windows defaults to cp1252 encoding, while Unix systems default to UTF-8. Files containing non-ASCII characters (emojis, accented characters, etc.) will fail on Windows if encoding isn't specified.

### The Solution
**Always specify `encoding='utf-8'` for text file operations.**

### ✅ Correct Patterns

```python
# Reading files
with open('config.yaml', 'r', encoding='utf-8') as f:
    content = f.read()

# Writing files
with open('output.txt', 'w', encoding='utf-8') as f:
    f.write(content)

# Path.read_text / write_text
from pathlib import Path
content = Path('file.txt').read_text(encoding='utf-8')
Path('file.txt').write_text(content, encoding='utf-8')

# CSV files (require special newline handling)
with open('data.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(data)

# Temporary files
with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as f:
    f.write('test data')
```

### ❌ Avoid

```python
# Missing encoding
with open('file.txt', 'r') as f:  # BAD: defaults to platform encoding
    content = f.read()

# Path operations without encoding
Path('file.txt').write_text(content)  # BAD: no encoding specified
```

### Where This Applies
- Configuration files (YAML, INI, JSON)
- GEDCOM files
- HTML/Markdown output
- CSV files
- Log files
- Any text file that might contain non-ASCII characters

---

## Path Handling

### The Problem
- Windows uses backslashes (`\`) as path separators
- Unix uses forward slashes (`/`)
- String concatenation with `/` breaks on Windows
- Hardcoded paths in tests cause cross-platform failures

### The Solution
**Use `pathlib.Path` for all path operations.**

### ✅ Correct Patterns

```python
from pathlib import Path

# Path construction
config_dir = Path('config')
config_file = config_dir / 'settings.yaml'

# Cross-platform home directory
home = Path.home()
config_path = home / '.myapp' / 'config.ini'

# Get POSIX path (forward slashes) for URLs
file_url = f'file://{Path("path/to/file").as_posix()}'

# Join multiple components
path = Path('dir1', 'dir2', 'file.txt')

# Convert to string when needed
path_str = str(config_file)
```

### ❌ Avoid

```python
# String concatenation
path = 'config/' + filename  # BAD: hardcoded separator

# Manual separator handling
path = 'dir' + os.sep + 'file'  # BAD: use Path instead

# Hardcoded absolute paths in tests
test_path = '/tmp/test.txt'  # BAD: Unix-only path
```

### Testing Path-Related Code

When testing path operations, normalize paths for assertions:

```python
from services.file_utils import normalize_path_for_display

# In tests:
result = function_that_returns_path()
normalized = normalize_path_for_display(result)
assert '/expected/path' in normalized  # Works on both Windows and Unix
```

---

## Line Endings

### The Problem
- Windows: `\r\n` (CRLF)
- Unix: `\n` (LF)
- Mixed line endings can cause issues

### The Solution

```python
# For input files (accept any line ending)
with open(file, 'r', encoding='utf-8', newline='') as f:
    content = f.read()

# For output files (specify line ending)
with open(file, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

# CSV files (empty newline for csv module)
with open(file, 'w', encoding='utf-8', newline='') as csvfile:
    writer = csv.writer(csvfile)
```

### Git Configuration
`.gitattributes` ensures consistent line endings:
```
* text=auto
*.py text eol=lf
*.md text eol=lf
*.yaml text eol=lf
```

---

## Testing

### Platform-Specific Tests

```python
import sys
import platform
import pytest

# Skip on specific platforms
@pytest.mark.skipif(sys.platform == 'win32', reason="Unix-only test")
def test_unix_feature():
    pass

# Run only on specific platforms
@pytest.mark.skipif(sys.platform != 'win32', reason="Windows-specific")
def test_windows_feature():
    pass
```

### Mocking Platform Behavior

When mocking `platform.system()` or `sys.platform`, remember:
- Mocking changes what the function returns
- It doesn't change underlying OS behavior (like `pathlib.Path` separators)
- You may need to normalize paths in assertions

```python
from unittest.mock import patch
from services.file_utils import normalize_path_for_display

@patch('platform.system', return_value='Darwin')
def test_darwin_path(mock_system):
    result = get_config_path()
    # Normalize for cross-platform testing
    normalized = normalize_path_for_display(result)
    assert '/Library/Application Support' in normalized
```

### Temporary Files in Tests

```python
import tempfile
from pathlib import Path

# Use tmp_path fixture (pytest)
def test_something(tmp_path):
    test_file = tmp_path / 'test.txt'
    test_file.write_text('content', encoding='utf-8')
    
# Or tempfile.TemporaryDirectory
def test_something_else():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / 'test.txt'
        test_file.write_text('content', encoding='utf-8')
```

---

## Utilities

### File Utils Module

The project provides `services/file_utils.py` for safe cross-platform file operations:

```python
from services.file_utils import (
    safe_read_text,
    safe_write_text,
    safe_open,
    safe_temp_file,
    get_posix_path,
    normalize_path_for_display,
)

# Read with automatic UTF-8 encoding
content = safe_read_text('config.yaml')

# Write with automatic UTF-8 encoding
safe_write_text('output.txt', content)

# Context manager with UTF-8 default
with safe_open('data.json', 'w') as f:
    json.dump(data, f)

# Temporary file with UTF-8
with safe_temp_file(suffix='.yaml') as f:
    f.write('test: value\n')
    temp_path = f.name

# Always get forward slashes
url = f'file://{get_posix_path(file_path)}'

# Normalize for display/assertions
normalized = normalize_path_for_display(windows_or_unix_path)
```

---

## Checklist for New Code

Before committing code, verify:

- [ ] All text file operations specify `encoding='utf-8'`
- [ ] Path operations use `pathlib.Path`, not string concatenation
- [ ] No hardcoded path separators (`/` or `\`)
- [ ] No hardcoded platform-specific paths (`C:\`, `/tmp`, etc.) except in tests
- [ ] Test files use `tmp_path` fixture or proper tempfile handling
- [ ] CSV operations use `newline=''` parameter
- [ ] Tests normalize paths before assertions if platform-agnostic behavior expected
- [ ] Temporary files in tests specify encoding

---

## Common Pitfalls

### 1. Path Construction
```python
# ❌ Don't
path = 'dir/' + filename
path = f'{base_dir}/{filename}'

# ✅ Do
path = Path(base_dir) / filename
path = Path('dir', filename)
```

### 2. File URLs
```python
# ❌ Don't
url = 'file://' + str(path)

# ✅ Do
from services.file_utils import get_posix_path
url = f'file://{get_posix_path(path)}'
```

### 3. Testing with Paths
```python
# ❌ Don't
assert 'C:/path/to/file' in str(result)  # Windows-specific

# ✅ Do
from services.file_utils import normalize_path_for_display
assert 'path/to/file' in normalize_path_for_display(result)
```

### 4. Missing Encoding
```python
# ❌ Don't
with open('config.yaml') as f:  # Platform-dependent encoding
    data = yaml.safe_load(f)

# ✅ Do
with open('config.yaml', encoding='utf-8') as f:
    data = yaml.safe_load(f)
```

---

## Testing Cross-Platform Compatibility

### Run Tests Locally
```bash
python -m pytest
```

### Verify on Multiple Platforms
- macOS (local)
- Windows (collaborator or CI)
- Linux (CI or WSL)

### Key Test Categories
1. File I/O operations
2. Path construction and manipulation
3. Configuration loading/saving
4. Platform-specific features (GUI, file opening)

---

## Resources

- [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html)
- [Python open() encoding](https://docs.python.org/3/library/functions.html#open)
- [CSV module and newlines](https://docs.python.org/3/library/csv.html#csv.writer)
- [Python tempfile](https://docs.python.org/3/library/tempfile.html)

---

## Summary

The key to cross-platform compatibility:

1. **Always use UTF-8**: Specify `encoding='utf-8'` for all text operations
2. **Use pathlib.Path**: Never concatenate strings for paths
3. **Normalize in tests**: Use utility functions for path assertions
4. **Test everywhere**: Verify on Windows, macOS, and Linux

Following these guidelines ensures the codebase works reliably across all platforms.
