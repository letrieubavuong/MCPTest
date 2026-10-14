"""Tech12h (tech12h.com) website adapter for educational multiple choice questions."""
import re
import urllib.parse
from html import unescape
from typing import Any

from latex_question_studio.scraping.adapters.base import (
    BaseSiteAdapter,
    RawExtractedQuestion,
    extract_img_urls,
)


class Tech12hAdapter(BaseSiteAdapter):
    """Dedicated adapter for tech12h.com educational articles and quizzes."""

    @property
    def name(self) -> str:
        return "Tech12h (tech12h.com)"

    @property
    def supported_domains(self) -> list[str]:
        return ["tech12h.com"]

    def can_handle(self, url: str) -> bool:
        """Strict domain verification for tech12h.com (rejects tech24.vn and lookalike hostnames)."""
        try:
            parsed = urllib.parse.urlparse(url.strip())
            netloc = parsed.netloc.lower()
            if ":" in netloc:
                netloc = netloc.split(":")[0]
            # Must strictly match tech12h.com or a valid subdomain *.tech12h.com
            if netloc == "tech12h.com" or netloc.endswith(".tech12h.com"):
                return True
        except Exception:
            pass
        return False

    def extract_questions(self, html: str, base_url: str) -> list[RawExtractedQuestion]:
        questions: list[RawExtractedQuestion] = []
        if not html or not html.strip():
            return questions

        # 1. Isolate the quiz container, stripping header, sidebar, navigation, ads, and related articles
        container_html = self._isolate_quiz_container(html)
        if not container_html:
            return questions

        # 2. Normalize non-breaking spaces & whitespace
        normalized_content = re.sub(r"&nbsp;|\u00a0", " ", container_html)

        # 3. Match questions starting with "Câu <number>:"
        # Tech12h can use:
        # - <p><strong>Câu 1:&nbsp;</strong>
        # - <p><b>Câu 1:</b>
        # - <p>Câu 1:&nbsp; (plain paragraph without strong/b tags)
        # - <strong>Câu 1:</strong>
        q_pattern = re.compile(
            r"(?:<(?:p|div|h\d)[^>]*>\s*(?:<(?:b|strong)[^>]*>\s*)?|<(?:b|strong)[^>]*>\s*)Câu\s*(\d+)[:.]?\s*(?:</(?:b|strong)>\s*)?(.*?)(?=(?:<(?:p|div|h\d)[^>]*>\s*(?:<(?:b|strong)[^>]*>\s*)?|<(?:b|strong)[^>]*>\s*)Câu\s*\d+[:.]?\s*(?:</(?:b|strong)>\s*)?|$)",
            re.DOTALL | re.IGNORECASE,
        )

        matches = list(q_pattern.finditer(normalized_content))

        for idx, m in enumerate(matches, start=1):
            q_num_str = m.group(1)
            q_body = m.group(2)
            parsed_q = self._parse_single_question(q_num_str, q_body, base_url, idx)
            if parsed_q:
                questions.append(parsed_q)

        return questions

    def _isolate_quiz_container(self, html: str) -> str:
        """Finds the main quiz section on tech12h and removes surrounding noise."""
        # Clean external non-math scripts
        cleaned = re.sub(
            r'<script(?![^>]*type=["\']math/tex)[^>]*>[\s\S]*?</script>',
            "",
            html,
            flags=re.IGNORECASE,
        )

        # Tech12h wraps the quiz in <div class="block-content-body trac_nghiem">
        # or <div class="accordion accordion-detail tex2jax" id="accordionExample">
        patterns = [
            r'<div[^>]*class=["\'][^"\']*(?:trac_nghiem|accordion-detail)[^"\']*["\'][^>]*>(.*?)(?:</div>\s*<!--/\.accordion-->|<div[^>]*class=["\']kqua|<h4[^>]*class=["\']cate-item-header|<ul[^>]*class=["\']list-news-related|$)',
            r'<div[^>]*id=["\']accordionExample["\'][^>]*>(.*?)(?:<div[^>]*class=["\']kqua|<h4|<ul[^>]*class=["\']list-news-related|$)',
        ]
        for pat in patterns:
            m = re.search(pat, cleaned, re.DOTALL | re.IGNORECASE)
            if m and "Câu" in m.group(1):
                return m.group(1)

        # Fallback: if no specific class matches, search from first 'Câu 1' to related news / footer
        m_start = re.search(r'(?:<(?:p|div|h\d)[^>]*>\s*)?<(?:strong|b)[^>]*>\s*Câu\s*1\b', cleaned, re.IGNORECASE)
        if m_start:
            start_pos = m_start.start()
            end_match = re.search(
                r'(?:<h4[^>]*class=["\']cate-item-header|<ul[^>]*class=["\']list-news-related|<div[^>]*class=["\']kqua|<!-- Start: quang cao)',
                cleaned[start_pos:],
                re.IGNORECASE,
            )
            end_pos = (start_pos + end_match.start()) if end_match else len(cleaned)
            return cleaned[start_pos:end_pos]

        if "Câu" in cleaned:
            return cleaned

        return ""

    def _parse_single_question(
        self, q_num: str, q_body: str, base_url: str, fallback_idx: int
    ) -> RawExtractedQuestion | None:
        warnings: list[str] = []
        needs_review = False

        # 1. Separate Prompt and Options
        # Options in tech12h are usually inside <ul><li>A. ...</li>...</ul>
        ul_match = re.search(r"<ul[^>]*>(.*?)</ul>", q_body, re.DOTALL | re.IGNORECASE)
        if ul_match:
            prompt_html = q_body[: ul_match.start()].strip()
            opts_html = ul_match.group(1)
            raw_options = re.findall(r"<li[^>]*>(.*?)</li>", opts_html, re.DOTALL | re.IGNORECASE)
        else:
            # Fallback: separate paragraphs <p>A. ...</p>
            p_opts = re.findall(
                r"<p[^>]*>\s*(?:<h6[^>]*>)?\s*([A-D]\s*[.:\)].*?)(?:</h6>)?\s*</p>",
                q_body,
                re.DOTALL | re.IGNORECASE,
            )
            if p_opts:
                first_opt = re.search(r"<p[^>]*>\s*(?:<h6[^>]*>)?\s*[A-D]\s*[.:\)]", q_body, re.IGNORECASE)
                prompt_html = q_body[: first_opt.start()].strip() if first_opt else q_body.strip()
                raw_options = p_opts
            else:
                prompt_html = q_body.strip()
                raw_options = []

        # Clean prompt tags
        prompt_html = re.sub(r"^</p>\s*", "", prompt_html)
        prompt_html = re.sub(r"<p>\s*$", "", prompt_html).strip()

        # Extract images from prompt
        prompt_images = extract_img_urls(prompt_html, base_url)
        all_images = list(prompt_images)

        # 2. Parse Options and Determine Correct Choice
        options_html: list[str] = []
        correct_candidates: list[int] = []

        for idx, opt_raw in enumerate(raw_options):
            # Check for correct answer signal:
            # On Tech12h, the correct choice is uniquely wrapped in <h6>...</h6> inside the <li>
            # (Verified against site JS: jQuery('.accordion-detail h6').css({"color": "green", "font-weight": "bold"}))
            has_h6 = bool(re.search(r"<h6\b", opt_raw, re.IGNORECASE))
            if has_h6:
                correct_candidates.append(idx)

            # Extract any images in this option
            opt_imgs = extract_img_urls(opt_raw, base_url)
            all_images.extend(opt_imgs)

            # Clean option markup: remove <h6>, </h6>
            clean_opt = re.sub(r"</?h6[^>]*>", "", opt_raw, flags=re.IGNORECASE).strip()

            # Strip leading option letter: A., B., C., D., A), etc.
            clean_opt = re.sub(r"^[A-Da-d]\s*[.:\)]\s*", "", clean_opt).strip()

            # Check if option is empty or only an image
            text_without_tags = re.sub(r"<[^>]+>", "", clean_opt).strip()
            if not text_without_tags and not opt_imgs:
                warnings.append(f"Phương án {chr(65+idx)} rỗng hoặc thiếu nội dung.")
                needs_review = True
            elif not text_without_tags and opt_imgs:
                warnings.append(f"Phương án {chr(65+idx)} chỉ chứa hình ảnh.")

            options_html.append(clean_opt)

        # 3. Guardrail for Answer Verification
        correct_choice: int | None = None
        if len(correct_candidates) == 1:
            correct_choice = correct_candidates[0]
        else:
            # 0 or >1 options marked with <h6>: do not speculate!
            correct_choice = None
            needs_review = True
            if len(correct_candidates) == 0:
                warnings.append("Chưa xác định chắc chắn đáp án đúng từ cấu trúc trang (cần giáo viên kiểm duyệt).")
            else:
                warnings.append("Có nhiều hơn 1 phương án được đánh dấu nổi bật (cần giáo viên kiểm duyệt).")

        if len(options_html) != 4:
            warnings.append(f"Số lượng phương án ({len(options_html)}) khác 4.")
            needs_review = True

        title = f"Câu {q_num}" if q_num else f"Câu {fallback_idx}"

        return RawExtractedQuestion(
            prompt_html=prompt_html,
            options_html=options_html,
            correct_choice=correct_choice,
            question_type="mcq",
            image_urls=list(dict.fromkeys(all_images)),
            title=title,
            raw_source_snippet=q_body[:300],
            needs_review=needs_review,
            warnings=warnings,
        )
