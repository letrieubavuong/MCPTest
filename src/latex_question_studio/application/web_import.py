"""Web Import & Staging application service for Phase L."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any
import urllib.parse
import uuid
import zipfile

from latex_question_studio.application.assets import AssetStore
from latex_question_studio.application.services import Services
from latex_question_studio.preview.compiler import Compiler, BUILTIN_PREAMBLE
from latex_question_studio.scraping.adapters import get_adapter_for_url
from latex_question_studio.scraping.adapters.base import BaseSiteAdapter, RawExtractedQuestion
from latex_question_studio.scraping.fetcher import SafeFetcher
from latex_question_studio.scraping.html_to_latex import html_to_latex


@dataclass
class QuestionDraft:
    """Represents an extracted question in the staging and review pipeline."""
    id: str
    source_url: str
    title: str
    question_type: str  # "mcq", "true_false", "short_answer", "essay"
    prompt_latex: str
    options_latex: list[str] = field(default_factory=list)
    correct_choice: int | None = None  # 0..3 for mcq
    choice_tf_answers: list[bool] | None = None  # For true_false: [True, False, ...]
    short_answer_key: str = ""
    solution_latex: str = ""
    image_urls: list[str] = field(default_factory=list)
    local_assets: list[dict[str, Any]] = field(default_factory=list)
    status: str = "needs_review"  # "needs_review", "verified", "rejected"
    review_notes: str = ""
    warnings: list[str] = field(default_factory=list)
    created_at: str = ""

    def validate_and_update_warnings(self) -> None:
        """Validates draft fields and populates warnings."""
        warns = []
        if not self.prompt_latex.strip():
            warns.append("Nội dung đề bài còn rỗng.")
        if self.question_type == "mcq":
            if len(self.options_latex) != 4:
                warns.append(f"Số lượng phương án ({len(self.options_latex)}) khác 4.")
            if self.correct_choice is None:
                warns.append("Chưa chỉ định đáp án đúng cho câu trắc nghiệm.")
            elif self.correct_choice not in (0, 1, 2, 3):
                warns.append(f"Chỉ số đáp án đúng ({self.correct_choice}) không hợp lệ (cần 0..3).")
        elif self.question_type == "true_false":
            if len(self.options_latex) != 4:
                warns.append(f"Số lượng mệnh đề Đúng/Sai ({len(self.options_latex)}) khác 4.")
            if not self.choice_tf_answers or len(self.choice_tf_answers) != 4:
                warns.append("Chưa đánh dấu đầy đủ Đúng/Sai cho 4 ý a, b, c, d.")
        elif self.question_type == "short_answer":
            if not self.short_answer_key.strip():
                warns.append("Chưa có kết quả / đáp án ngắn.")
        self.warnings = warns

    def to_ex_test_latex(self) -> str:
        """Serializes draft into an ex_test compatible LaTeX snippet."""
        lines = ["\\begin{ex}", self.prompt_latex.strip()]

        if self.question_type == "mcq" and self.options_latex:
            opts_formatted = []
            for i, opt in enumerate(self.options_latex):
                clean_opt = opt.strip()
                if self.correct_choice == i:
                    opts_formatted.append(f"\\True {clean_opt}")
                else:
                    opts_formatted.append(clean_opt)
            # Pad if fewer than 4
            while len(opts_formatted) < 4:
                opts_formatted.append("")
            lines.append(
                f"\\choice\n{{{opts_formatted[0]}}}\n{{{opts_formatted[1]}}}\n{{{opts_formatted[2]}}}\n{{{opts_formatted[3]}}}"
            )
        elif self.question_type == "true_false" and self.options_latex:
            opts_formatted = []
            tf_ans = self.choice_tf_answers or [False] * len(self.options_latex)
            for i, opt in enumerate(self.options_latex):
                clean_opt = opt.strip()
                is_true = tf_ans[i] if i < len(tf_ans) else False
                if is_true:
                    opts_formatted.append(f"\\True {clean_opt}")
                else:
                    opts_formatted.append(clean_opt)
            while len(opts_formatted) < 4:
                opts_formatted.append("")
            lines.append(
                f"\\choiceTF\n{{{opts_formatted[0]}}}\n{{{opts_formatted[1]}}}\n{{{opts_formatted[2]}}}\n{{{opts_formatted[3]}}}"
            )
        elif self.question_type == "short_answer":
            if self.short_answer_key:
                lines.append(f"\\shortans{{{self.short_answer_key.strip()}}}")

        if self.solution_latex.strip():
            lines.append(f"\\loigiai{{{self.solution_latex.strip()}}}")

        lines.append("\\end{ex}")
        return "\n".join(lines)


class WebScraperService:
    """Service handling web question scraping, HTML conversion, asset staging, moderation and export."""

    def __init__(self, fetcher: SafeFetcher | None = None):
        self.fetcher = fetcher or SafeFetcher()

    def fetch_and_extract(
        self,
        url: str,
        asset_store: AssetStore | None = None,
        check_robots: bool = True
    ) -> tuple[bool, str, list[QuestionDraft]]:
        """Safely fetches a webpage and extracts question drafts."""
        res = self.fetcher.fetch(url, check_robots=check_robots)
        if not res.ok:
            return False, res.error, []

        html_text = res.content.decode("utf-8", errors="replace")
        adapter = get_adapter_for_url(res.final_url)
        raw_questions = adapter.extract_questions(html_text, res.final_url)

        if not raw_questions:
            return True, f"Trang web đã được tải thành công nhưng bộ phân tích ({adapter.name}) không tìm thấy câu hỏi nào.", []

        drafts = self._convert_raw_questions(raw_questions, res.final_url, asset_store)
        return True, f"Thu thập thành công {len(drafts)} câu hỏi từ {adapter.name}.", drafts

    def extract_from_html(
        self,
        html_text: str,
        base_url: str = "http://pasted.local",
        asset_store: AssetStore | None = None
    ) -> list[QuestionDraft]:
        """Extracts question drafts from raw pasted HTML."""
        adapter = get_adapter_for_url(base_url)
        raw_questions = adapter.extract_questions(html_text, base_url)
        return self._convert_raw_questions(raw_questions, base_url, asset_store)

    def _convert_raw_questions(
        self,
        raw_questions: list[RawExtractedQuestion],
        base_url: str,
        asset_store: AssetStore | None
    ) -> list[QuestionDraft]:
        drafts: list[QuestionDraft] = []
        batch_id = f"web-import-{uuid.uuid4().hex[:8]}"

        for raw in raw_questions:
            prompt_latex, prompt_imgs = html_to_latex(raw.prompt_html, base_url)
            sol_latex, sol_imgs = html_to_latex(raw.solution_html, base_url)

            options_latex = []
            for opt_h in raw.options_html:
                opt_ltx, opt_imgs = html_to_latex(opt_h, base_url)
                options_latex.append(opt_ltx)
                prompt_imgs.extend(opt_imgs)

            all_img_urls = list(dict.fromkeys(raw.image_urls + prompt_imgs + sol_imgs))
            staged_assets = []

            # Safely fetch and stage assets if asset_store is provided
            if asset_store and all_img_urls:
                for img_url in all_img_urls:
                    try:
                        img_res = self.fetcher.fetch(img_url, check_robots=False)
                        if img_res.ok and img_res.content:
                            parsed = urllib.parse.urlparse(img_url)
                            suffix = Path(parsed.path).suffix.lower()
                            if suffix not in (".png", ".jpg", ".jpeg", ".pdf"):
                                suffix = ".png"
                            staged = asset_store.stage_bytes(img_res.content, suffix, batch_id)
                            staged["original_url"] = img_url
                            staged_assets.append(staged)
                            # Replace placeholder in LaTeX text
                            rel_posix = staged["relative_path"]
                            img_macro = f"\\includegraphics[max width=0.85\\linewidth]{{{rel_posix}}}"
                            prompt_latex = prompt_latex.replace(f"[IMG:{img_url}]", img_macro)
                            sol_latex = sol_latex.replace(f"[IMG:{img_url}]", img_macro)
                    except Exception:
                        pass

            # Clean any remaining placeholder tokens
            prompt_latex = re.sub(r'\[IMG:[^\]]+\]', '', prompt_latex).strip()
            sol_latex = re.sub(r'\[IMG:[^\]]+\]', '', sol_latex).strip()

            draft = QuestionDraft(
                id=str(uuid.uuid4()),
                source_url=base_url,
                title=raw.title or "Câu hỏi thu thập",
                question_type=raw.question_type,
                prompt_latex=prompt_latex,
                options_latex=options_latex,
                correct_choice=raw.correct_choice,
                choice_tf_answers=raw.choice_tf_answers,
                short_answer_key=raw.short_answer_text,
                solution_latex=sol_latex,
                image_urls=all_img_urls,
                local_assets=staged_assets,
                status="needs_review",  # MANDATORY: never auto-verify
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            draft.validate_and_update_warnings()
            drafts.append(draft)

        return drafts

    def commit_drafts_to_db(
        self,
        drafts: list[QuestionDraft],
        services: Services,
        asset_store: AssetStore
    ) -> dict[str, Any]:
        """Commits ONLY verified drafts to the database repository."""
        # Non-negotiable: Never import unmoderated / unreviewed content!
        verified_drafts = [d for d in drafts if d.status == "verified"]
        if not verified_drafts:
            return {
                "ok": False,
                "committed_count": 0,
                "skipped_count": len(drafts),
                "message": "Không có câu hỏi nào ở trạng thái 'Đã kiểm duyệt' (Verified) để lưu vào CSDL."
            }

        committed_ids = []
        errors = []

        for draft in verified_drafts:
            try:
                # Promote staged assets first
                for asset_info in draft.local_assets:
                    try:
                        asset_store.promote(asset_info)
                    except Exception as e:
                        errors.append(f"Không thể lưu hình ảnh {asset_info.get('hash', '')}: {str(e)}")

                # Generate final LaTeX source
                latex_source = draft.to_ex_test_latex()

                # Insert into QuestionRepository
                q = services.questions.create(
                    latex_source=latex_source,
                    question_type=draft.question_type,
                    solution=draft.solution_latex,
                    difficulty_legacy=None,
                    cognitive_level=None
                )
                committed_ids.append(q.id)

                # Record assets in database if present
                if draft.local_assets:
                    with services.database.transaction() as conn:
                        now = datetime.now(timezone.utc).isoformat()
                        for asset_info in draft.local_assets:
                            asset_id = str(uuid.uuid4())
                            rel_p = asset_info["relative_path"]
                            c_hash = asset_info["hash"]
                            b_size = asset_info["bytes"]
                            conn.execute(
                                "INSERT OR IGNORE INTO assets (id, content_hash, relative_path, bytes, created_at) VALUES (?,?,?,?,?)",
                                (asset_id, c_hash, rel_p, b_size, now)
                            )
                            # Link to question
                            conn.execute(
                                "INSERT OR IGNORE INTO question_assets (question_id, asset_id, reference_name) VALUES (?,?,?)",
                                (q.id, asset_id, Path(rel_p).name)
                            )
            except Exception as e:
                errors.append(f"Lỗi nhập câu hỏi '{draft.title}': {str(e)}")

        return {
            "ok": len(committed_ids) > 0,
            "committed_count": len(committed_ids),
            "skipped_count": len(drafts) - len(committed_ids),
            "committed_ids": committed_ids,
            "errors": errors,
            "message": f"Đã nhập thành công {len(committed_ids)} câu hỏi vào CSDL ngân hàng."
        }

    def export_drafts_to_exam_bundle(
        self,
        drafts: list[QuestionDraft],
        exam_title: str,
        output_dir: Path,
        compiler: Compiler,
        author_name: str = "Tổ Toán - MCPTest"
    ) -> dict[str, Any]:
        """Exports verified drafts into a Phase K compliant exam structure and verifies compilation.
        
        Mandatory non-negotiable: If compilation fails or PDF is not created, MUST NOT report success!
        """
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        verified = [d for d in drafts if d.status == "verified"]
        if not verified:
            return {
                "ok": False,
                "tex_path": None,
                "pdf_path": None,
                "zip_path": None,
                "error": "Không có câu hỏi nào được xác nhận (Verified) để xuất đề thi."
            }

        # Segregate by question type per Phase K structure
        mcq_drafts = [d for d in verified if d.question_type == "mcq"]
        tf_drafts = [d for d in verified if d.question_type == "true_false"]
        short_drafts = [d for d in verified if d.question_type == "short_answer"]
        essay_drafts = [d for d in verified if d.question_type == "essay"]

        # Build Phase K exam body
        body_lines = [
            f"\\TieudeT{{{exam_title.upper()}}}",
            "",
        ]

        if mcq_drafts:
            body_lines.append("\\PhanI")
            body_lines.append("\\begin{cauhoiTN}{De01}")
            for d in mcq_drafts:
                body_lines.append(d.to_ex_test_latex())
                body_lines.append("")
            body_lines.append("\\end{cauhoiTN}")
            body_lines.append("")

        if tf_drafts:
            body_lines.append("\\PhanII")
            body_lines.append("\\begin{cauhoiDS}{De01}")
            for d in tf_drafts:
                body_lines.append(d.to_ex_test_latex())
                body_lines.append("")
            body_lines.append("\\end{cauhoiDS}")
            body_lines.append("")

        if short_drafts:
            body_lines.append("\\PhanIII")
            body_lines.append("\\begin{cauhoiTLN}{De01}")
            for d in short_drafts:
                body_lines.append(d.to_ex_test_latex())
                body_lines.append("")
            body_lines.append("\\end{cauhoiTLN}")
            body_lines.append("")

        if essay_drafts:
            body_lines.append("\\PhanTL")
            body_lines.append("\\begin{cauhoiTL}{De01}")
            for d in essay_drafts:
                body_lines.append(d.to_ex_test_latex())
                body_lines.append("")
            body_lines.append("\\end{cauhoiTL}")
            body_lines.append("")

        exam_body = "\n".join(body_lines)

        # Full LaTeX document
        full_tex = f"{BUILTIN_PREAMBLE}\n\\begin{{document}}\n{exam_body}\n\\end{{document}}\n"

        slug = re.sub(r'[^a-zA-Z0-9_\-]+', '_', exam_title.lower()).strip('_') or 'de_thi_web'
        tex_file = output_dir / f"{slug}.tex"
        tex_file.write_text(full_tex, encoding="utf-8")

        # Compile with pdfLaTeX to verify
        # Map any assets needed for compilation
        assets_map = {}
        for d in verified:
            for ast in d.local_assets:
                rel = ast.get("relative_path", "")
                stg = ast.get("staging_path", "")
                if rel and stg and Path(stg).is_file():
                    assets_map[rel] = stg

        compile_res = compiler.compile(full_tex, assets=assets_map)

        if not compile_res.ok or not compile_res.pdf or not compile_res.pdf.is_file():
            # Compiling failed! Strictly do not report export success
            return {
                "ok": False,
                "tex_path": str(tex_file),
                "pdf_path": None,
                "zip_path": None,
                "error": f"Biên dịch pdfLaTeX thất bại. Không tạo được PDF: {compile_res.log[:400]}",
                "compile_log": compile_res.log
            }

        # Copy generated PDF to target output_dir
        final_pdf = output_dir / f"{slug}.pdf"
        shutil.copy2(compile_res.pdf, final_pdf)

        # Build portable ZIP bundle
        zip_file = output_dir / f"{slug}_bundle.zip"
        with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tex_file, arcname=tex_file.name)
            zf.write(final_pdf, arcname=final_pdf.name)
            for rel, path in assets_map.items():
                if Path(path).is_file():
                    zf.write(path, arcname=rel)

        return {
            "ok": True,
            "tex_path": str(tex_file),
            "pdf_path": str(final_pdf),
            "zip_path": str(zip_file),
            "verified_count": len(verified),
            "compile_log": compile_res.log,
            "message": f"Xuất đề thi và biên dịch PDF thành công! Đã tạo file: {final_pdf.name} và gói {zip_file.name}."
        }
