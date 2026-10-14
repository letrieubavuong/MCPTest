"""Deduplication engine for MCPTest.

Provides multi-scope scanning (in .tex files and in SQLite database),
3-level matching (exact normalized, MCQ permutation, advisory similarity),
asset fingerprinting, safe transaction-backed resolution, and clean report/TeX export.
"""
from dataclasses import dataclass, field
import hashlib
import json
import csv
from pathlib import Path
import re
import unicodedata
from typing import Any, Callable

from latex_question_studio.domain.question import Question
from latex_question_studio.parsing.latex import parse_questions, ParsedQuestion


@dataclass
class DuplicateItem:
    id: str
    source: str
    normalized_source: str
    question_type: str
    solution: str = ""
    options: list[dict] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    created_at: str = ""
    source_location: str = ""
    usage_count: int = 0
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "question_type": self.question_type,
            "solution": self.solution,
            "options": self.options,
            "assets": self.assets,
            "created_at": self.created_at,
            "source_location": self.source_location,
            "usage_count": self.usage_count,
            "references": self.references,
        }


@dataclass
class DuplicateGroup:
    group_id: str
    match_level: str  # 'exact', 'permutation', 'similarity'
    confidence: float
    match_reason: str
    items: list[DuplicateItem]
    primary_id: str
    selected_to_delete: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "match_level": self.match_level,
            "confidence": self.confidence,
            "match_reason": self.match_reason,
            "primary_id": self.primary_id,
            "selected_to_delete": list(self.selected_to_delete),
            "items": [item.to_dict() for item in self.items],
        }


def normalize_latex(source: str) -> str:
    """Safe normalization of LaTeX source.
    
    Preserves math semantics, numbers, signs, exponents, TikZ, and graphic inclusion,
    while stripping comments, normalizing diacritics, and collapsing insignificant whitespace.
    """
    if not source:
        return ""
    text = unicodedata.normalize("NFC", source.strip())

    # Strip line comments (% not preceded by backslash)
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"(?<!\\)%.*$", "", line)
        if cleaned.strip():
            lines.append(cleaned.strip())
    text = " ".join(lines)

    # Collapse all whitespace sequences into a single space
    text = re.sub(r"\s+", " ", text)

    # Normalize argument braces for macros: }\s*{ -> }{
    text = re.sub(r"\}\s*\{", "}{", text)
    # Normalize macro names followed by brace: \choice { -> \choice{
    text = re.sub(r"(\\[a-zA-Z@]+)\s*\{", r"\1{", text)
    # Normalize spaces immediately inside braces: { foo } -> {foo}
    text = re.sub(r"\{\s+", "{", text)
    text = re.sub(r"\s+\}", "}", text)
    # Normalize whitespace before \end and after \begin
    text = re.sub(r"\s*(\\end\{)", r"\1", text)
    text = re.sub(r"(\\begin\{[^}]+\})\s+", r"\1 ", text)
    return text.strip()


def extract_prompt_and_options(source: str, question_type: str = "unknown") -> tuple[str, list[dict], str]:
    """Splits a question into prompt body, options, and solution."""
    parsed_list = parse_questions(source)
    if not parsed_list:
        return source.strip(), [], ""
    parsed = parsed_list[0]
    options = []
    if isinstance(parsed.answer, dict) and "options" in parsed.answer:
        for opt in parsed.answer["options"]:
            clean_text = re.sub(r"\\True\b", "", opt.get("source", "")).strip()
            options.append({
                "text": clean_text,
                "source": opt.get("source", ""),
                "correct": opt.get("correct", False),
            })
    # Extract prompt by stripping options and solution from raw source
    prompt = parsed.source
    if parsed.solution:
        prompt = re.sub(r"\\(?:loigiai|hdan)\s*\{[\s\S]*\}", "", prompt)
    if options:
        prompt = re.sub(r"\\(?:choice|choiceTF|choiceTFt)\s*(?:\[[^\]]*\])?\s*\{[\s\S]*$", "", prompt)
    prompt = re.sub(r"\\begin\{(?:ex|ex\*|vidu|vidu*)\}", "", prompt)
    prompt = re.sub(r"\\end\{(?:ex|ex\*|vidu|vidu*)\}", "", prompt)
    return prompt.strip(), options, parsed.solution.strip()


