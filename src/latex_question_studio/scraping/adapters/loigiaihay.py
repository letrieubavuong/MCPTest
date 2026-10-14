"""Loigiaihay (loigiaihay.com) website adapter supporting multi-layout extraction:
- SBTExerciseExtractor: Exercise articles with sub-questions (e.g. 36.1 to 36.9)
- ExamPaperExtractor: Multi-section exam papers (Phần I MCQ, Phần II True/False, Phần III Short Answer)
- GenericLoigiaihayExtractor: Fallback for generic article layouts
"""
from datetime import datetime, timezone
import hashlib
from html import unescape
import re
import urllib.parse
from typing import Any

from latex_question_studio.scraping.adapters.base import (
    AdapterStatus,
    BaseSiteAdapter,
    RawExtractedQuestion,
    extract_img_urls,
)


def _clean_html_noise(html: str) -> str:
    """Removes non-math scripts, comments, and rating widgets from HTML."""
    if not html:
        return ""
    cleaned = unescape(html)
    cleaned = re.sub(r'<script(?![^>]*type=["\']math/tex)[^>]*>[\s\S]*?</script>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<!--[\s\S]*?-->', '', cleaned)
    cleaned = re.sub(r'<div[^>]*class=["\']rating-section["\'][\s\S]*?</div>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<div[^>]*id=["\'](?:pcinread|adCall|teads)[\s\S]*?</div>', '', cleaned, flags=re.IGNORECASE)
    return cleaned


class SBTExerciseExtractor:
    """Extractor for SBT / SGK exercise articles (e.g. exercises 36.1 to 36.9)."""

    def extract(self, html: str, base_url: str) -> list[RawExtractedQuestion]:
        questions: list[RawExtractedQuestion] = []
        cleaned = _clean_html_noise(html)

        # Match sub-question units: <div ... id="sub-question-\d+" ...>
        sq_pattern = re.compile(
            r'<div[^>]*id=["\']sub-question-(\d+)["\'][^>]*>(.*?)(?=<div[^>]*id=["\']sub-question-\d+|<div[^>]*id=["\']end_sub_question_nav|<div[^>]*class=["\'](?:box-related|list-news)|$)',
            re.DOTALL | re.IGNORECASE,
        )
        matches = list(sq_pattern.finditer(cleaned))
        if not matches:
            # Fallback by content-box-unit
            sq_pattern_fallback = re.compile(
                r'<div[^>]*class=["\'][^"\']*content-box-unit[^"\']*["\'][^>]*>(.*?)(?=<div[^>]*class=["\'][^"\']*content-box-unit|<div[^>]*id=["\']end_sub_question_nav|$)',
                re.DOTALL | re.IGNORECASE,
            )
            matches = list(sq_pattern_fallback.finditer(cleaned))

        for idx, m in enumerate(matches, start=1):
            sq_num = m.group(1) if m.re.groups >= 1 else str(idx)
            sq_body = m.group(m.re.groups)

            # Find title / label (e.g. 36.1, 36.2)
            t_m = re.search(
                r'<p[^>]*id=["\']question-title-idx-\d+["\'][^>]*>\s*(?:<[^>]+>)*\s*([0-9.]+)',
                sq_body,
                re.IGNORECASE,
            )
            q_label = t_m.group(1).strip() if t_m else f"36.{sq_num}"

            # Separate prompt from "Phương pháp giải" and "Lời giải chi tiết"
            sol_pattern = re.compile(
                r'(<p[^>]*>\s*<strong[^>]*>\s*(?:Phương pháp giải|Lời giải chi tiết)[\s\S]*$)',
                re.IGNORECASE,
            )
            sol_m = sol_pattern.search(sq_body)
            if sol_m:
                prompt_raw = sq_body[: sol_m.start()]
                sol_raw = sol_m.group(1)
            else:
                prompt_raw = sq_body
                sol_raw = ""

            # Remove title paragraph from prompt
            prompt_clean = re.sub(
                r'<p[^>]*id=["\']question-title-idx-\d+["\'][\s\S]*?</p>',
                '',
                prompt_raw,
                flags=re.IGNORECASE,
            ).strip()

            # Clean outer div tag leftovers if any
            prompt_clean = re.sub(r'^</?(?:div|p)[^>]*>\s*', '', prompt_clean).strip()

            # Check if prompt contains an HTML table (e.g. 36.5 with 7 statements)
            has_table = "<table" in prompt_clean.lower()

            # Check if multiple choice A-D
            opt_matches = list(
                re.finditer(r'<p[^>]*>\s*([A-D])\s*[.:\)]\s*(.*?)</p>', prompt_clean, re.DOTALL | re.IGNORECASE)
            )
            if len(opt_matches) == 4 and not has_table:
                q_type = "mcq"
                options = [om.group(2).strip() for om in opt_matches]
                prompt_final = prompt_clean[: opt_matches[0].start()].strip()
            else:
                # Keep as essay to preserve entire table / open question without loss
                q_type = "essay"
                options = []
                prompt_final = prompt_clean.strip()

            # Find correct answer if mcq
            correct_choice = None
            if q_type == "mcq" and sol_raw:
                ans_m = re.search(r'Đáp án\s*:\s*([A-D])\b', sol_raw, re.IGNORECASE)
                if ans_m:
                    correct_choice = ord(ans_m.group(1).upper()) - ord('A')

            imgs = extract_img_urls(sq_body, base_url)
            snapshot_hash = hashlib.sha256(sq_body.encode("utf-8")).hexdigest()[:16]

            needs_review = (q_type == "mcq" and correct_choice is None)
            warnings = ["Chưa xác định chắc chắn đáp án đúng."] if needs_review else []

            raw_q = RawExtractedQuestion(
                prompt_html=prompt_final,
                options_html=options,
                correct_choice=correct_choice,
                solution_html=sol_raw.strip(),
                question_type=q_type,
                image_urls=imgs,
                title=f"Bài {q_label}",
                raw_source_snippet=sq_body[:300],
                needs_review=needs_review,
                warnings=warnings,
                metadata={
                    "source_url": base_url,
                    "source_section": "SBT",
                    "source_question_number": q_label,
                    "dom_locator": f"#sub-question-{sq_num}",
                    "extraction_confidence": 0.95,
                    "source_snapshot_hash": snapshot_hash,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "has_table": has_table,
                },
            )
            questions.append(raw_q)

        return questions


