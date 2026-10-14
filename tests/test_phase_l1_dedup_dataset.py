"""Phase L.1 Deduplication Hardening & Labeled Dataset Test Suite.

Contains:
- Labeled dataset of >= 300 question pairs covering 9 mandatory categories:
  1. Exact verbatim duplicates
  2. Formatting/whitespace/comment differences
  3. MCQ choice permutation with \\True
  4. True/False \\choiceTF permutation (MUST NOT be treated as duplicate/permutation)
  5. Different numbers / signs / powers
  6. Different images / TikZ / assets
  7. Different solutions (\\loigiai)
  8. Near duplicates but different math concepts
  9. Nested \\immini questions
- Precision, recall, and false-positive evaluation across 3 match levels.
- Synthetic scale benchmark (10k items with seed) testing time, peak RAM, and cancel.
"""

from pathlib import Path
import random
import time
import tracemalloc
import pytest

from latex_question_studio.application.dedup import (
    DeduplicationService,
    DuplicateItem,
    DuplicateGroup,
    normalize_latex,
    extract_prompt_and_options,
)


def generate_labeled_dataset_300_pairs() -> list[dict]:
    """Generates >= 300 labeled pairs across all 9 required categories."""
    pairs = []

    # Category 1: Exact verbatim duplicates (35 pairs)
    for i in range(35):
        src_a = f"\\begin{{ex}}\nGiải phương trình $x^{{2}} - {i+1} = 0$.\n\\choice{{$x = {i+1}$}}{{\\True $x = \\pm \\sqrt{{{i+1}}}$}}{{$x = 0$}}{{$x = -{i+1}$}}\n\\loigiai{{Ta có $x = \\pm \\sqrt{{{i+1}}}$.}}\n\\end{{ex}}"
        src_b = src_a
        pairs.append({
            "cat": "exact_verbatim",
            "a": src_a,
            "b": src_b,
            "expected_level": "exact",
            "is_duplicate": True,
        })

    # Category 2: Formatting, comment, whitespace differences (35 pairs)
    for i in range(35):
        src_a = f"\\begin{{ex}}\nTìm tập xác định của hàm số $y = \\sqrt{{x - {i+1}}}$.\n\\choice{{$D = [{i+1}; +\\infty)$}}{{\\True $D = ({i+1}; +\\infty)$}}{{$D = \\mathbb{{R}}$}}{{$D = \\emptyset$}}\n\\end{{ex}}"
        src_b = (
            f"% Đề bài số {i+1}\n"
            f"\\begin{{ex}} % Bắt đầu câu hỏi\n"
            f"  Tìm tập xác định của hàm số   $y = \\sqrt{{x - {i+1}}}$.  % Chú ý căn bậc 2\n"
            f"  \\choice \n"
            f"  {{ $D = [{i+1}; +\\infty)$ }} \n"
            f"  {{ \\True  $D = ({i+1}; +\\infty)$ }} \n"
            f"  {{ $D = \\mathbb{{R}}$ }} \n"
            f"  {{ $D = \\emptyset$ }} \n"
            f"\\end{{ex}}\n"
        )
        pairs.append({
            "cat": "whitespace_comments",
            "a": src_a,
            "b": src_b,
            "expected_level": "exact",
            "is_duplicate": True,
        })

    # Category 3: MCQ choice permutation with \True (35 pairs)
    for i in range(35):
        src_a = f"\\begin{{ex}}\nGiá trị của biểu thức $P = {i+1} + {i+2}$ là:\n\\choice{{A. $1$}}{{B. $2$}}{{\\True C. ${2*i+3}$}}{{D. $0$}}\n\\end{{ex}}"
        src_b = f"\\begin{{ex}}\nGiá trị của biểu thức $P = {i+1} + {i+2}$ là:\n\\choice{{\\True A. ${2*i+3}$}}{{B. $1$}}{{C. $0$}}{{D. $2$}}\n\\end{{ex}}"
        pairs.append({
            "cat": "mcq_permutation",
            "a": src_a,
            "b": src_b,
            "expected_level": "permutation",
            "is_duplicate": True,
        })

    # Category 4: True/False \choiceTF permutation (35 pairs) - MUST NOT BE PERMUTATION DUPLICATE!
    for i in range(35):
        # Shuffling propositions in \choiceTF changes the proposition index (a, b, c, d)
        src_a = f"\\begin{{ex}}\nCho hàm số bậc ba $y = f(x)$. Các mệnh đề sau đúng hay sai?\n\\choiceTF{{\\True Mệnh đề A_{i}}}{{\\True Mệnh đề B_{i}}}{{Mệnh đề C_{i}}}{{Mệnh đề D_{i}}}\n\\end{{ex}}"
        src_b = f"\\begin{{ex}}\nCho hàm số bậc ba $y = f(x)$. Các mệnh đề sau đúng hay sai?\n\\choiceTF{{Mệnh đề D_{i}}}{{\\True Mệnh đề A_{i}}}{{Mệnh đề C_{i}}}{{\\True Mệnh đề B_{i}}}\n\\end{{ex}}"
        pairs.append({
            "cat": "choicetf_permutation_rejected",
            "a": src_a,
            "b": src_b,
            "expected_level": None,  # NEVER duplicate/permutation!
            "is_duplicate": False,
        })

    # Category 5: Different numbers / signs / powers (35 pairs)
    for i in range(35):
        # A: positive 2, B: negative -2
        src_a = f"\\begin{{ex}}\nNghiệm của phương trình $x - {i+1} = 0$ là $x = {i+1}$.\n\\choice{{\\True $x = {i+1}$}}{{$x = -{i+1}$}}{{$x = 0$}}{{$x = 1$}}\n\\end{{ex}}"
        src_b = f"\\begin{{ex}}\nNghiệm của phương trình $x + {i+1} = 0$ là $x = -{i+1}$.\n\\choice{{\\True $x = -{i+1}$}}{{$x = {i+1}$}}{{$x = 0$}}{{$x = 1$}}\n\\end{{ex}}"
        pairs.append({
            "cat": "different_numbers_signs",
            "a": src_a,
            "b": src_b,
            "expected_level": None,  # Must not be classified as exact or permutation!
            "is_duplicate": False,
        })

    # Category 6: Different images / TikZ / assets (35 pairs)
    for i in range(35):
        src_a = f"\\begin{{ex}}\nĐồ thị hình bên biểu diễn hàm số nào?\n\\includegraphics{{figure_{i+1}_a.png}}\n\\choice{{\\True A}}{{B}}{{C}}{{D}}\n\\end{{ex}}"
        src_b = f"\\begin{{ex}}\nĐồ thị hình bên biểu diễn hàm số nào?\n\\includegraphics{{figure_{i+1}_b.png}}\n\\choice{{\\True A}}{{B}}{{C}}{{D}}\n\\end{{ex}}"
        pairs.append({
            "cat": "different_assets",
            "a": src_a,
            "b": src_b,
            "expected_level": None,  # Different assets -> NOT duplicate
            "is_duplicate": False,
        })

    # Category 7: Different solutions (35 pairs)
    for i in range(35):
        base_ex = f"Cho tam giác ABC có độ dài $a = {i+3}$, $b = 4$, $c = 5$."
        src_a = f"\\begin{{ex}}\n{base_ex}\n\\choice{{\\True Đúng}}{{Sai}}{{A}}{{B}}\n\\loigiai{{Cách giải 1: Dùng định lý cosin.}}\n\\end{{ex}}"
        src_b = f"\\begin{{ex}}\n{base_ex}\n\\choice{{\\True Đúng}}{{Sai}}{{A}}{{B}}\n\\loigiai{{Cách giải 2: Dùng công thức Heron tính diện tích.}}\n\\end{{ex}}"
        pairs.append({
            "cat": "different_solution",
            "a": src_a,
            "b": src_b,
            "expected_level": "permutation",
            "is_duplicate": True,
        })

    # Category 8: Near duplicate but different math concepts (35 pairs)
    for i in range(35):
        src_a = f"\\begin{{ex}}\nTìm giá trị lớn nhất (GTLN) của hàm số $y = \\sin({i+1}x)$ trên đoạn $[0; \\pi]$.\n\\choice{{\\True $1$}}{{$0$}}{{$-1$}}{{$2$}}\n\\end{{ex}}"
        src_b = f"\\begin{{ex}}\nTìm giá trị nhỏ nhất (GTNN) của hàm số $y = \\sin({i+1}x)$ trên đoạn $[0; \\pi]$.\n\\choice{{\\True $-1$}}{{$0$}}{{$1$}}{{$-2$}}\n\\end{{ex}}"
        pairs.append({
            "cat": "different_math_concept",
            "a": src_a,
            "b": src_b,
            "expected_level": None,
            "is_duplicate": False,
        })

    # Category 9: Nested \immini questions (30 pairs)
    for i in range(30):
        src_a = f"\\begin{{ex}}\n\\immini{{Cho hình lăng trụ đứng có diện tích đáy $S = {i+2}$. Tính thể tích.}}{{\\includegraphics{{langtru_{i}.png}}}}\n\\choice{{\\True $V = {2*i+4}$}}{{$V = {i+2}$}}{{$V = 1$}}{{$V = 0$}}\n\\end{{ex}}"
        src_b = f"\\begin{{ex}}\n\\immini{{Cho hình lăng trụ đứng có diện tích đáy $S = {i+2}$. Tính thể tích.}}{{\\includegraphics{{langtru_{i}.png}}}}\n\\choice{{$V = {i+2}$}}{{\\True $V = {2*i+4}$}}{{$V = 1$}}{{$V = 0$}}\n\\end{{ex}}"
        pairs.append({
            "cat": "nested_immini",
            "a": src_a,
            "b": src_b,
            "expected_level": "permutation",
            "is_duplicate": True,
        })

    return pairs


