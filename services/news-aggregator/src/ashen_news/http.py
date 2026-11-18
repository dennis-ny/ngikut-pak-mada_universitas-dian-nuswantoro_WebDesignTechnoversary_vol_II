"""HTTP sopan: User-Agent jelas, robots.txt, jeda 1-2 dtk, retry + backoff."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from urllib import robotparser
from urllib.parse import urlsplit

import httpx

log = logging.getLogger(__name__)

RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}
MAX_RETRY_AFTER = 60.0


class FetchError(Exception):
    """Kegagalan fetch umum (jaringan / HTTP)."""

    status = "error"


class BlockedError(FetchError):
    """Dihalangi (403, challenge Cloudflare, dsb). Jangan di-retry atau di-bypass."""

    status = "blocked"


class RobotsDisallowed(FetchError):
    status = "robots"


class NotFeedError(FetchError):
    """200 OK tetapi isinya bukan feed (HTML/challenge)."""

    status = "not_feed"


class Fetcher:
    def __init__(
        self,
        user_agent: str,
        robots_token: str,
        delay: tuple[float, float] = (1.0, 2.0),
        timeout: float = 20.0,
        max_attempts: int = 3,
        respect_robots: bool = True,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.user_agent = user_agent
        self.robots_token = robots_token
        self.delay = delay
        self.max_attempts = max_attempts
        self.respect_robots = respect_robots
        self._sleep = sleep
        self._clock = clock
        self._last_request = None  # type: float | None
        self._robots: dict[str, robotparser.RobotFileParser | None] = {}
        self._client = client or httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "application/rss+xml, application/xml, text/xml, */*;q=0.5"},
            timeout=timeout,
            follow_redirects=True,
        )

    # -- rate limit ---------------------------------------------------
    def _throttle(self) -> None:
        if self._last_request is not None:
            wait = random.uniform(*self.delay) - (self._clock() - self._last_request)
            if wait > 0:
                self._sleep(wait)
        self._last_request = self._clock()

    # -- request dengan retry ----------------------------------------
    def _request(self, url: str) -> httpx.Response:
        last: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            self._throttle()
            try:
                resp = self._client.get(url)
            except httpx.HTTPError as exc:
                last = exc
                log.warning("GET %s gagal (percobaan %d/%d): %s", url, attempt, self.max_attempts, exc)
            else:
                if resp.status_code == 403:
                    raise BlockedError(f"403 Forbidden: {url}")
                if resp.status_code in RETRY_STATUS:
                    last = FetchError(f"HTTP {resp.status_code}: {url}")
                    log.warning("GET %s -> %d (percobaan %d/%d)", url, resp.status_code, attempt, self.max_attempts)
                    retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
                    if attempt < self.max_attempts and retry_after:
                        self._sleep(min(retry_after, MAX_RETRY_AFTER))
                        continue
                else:
                    return resp
            if attempt < self.max_attempts:
                self._sleep(min(2 ** attempt, 30) + random.uniform(0, 1))
        raise FetchError(str(last))

    # -- robots.txt -----------------------------------------------------
    def _load_robots(self, origin: str) -> robotparser.RobotFileParser | None:
        """None = tidak ada aturan (4xx -> boleh); RobotFileParser lain = aturan."""
        if origin in self._robots:
            return self._robots[origin]
        rp = robotparser.RobotFileParser()
        try:
            resp = self._request(origin + "/robots.txt")
        except BlockedError:
            # robots.txt sendiri 403: perlakukan sebagai "tidak tersedia" (RFC 9309 4xx).
            self._robots[origin] = None
            return None
        if resp.status_code >= 500:
            rp.disallow_all = True
        elif resp.status_code >= 400:
            self._robots[origin] = None
            return None
        else:
            rp.parse(resp.text.splitlines())
        self._robots[origin] = rp
        return rp

    def allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        rp = self._load_robots(origin)
        if rp is None:
            return True
        target = parts.path + (f"?{parts.query}" if parts.query else "")
        return rp.can_fetch(self.robots_token, target or "/")

    # -- API publik -------------------------------------------------------
    def get_feed(self, url: str) -> bytes:
        if not self.allowed(url):
            raise RobotsDisallowed(f"robots.txt melarang {url}")
        resp = self._request(url)
        if resp.status_code >= 400:
            raise FetchError(f"HTTP {resp.status_code}: {url}")
        body = resp.content
        head = body[:600].lstrip().lower()
        if not (head.startswith(b"<?xml") or head.startswith(b"<rss") or head.startswith(b"<feed") or b"<rss" in head):
            raise NotFeedError(f"Respons bukan XML feed (kemungkinan challenge/HTML): {url}")
        return body


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
