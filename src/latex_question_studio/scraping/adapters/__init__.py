"""Site adapters package and registry."""
from latex_question_studio.scraping.adapters.base import BaseSiteAdapter, RawExtractedQuestion
from latex_question_studio.scraping.adapters.vietjack import VietjackAdapter
from latex_question_studio.scraping.adapters.tech24 import Tech24Adapter
from latex_question_studio.scraping.adapters.loigiaihay import LoigiaihayAdapter
from latex_question_studio.scraping.adapters.generic import GenericArticleAdapter


ADAPTER_CLASSES: list[type[BaseSiteAdapter]] = [
    VietjackAdapter,
    Tech24Adapter,
    LoigiaihayAdapter,
    GenericArticleAdapter,
]


def get_adapter_for_url(url: str) -> BaseSiteAdapter:
    """Finds the most specific adapter for a given URL, falling back to GenericArticleAdapter."""
    url = url.strip()
    for cls in ADAPTER_CLASSES:
        if cls is not GenericArticleAdapter:
            adapter = cls()
            if adapter.can_handle(url):
                return adapter
    return GenericArticleAdapter()


__all__ = [
    "BaseSiteAdapter",
    "RawExtractedQuestion",
    "VietjackAdapter",
    "Tech24Adapter",
    "LoigiaihayAdapter",
    "GenericArticleAdapter",
    "ADAPTER_CLASSES",
    "get_adapter_for_url",
]
