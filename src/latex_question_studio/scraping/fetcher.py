"""Safe HTTP Fetcher with SSRF Guard, Robots.txt policy, and rate limiting."""
import ipaddress
import re
import socket
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from typing import NamedTuple


USER_AGENT = "MCPTest-QuestionStudio/1.0 (+https://github.com/letrieubavuong/MCPTest)"
MAX_CONTENT_BYTES = 10 * 1024 * 1024  # 10 MB max per request
DEFAULT_TIMEOUT_SECONDS = 10.0


class FetchResult(NamedTuple):
    ok: bool
    status_code: int
    content: bytes
    final_url: str
    error: str = ""


class SSRFGuard:
    """Validates URLs and destination IP addresses against private / loopback / local networks."""

    @staticmethod
    def is_safe_url(url: str) -> tuple[bool, str]:
        try:
            parsed = urllib.parse.urlparse(url.strip())
        except Exception as e:
            return False, f"URL không hợp lệ: {str(e)}"

        if parsed.scheme.lower() not in ("http", "https"):
            return False, f"Chỉ hỗ trợ giao thức HTTP/HTTPS, từ chối: {parsed.scheme}"

        hostname = parsed.hostname
        if not hostname:
            return False, "Thiếu hostname trong URL"

        # Check raw IP or localhost names
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False, "Từ chối truy cập máy chủ cục bộ (localhost)"

        # Resolve DNS and check all IPs
        try:
            addr_info = socket.getaddrinfo(hostname, None)
        except socket.gaierror as e:
            return False, f"Không thể phân giải tên miền {hostname}: {str(e)}"

        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if (
                    ip_obj.is_private
                    or ip_obj.is_loopback
                    or ip_obj.is_link_local
                    or ip_obj.is_multicast
                    or ip_obj.is_reserved
                    or ip_obj.is_unspecified
                ):
                    return False, f"Từ chối kết nối tới địa chỉ mạng nội bộ / riêng tư: {ip_str}"
            except ValueError:
                return False, f"Địa chỉ IP không hợp lệ: {ip_str}"

        return True, ""


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Ensures redirected URLs also pass SSRF checks."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        is_safe, error = SSRFGuard.is_safe_url(newurl)
        if not is_safe:
            raise urllib.request.HTTPError(
                newurl, 403, f"SSRF Blocked redirect: {error}", headers, fp
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class RobotsPolicy:
    """Caches and validates robots.txt compliance for target sites."""

    def __init__(self):
        self._cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    def is_allowed(self, url: str) -> bool:
        try:
            parsed = urllib.parse.urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            if base not in self._cache:
                rp = urllib.robotparser.RobotFileParser()
                robots_url = f"{base}/robots.txt"
                is_safe, _ = SSRFGuard.is_safe_url(robots_url)
                if not is_safe:
                    return False
                try:
                    req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=5.0) as resp:
                        lines = resp.read().decode("utf-8", errors="ignore").splitlines()
                        rp.parse(lines)
                except Exception:
                    # If robots.txt cannot be fetched or 404, standard practice defaults to allowed
                    rp.allow_all = True
                self._cache[base] = rp

            return self._cache[base].can_fetch(USER_AGENT, url)
        except Exception:
            return True


class SafeFetcher:
    """HTTP client with safety guardrails: SSRF protection, robots.txt, rate limits, size limit."""

    def __init__(self, min_request_interval_s: float = 1.0):
        self.min_interval = min_request_interval_s
        self._last_request_time: dict[str, float] = {}
        self.robots = RobotsPolicy()

        opener = urllib.request.build_opener(SafeRedirectHandler())
        self.opener = opener

    def fetch(self, url: str, check_robots: bool = True) -> FetchResult:
        is_safe, ssrf_err = SSRFGuard.is_safe_url(url)
        if not is_safe:
            return FetchResult(False, 403, b"", url, f"Bảo mật SSRF: {ssrf_err}")

        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()

        # Enforce rate limit per domain
        now = time.monotonic()
        last_time = self._last_request_time.get(domain, 0.0)
        elapsed = now - last_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_time[domain] = time.monotonic()

        # Check robots.txt
        if check_robots and not self.robots.is_allowed(url):
            return FetchResult(
                False, 403, b"", url,
                f"Website {domain} từ chối thu thập nội dung theo chính sách robots.txt."
            )

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        req = urllib.request.Request(url, headers=headers)
        try:
            with self.opener.open(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
                content = bytearray()
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    content.extend(chunk)
                    if len(content) > MAX_CONTENT_BYTES:
                        return FetchResult(
                            False, 413, b"", url,
                            f"Kích thước trang vượt quá giới hạn an toàn ({MAX_CONTENT_BYTES // (1024*1024)}MB)."
                        )
                final_url = response.geturl()
                return FetchResult(True, response.status, bytes(content), final_url)
        except urllib.error.HTTPError as e:
            return FetchResult(False, e.code, b"", url, f"Lỗi HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            return FetchResult(False, 0, b"", url, f"Lỗi kết nối mạng: {str(e.reason)}")
        except Exception as e:
            return FetchResult(False, 0, b"", url, f"Lỗi không xác định: {str(e)}")
