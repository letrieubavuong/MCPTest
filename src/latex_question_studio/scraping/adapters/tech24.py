"""Tech24 website adapter for educational exercises and quiz pages."""
from html import unescape
import re
import unicodedata
from latex_question_studio.scraping.adapters.base import (
    BaseSiteAdapter,
    RawExtractedQuestion,
    extract_img_urls,
)


class Tech24Adapter(BaseSiteAdapter):
    """Adapter for tech24.vn quiz and exercise pages."""

    @property
    def name(self) -> str:
        return "Tech24 (tech24.vn)"

    @property
    def supported_domains(self) -> list[str]:
        return ["tech24.vn"]

    def extract_questions(self, html: str, base_url: str) -> list[RawExtractedQuestion]:
        questions: list[RawExtractedQuestion] = []
        if not html:
            return questions

        # Clean non-math scripts
        cleaned = re.sub(r'<script(?![^>]*type=["\']math/tex)[^>]*>[\s\S]*?</script>', '', html, flags=re.IGNORECASE)

        # Tech24 typically formats questions in container elements or standard headers
        container_pattern = re.compile(
            r'<div[^>]*class=["\'][^"\']*(?:question-item|question-box|quiz-question|content-question)[^"\']*["\'][^>]*>([\s\S]*?)</div>\s*(?=<div[^>]*class=["\']*(?:question-item|question-box|quiz-question|content-question)|$)',
            re.IGNORECASE
        )
        containers = list(container_pattern.finditer(cleaned))

        if containers:
            for idx, c in enumerate(containers, start=1):
                block = c.group(1)
                q = self._parse_block(block, base_url, idx)
                if q:
                    questions.append(q)
            return questions

        # Fallback to heading/numbering splitting: "Câu \d+:"
        q_split_pattern = re.compile(
            r'(?:<(?:p|div|h\d)[^>]*>\s*(?:<b>|<strong>)?\s*(?:Câu|Bài)\s*(\d+)[\s:.]*(?:</b>|</strong>)?|</(?:p|div|h\d)>\s*(?:Câu|Bài)\s*(\d+)[\s:.])',
            re.IGNORECASE
        )
        splits = list(q_split_pattern.finditer(cleaned))
        if splits:
            for i, sp in enumerate(splits):
                start = sp.start()
                end = splits[i + 1].start() if i + 1 < len(splits) else len(cleaned)
                block = cleaned[start:end]
                idx = int(sp.group(1) or sp.group(2) or (i + 1))
                q = self._parse_block(block, base_url, idx)
                if q:
                    questions.append(q)

        return questions

    def _parse_block(self, block: str, base_url: str, idx: int) -> RawExtractedQuestion | None:
        # Separate solution/explanation
        sol_match = re.split(
            r'(?:<(?:div|p|span)[^>]*class=["\'][^"\']*(?:explanation|solution|loi-giai|dap-an)[^"\']*["\'][^>]*>|(?:\b(?:Lời giải|Đáp án|Giải thích)[\s:.]))',
            block,
            maxsplit=1,
            flags=re.IGNORECASE
        )
        content_part = sol_match[0]
        solution_part = sol_match[1] if len(sol_match) > 1 else ""

        # Extract answer if present
        correct_idx = None
        block_text = unicodedata.normalize('NFC', re.sub(r'<[^>]+>', ' ', block))
        ans_m = re.search(
            r'(?:[ĐđDd][aáa]p\s*[aáa]n|[Cc]h[oọo]n|[Pp]h\u01b0\u01a1ng\s*[aáa]n\s*(?:\u0111\xfang)?)\s*[:\s]*([A-D])\b',
            block_text,
            re.IGNORECASE
        )
        if ans_m:
            letter = ans_m.group(1).upper()
            correct_idx = ord(letter) - ord('A')

        # Find choices A, B, C, D
        opt_pattern = re.compile(
            r'(?:<(?:div|p|li|label)[^>]*class=["\'][^"\']*(?:answer|option|choice)[^"\']*["\'][^>]*>|<(?:b|strong)>\s*([A-D])[\s:.]*</(?:b|strong)>|(?:^|[\s\n>])([A-D])[\s:.]\s+)',
            re.IGNORECASE | re.MULTILINE
        )
        opt_matches = list(opt_pattern.finditer(content_part))
        found_options: dict[str, str] = {}
        if opt_matches:
            for j, om in enumerate(opt_matches):
                letter = (om.group(1) or om.group(2) or "").upper()
                if not letter:
                    # check if answer letter is in tag content
                    m_text = content_part[om.start():om.end()]
                    for ltr in ('A', 'B', 'C', 'D'):
                        if ltr in m_text:
                            letter = ltr
                            break
                if letter in ('A', 'B', 'C', 'D') and letter not in found_options:
                    start_pos = om.end()
                    end_pos = opt_matches[j + 1].start() if j + 1 < len(opt_matches) else len(content_part)
                    found_options[letter] = content_part[start_pos:end_pos].strip()

        if len(found_options) == 4:
            options = [found_options['A'], found_options['B'], found_options['C'], found_options['D']]
            prompt_html = content_part[:opt_matches[0].start()].strip()
            q_type = "mcq"
        else:
            options = []
            prompt_html = content_part.strip()
            q_type = "essay"

        # Strip question prefix
        prompt_html = re.sub(r'^(?:<(?:p|div|h\d)[^>]*>\s*)?(?:<(?:b|strong)>)?\s*(?:Câu|Bài)\s*\d+[\s:.]*(?:</(?:b|strong)>)?', '', prompt_html, flags=re.IGNORECASE).strip()

        # Collect images (standard and lazy-loaded)
        image_urls = extract_img_urls(block, base_url)

        if not prompt_html and not options:
            return None

        return RawExtractedQuestion(
            prompt_html=prompt_html,
            options_html=options,
            correct_choice=correct_idx,
            solution_html=solution_part.strip(),
            question_type=q_type,
            image_urls=image_urls,
            title=f"Tech24 Câu {idx}",
            raw_source_snippet=block[:500],
            metadata={"source_domain": "tech24.vn", "question_index": idx}
        )
