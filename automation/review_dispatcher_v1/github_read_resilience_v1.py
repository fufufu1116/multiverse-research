from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.request
from typing import Any, Callable

READ_MAX_ATTEMPTS = 3
READ_MAX_TOTAL_WAIT_SECONDS = 60.0
READ_TIMEOUT_SECONDS = 30
MIN_RETRY_DELAY_SECONDS = 1.0


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
                return json.load(response)
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