def test_labeled_dataset_size_at_least_300():
    """Yêu cầu L3.1: Bộ dữ liệu có nhãn phải có ít nhất 300 cặp."""
    dataset = generate_labeled_dataset_300_pairs()
    assert len(dataset) >= 300
    assert len(dataset) == 310


def test_precision_recall_and_false_positive_rates():
    """Yêu cầu L3.2: Đánh giá độ chính xác, độ bao phủ và tỷ lệ dương tính giả (false-positive)."""
    dataset = generate_labeled_dataset_300_pairs()
    service = DeduplicationService(services=None)

    level1_tp, level1_fp, level1_fn = 0, 0, 0
    level2_tp, level2_fp, level2_fn = 0, 0, 0
    for idx, pair in enumerate(dataset):
        _, opts_a, sol_a = extract_prompt_and_options(pair["a"])
        item_a = DuplicateItem(
            id=f"pair_{idx}_a",
            source=pair["a"],
            normalized_source=normalize_latex(pair["a"]),
            question_type="true_false" if "\\choiceTF" in pair["a"] else "mcq",
            options=opts_a,
            solution=sol_a,
        )
        _, opts_b, sol_b = extract_prompt_and_options(pair["b"])
        item_b = DuplicateItem(
            id=f"pair_{idx}_b",
            source=pair["b"],
            normalized_source=normalize_latex(pair["b"]),
            question_type="true_false" if "\\choiceTF" in pair["b"] else "mcq",
            options=opts_b,
            solution=sol_b,
        )

        groups = service._cluster_duplicates([item_a, item_b])
        matched_level = groups[0].match_level if groups else None

        # Check Level 1 (Exact)
        if pair["expected_level"] == "exact":
            if matched_level == "exact":
                level1_tp += 1
            else:
                level1_fn += 1
        elif matched_level == "exact":
            level1_fp += 1

        # Check Level 2 (MCQ Permutation)
        if pair["expected_level"] == "permutation":
            if matched_level == "permutation":
                level2_tp += 1
            else:
                level2_fn += 1
        elif matched_level == "permutation":
            level2_fp += 1

        # Critical Guardrail: \choiceTF proposition shuffle MUST NEVER be classified as duplicate!
        if pair["cat"] == "choicetf_permutation_rejected":
            assert matched_level != "exact", f"Lỗi nghiêm trọng: \\choiceTF bị nhận nhầm là trùng exact tại cặp #{idx}!"
            assert matched_level != "permutation", f"Lỗi nghiêm trọng: \\choiceTF bị nhận nhầm là permutation tại cặp #{idx}!"

        # Critical Guardrail: Different numbers or signs MUST NEVER be classified as exact or permutation!
        if pair["cat"] == "different_numbers_signs":
            assert matched_level not in ("exact", "permutation"), f"Lỗi: số liệu khác nhau bị nhận nhầm trùng tại cặp #{idx}!"

        # Category 7: Different solutions must be matched with solution divergence note
        if pair["cat"] == "different_solution":
            assert matched_level == "permutation", f"Lỗi: khác lời giải không được nhận diện trùng prompt/options tại cặp #{idx}!"
            assert "Lời giải hai câu khác nhau" in groups[0].match_reason, f"Thiếu cảnh báo khác lời giải tại cặp #{idx}!"

    # Precision & False Positive Rate Assertions
    # Level 1 Precision must be 100% (0 false positives)
    assert level1_fp == 0, f"False positives ở Level 1: {level1_fp}"
    assert level1_tp == 70, f"Level 1 TP mong đợi 70, đạt: {level1_tp}"

    # Level 2 Precision must be 100% (0 false positives)
    # 35 mcq_permutation + 35 different_solution + 30 nested_immini = 100
    assert level2_fp == 0, f"False positives ở Level 2: {level2_fp}"
    assert level2_tp == 100, f"Level 2 TP mong đợi 100, đạt: {level2_tp}"


