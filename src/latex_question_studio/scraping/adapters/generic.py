"""Generic adapter for arbitrary educational web pages and pasted HTML."""
from html import unescape
import re
import unicodedata
import urllib.parse
from latex_question_studio.scraping.adapters.base import BaseSiteAdapter, RawExtractedQuestion


class GenericArticleAdapter(BaseSiteAdapter):
    """Fallback adapter that parses general HTML articles, worksheets, and pasted content."""

    @property
    def name(self) -> str:
        return "Bộ phân tích chung (Generic HTML / Bài viết)"

    @property
    def supported_domains(self) -> list[str]:
        return ["*"]

    def can_handle(self, url: str) -> bool:
        # Handles anything as fallback
        return True

    def extract_questions(self, html: str, base_url: str) -> list[RawExtractedQuestion]:
        questions: list[RawExtractedQuestion] = []
        if not html:
            return questions

        # Clean non-math scripts
        cleaned = re.sub(r'<script(?![^>]*type=["\']math/tex)[^>]*>[\s\S]*?</script>', '', html, flags=re.IGNORECASE)

        # 1. Try splitting by question pattern: "Câu \d+:", "Bài \d+:", "Question \d+:"
        split_pattern = re.compile(
            r'(?:<(?:p|div|h\d|li)[^>]*>\s*(?:<b>|<strong>)?\s*(?:Câu|Bài|Question)\s*(\d+)[\s:.]*(?:</b>|</strong>)?|(?:\b(?:Câu|Bài|Question)\s*(\d+)[\s:.]))',
            re.IGNORECASE
        )
        matches = list(split_pattern.finditer(cleaned))

        if matches:
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned)
                block = cleaned[start:end]
                idx = int(match.group(1) or match.group(2) or (i + 1))
                q = self._parse_block(block, base_url, idx)
                if q:
                    questions.append(q)
            return questions

        # 2. Try numbered list items (<ol><li>...</li></ol>)
        li_pattern = re.compile(r'<li[^>]*>([\s\S]*?)</li>', re.IGNORECASE)
        li_matches = list(li_pattern.finditer(cleaned))
        if len(li_matches) >= 2:
            for idx, li_m in enumerate(li_matches, start=1):
                block = li_m.group(1)
                q = self._parse_block(block, base_url, idx)
                if q:
                    questions.append(q)
            if questions:
                return questions

        # 3. Fallback: single block parse
        single_q = self._parse_block(cleaned, base_url, 1)
        if single_q:
            questions.append(single_q)

        return questions

    def _parse_block(self, block: str, base_url: str, idx: int) -> RawExtractedQuestion | None:
        # Separate solution
        split = re.split(
            r'(?:<(?:div|p|span|b|strong)[^>]*class=["\'][^"\']*(?:solution|loi-giai|huong-dan|giai-chi-tiet)[^"\']*["\'][^>]*>|(?:\b(?:Lời giải|Hướng dẫn giải|Giải chi tiết|Giải)[\s:.]))',
            block,
            maxsplit=1,
            flags=re.IGNORECASE
        )
        content_part = split[0]
        solution_part = split[1] if len(split) > 1 else ""

        # Check for answer letter (A, B, C, D)
        correct_idx = None
        block_text = unicodedata.normalize('NFC', re.sub(r'<[^>]+>', ' ', block))
        ans_m = re.search(
            r'(?:[ĐđDd][aáa]p\s*[aáa]n|[Cc]h[oọo]n|[Pp]h\u01b0\u01a1ng\s*[aáa]n\s*(?:\u0111\xfang)?)\s*[:\s]*([A-D])\b',
            block_text,
            re.IGNORECASE
        )
        if ans_m:
            correct_idx = ord(ans_m.group(1).upper()) - ord('A')

        # Check for short answer keyword: "Đáp số: ..." or "Kết quả: ..."
        short_ans_text = ""
        short_m = re.search(r'(?:Đáp số|Kết quả|Đáp án)\s*[:\s]*([^\n<]+)', block, re.IGNORECASE)
        if short_m and not ans_m:
            short_ans_text = short_m.group(1).strip()

        # Check for True/False options (a, b, c, d)
        tf_pattern = re.compile(r'(?:^|[\s\n>])\s*([a-d])\)\s+', re.MULTILINE)
        tf_matches = list(tf_pattern.finditer(content_part))

        # Check for MCQ options (A, B, C, D)
        opt_pattern = re.compile(
            r'(?:<(?:p|div|li)[^>]*>\s*<(?:b|strong)>\s*([A-D])[\s:.]*</(?:b|strong)>|(?:^|[\s\n>])\s*([A-D])[\s:.]\s+)',
            re.IGNORECASE | re.MULTILINE
        )
        opt_matches = list(opt_pattern.finditer(content_part))

        q_type = "essay"
        options: list[str] = []
        choice_tf_answers = None

        if len(opt_matches) >= 4:
            found_options: dict[str, str] = {}
            for j, om in enumerate(opt_matches):
                letter = (om.group(1) or om.group(2) or "").upper()
                if letter in ('A', 'B', 'C', 'D') and letter not in found_options:
                    start_pos = om.end()
                    end_pos = opt_matches[j + 1].start() if j + 1 < len(opt_matches) else len(content_part)
                    found_options[letter] = content_part[start_pos:end_pos].strip()

            if len(found_options) == 4:
                options = [found_options['A'], found_options['B'], found_options['C'], found_options['D']]
                prompt_html = content_part[:opt_matches[0].start()].strip()
                q_type = "mcq"
            else:
                prompt_html = content_part.strip()
        elif len(tf_matches) == 4:
            found_tf: dict[str, str] = {}
            for j, tm in enumerate(tf_matches):
                letter = tm.group(1).lower()
                if letter in ('a', 'b', 'c', 'd') and letter not in found_tf:
                    start_pos = tm.end()
                    end_pos = tf_matches[j + 1].start() if j + 1 < len(tf_matches) else len(content_part)
                    found_tf[letter] = content_part[start_pos:end_pos].strip()

            if len(found_tf) == 4:
                options = [found_tf['a'], found_tf['b'], found_tf['c'], found_tf['d']]
                prompt_html = content_part[:tf_matches[0].start()].strip()
                q_type = "true_false"
                # Check for (Đúng / Sai) inside statement or solution
                choice_tf_answers = []
                for opt in options:
                    if re.search(r'\bĐúng\b', opt, re.IGNORECASE):
                        choice_tf_answers.append(True)
                    elif re.search(r'\bSai\b', opt, re.IGNORECASE):
                        choice_tf_answers.append(False)
                    else:
                        choice_tf_answers.append(False)
            else:
                prompt_html = content_part.strip()
        elif short_ans_text and not options:
            prompt_html = content_part.strip()
            q_type = "short_answer"
        else:
            prompt_html = content_part.strip()
            q_type = "essay"

        # Strip prefix
        prompt_html = re.sub(
            r'^(?:<(?:p|div|h\d)[^>]*>\s*)?(?:<(?:b|strong)>)?\s*(?:Câu|Bài|Question)\s*\d+[\s:.]*(?:</(?:b|strong)>)?',
            '',
            prompt_html,
            flags=re.IGNORECASE
        ).strip()

        # Collect images
        image_urls = []
        for img_m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.IGNORECASE):
            src = img_m.group(1).strip()
            if src and not src.startswith("data:"):
                resolved = urllib.parse.urljoin(base_url, src)
                image_urls.append(resolved)

        if not prompt_html and not options:
            return None

        return RawExtractedQuestion(
            prompt_html=prompt_html,
            options_html=options,
            correct_choice=correct_idx,
            choice_tf_answers=choice_tf_answers,
            short_answer_text=short_ans_text,
            solution_html=solution_part.strip(),
            question_type=q_type,
            image_urls=image_urls,
            title=f"Câu {idx}",
            raw_source_snippet=block[:500],
            metadata={"source_domain": "generic", "question_index": idx}
        )
