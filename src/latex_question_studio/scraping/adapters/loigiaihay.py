"""Loigiaihay website adapter for exercise pages."""
from html import unescape
import re
import unicodedata
from latex_question_studio.scraping.adapters.base import (
    BaseSiteAdapter,
    RawExtractedQuestion,
    extract_img_urls,
)


class LoigiaihayAdapter(BaseSiteAdapter):
    """Adapter for loigiaihay.com educational solutions and exercises."""

    @property
    def name(self) -> str:
        return "Lời Giải Hay (loigiaihay.com)"

    @property
    def supported_domains(self) -> list[str]:
        return ["loigiaihay.com"]

    def extract_questions(self, html: str, base_url: str) -> list[RawExtractedQuestion]:
        questions: list[RawExtractedQuestion] = []
        if not html:
            return questions

        cleaned = re.sub(r'<script(?![^>]*type=["\']math/tex)[^>]*>[\s\S]*?</script>', '', html, flags=re.IGNORECASE)

        # 1. Try splitting by question pattern: "Câu \d+:" or "Bài \d+:"
        q_split_pattern = re.compile(
            r'(?:<(?:p|div|h\d)[^>]*>\s*(?:<b>|<strong>)?\s*(?:Câu|Bài)\s*(\d+)[\s:.]*(?:</b>|</strong>)?|(?:\b(?:Câu|Bài)\s*(\d+)[\s:.]))',
            re.IGNORECASE
        )
        matches = list(q_split_pattern.finditer(cleaned))
        if matches:
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned)
                block = cleaned[start:end]
                idx = int(match.group(1) or match.group(2) or (i + 1))
                q = self._parse_block(block, base_url, idx)
                if q:
                    questions.append(q)
            if questions:
                return questions

        # 2. Try box items
        box_pattern = re.compile(
            r'<div[^>]*class=["\'][^"\']*(?:box-item|content-question|item-cau-hoi)[^"\']*["\'][^>]*>([\s\S]*?)</div>\s*(?=<div[^>]*class=["\']*(?:box-item|content-question|item-cau-hoi)|$)',
            re.IGNORECASE
        )
        boxes = list(box_pattern.finditer(cleaned))
        if boxes:
            for idx, box in enumerate(boxes, start=1):
                q = self._parse_block(box.group(1), base_url, idx)
                if q:
                    questions.append(q)
            if questions:
                return questions

        # Fallback single block
        single = self._parse_block(cleaned, base_url, 1)
        if single:
            questions.append(single)

        return questions

    def _parse_block(self, block: str, base_url: str, idx: int) -> RawExtractedQuestion | None:
        # Split prompt and solution
        split = re.split(
            r'(?:<(?:div|p|span|b|strong)[^>]*class=["\'][^"\']*(?:loi-giai|solution|huong-dan|giai-chi-tiet)[^"\']*["\'][^>]*>|(?:\b(?:Lời giải|Hướng dẫn giải|Giải chi tiết)[\s:.]))',
            block,
            maxsplit=1,
            flags=re.IGNORECASE
        )
        content_part = split[0]
        solution_part = split[1] if len(split) > 1 else ""

        # Check for correct answer
        correct_idx = None
        block_text = unicodedata.normalize('NFC', re.sub(r'<[^>]+>', ' ', block))
        ans_m = re.search(
            r'(?:[ĐđDd][aáa]p\s*[aáa]n|[Cc]h[oọo]n|[Pp]h\u01b0\u01a1ng\s*[aáa]n\s*(?:\u0111\xfang)?)\s*[:\s]*([A-D])\b',
            block_text,
            re.IGNORECASE
        )
        if ans_m:
            correct_idx = ord(ans_m.group(1).upper()) - ord('A')

        # Detect options A., B., C., D.
        opt_pattern = re.compile(
            r'(?:<(?:p|div|li)[^>]*>\s*<(?:b|strong)[^>]*>\s*([A-D])\s*[.:\)]\s*</(?:b|strong)>|<(?:b|strong)>\s*([A-D])\s*</(?:b|strong)>\s*[.:\)]|(?:^|[\s\n>])\s*([A-D])\s*[.:\)]\s+)',
            re.MULTILINE
        )
        opt_matches = list(opt_pattern.finditer(content_part))
        found_options: dict[str, str] = {}
        first_opt_pos = None

        if opt_matches:
            for j, om in enumerate(opt_matches):
                letter = (om.group(1) or om.group(2) or om.group(3) or "").upper()
                if letter in ('A', 'B', 'C', 'D') and letter not in found_options:
                    if first_opt_pos is None and letter == 'A':
                        first_opt_pos = om.start()
                    start_pos = om.end()
                    end_pos = opt_matches[j + 1].start() if j + 1 < len(opt_matches) else len(content_part)
                    raw_opt = content_part[start_pos:end_pos].strip()
                    clean_opt = re.sub(r'</?(?:p|div|li|span)[^>]*>', '', raw_opt).strip()
                    found_options[letter] = clean_opt

        if len(found_options) == 4 and first_opt_pos is not None:
            options = [found_options['A'], found_options['B'], found_options['C'], found_options['D']]
            prompt_html = content_part[:first_opt_pos].strip()
            q_type = "mcq"
        else:
            options = []
            prompt_html = content_part.strip()
            q_type = "essay"

        prompt_html = re.sub(r'^(?:<(?:p|div|h\d)[^>]*>\s*)?(?:<(?:b|strong)>)?\s*(?:Câu|Bài)\s*\d+[\s:.]*(?:</(?:b|strong)>)?', '', prompt_html, flags=re.IGNORECASE).strip()
        prompt_html = re.sub(r'</?(?:p|div|li|span)[^>]*>', ' ', prompt_html).strip()

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
            title=f"Lời Giải Hay Câu {idx}",
            raw_source_snippet=block[:500],
            metadata={"source_domain": "loigiaihay.com", "question_index": idx}
        )
