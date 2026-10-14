"""Base classes and types for website adapters."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re
from typing import Any
import urllib.parse


class AdapterStatus:
    """Explicit status codes for website scraping and extraction."""
    SUPPORTED = "supported"
    GENERIC_FALLBACK = "generic_fallback"
    BLOCKED = "blocked"
    PARSE_FAILED = "parse_failed"
    PARTIAL = "partial"
    NEEDS_REVIEW = "needs_review"


def extract_img_urls(html_block: str, base_url: str) -> list[str]:
    """Extracts image URLs supporting standard src and lazy-loaded attributes.

    Attribute priority: data-original, data-src, data-lazy-src, src, srcset.
    """
    if not html_block:
        return []

    urls: list[str] = []
    img_pattern = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
    attr_pattern = re.compile(r'([a-zA-Z0-9_\-]+)\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)

    for match in img_pattern.finditer(html_block):
        attrs = dict(attr_pattern.findall(match.group(1)))
        candidates = [
            attrs.get("data-original"),
            attrs.get("data-src"),
            attrs.get("data-lazy-src"),
            attrs.get("src"),
        ]
        srcset = attrs.get("srcset")
        if srcset:
            candidates.append(srcset.split(",")[0].strip().split(" ")[0])

        for c in candidates:
            c = (c or "").strip()
            if c and not c.startswith("data:"):
                resolved = urllib.parse.urljoin(base_url, c)
                if resolved not in urls:
                    urls.append(resolved)
                break

    return urls


@dataclass
class RawExtractedQuestion:
    """Raw structured data extracted from a webpage before LaTeX conversion."""
    prompt_html: str
    options_html: list[str] = field(default_factory=list)
    correct_choice: int | None = None  # 0-indexed: 0=A, 1=B, 2=C, 3=D
    choice_tf_answers: list[bool] | None = None  # [True, False, ...] for true/false
    short_answer_text: str = ""  # For short answer key
    solution_html: str = ""
    question_type: str = "mcq"  # "mcq", "true_false", "short_answer", "essay"
    image_urls: list[str] = field(default_factory=list)
    title: str = ""
    raw_source_snippet: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    has_missing_images: bool = False
    needs_review: bool = False
    warnings: list[str] = field(default_factory=list)


class BaseSiteAdapter(ABC):
    """Abstract base class for website-specific scrapers/extractors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name of the website adapter."""
        ...

    @property
    @abstractmethod
    def supported_domains(self) -> list[str]:
        """List of domain names handled by this adapter (e.g. ['vietjack.com'])."""
        ...

    def can_handle(self, url: str) -> bool:
        """Checks if this adapter is suitable for the given URL."""
        try:
            parsed = urllib.parse.urlparse(url.strip())
            netloc = parsed.netloc.lower()
            if ":" in netloc:
                netloc = netloc.split(":")[0]
            for domain in self.supported_domains:
                if netloc == domain or netloc.endswith("." + domain):
                    return True
        except Exception:
            pass
        return False

    @abstractmethod
    def extract_questions(self, html: str, base_url: str) -> list[RawExtractedQuestion]:
        """Extracts candidate questions from HTML content."""
        ...

    def extract_with_status(self, html: str, base_url: str) -> tuple[list[RawExtractedQuestion], str, list[str]]:
        """Extracts candidate questions and returns explicit status and diagnostic warnings."""
        warnings: list[str] = []
        if not html or not html.strip():
            return [], AdapterStatus.PARSE_FAILED, ["Nội dung HTML rỗng."]

        # Check for access blocks (Cloudflare, CAPTCHA, 403 pages)
        block_signals = ("captcha", "cloudflare", "access denied", "403 forbidden", "vui lòng xác minh")
        html_lower = html.lower()
        if any(sig in html_lower for sig in block_signals) and len(html) < 4000:
            return [], AdapterStatus.BLOCKED, ["Trang web yêu cầu xác minh bảo mật hoặc từ chối truy cập (BLOCKED)."]

        questions = self.extract_questions(html, base_url)
        if not questions:
            return [], AdapterStatus.PARSE_FAILED, ["Không nhận diện được câu hỏi nào từ cấu trúc HTML."]

        # Check completeness of extracted questions
        all_complete = True
        for q in questions:
            if q.question_type == "mcq" and (len(q.options_html) != 4 or q.correct_choice is None):
                q.needs_review = True
                all_complete = False
            elif q.question_type == "true_false" and (not q.choice_tf_answers or len(q.choice_tf_answers) != 4):
                q.needs_review = True
                all_complete = False
            elif q.has_missing_images:
                q.needs_review = True
                all_complete = False

        status = AdapterStatus.SUPPORTED if all_complete else AdapterStatus.PARTIAL
        if not all_complete:
            warnings.append("Một số câu hỏi trích xuất thiếu phương án hoặc chưa xác định đáp án đúng (cần duyệt).")

        return questions, status, warnings
