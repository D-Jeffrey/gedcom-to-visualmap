"""
Cross-platform file operation utilities.

This module provides utilities to ensure consistent and safe file operations
across different platforms (Windows, macOS, Linux).

Key features:
- Enforced UTF-8 encoding for text operations
- Proper newline handling
- Path normalization
- Tempfile wrappers

Best Practices:
1. Always use UTF-8 encoding for text files
2. Use pathlib.Path for path operations
3. Use these utilities instead of direct open() calls
4. Be careful with path separators (use Path() instead of string concatenation)
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Union, Optional, Any
import tempfile


# Default encoding for all text operations
DEFAULT_ENCODING = "utf-8"


def safe_read_text(path: Union[str, Path], encoding: str = DEFAULT_ENCODING, errors: str = "strict") -> str:
    """
    Read text from a file with explicit UTF-8 encoding.

    Args:
        path: File path to read
        encoding: Text encoding (default: utf-8)
        errors: Error handling strategy ('strict', 'replace', 'ignore')

    Returns:
        File contents as string

    Example:
        >>> content = safe_read_text('config.yaml')
    """
    return Path(path).read_text(encoding=encoding, errors=errors)


def safe_write_text(
    path: Union[str, Path], content: str, encoding: str = DEFAULT_ENCODING, newline: Optional[str] = None
) -> int:
    """
    Write text to a file with explicit UTF-8 encoding.

    Args:
        path: File path to write
        content: Text content to write
        encoding: Text encoding (default: utf-8)
        newline: Newline mode (None=universal, '', '\\n', '\\r\\n')

    Returns:
        Number of characters written

    Example:
        >>> safe_write_text('output.txt', 'Hello, World!')
    """
    path_obj = Path(path)

    # For simple writes without newline control, use Path.write_text
    if newline is None:
        return path_obj.write_text(content, encoding=encoding)

    # For explicit newline control, use open()
    with open(path_obj, "w", encoding=encoding, newline=newline) as f:
        return f.write(content)


@contextmanager
def safe_open(
    path: Union[str, Path],
    mode: str = "r",
    encoding: Optional[str] = DEFAULT_ENCODING,
    newline: Optional[str] = None,
    errors: Optional[str] = None,
):
    """
    Context manager for safely opening files with proper encoding.

    Args:
        path: File path
        mode: File mode ('r', 'w', 'a', 'rb', 'wb', etc.)
        encoding: Text encoding (default: utf-8 for text modes, None for binary)
        newline: Newline mode for text files
        errors: Error handling strategy

    Yields:
        Open file object

    Example:
        >>> with safe_open('data.json', 'w') as f:
        ...     json.dump(data, f)
    """
    # Don't use encoding for binary modes
    if "b" in mode:
        encoding = None

    file_obj = open(path, mode, encoding=encoding, newline=newline, errors=errors)
    try:
        yield file_obj
    finally:
        file_obj.close()


@contextmanager
def safe_temp_file(
    mode: str = "w+",
    suffix: str = "",
    encoding: str = DEFAULT_ENCODING,
    newline: Optional[str] = None,
    delete: bool = True,
):
    """
    Context manager for creating temporary files with proper encoding.

    Args:
        mode: File mode
        suffix: File suffix (e.g., '.txt', '.json')
        encoding: Text encoding (default: utf-8 for text modes)
        newline: Newline mode
        delete: Whether to delete file on close

    Yields:
        NamedTemporaryFile object

    Example:
        >>> with safe_temp_file(suffix='.yaml') as f:
        ...     f.write('test: value\\n')
        ...     f.flush()
        ...     process_file(f.name)
    """
    # Don't use encoding for binary modes
    if "b" in mode:
        encoding = None

    temp_file = tempfile.NamedTemporaryFile(mode=mode, suffix=suffix, encoding=encoding, newline=newline, delete=delete)
    try:
        yield temp_file
    finally:
        if not temp_file.closed:
            temp_file.close()


def normalize_path_for_display(path: Union[str, Path]) -> str:
    """
    Normalize a path for display purposes (always forward slashes).

    Useful for logging and assertions in tests where you want consistent
    path representation across platforms.

    Args:
        path: Path to normalize

    Returns:
        Path with forward slashes

    Example:
        >>> normalize_path_for_display(r'C:\\Users\\test\\file.txt')
        'C:/Users/test/file.txt'
    """
    return str(path).replace("\\", "/")


def ensure_utf8_csv(path: Union[str, Path], mode: str = "r", newline: str = "", **kwargs):
    """
    Open CSV file with proper UTF-8 encoding and newline handling.

    CSV files require special newline handling per Python csv module docs.

    Args:
        path: CSV file path
        mode: File mode
        newline: Newline mode (default: '' for csv module compatibility)
        **kwargs: Additional arguments passed to open()

    Returns:
        Open file object

    Example:
        >>> with ensure_utf8_csv('data.csv', 'w') as f:
        ...     writer = csv.writer(f)
        ...     writer.writerow(['Name', 'Value'])
    """
    return open(path, mode, encoding="utf-8", newline=newline, **kwargs)


def safe_path_join(*parts: str) -> Path:
    """
    Join path components in a cross-platform way.

    Args:
        *parts: Path components to join

    Returns:
        Joined Path object

    Example:
        >>> path = safe_path_join('dir', 'subdir', 'file.txt')
        >>> str(path)  # Uses OS-appropriate separator
    """
    return Path(*parts)


def get_posix_path(path: Union[str, Path]) -> str:
    """
    Get POSIX-style path (forward slashes) from any path.

    Useful for file:// URLs and cross-platform path representation.

    Args:
        path: Path to convert

    Returns:
        POSIX-style path string

    Example:
        >>> get_posix_path(Path('some/path'))
        'some/path'
        >>> get_posix_path(r'C:\\Windows\\Path')  # on Windows
        'C:/Windows/Path'
    """
    return Path(path).as_posix()


# Module-level constants for documentation
__all__ = [
    "DEFAULT_ENCODING",
    "safe_read_text",
    "safe_write_text",
    "safe_open",
    "safe_temp_file",
    "normalize_path_for_display",
    "ensure_utf8_csv",
    "safe_path_join",
    "get_posix_path",
]


# Usage examples and patterns
"""
COMMON PATTERNS:

1. Reading configuration files:
    from services.file_utils import safe_read_text
    content = safe_read_text('config.yaml')

2. Writing output files:
    from services.file_utils import safe_write_text
    safe_write_text('output.json', json.dumps(data))

3. Opening files with context manager:
    from services.file_utils import safe_open
    with safe_open('data.txt', 'w') as f:
        f.write('content')

4. Temporary files in tests:
    from services.file_utils import safe_temp_file
    with safe_temp_file(suffix='.ini', delete=False) as f:
        f.write('[section]\\n')
        temp_path = f.name

5. CSV files:
    from services.file_utils import ensure_utf8_csv
    with ensure_utf8_csv('data.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

6. Cross-platform paths:
    from services.file_utils import safe_path_join, get_posix_path
    path = safe_path_join('dir', 'file.txt')
    url = f'file://{get_posix_path(path)}'

7. Test assertions:
    from services.file_utils import normalize_path_for_display
    # Handles both Windows backslashes and Unix forward slashes
    assert '/expected/path' in normalize_path_for_display(actual_path)
"""