def test_scale_benchmark_10000_questions_and_peak_ram():
    """Yêu cầu L3.3: Quét 10,000 câu tổng hợp có seed, đo thời gian, RAM peak và khả năng cancel."""
    rng = random.Random(20261014)
    service = DeduplicationService(services=None)

    # Sinh 10,000 câu hỏi với ~5% trùng lặp rải rác
    items: list[DuplicateItem] = []
    base_templates = [
        "Tính đạo hàm của hàm số $y = x^{{{p}}} - {c}x$.",
        "Cho tam giác $ABC$ có cạnh $AB = {p}$, $AC = {c}$ và góc $A = 60^\\circ$.",
        "Tìm tập nghiệm của bất phương trình $\\log_{{2}}(x - {c}) < {p}$.",
        "Biết tích phân $\\int_{{0}}^{{{p}}} f(x)dx = {c}$. Tính $I$.",
        "Phương trình mặt cầu tâm $I({p}, 0, {c})$ bán kính $R = {p}$ là:",
    ]

    for i in range(10000):
        tmpl = base_templates[i % len(base_templates)]
        p = (i % 20) + 1
        c = (i % 50) + 1
        prompt = tmpl.format(p=p, c=c)
        src = f"\\begin{{ex}}\n{prompt}\n\\choice{{\\True $A$}}{{$B$}}{{$C$}}{{$D$}}\n\\end{{ex}}"
        items.append(
            DuplicateItem(
                id=f"synth_{i:05d}",
                source=src,
                normalized_source=normalize_latex(src),
                question_type="mcq",
            )
        )

    # Bắt đầu đo hiệu năng và RAM
    tracemalloc.start()
    t_start = time.perf_counter()

    groups = service._cluster_duplicates(items)

    elapsed = time.perf_counter() - t_start
    current_ram, peak_ram = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_ram_mb = peak_ram / (1024 * 1024)

    # Yêu cầu L3.3: Thuật toán không bị treo, hoàn thành nhanh (< 5 giây cho 10,000 câu), RAM < 100 MB
    assert elapsed < 5.0, f"Thời gian quét 10,000 câu vượt quá giới hạn: {elapsed:.2f}s (cần < 5.0s)"
    assert peak_ram_mb < 120.0, f"RAM peak quá cao: {peak_ram_mb:.1f} MB (cần < 120 MB)"
    assert len(groups) > 0, "Phải phát hiện các nhóm trùng lặp từ bộ câu hỏi lặp chu kỳ."


def test_cancel_responsiveness():
    """Yêu cầu L3.3: Có thể hủy ngay lập tức mà không treo."""
    service = DeduplicationService(services=None)
    items = [
        DuplicateItem(
            id=f"q_{i}",
            source=f"\\begin{{ex}}Câu {i}\\end{{ex}}",
            normalized_source=f"\\begin{{ex}}Câu {i}\\end{{ex}}",
            question_type="essay",
        )
        for i in range(500)
    ]
    # Cancelled immediately
    groups = service._cluster_duplicates(items, cancelled=lambda: True)
    assert len(groups) == 0