class ExamPaperExtractor:
    """Extractor for comprehensive multi-section exam papers (Parts I, II, III)."""

    @staticmethod
    def _extract_solution_html(lg_body: str, target_class: str = "loigiai") -> str:
        if not lg_body:
            return ""
        pos = lg_body.find(f'class="{target_class}"')
        if pos == -1:
            pos = lg_body.find(f"class='{target_class}'")
            if pos == -1:
                pos = lg_body.find(target_class)
        if pos != -1:
            open_div = lg_body.rfind('<div', 0, pos)
            start_idx = open_div if open_div != -1 else pos
            sol_html = lg_body[start_idx:]
            part_pos = sol_html.find('class="exam-part-title"')
            if part_pos != -1:
                open_div_p = sol_html.rfind('<div', 0, part_pos)
                if open_div_p != -1:
                    sol_html = sol_html[:open_div_p]
            return sol_html.strip()
        return ""

    def extract(self, html: str, base_url: str) -> list[RawExtractedQuestion]:
        questions: list[RawExtractedQuestion] = []
        cleaned = _clean_html_noise(html)

        # Delineate 'Đề bài' and 'Lời giải và đáp án'
        pos_loigiai = cleaned.find("Lời giải và đáp án")
        debai_html = cleaned[:pos_loigiai] if pos_loigiai != -1 else cleaned
        loigiai_html = cleaned[pos_loigiai:] if pos_loigiai != -1 else ""

        # Cut off trailing noise after the last question in loigiai_html
        end_nav_pos = loigiai_html.find('id="end_sub_question_nav"')
        if end_nav_pos != -1:
            loigiai_html = loigiai_html[:end_nav_pos]

        def _split_parts(chunk: str) -> dict[str, str]:
            p1 = re.search(r'PHẦN\s*I\b', chunk, re.IGNORECASE)
            p2 = re.search(r'PHẦN\s*II\b', chunk, re.IGNORECASE)
            p3 = re.search(r'PHẦN\s*III\b', chunk, re.IGNORECASE)
            parts = {}
            if p1 and p2 and p3:
                parts["P1"] = chunk[p1.start():p2.start()]
                parts["P2"] = chunk[p2.start():p3.start()]
                parts["P3"] = chunk[p3.start():]
            elif p1 and p2:
                parts["P1"] = chunk[p1.start():p2.start()]
                parts["P2"] = chunk[p2.start():]
            elif p1:
                parts["P1"] = chunk[p1.start():]
            return parts

        debai_parts = _split_parts(debai_html)
        loigiai_parts = _split_parts(loigiai_html)

        q_pattern = re.compile(
            r'<div[^>]*class=["\'][^"\']*question\s+c[0-9a-f]{20,}[^"\']*["\'][^>]*>(.*?)(?=<div[^>]*class=["\'][^"\']*question\s+c[0-9a-f]{20,}|$)',
            re.DOTALL | re.IGNORECASE,
        )

        # ----------------------------------------------------
        # PHẦN I: 16 MCQ Questions (4 choices each)
        # ----------------------------------------------------
        p1_debai = list(q_pattern.finditer(debai_parts.get("P1", "")))
        if not p1_debai:
            fb_pattern = re.compile(
                r'<div[^>]*class=["\']question["\'][^>]*>(.*?)(?=<div[^>]*class=["\']question["\']|$)',
                re.DOTALL | re.IGNORECASE,
            )
            p1_debai = list(fb_pattern.finditer(debai_parts.get("P1", "")))

        p1_loigiai = list(q_pattern.finditer(loigiai_parts.get("P1", "")))

        for idx, m_db in enumerate(p1_debai, start=1):
            db_body = m_db.group(1) if m_db.groups() else m_db.group(0)
            lg_body = p1_loigiai[idx - 1].group(1) if idx - 1 < len(p1_loigiai) else ""

            # Extract Prompt
            p_match = re.search(
                r'<div[^>]*class=["\']question-content-inner["\'][^>]*>(.*?)</div>',
                db_body,
                re.DOTALL | re.IGNORECASE,
            )
            prompt_html = p_match.group(1) if p_match else db_body
            prompt_html = re.sub(
                r'<strong[^>]*class=["\']question-index-number["\'][\s\S]*?</strong>',
                '',
                prompt_html,
                flags=re.IGNORECASE,
            ).strip()
            prompt_html = re.sub(r'^\s*:\s*', '', prompt_html).strip()

            # Extract 4 options from ul.dapan or <p>A. ...</p>
            opts_match = re.search(
                r'<ul[^>]*class=["\'][^"\']*dapan[^"\']*["\'][^>]*>(.*?)</ul>',
                db_body,
                re.DOTALL | re.IGNORECASE,
            )
            options = []
            if opts_match:
                li_items = re.findall(r'<li[^>]*>(.*?)</li>', opts_match.group(1), re.DOTALL | re.IGNORECASE)
                for li in li_items:
                    clean_li = re.sub(r'<span[^>]*class=["\']span-answer["\'][\s\S]*?</span>', '', li, flags=re.IGNORECASE)
                    clean_li = re.sub(r'^[A-Da-d]\s*[.:\)]\s*', '', clean_li.strip()).strip()
                    options.append(clean_li)
            else:
                opt_matches = list(re.finditer(
                    r'<p[^>]*>\s*(?:<(?:b|strong)>)?\s*([A-D])\s*[.:\)]\s*(?:</(?:b|strong)>)?\s*(.*?)</p>',
                    db_body,
                    re.DOTALL | re.IGNORECASE,
                ))
                if len(opt_matches) == 4:
                    options = [om.group(2).strip() for om in opt_matches]
                    prompt_html = db_body[: opt_matches[0].start()].strip()

            # Extract correct answer and solution from loigiai
            correct_choice = None
            ans_m = re.search(r'Đáp án\s*:\s*([A-D])\b', lg_body, re.IGNORECASE)
            if ans_m:
                correct_choice = ord(ans_m.group(1).upper()) - ord('A')

            sol_html = self._extract_solution_html(lg_body, "loigiai")

            imgs = extract_img_urls(db_body + " " + lg_body, base_url)
            snapshot_hash = hashlib.sha256(db_body.encode("utf-8")).hexdigest()[:16]

            needs_review = (correct_choice is None)
            warnings = ["Chưa trích xuất được đáp án đúng từ lời giải."] if needs_review else []

            q = RawExtractedQuestion(
                prompt_html=prompt_html,
                options_html=options,
                correct_choice=correct_choice,
                solution_html=sol_html,
                question_type="mcq",
                image_urls=imgs,
                title=f"Phần I - Câu {idx}",
                raw_source_snippet=db_body[:300],
                needs_review=needs_review,
                warnings=warnings,
                metadata={
                    "source_url": base_url,
                    "source_section": "Phần I",
                    "source_question_number": f"Câu {idx}",
                    "dom_locator": f"P1-q{idx}",
                    "extraction_confidence": 0.95 if correct_choice is not None else 0.70,
                    "source_snapshot_hash": snapshot_hash,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            questions.append(q)

        # ----------------------------------------------------
        # PHẦN II: 3 True/False Questions (4 statements each)
        # ----------------------------------------------------
        p2_debai = list(q_pattern.finditer(debai_parts.get("P2", "")))
        p2_loigiai = list(q_pattern.finditer(loigiai_parts.get("P2", "")))

        for idx, m_db in enumerate(p2_debai, start=1):
            db_body = m_db.group(1)
            lg_body = p2_loigiai[idx - 1].group(1) if idx - 1 < len(p2_loigiai) else ""

            # Extract main prompt
            t_m = re.search(
                r'<div[^>]*class=["\']question-title["\'][^>]*>(.*?)</div>',
                db_body,
                re.DOTALL | re.IGNORECASE,
            )
            prompt_html = t_m.group(1) if t_m else ""
            prompt_html = re.sub(
                r'<strong[^>]*class=["\']question-index-number["\'][\s\S]*?</strong>',
                '',
                prompt_html,
                flags=re.IGNORECASE,
            ).strip()
            prompt_html = re.sub(r'^\s*:\s*', '', prompt_html).strip()

            # Extract statements (4 statements formatted with width: 60%)
            stmt_nodes = re.findall(
                r'<div[^>]*width:\s*60%[^>]*>(.*?)</div>',
                db_body,
                re.DOTALL | re.IGNORECASE,
            )
            statements = [s.strip() for s in stmt_nodes[:4]]

            # Extract True/False vector from loigiai (using fa-square-check)
            tf_vector = []
            if lg_body:
                ans_box = re.search(
                    r'<div[^>]*class=["\']question-answer\w*["\'][^>]*>(.*?)</div>\s*(?=<div[^>]*class=["\']solution|$)',
                    lg_body,
                    re.DOTALL | re.IGNORECASE,
                )
                search_scope = ans_box.group(1) if ans_box else lg_body
                rows = re.findall(
                    r'<div style=["\']display:\s*flex["\']>(.*?)</div>\s*(?=<div style=["\']display:\s*flex["\']|$)',
                    search_scope,
                    re.DOTALL | re.IGNORECASE,
                )
                for row in rows:
                    is_dung_checked = bool(re.search(r'<i[^>]*fa-square-check[^>]*></i>\s*Đúng', row, re.IGNORECASE))
                    is_sai_checked = bool(re.search(r'<i[^>]*fa-square-check[^>]*></i>\s*Sai', row, re.IGNORECASE))
                    if is_dung_checked and not is_sai_checked:
                        tf_vector.append(True)
                    elif is_sai_checked and not is_dung_checked:
                        tf_vector.append(False)
                    else:
                        tf_vector.append(None)

            sol_html = self._extract_solution_html(lg_body, "solution-detail")

            imgs = extract_img_urls(db_body + " " + lg_body, base_url)
            snapshot_hash = hashlib.sha256(db_body.encode("utf-8")).hexdigest()[:16]

            valid_tf = (len(tf_vector) == 4 and all(isinstance(v, bool) for v in tf_vector))
            needs_review = not valid_tf
            warnings = ["Chưa trích xuất đầy đủ vector Đúng/Sai 4 nhận định."] if not valid_tf else []

            q = RawExtractedQuestion(
                prompt_html=prompt_html,
                options_html=statements,
                choice_tf_answers=tf_vector if len(tf_vector) == 4 else None,
                solution_html=sol_html,
                question_type="true_false",
                image_urls=imgs,
                title=f"Phần II - Câu {idx}",
                raw_source_snippet=db_body[:300],
                needs_review=needs_review,
                warnings=warnings,
                metadata={
                    "source_url": base_url,
                    "source_section": "Phần II",
                    "source_question_number": f"Câu {idx}",
                    "dom_locator": f"P2-q{idx}",
                    "extraction_confidence": 0.95 if valid_tf else 0.70,
                    "source_snapshot_hash": snapshot_hash,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            questions.append(q)

        # ----------------------------------------------------
        # PHẦN III: 3 Short-Answer Questions (with sub-items a, b, c, d)
        # ----------------------------------------------------
        p3_debai = list(q_pattern.finditer(debai_parts.get("P3", "")))
        p3_loigiai = list(q_pattern.finditer(loigiai_parts.get("P3", "")))

        for idx, m_db in enumerate(p3_debai, start=1):
            db_body = m_db.group(1) if m_db.groups() else m_db.group(0)
            lg_body = p3_loigiai[idx - 1].group(1) if idx - 1 < len(p3_loigiai) else ""

            # Extract Prompt
            p_m = re.search(
                r'<div[^>]*class=["\']question-content-inner["\'][^>]*>(.*?)</div>',
                db_body,
                re.DOTALL | re.IGNORECASE,
            )
            prompt_html = p_m.group(1) if p_m else db_body
            prompt_html = re.sub(
                r'<strong[^>]*class=["\']question-index-number["\'][\s\S]*?</strong>',
                '',
                prompt_html,
                flags=re.IGNORECASE,
            ).strip()
            prompt_html = re.sub(r'^\s*:\s*', '', prompt_html).strip()

            # Extract solution and answer key
            sol_pos = lg_body.find('class="loigiai"')
            sol_html = lg_body[sol_pos:] if sol_pos != -1 else ""

            # Extract answer lines under "Đáp án"
            short_key = ""
            if sol_html:
                ans_sec = re.search(r'<p>\s*Đáp\s*án\s*</p>([\s\S]*)$', sol_html, re.IGNORECASE)
                if ans_sec:
                    raw_lines = re.findall(r'<p>(.*?)</p>', ans_sec.group(1), re.DOTALL | re.IGNORECASE)
                    clean_lines = [re.sub(r'<[^>]+>', '', l).strip() for l in raw_lines if l.strip()]
                    if clean_lines:
                        short_key = "; ".join(clean_lines)

            imgs = extract_img_urls(db_body + " " + lg_body, base_url)
            snapshot_hash = hashlib.sha256(db_body.encode("utf-8")).hexdigest()[:16]

            valid_short = bool(short_key)
            needs_review = not valid_short
            warnings = ["Chưa trích xuất được đáp án trả lời ngắn."] if not valid_short else []

            q = RawExtractedQuestion(
                prompt_html=prompt_html,
                options_html=[],
                short_answer_text=short_key,
                solution_html=sol_html,
                question_type="short_answer",
                image_urls=imgs,
                title=f"Phần III - Câu {idx}",
                raw_source_snippet=db_body[:300],
                needs_review=needs_review,
                warnings=warnings,
                metadata={
                    "source_url": base_url,
                    "source_section": "Phần III",
                    "source_question_number": f"Câu {idx}",
                    "dom_locator": f"P3-q{idx}",
                    "extraction_confidence": 0.95 if valid_short else 0.70,
                    "source_snapshot_hash": snapshot_hash,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            questions.append(q)

        return questions


class GenericLoigiaihayExtractor:
    """Fallback extractor for unclassified articles on loigiaihay.com."""

    def extract(self, html: str, base_url: str) -> list[RawExtractedQuestion]:
        questions: list[RawExtractedQuestion] = []
        cleaned = _clean_html_noise(html)

        # Look for question blocks by 'Câu \d+' or 'Bài \d+'
        q_split_pattern = re.compile(
            r'(?:<(?:p|div|h\d)[^>]*>\s*(?:<b>|<strong>)?\s*(?:Câu|Bài)\s*(\d+)[\s:.]*(?:</b>|</strong>)?|(?:\b(?:Câu|Bài)\s*(\d+)[\s:.]))',
            re.IGNORECASE,
        )
        matches = list(q_split_pattern.finditer(cleaned))
        if matches:
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned)
                block = cleaned[start:end]
                idx = int(match.group(1) or match.group(2) or (i + 1))
                q = self._parse_generic_block(block, base_url, idx)
                if q:
                    questions.append(q)
        return questions

    def _parse_generic_block(self, block: str, base_url: str, idx: int) -> RawExtractedQuestion | None:
        split = re.split(
            r'(?:<(?:div|p|span|b|strong)[^>]*class=["\'][^"\']*(?:loi-giai|solution|huong-dan|giai-chi-tiet)[^"\']*["\'][^>]*>|(?:\b(?:Lời giải|Hướng dẫn giải|Giải chi tiết)[\s:.]))',
            block,
            maxsplit=1,
            flags=re.IGNORECASE,
        )
        content_part = split[0]
        solution_part = split[1] if len(split) > 1 else ""

        opt_matches = list(re.finditer(
            r'<p[^>]*>\s*(?:<(?:b|strong)>)?\s*([A-D])\s*[.:\)]\s*(?:</(?:b|strong)>)?\s*(.*?)</p>',
            content_part,
            re.DOTALL | re.IGNORECASE,
        ))
        if len(opt_matches) == 4:
            options = [om.group(2).strip() for om in opt_matches]
            prompt = content_part[: opt_matches[0].start()].strip()
            q_type = "mcq"
        else:
            options = []
            prompt = content_part.strip()
            q_type = "essay"

        prompt = re.sub(
            r'^(?:<(?:p|div|h\d)[^>]*>\s*)?(?:<(?:b|strong)>)?\s*(?:Câu|Bài)\s*\d+[\s:.]*(?:</(?:b|strong)>)?',
            '',
            prompt,
            flags=re.IGNORECASE,
        ).strip()
        imgs = extract_img_urls(block, base_url)

        # Detect correct choice from solution or text
        correct_choice = None
        ans_match = re.search(r'(?:Chọn|Đáp án|Đáp án đúng là)\s*:?\s*([A-D])\b', solution_part, re.IGNORECASE)
        if not ans_match:
            ans_match = re.search(r'(?:Chọn|Đáp án|Đáp án đúng là)\s*:?\s*([A-D])\b', block, re.IGNORECASE)
        if ans_match:
            correct_choice = ord(ans_match.group(1).upper()) - ord("A")

        needs_review = (q_type == "mcq" and correct_choice is None)
        warnings = []
        if needs_review:
            warnings.append("Chưa xác định chắc chắn đáp án đúng từ lời giải chung.")

        return RawExtractedQuestion(
            prompt_html=prompt,
            options_html=options,
            correct_choice=correct_choice,
            solution_html=solution_part.strip(),
            question_type=q_type,
            image_urls=imgs,
            title=f"Câu {idx}",
            raw_source_snippet=block[:300],
            needs_review=needs_review,
            warnings=warnings,
            metadata={
                "source_url": base_url,
                "source_section": "Generic",
                "source_question_number": f"Câu {idx}",
                "dom_locator": f"generic-q{idx}",
                "extraction_confidence": 0.85 if correct_choice is not None else 0.60,
            },
        )


class LoigiaihayAdapter(BaseSiteAdapter):
    """Dedicated adapter for loigiaihay.com multi-layout educational solutions and exams."""

    @property
    def name(self) -> str:
        return "Lời Giải Hay (loigiaihay.com)"

    @property
    def supported_domains(self) -> list[str]:
        return ["loigiaihay.com"]

    def can_handle(self, url: str) -> bool:
        """Strict domain check: accepts loigiaihay.com and subdomains, rejects lookalike hostnames."""
        try:
            parsed = urllib.parse.urlparse(url.strip())
            netloc = parsed.netloc.lower()
            if ":" in netloc:
                netloc = netloc.split(":")[0]
            if netloc == "loigiaihay.com" or netloc.endswith(".loigiaihay.com"):
                return True
        except Exception:
            pass
        return False

    def extract_questions(self, html: str, base_url: str) -> list[RawExtractedQuestion]:
        if not html or not html.strip():
            return []

        # Layout detection heuristic:
        # 1. Multi-part Exam Paper Layout
        if "exam-part-title" in html or ("PHẦN I" in html and "PHẦN II" in html):
            extractor = ExamPaperExtractor()
            return extractor.extract(html, base_url)

        # 2. SBT Exercise Layout (sub-question-N or content-box-unit with 36.1, 36.2...)
        if "sub-question-" in html or "content-box-unit" in html or "question-title-idx-" in html:
            extractor = SBTExerciseExtractor()
            return extractor.extract(html, base_url)

        # 3. Fallback to generic extractor
        fallback = GenericLoigiaihayExtractor()
        return fallback.extract(html, base_url)
