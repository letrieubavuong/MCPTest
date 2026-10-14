"""VietJack website adapter for exercise pages."""
from html import unescape
import re
import unicodedata
import urllib.parse
from latex_question_studio.scraping.adapters.base import BaseSiteAdapter, RawExtractedQuestion


class VietjackAdapter(BaseSiteAdapter):
    """Adapter for vietjack.com and vietjack.me educational content."""

    @property
    def name(self) -> str:
        return "VietJack (vietjack.com)"

    @property
    def supported_domains(self) -> list[str]:
        return ["vietjack.com", "vietjack.me"]

    def extract_questions(self, html: str, base_url: str) -> list[RawExtractedQuestion]:
        questions: list[RawExtractedQuestion] = []
        if not html:
            return questions

        # Clean script tags that are NOT mathjax
        cleaned_html = re.sub(
            r'<script(?![^>]*type=["\']math/tex)[^>]*>[\s\S]*?</script>',
            '',
            html,
            flags=re.IGNORECASE
        )

        # Look for questions split by 'Câu \d+[:.]' or 'Bài \d+[:.]'
        # Matching pattern: <p[^>]*>\s*<b>\s*Câu\s*(\d+)[\s:.]*</b> or raw "Câu \d+:"
        question_pattern = re.compile(
            r'(?:<(?:p|div|h\d)[^>]*>\s*<(?:b|strong)[^>]*>\s*(?:Câu|Bài)\s*(\d+)[\s:.]*</(?:b|strong)>|(?:\b(?:Câu|Bài)\s*(\d+)[\s:.]))',
            re.IGNORECASE
        )

        matches = list(question_pattern.finditer(cleaned_html))
        if not matches:
            # Fallback: try finding question container divs
            container_pattern = re.compile(
                r'<div[^>]*class=["\'][^"\']*(?:question|quiz-item|cau-hoi)[^"\']*["\'][^>]*>([\s\S]*?)</div>\s*(?=<div[^>]*class=["\']|$)',
                re.IGNORECASE
            )
            for m in container_pattern.finditer(cleaned_html):
                q = self._parse_question_block(m.group(0), base_url, len(questions) + 1)
                if q:
                    questions.append(q)
            return questions

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned_html)
            block = cleaned_html[start:end]
            q_num = match.group(1) or match.group(2) or str(i + 1)
            q = self._parse_question_block(block, base_url, int(q_num) if q_num.isdigit() else i + 1)
            if q:
                questions.append(q)

        return questions

    def _parse_question_block(self, block: str, base_url: str, idx: int) -> RawExtractedQuestion | None:
        # Check for solution section
        solution_split = re.split(
            r'(?:<(?:b|strong)[^>]*>\s*(?:Lời giải|Hướng dẫn giải|Giải chi tiết|Đáp án)[\s:.]*</(?:b|strong)>|(?:\b(?:Lời giải|Hướng dẫn giải|Giải chi tiết|Đáp án)[\s:.]))',
            block,
            maxsplit=1,
            flags=re.IGNORECASE
        )
        content_part = solution_split[0]
        solution_part = solution_split[1] if len(solution_split) > 1 else ""

        # Find correct answer in solution or block
        correct_idx = None
        block_text = unicodedata.normalize('NFC', re.sub(r'<[^>]+>', ' ', block))
        ans_match = re.search(
            r'(?:[ĐđDd][aáa]p\s*[aáa]n|[Cc]h[oọo]n|[Pp]h\u01b0\u01a1ng\s*[aáa]n\s*(?:\u0111\xfang)?)\s*[:\s]*([A-D])\b',
            block_text,
            re.IGNORECASE
        )
        if ans_match:
            letter = ans_match.group(1).upper()
            correct_idx = ord(letter) - ord('A')

        # Extract options A., B., C., D.
        # Options can be structured like: <p><b>A.</b> content</p> or A. content B. content
        options: list[str] = []
        option_pattern = re.compile(
            r'(?:<(?:p|div|li)[^>]*>\s*<(?:b|strong)[^>]*>\s*([A-D])\s*[.:\)]\s*</(?:b|strong)>|<(?:b|strong)>\s*([A-D])\s*</(?:b|strong)>\s*[.:\)]|(?:^|[\s\n>])\s*([A-D])\s*[.:\)]\s+)',
            re.MULTILINE
        )
        opt_matches = list(option_pattern.finditer(content_part))
        
        # Filter matches so that we get sequence A, B, C, D
        found_options: dict[str, str] = {}
        first_opt_pos = None
        if opt_matches:
            for j, opt_m in enumerate(opt_matches):
                letter = (opt_m.group(1) or opt_m.group(2) or opt_m.group(3) or "").upper()
                if letter in ('A', 'B', 'C', 'D') and letter not in found_options:
                    if first_opt_pos is None and letter == 'A':
                        first_opt_pos = opt_m.start()
                    opt_start = opt_m.end()
                    opt_end = opt_matches[j + 1].start() if j + 1 < len(opt_matches) else len(content_part)
                    raw_opt = content_part[opt_start:opt_end].strip()
                    clean_opt = re.sub(r'</?(?:p|div|li|span)[^>]*>', '', raw_opt).strip()
                    found_options[letter] = clean_opt

        if len(found_options) == 4 and first_opt_pos is not None:
            options = [found_options['A'], found_options['B'], found_options['C'], found_options['D']]
            prompt_html = content_part[:first_opt_pos].strip()
            q_type = "mcq"
        else:
            # Could be essay or true/false
            prompt_html = content_part.strip()
            if "đúng" in prompt_html.lower() and "sai" in prompt_html.lower():
                q_type = "true_false"
            else:
                q_type = "essay"

        # Clean prompt title prefix (e.g. "Câu 1: ")
        prompt_html = re.sub(
            r'^(?:<(?:p|div|h\d)[^>]*>\s*)?<(?:b|strong)[^>]*>\s*(?:Câu|Bài)\s*\d+[\s:.]*</(?:b|strong)>',
            '',
            prompt_html,
            flags=re.IGNORECASE
        ).strip()
        prompt_html = re.sub(r'^(?:Câu|Bài)\s*\d+[\s:.]*', '', prompt_html, flags=re.IGNORECASE).strip()

        # Extract image URLs
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
            solution_html=solution_part.strip(),
            question_type=q_type,
            image_urls=image_urls,
            title=f"VietJack Câu {idx}",
            raw_source_snippet=block[:500],
            metadata={"source_domain": "vietjack.com", "question_index": idx}
        )
