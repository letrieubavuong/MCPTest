"""Base classes and types for website adapters."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import urllib.parse


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
