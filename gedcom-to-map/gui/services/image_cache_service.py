"""image_cache_service.py

Provides the ImageCacheService: a stateless helper that handles downloading and
caching of remote (HTTP/HTTPS) media files referenced by GEDCOM person records.

Key concepts
------------
* **Remote URL** – an http/https URL whose hostname does NOT match any pattern in
  the configured ``local_photo_hosts`` list.  These files are downloaded and stored
  in the image-cache directory.
* **Local-web URL** – an http/https URL whose hostname matches one of the
  ``local_photo_hosts`` regex patterns (e.g. ``localhost``).  These are fetched
  directly on demand without caching, because they are always reachable from the
  running machine and their content may change frequently.
* **Cache filename** – by default the original filename from the URL path is
  preserved (``preserve_name=True``); when ``preserve_name=False`` a SHA-1 hash of
  the full URL is used to avoid collisions between files with the same name from
  different servers.

Thread-safety
-------------
``download_all`` is designed to be run in a background thread.  It accepts
optional ``progress_cb`` and ``stop_cb`` callbacks that are called from that thread.
Any GUI updates triggered from those callbacks must be marshalled back to the main
thread by the caller (e.g. ``wx.CallAfter``).
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.parse import urlparse

import requests

_log = logging.getLogger(__name__.lower())

__all__ = ["ImageCacheService"]

_REQUEST_TIMEOUT = 15  # seconds


class ImageCacheService:
    """Stateless helper for caching remote GEDCOM media files.

    All methods are class-level helpers so there is no shared mutable state;
    the service is safe to use from multiple threads simultaneously.
    """

    # ------------------------------------------------------------------
    # URL classification
    # ------------------------------------------------------------------

    @classmethod
    def is_http_url(cls, url: str) -> bool:
        """Return True if *url* starts with http:// or https://."""
        if not url:
            return False
        low = url.lower()
        return low.startswith("http://") or low.startswith("https://")

    @classmethod
    def is_local_web_url(cls, url: str, local_host_patterns: list) -> bool:
        """Return True if *url* is http/https but targets a local/intranet host.

        The hostname portion of the URL is matched case-insensitively against each
        pattern in *local_host_patterns*.

        Args:
            url: URL string to test.
            local_host_patterns: List of regex pattern strings.  A URL is considered
                local if its hostname matches *any* of these patterns.

        Returns:
            bool: True when the URL should be treated as locally accessible.
        """
        if not cls.is_http_url(url):
            return False
        try:
            hostname = urlparse(url).hostname or ""
        except Exception:
            return False
        for pattern in (local_host_patterns or []):
            try:
                if re.search(pattern, hostname, re.IGNORECASE):
                    return True
            except re.error:
                _log.warning("Invalid local_photo_hosts regex pattern: %r", pattern)
        return False

    @classmethod
    def is_remote_url(cls, url: str, local_host_patterns: list) -> bool:
        """Return True if *url* is http/https and NOT a local-web URL.

        Args:
            url: URL string to test.
            local_host_patterns: Patterns forwarded to ``is_local_web_url``.

        Returns:
            bool: True when the URL targets a remote server that should be cached.
        """
        return cls.is_http_url(url) and not cls.is_local_web_url(url, local_host_patterns)

    # ------------------------------------------------------------------
    # Cache path helpers
    # ------------------------------------------------------------------

    @classmethod
    def get_cache_filename(cls, url: str, preserve_name: bool) -> str:
        """Derive the cache filename for *url*.

        Args:
            url: Remote URL whose media is being cached.
            preserve_name: When True the original filename is kept (e.g.
                ``photo.jpg``).  When False a SHA-1 hex digest of the full URL
                is used (e.g. ``a3f2...d1.jpg``).

        Returns:
            str: Filename (no directory component).
        """
        parsed = urlparse(url)
        original_name = Path(parsed.path).name  # may be empty
        suffix = Path(original_name).suffix if original_name else ""

        if preserve_name and original_name:
            return original_name

        # Hash-based name: sha1 of the URL + original extension
        url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return url_hash + (suffix if suffix else "")

    @classmethod
    def get_cached_path(cls, url: str, cache_dir: str, preserve_name: bool) -> Path:
        """Return the full ``Path`` where *url*'s media would be cached.

        Args:
            url: Remote URL.
            cache_dir: Target directory for cached files.
            preserve_name: Forwarded to ``get_cache_filename``.

        Returns:
            Path: Full path to the cached file (may or may not exist).
        """
        filename = cls.get_cache_filename(url, preserve_name)
        return Path(cache_dir) / filename

    @classmethod
    def is_cached(cls, url: str, cache_dir: str, preserve_name: bool) -> bool:
        """Return True if the media for *url* already exists in *cache_dir*.

        Args:
            url: Remote URL.
            cache_dir: Directory to check.
            preserve_name: Forwarded to ``get_cached_path``.

        Returns:
            bool: True when the cached file exists on disk.
        """
        try:
            return cls.get_cached_path(url, cache_dir, preserve_name).exists()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Download helpers
    # ------------------------------------------------------------------

    @classmethod
    def download_one(cls, url: str, cache_dir: str, preserve_name: bool) -> Optional[Path]:
        """Download *url* into *cache_dir* and return the local ``Path``.

        If the file is already cached, the existing path is returned immediately
        without re-downloading.

        Args:
            url: Remote http/https URL to download.
            cache_dir: Directory where the file will be saved.
            preserve_name: Forwarded to ``get_cached_path``.

        Returns:
            Path to the locally cached file, or None on failure.
        """
        try:
            dest = cls.get_cached_path(url, cache_dir, preserve_name)
            if dest.exists():
                _log.debug("Cache hit: %s -> %s", url, dest)
                return dest

            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            _log.info("Downloading media: %s -> %s", url, dest)
            response = requests.get(url, timeout=_REQUEST_TIMEOUT, stream=True)
            response.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in response.iter_content(chunk_size=65536):
                    fh.write(chunk)
            _log.info("Cached: %s (%d bytes)", dest.name, dest.stat().st_size)
            return dest
        except requests.RequestException as exc:
            _log.warning("Failed to download %s: %s", url, exc)
        except OSError as exc:
            _log.warning("Failed to write cached file for %s: %s", url, exc)
        except Exception as exc:
            _log.warning("Unexpected error caching %s: %s", url, exc)
        return None

    @classmethod
    def download_all(
        cls,
        people: Dict,
        cache_dir: str,
        preserve_name: bool,
        local_host_patterns: list,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        stop_cb: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, int]:
        """Download all remote photos referenced in *people* into *cache_dir*.

        Iterates through each ``Person`` object in *people* and, for those whose
        ``photo`` attribute is a remote URL, downloads the file unless it is
        already present in the cache.

        Args:
            people: ``{xref_id: Person}`` mapping from loaded GEDCOM data.
            cache_dir: Directory where downloaded files are stored.
            preserve_name: Filename strategy – see ``download_one``.
            local_host_patterns: Patterns identifying local-web hosts that should
                NOT be cached – see ``is_local_web_url``.
            progress_cb: Optional callback ``(current, total, message)`` called
                after each URL attempt.  **Called from the background thread.**
            stop_cb: Optional callable returning ``True`` when the download loop
                should abort.  **Called from the background thread.**

        Returns:
            dict: ``{"found": n, "downloaded": n, "cached": n, "skipped": n, "failed": n}``
        """
        stats: Dict[str, int] = {"found": 0, "downloaded": 0, "cached": 0, "skipped": 0, "failed": 0}
        if not people:
            return stats

        # Collect unique remote URLs
        urls = []
        seen = set()
        for person in people.values():
            url = getattr(person, "photo", None)
            if url and cls.is_remote_url(url, local_host_patterns) and url not in seen:
                urls.append(url)
                seen.add(url)

        stats["found"] = len(urls)
        total = len(urls)
        _log.info("Image cache: found %d unique remote photo URLs", total)

        for idx, url in enumerate(urls):
            if stop_cb and stop_cb():
                _log.info("Image cache: download aborted by user")
                break

            if cls.is_cached(url, cache_dir, preserve_name):
                stats["cached"] += 1
                msg = f"Already cached ({idx + 1}/{total}): {Path(url).name}"
            else:
                result = cls.download_one(url, cache_dir, preserve_name)
                if result:
                    stats["downloaded"] += 1
                    msg = f"Downloaded ({idx + 1}/{total}): {result.name}"
                else:
                    stats["failed"] += 1
                    msg = f"Failed ({idx + 1}/{total}): {url}"

            if progress_cb:
                try:
                    progress_cb(idx + 1, total, msg)
                except Exception:
                    pass

        _log.info(
            "Image cache complete: found=%d downloaded=%d cached=%d failed=%d",
            stats["found"],
            stats["downloaded"],
            stats["cached"],
            stats["failed"],
        )
        return stats

    # ------------------------------------------------------------------
    # Post-load photo path rewriting
    # ------------------------------------------------------------------

    @classmethod
    def rewrite_people_photos(
        cls,
        people: Dict,
        cache_dir: str,
        preserve_name: bool,
        local_host_patterns: list,
    ) -> int:
        """Rewrite remote photo URLs to local cached paths for all people.

        For each ``Person`` whose ``photo`` is a remote URL (not a local-web URL)
        that has already been cached in *cache_dir*, replaces ``person.photo``
        with the local file path string so that the rest of the application can
        treat it as a local file.

        Persons whose photos are not yet cached are left unchanged; they will be
        fetched on demand when their ``PersonDialog`` opens.

        Args:
            people: ``{xref_id: Person}`` mapping.
            cache_dir: Directory where cached files reside.
            preserve_name: Filename strategy used when originally downloading.
            local_host_patterns: Forwarded to ``is_remote_url``.

        Returns:
            int: Number of person photos rewritten.
        """
        if not people or not cache_dir:
            return 0
        count = 0
        for person in people.values():
            url = getattr(person, "photo", None)
            if not url:
                continue
            if not cls.is_remote_url(url, local_host_patterns):
                continue
            cached_path = cls.get_cached_path(url, cache_dir, preserve_name)
            if cached_path.exists():
                try:
                    person.photo = str(cached_path)
                    count += 1
                except Exception as exc:
                    _log.debug("Could not rewrite photo for person %s: %s", getattr(person, "xref_id", "?"), exc)
        _log.debug("rewrite_people_photos: rewrote %d photo URLs to local paths", count)
        return count
