import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import httpx
from app.reference import SOURCES

class CrawlError(RuntimeError):
    pass

class SafeClient:
    def __init__(self, settings, transport=None, sleeper=time.sleep, heartbeat=None):
        self.settings = settings
        self.sleep = sleeper
        self.heartbeat = heartbeat or (lambda: None)
        self.last_request = None
        self.delay = settings.crawl_request_delay
        self.robot = None
        self.client = httpx.Client(timeout=settings.crawl_timeout, follow_redirects=False,
            trust_env=False, transport=transport, headers={"User-Agent": settings.crawl_user_agent,
                                                          "Accept": "text/html,text/plain"})
        self.paths = {"/robots.txt"} | {
            f"/{s['site']}/na/ntt/{page}" for s in SOURCES.values()
            for page in ("selectNttList.do", "selectNttInfo.do")
        }

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.client.close()

    def validate_url(self, url):
        p = urlsplit(url)
        if p.scheme != "https" or p.hostname != "www.scnu.ac.kr" or p.port not in (None,443):
            raise CrawlError("UNSAFE_CRAWL_URL")
        if p.username or p.password or p.path not in self.paths or p.fragment:
            raise CrawlError("UNSAFE_CRAWL_URL")

    def request(self, url):
        self.validate_url(url)
        for attempt in range(3):
            self.heartbeat()
            if self.last_request is not None:
                self.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
            try:
                self.last_request = time.monotonic()
                with self.client.stream("GET", url) as response:
                    if response.status_code in {429,500,502,503,504} and attempt < 2:
                        retry_after = response.headers.get("Retry-After", "")
                        wait = min(60, int(retry_after)) if retry_after.isdigit() else 2 ** (attempt + 1)
                        self.sleep(max(self.delay, wait))
                        continue
                    if 300 <= response.status_code < 400:
                        raise CrawlError("REDIRECT_NOT_ALLOWED")
                    # Enforce on decoded bytes, including streamed or compressed bodies.
                    parts, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 4_000_000:
                            raise CrawlError("SOURCE_RESPONSE_TOO_LARGE")
                        parts.append(chunk)
                    data = b"".join(parts)
                    encoding = response.encoding or "utf-8"
                    self.heartbeat()
                    return response.status_code, data.decode(encoding, errors="replace")
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == 2:
                    raise CrawlError("SOURCE_NETWORK_ERROR") from exc
                self.sleep(2 ** (attempt + 1))
        raise CrawlError("SOURCE_REQUEST_FAILED")

    def prepare_robots(self):
        if self.settings.robots_policy == "written_permission":
            # Explicitly documented permission exception; never silently enabled.
            return
        status, body = self.request("https://www.scnu.ac.kr/robots.txt")
        if status == 404:
            self.robot = RobotFileParser()
            self.robot.parse(["User-agent: *", "Disallow:"])
            return
        if status != 200:
            raise CrawlError(f"ROBOTS_HTTP_{status}")
        if "<html" in body.lower() or "<!doctype" in body.lower():
            raise CrawlError("ROBOTS_INVALID_CONTENT")
        self.robot = RobotFileParser()
        self.robot.parse(body.splitlines())
        wait = self.robot.crawl_delay(self.settings.crawl_user_agent)
        if wait:
            self.delay = max(self.delay, float(wait))
        rate = self.robot.request_rate(self.settings.crawl_user_agent)
        if rate and rate.requests > 0:
            self.delay = max(self.delay, rate.seconds / rate.requests)

    def get_html(self, url):
        if self.settings.robots_policy == "strict" and self.robot is None:
            raise CrawlError("ROBOTS_NOT_CHECKED")
        if self.robot and not self.robot.can_fetch(self.settings.crawl_user_agent, url):
            raise CrawlError("ROBOTS_DISALLOWED")
        status, html = self.request(url)
        if status != 200:
            raise CrawlError(f"SOURCE_HTTP_{status}")
        return html