def extract_assets(source: str) -> list[str]:
    """Finds all \\includegraphics references in source."""
    matches = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", source)
    return [m.strip().replace("\\", "/") for m in matches]


def extract_numbers(text: str) -> list[str]:
    """Extracts numeric constants for equivalence checking."""
    return re.findall(r"(?<![a-zA-Z\\])[+-]?(?:\d+(?:[.,]\d+)?|\d+/\d+)", text)


def compute_token_similarity(prompt1: str, prompt2: str) -> float:
    """Jaccard similarity on tokens outside commands."""
    tokens1 = set(re.findall(r"[a-zA-Z0-9_\u00C0-\u1EF9]+", prompt1.lower()))
    tokens2 = set(re.findall(r"[a-zA-Z0-9_\u00C0-\u1EF9]+", prompt2.lower()))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return intersection / union if union > 0 else 0.0


class DeduplicationService:
    def __init__(self, services):
        self.services = services

    def scan_files(
        self,
        file_paths: list[Path | str],
        cancelled: Callable[[], bool] = lambda: False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[DuplicateGroup]:
        """Scans one or more .tex files for duplicate questions."""
        items: list[DuplicateItem] = []
        total_files = len(file_paths)

        for f_idx, path_val in enumerate(file_paths):
            if cancelled():
                return []
            path = Path(path_val)
            if not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8-sig")
            except Exception:
                continue

            parsed_list = parse_questions(content)
            for q_idx, q in enumerate(parsed_list):
                raw_src = q.source.strip()
                if not raw_src:
                    continue
                norm_src = normalize_latex(raw_src)
                q_type = q.question_type
                options = []
                if isinstance(q.answer, dict) and "options" in q.answer:
                    for opt in q.answer["options"]:
                        clean_text = re.sub(r"\\True\b", "", opt.get("source", "")).strip()
                        options.append({
                            "text": clean_text,
                            "source": opt.get("source", ""),
                            "correct": opt.get("correct", False),
                        })
                solution = q.solution
                assets = q.assets if hasattr(q, "assets") and q.assets else extract_assets(raw_src)

                item_id = f"{path.name}::q{q_idx + 1}"
                line_no = content.count("\n", 0, q.start) + 1
                items.append(
                    DuplicateItem(
                        id=item_id,
                        source=raw_src,
                        normalized_source=norm_src,
                        question_type=q_type,
                        solution=solution,
                        options=options,
                        assets=assets,
                        source_location=f"{path.name} (dòng {line_no})",
                    )
                )

            if progress_callback:
                progress_callback(f_idx + 1, total_files, f"Đã quét file {path.name}")

        return self._cluster_duplicates(items, cancelled)

    def scan_database(
        self,
        filters: dict[str, Any] | None = None,
        cancelled: Callable[[], bool] = lambda: False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[DuplicateGroup]:
        """Scans questions in SQLite database for duplicates."""
        filters = filters or {}
        query = "SELECT q.id, q.latex_source, q.question_type, q.solution, q.created_at FROM questions q"
        params = []
        where_clauses = []

        if filters.get("question_type"):
            where_clauses.append("q.question_type = ?")
            params.append(filters["question_type"])

        if filters.get("cognitive_level"):
            where_clauses.append("q.cognitive_level = ?")
            params.append(filters["cognitive_level"])

        if filters.get("query"):
            where_clauses.append("q.latex_source LIKE ?")
            params.append(f"%{filters['query']}%")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY q.created_at ASC, q.id ASC"

        with self.services.database.connect() as conn:
            rows = conn.execute(query, params).fetchall()

        total = len(rows)
        items: list[DuplicateItem] = []

        for idx, row in enumerate(rows):
            if cancelled():
                return []
            q_id = row["id"]
            src = row["latex_source"]
            q_type = row["question_type"]
            solution = row["solution"] or ""
            created_at = row["created_at"] or ""

            norm_src = normalize_latex(src)
            _, options, extracted_sol = extract_prompt_and_options(src, q_type)
            if not solution and extracted_sol:
                solution = extracted_sol
            assets = extract_assets(src)

            # Check references in lessons/exams
            refs = self._check_question_references(q_id)

            items.append(
                DuplicateItem(
                    id=q_id,
                    source=src,
                    normalized_source=norm_src,
                    question_type=q_type,
                    solution=solution,
                    options=options,
                    assets=assets,
                    created_at=created_at,
                    source_location="CSDL",
                    usage_count=len(refs),
                    references=refs,
                )
            )

            if progress_callback and (idx % 100 == 0 or idx == total - 1):
                progress_callback(idx + 1, total, f"Đang nạp câu hỏi {idx + 1}/{total}...")

        return self._cluster_duplicates(items, cancelled)

    def _check_question_references(self, question_id: str) -> list[str]:
        """Finds referencing lessons or exams for a given question ID."""
        refs = []
        with self.services.database.connect() as conn:
            # 1. Check lesson_file_exercises table
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "lesson_file_exercises" in tables:
                lfe = conn.execute(
                    "SELECT f.title, l.title as lesson_title FROM lesson_file_exercises e "
                    "JOIN lesson_files f ON f.id=e.file_id "
                    "JOIN lessons l ON l.id=f.lesson_id WHERE e.question_id=?",
                    (question_id,),
                ).fetchall()
                for r in lfe:
                    refs.append(f"Bài giảng: {r['lesson_title']} / {r['title']}")

            # 2. Check lessons table document_json
            if "lessons" in tables:
                lessons = conn.execute(
                    "SELECT title FROM lessons WHERE document_json LIKE ?",
                    (f"%{question_id}%",),
                ).fetchall()
                for l in lessons:
                    name = f"Bài giảng: {l['title']}"
                    if name not in refs:
                        refs.append(name)
        return refs

    def _cluster_duplicates(
        self,
        items: list[DuplicateItem],
        cancelled: Callable[[], bool] = lambda: False,
    ) -> list[DuplicateGroup]:
        """Clustering engine applying 3-level matching."""
        if not items:
            return []

        groups: list[DuplicateGroup] = []
        visited: set[str] = set()

        # Step 1: Exact Normalized Matching via Hash Table O(N)
        hash_map: dict[str, list[DuplicateItem]] = {}
        for item in items:
            key = hashlib.sha256(item.normalized_source.encode("utf-8")).hexdigest()
            # If assets exist, incorporate asset fingerprints
            if item.assets:
                asset_key = "|".join(sorted(item.assets))
                key = f"{key}:{asset_key}"
            hash_map.setdefault(key, []).append(item)

        for key, bucket in hash_map.items():
            if len(bucket) > 1:
                for it in bucket:
                    visited.add(it.id)
                # Primary is the oldest or first item
                primary = bucket[0]
                groups.append(
                    DuplicateGroup(
                        group_id=f"exact_{key[:12]}",
                        match_level="exact",
                        confidence=1.0,
                        match_reason="Nội dung mã nguồn LaTeX chuẩn hóa trùng khớp 100%.",
                        items=bucket,
                        primary_id=primary.id,
                        selected_to_delete=set(),  # NO auto delete!
                    )
                )

        remaining = [it for it in items if it.id not in visited]

        # Step 2: MCQ Choice Permutation Matching
        # Only for mcq questions with options
        mcq_buckets: dict[str, list[DuplicateItem]] = {}
        for item in remaining:
            if item.question_type == "mcq" and item.options and len(item.options) >= 2:
                prompt, opts, _ = extract_prompt_and_options(item.source, "mcq")
                norm_prompt = normalize_latex(prompt)
                # Build canonical set of choices with their correctness
                # tuple: (normalized_text, is_correct)
                canonical_choices = frozenset(
                    (normalize_latex(o.get("text", "")), bool(o.get("correct", False)))
                    for o in opts
                )
                perm_key = f"{norm_prompt}###{hash(canonical_choices)}"
                mcq_buckets.setdefault(perm_key, []).append(item)

        for p_key, bucket in mcq_buckets.items():
            if len(bucket) > 1:
                for it in bucket:
                    visited.add(it.id)
                primary = bucket[0]
                groups.append(
                    DuplicateGroup(
                        group_id=f"perm_{hashlib.sha256(p_key.encode('utf-8')).hexdigest()[:12]}",
                        match_level="permutation",
                        confidence=0.95,
                        match_reason="Thân câu hỏi và tập 4 phương án trùng khớp (thứ tự các phương án bị xáo trộn).",
                        items=bucket,
                        primary_id=primary.id,
                        selected_to_delete=set(),
                    )
                )

        remaining = [it for it in remaining if it.id not in visited]

        # Step 3: Advisory Near-Duplicate Similarity (O(N^2) over remaining unclustered)
        # Limit candidate search to avoid excessive CPU on huge sets
        max_similarity_candidates = min(len(remaining), 1000)
        advisory_pool = remaining[:max_similarity_candidates]

        for i in range(len(advisory_pool)):
            if cancelled():
                return groups
            it_a = advisory_pool[i]
            if it_a.id in visited:
                continue

            sim_group = [it_a]
            prompt_a, _, _ = extract_prompt_and_options(it_a.source, it_a.question_type)
            norm_a = normalize_latex(prompt_a)
            nums_a = extract_numbers(norm_a)

            for j in range(i + 1, len(advisory_pool)):
                it_b = advisory_pool[j]
                if it_b.id in visited:
                    continue
                # If question types differ, do not treat as similar
                if it_a.question_type != it_b.question_type and it_a.question_type != "unknown" and it_b.question_type != "unknown":
                    continue

                prompt_b, _, _ = extract_prompt_and_options(it_b.source, it_b.question_type)
                norm_b = normalize_latex(prompt_b)
                nums_b = extract_numbers(norm_b)

                sim = compute_token_similarity(norm_a, norm_b)
                if sim >= 0.82:
                    # Guardrail: check if numbers or signs differ
                    diff_reason = []
                    if nums_a != nums_b:
                        diff_reason.append(f"Khác số liệu ({nums_a} vs {nums_b})")
                    if it_a.assets != it_b.assets:
                        diff_reason.append("Khác tệp hình ảnh đính kèm")

                    match_msg = f"Độ tương đồng cấu trúc {sim*100:.1f}% (Gợi ý xem xét thủ công)."
                    if diff_reason:
                        match_msg += f" Chú ý: {'; '.join(diff_reason)}."

                    sim_group.append(it_b)
                    visited.add(it_b.id)

            if len(sim_group) > 1:
                visited.add(it_a.id)
                groups.append(
                    DuplicateGroup(
                        group_id=f"sim_{it_a.id[:8]}",
                        match_level="similarity",
                        confidence=round(sim, 2),
                        match_reason=match_msg,
                        items=sim_group,
                        primary_id=it_a.id,
                        selected_to_delete=set(),
                    )
                )

        return groups

    def delete_selected(
        self,
        selected_ids: list[str],
        force: bool = False,
    ) -> tuple[int, list[str]]:
        """Deletes selected question IDs safely with FK protection in SQLite.
        
        Returns:
            (deleted_count, error_messages)
        """
        if not selected_ids:
            return 0, []

        deleted_count = 0
        errors: list[str] = []

        with self.services.database.transaction() as conn:
            for q_id in selected_ids:
                # Check FK constraints
                refs = self._check_question_references(q_id)
                if refs and not force:
                    errors.append(
                        f"Không thể xóa câu [{q_id[:8]}]: Đang được sử dụng trong {len(refs)} tài liệu ({', '.join(refs[:2])})."
                    )
                    continue

                try:
                    conn.execute("DELETE FROM questions WHERE id = ?", (q_id,))
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"Lỗi khi xóa câu [{q_id[:8]}]: {str(e)}")

        return deleted_count, errors

    def merge_metadata(self, primary_id: str, secondary_ids: list[str]) -> bool:
        """Merges metadata and taxonomy tags from duplicate copies into primary question."""
        if not primary_id or not secondary_ids:
            return False

        with self.services.database.transaction() as conn:
            # Fetch primary metadata
            p_row = conn.execute("SELECT data_json FROM question_metadata WHERE question_id=?", (primary_id,)).fetchone()
            p_meta = json.loads(p_row[0]) if p_row and p_row[0] else {}

            # Merge from secondaries
            merged_tags = set(p_meta.get("tags", []))
            notes = p_meta.get("notes", "")

            for s_id in secondary_ids:
                s_row = conn.execute("SELECT data_json FROM question_metadata WHERE question_id=?", (s_id,)).fetchone()
                if s_row and s_row[0]:
                    s_meta = json.loads(s_row[0])
                    for t in s_meta.get("tags", []):
                        merged_tags.add(t)
                    if s_meta.get("notes"):
                        notes += f"\n[Gộp từ {s_id[:8]}]: {s_meta['notes']}"

                # Copy taxonomy associations
                tax_rows = conn.execute("SELECT taxonomy_id FROM question_taxonomy WHERE question_id=?", (s_id,)).fetchall()
                for tax in tax_rows:
                    conn.execute(
                        "INSERT OR IGNORE INTO question_taxonomy (question_id, taxonomy_id) VALUES (?, ?)",
                        (primary_id, tax[0]),
                    )

            p_meta["tags"] = list(merged_tags)
            if notes.strip():
                p_meta["notes"] = notes.strip()

            conn.execute(
                "INSERT OR REPLACE INTO question_metadata (question_id, data_json) VALUES (?, ?)",
                (primary_id, json.dumps(p_meta, ensure_ascii=False)),
            )

        return True

    def export_report(
        self,
        groups: list[DuplicateGroup],
        output_path: Path | str,
        report_format: str = "json",
    ) -> Path:
        """Exports duplicate detection report to JSON or CSV."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

        if report_format == "csv":
            with out.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Group ID", "Cấp trùng lặp", "Độ tin cậy", "Lý do",
                    "Số câu trùng", "ID câu giữ lại", "Danh sách ID trong nhóm"
                ])
                for g in groups:
                    item_ids = "; ".join(it.id for it in g.items)
                    writer.writerow([
                        g.group_id, g.match_level, f"{g.confidence:.2f}",
                        g.match_reason, len(g.items), g.primary_id, item_ids
                    ])
        else:
            data = [g.to_dict() for g in groups]
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        return out

    def export_clean_tex(
        self,
        source_file: Path | str,
        items_to_keep: set[str],
        output_file: Path | str,
    ) -> Path:
        """Exports clean .tex file keeping only non-deleted questions."""
        src_path = Path(source_file)
        out_path = Path(output_file).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        content = src_path.read_text(encoding="utf-8-sig")
        parsed_list = parse_questions(content)

        clean_blocks = []
        for idx, q in enumerate(parsed_list):
            item_id = f"{src_path.name}::q{idx + 1}"
            if item_id in items_to_keep:
                raw = q.source.strip()
                if raw:
                    clean_blocks.append(raw)

        out_content = "\n\n".join(clean_blocks) + "\n"
        out_path.write_text(out_content, encoding="utf-8")
        return out_path
