from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
from typing import Any, Callable

READ_MAX_ATTEMPTS = 3
READ_MAX_TOTAL_WAIT_SECONDS = 60.0
READ_TIMEOUT_SECONDS = 30
MIN_RETRY_DELAY_SECONDS = 1.0
SAME_BUILD_CACHE_TTL_SECONDS = 5.0
SAME_BUILD_CACHE_ROOT = ".mv_github_read_cache_v1"


_CACHE_MISS = object()


def _header(headers: Any, name: str) -> str | None:
    if headers is None:
        return None
    try:
        value = headers.get(name)
    except Exception:
        return None
    if value is None:
        return None
    return str(value).strip()


def _strict_nonnegative_int(value: str | None) -> int | None:
    if value is None or not value or not value.isdigit():
        return None
    try:
        return int(value)
    except Exception:
        return None


def _error_text(exc: urllib.error.HTTPError) -> str:
    parts = [str(getattr(exc, "reason", ""))]
    try:
        raw = exc.read()
    except Exception:
        raw = b""
    if isinstance(raw, bytes):
        try:
            parts.append(raw.decode("utf-8", errors="replace"))
        except Exception:
            pass
    elif isinstance(raw, str):
        parts.append(raw)
    return " ".join(parts).lower()


def _mechanical_rate_limit_delay(
    exc: urllib.error.HTTPError,
    *,
    now: float,
) -> float | None:
    if exc.code not in (403, 429):
        return None

    retry_after_raw = _header(exc.headers, "Retry-After")
    remaining_raw = _header(exc.headers, "X-RateLimit-Remaining")
    reset_raw = _header(exc.headers, "X-RateLimit-Reset")

    retry_after: int | None = None
    if retry_after_raw is not None:
        retry_after = _strict_nonnegative_int(retry_after_raw)
        if retry_after is None:
            return None

    reset_delay: float | None = None
    if remaining_raw == "0":
        reset_epoch = _strict_nonnegative_int(reset_raw)
        if reset_epoch is None:
            return None
        reset_delay = max(
            MIN_RETRY_DELAY_SECONDS,
            float(math.ceil(reset_epoch - now) + 1),
        )
    elif reset_raw is not None and remaining_raw is not None:
        # A reset timestamp without an exhausted primary bucket is not a
        # mechanically sufficient retry signal for this bounded helper.
        reset_delay = None

    if retry_after is not None:
        text = _error_text(exc)
        if "rate limit" not in text and exc.code != 429:
            return None
        retry_delay = max(MIN_RETRY_DELAY_SECONDS, float(retry_after))
        if reset_delay is not None:
            return max(retry_delay, reset_delay)
        return retry_delay

    if reset_delay is not None:
        return reset_delay

    # Body-only 403s, secondary-limit prose without Retry-After, and all
    # other ambiguous failures intentionally fail closed with no retry.
    return None


def _cache_scope() -> str | None:
    build_id = os.environ.get("BUILDKITE_BUILD_ID", "").strip()
    if not build_id:
        return None
    return hashlib.sha256(build_id.encode("utf-8")).hexdigest()


def _cache_directory() -> Path | None:
    scope = _cache_scope()
    if scope is None:
        return None
    return Path(SAME_BUILD_CACHE_ROOT) / scope


def _cache_path(url: str) -> Path | None:
    directory = _cache_directory()
    if directory is None:
        return None
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return directory / f"{digest}.json"


def _valid_cache_entry(entry: Any, *, url: str, now: float) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("url") != url:
        return False
    fetched_at = entry.get("fetched_at")
    if not isinstance(fetched_at, (int, float)):
        return False
    age = now - float(fetched_at)
    if age < 0.0 or age > SAME_BUILD_CACHE_TTL_SECONDS:
        return False
    return "payload" in entry


def _read_exact_cache(url: str, *, now: float) -> Any:
    path = _cache_path(url)
    if path is None:
        return _CACHE_MISS
    try:
        entry = json.loads(path.read_text())
    except Exception:
        return _CACHE_MISS
    if not _valid_cache_entry(entry, url=url, now=now):
        return _CACHE_MISS
    return entry["payload"]


def _comment_id_from_url(url: str) -> int | None:
    marker = "/issues/comments/"
    if marker not in url:
        return None
    raw = url.rsplit(marker, 1)[1]
    if not raw.isdigit():
        return None
    try:
        return int(raw)
    except Exception:
        return None


def _read_comment_from_recent_issue_cache(url: str, *, now: float) -> Any:
    comment_id = _comment_id_from_url(url)
    directory = _cache_directory()
    if comment_id is None or directory is None:
        return _CACHE_MISS
    try:
        paths = list(directory.glob("*.json"))
    except Exception:
        return _CACHE_MISS
    for path in paths:
        try:
            entry = json.loads(path.read_text())
        except Exception:
            continue
        source_url = entry.get("url") if isinstance(entry, dict) else None
        if not isinstance(source_url, str):
            continue
        if "/issues/" not in source_url or "/comments" not in source_url:
            continue
        if not _valid_cache_entry(entry, url=source_url, now=now):
            continue
        payload = entry.get("payload")
        if not isinstance(payload, list):
            continue
        for item in payload:
            if isinstance(item, dict) and item.get("id") == comment_id:
                return item
    return _CACHE_MISS


def _write_cache(url: str, payload: Any, *, now: float) -> None:
    path = _cache_path(url)
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(
                {
                    "url": url,
                    "fetched_at": float(now),
                    "payload": payload,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        os.replace(tmp, path)
    except Exception:
        # Cache is only a same-build read-budget optimization. Any cache
        # write problem must leave the original live fail-closed behavior.
        return


def _cached_read(url: str, *, now: float) -> Any:
    exact = _read_exact_cache(url, now=now)
    if exact is not _CACHE_MISS:
        return exact
    return _read_comment_from_recent_issue_cache(url, now=now)


def github_json_request(
    url: str,
    *,
    user_agent: str,
    method: str = "GET",
    data: bytes | None = None,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.time,
    max_attempts: int = READ_MAX_ATTEMPTS,
    max_total_wait_seconds: float = READ_MAX_TOTAL_WAIT_SECONDS,
    timeout: int = READ_TIMEOUT_SECONDS,
) -> Any:
    method = method.upper()
    is_read = method == "GET" and data is None
    attempts = max(1, int(max_attempts))
    total_wait = 0.0

    if is_read:
        now = clock()
        cached = _cached_read(url, now=now)
        if cached is not _CACHE_MISS:
            return cached

    for attempt in range(attempts):
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": user_agent,
            },
        )
        try:
            with opener(req, timeout=timeout) as response:
                payload = json.load(response)
                if is_read:
                    _write_cache(url, payload, now=clock())
                return payload
        except urllib.error.HTTPError as exc:
            # This helper is deliberately mutation-hostile: POST/PUT/PATCH/
            # DELETE or any request with a body is never retried here.
            if not is_read:
                raise

            delay = _mechanical_rate_limit_delay(exc, now=clock())
            if delay is None:
                raise
            if attempt + 1 >= attempts:
                raise
            if delay > max_total_wait_seconds - total_wait:
                raise

            sleeper(delay)
            total_wait += delay

    raise AssertionError("unreachable")


def github_json_read(
    url: str,
    *,
    user_agent: str,
    **kwargs: Any,
) -> Any:
    return github_json_request(
        url,
        user_agent=user_agent,
        method="GET",
        data=None,
        **kwargs,
    )
