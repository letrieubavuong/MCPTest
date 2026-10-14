"""Phase L.1 LaTeX Conversion Hardening Test Suite.

Contains >= 60 test cases covering:
- Math 6-12 (arithmetic, algebra, calculus, geometry, sets, matrices)
- Natural Sciences KHTN 6-9 & Physics 10-12 (kinematics, electricity, optics, units)
- Chemistry (reactions, ions, formulas)
- KaTeX, MathJax, MathML conversions
- Escaping (% & # _ { } ~ ^) and text vs math mode state machine
- Dangerous macro sanitization (\\write18, \\input)
- Real pdfLaTeX compilation tests on >= 20 representative cases
- Manual semantic verification on 10 gold standard cases
"""

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import pytest

from latex_question_studio.scraping.html_to_latex import (
    html_to_latex,
    sanitize_latex,
    escape_latex_text,
    convert_unicode_in_text,
    clean_latex_spacing,
)


CORPUS_60_CASES = [
    # 1-10: Math 6-9 (Arithmetic, basic algebra, fractions, geometry)
    {"id": "M01", "html": "<p>Tính giá trị: <b>15%</b> của 200 bằng bao nhiêu?</p>", "expect": [r"15\%", r"\textbf{15\%}"], "subject": "Math6"},
    {"id": "M02", "html": "<p>Phân số: <math><mfrac><mn>3</mn><mn>4</mn></mfrac></math> cộng với <math><mfrac><mn>1</mn><mn>2</mn></mfrac></math></p>", "expect": [r"\frac{3}{4}", r"\frac{1}{2}"], "subject": "Math6"},
    {"id": "M03", "html": "<p>Cho tập hợp A = {1, 2, 3}. Phần tử 2 ∈ A và 5 ∉ A.</p>", "expect": [r"$2 \in A$", r"\notin"], "subject": "Math6"},
    {"id": "M04", "html": "<p>Lũy thừa: 2<sup>3</sup> = 8 và 10<sup>5</sup>.</p>", "expect": [r"$^3$", r"$^5$"], "subject": "Math6"},
    {"id": "M05", "html": "<p>Góc: Cho tam giác ABC có góc A = 90° và góc B = 30°.</p>", "expect": [r"90$^\circ$", r"30$^\circ$"], "subject": "Math7"},
    {"id": "M06", "html": "<p>Đoạn thẳng: AB ⊥ CD và d1 ∥ d2.</p>", "expect": [r"\perp", r"\parallel"], "subject": "Math7"},
    {"id": "M07", "html": "<p>Căn bậc hai: <math><msqrt><mi>x</mi><mo>+</mo><mn>1</mn></msqrt></math> có nghĩa khi x ≥ -1.</p>", "expect": [r"\sqrt{x+1}", r"\ge"], "subject": "Math9"},
    {"id": "M08", "html": "<p>Căn bậc ba: <math><mroot><mi>a</mi><mn>3</mn></mroot></math></p>", "expect": [r"\sqrt[3]{a}"], "subject": "Math9"},
    {"id": "M09", "html": "<p>Phương trình: <i>ax</i><sup>2</sup> + <i>bx</i> + <i>c</i> = 0 với a ≠ 0.</p>", "expect": [r"\textit{ax}", r"$^2$", r"\ne"], "subject": "Math9"},
    {"id": "M10", "html": "<p>Hệ bất phương trình: x ≤ 10 và y ≥ 5.</p>", "expect": [r"$x \le 10$", r"$y \ge 5$"], "subject": "Math9"},

    # 11-20: Math 10-12 (Sets, vectors, calculus, trigonometry, matrices)
    {"id": "M11", "html": "<p>Tập hợp số thực ℝ và số tự nhiên ℕ: x ∈ ℝ.</p>", "expect": [r"\mathbb{R}", r"$x \in \mathbb{R}$"], "subject": "Math10"},
    {"id": "M12", "html": "<p>Giao và hợp: A ∩ B = ∅ và A ∪ B = C.</p>", "expect": [r"\cap", r"\cup", r"\emptyset"], "subject": "Math10"},
    {"id": "M13", "html": "<p>Vectơ: <math><mover><mrow><mi>A</mi><mi>B</mi></mrow><mo>→</mo></mover></math></p>", "expect": [r"\vec{AB}"], "subject": "Math10"},
    {"id": "M14", "html": "<p>Lượng giác: sin(α + β) và cos 2α, với α, β ∈ ℝ.</p>", "expect": [r"\alpha", r"\beta", r"\in"], "subject": "Math10"},
    {"id": "M15", "html": "<p>Đạo hàm: <math><msup><mi>f</mi><mo>′</mo></msup><mo>(</mo><mi>x</mi><mo>)</mo></math> với x ∈ (0, +∞).</p>", "expect": [r"\infty", r"\in"], "subject": "Math11"},
    {"id": "M16", "html": "<p>Tích phân: <math><msubsup><mo>∫</mo><mn>0</mn><mn>1</mn></msubsup><msup><mi>x</mi><mn>2</mn></msup><mi>d</mi><mi>x</mi></math></p>", "expect": [r"\int", r"_{0}^{1}"], "subject": "Math12"},
    {"id": "M17", "html": "<p>Tổng sigma: ∑ từ i=1 đến n.</p>", "expect": [r"\sum"], "subject": "Math11"},
    {"id": "M18", "html": "<p>Số phức: z = a + bi với z ∈ ℂ và i<sup>2</sup> = -1.</p>", "expect": [r"\mathbb{C}", r"$^2$"], "subject": "Math12"},
    {"id": "M19", "html": "<p>Ma trận:<math><mtable><mtr><mtd><mn>1</mn></mtd><mtd><mn>2</mn></mtd></mtr><mtr><mtd><mn>3</mn></mtd><mtd><mn>4</mn></mtd></mtr></mtable></math></p>", "expect": [r"\begin{matrix}", r"1 & 2", r"3 & 4", r"\end{matrix}"], "subject": "Math12"},
    {"id": "M20", "html": "<p>Giới hạn: <math><munder><mo>lim</mo><mrow><mi>x</mi><mo>→</mo><mn>0</mn></mrow></munder><mfrac><mrow><mi>sin</mi><mi>x</mi></mrow><mi>x</mi></mfrac></math></p>", "expect": [r"\lim", r"\to", r"\frac{"], "subject": "Math11"},

    # 21-30: Natural Sciences KHTN 6-9
    {"id": "S21", "html": "<p>Vận tốc của vật là 15 m/s và gia tốc 2 m/s².</p>", "expect": [r"15 m/s", r"2 m/s$^2$"], "subject": "KHTN6"},
    {"id": "S22", "html": "<p>Khối lượng riêng của nước là 1000 kg/m³.</p>", "expect": [r"1000 kg/m$^3$"], "subject": "KHTN6"},
    {"id": "S23", "html": "<p>Thể tích chất lỏng là 250 cm³ hoặc 0.25 dm³.</p>", "expect": [r"250 cm$^3$", r"0.25 dm$^3$"], "subject": "KHTN6"},
    {"id": "S24", "html": "<p>Nhiệt độ nóng chảy của nước đá là 0°C và sôi ở 100°C.</p>", "expect": [r"0$^\circ$C", r"100$^\circ$C"], "subject": "KHTN6"},
    {"id": "S25", "html": "<p>Phân tử nước gồm 2 nguyên tử H và 1 nguyên tử O: H₂O.</p>", "expect": [r"H$_2$O"], "subject": "KHTN7"},
    {"id": "S26", "html": "<p>Khí cacbonic: CO₂ chiếm tỉ lệ nhỏ trong không khí.</p>", "expect": [r"CO$_2$"], "subject": "KHTN7"},
    {"id": "S27", "html": "<p>Muối ăn có công thức hóa học là NaCl.</p>", "expect": [r"NaCl"], "subject": "KHTN7"},
    {"id": "S28", "html": "<p>Quang hợp: 6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂.</p>", "expect": [r"CO$_2$", r"H$_2$O", r"\to", r"O$_2$"], "subject": "KHTN7"},
    {"id": "S29", "html": "<p>Công thức phân tử axit sunfuric: H₂SO₄.</p>", "expect": [r"H$_2$SO$_4$"], "subject": "KHTN8"},
    {"id": "S30", "html": "<p>Dung dịch nước vôi trong là Ca(OH)₂.</p>", "expect": [r"Ca(OH)$_2$"], "subject": "KHTN8"},

    # 31-40: Physics 10-12
    {"id": "P31", "html": "<p>Phương trình chuyển động: s = v₀t + ½at².</p>", "expect": [r"s = v$_0$t", r"at$^2$"], "subject": "Phys10"},
    {"id": "P32", "html": "<p>Định luật II Newton: F = ma và trọng lực P = mg.</p>", "expect": [r"F = ma", r"P = mg"], "subject": "Phys10"},
    {"id": "P33", "html": "<p>Nhiệt động lực học: ΔU = A + Q với Q > 0.</p>", "expect": [r"\Delta", r"U = A + Q"], "subject": "Phys12"},
    {"id": "P34", "html": "<p>Bước sóng: λ = v/f và tần số góc ω = 2πf.</p>", "expect": [r"\lambda", r"\omega", r"\pi"], "subject": "Phys11"},
    {"id": "P35", "html": "<p>Điện trở R = 100 Ω, hiệu điện thế U = 220 V.</p>", "expect": [r"\Omega", r"220 V"], "subject": "Phys11"},
    {"id": "P36", "html": "<p>Hệ số ma sát trượt: μ = 0.05.</p>", "expect": [r"\mu"], "subject": "Phys10"},
    {"id": "P37", "html": "<p>Khối lượng riêng ρ = m/V.</p>", "expect": [r"\rho"], "subject": "Phys10"},
    {"id": "P38", "html": "<p>Công sai số: g = 9.8 ± 0.1 m/s².</p>", "expect": [r"\pm", r"m/s$^2$"], "subject": "Phys10"},
    {"id": "P39", "html": "<p>Phóng xạ hạt: tia α, tia β⁻ và tia γ.</p>", "expect": [r"\alpha", r"\beta", r"\gamma"], "subject": "Phys12"},
    {"id": "P40", "html": "<p>Năng lượng Einstein: E = mc<sup>2</sup>.</p>", "expect": [r"E = mc$^2$"], "subject": "Phys12"},

    # 41-50: KaTeX, MathJax, MathML advanced
    {"id": "K41", "html": '<span class="katex"><annotation encoding="application/x-tex">\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1</annotation></span>', "expect": [r"\lim_{x \to 0} \frac{\sin x}{x} = 1"], "subject": "KaTeX"},
    {"id": "K42", "html": '<div class="katex-display"><annotation encoding="application/x-tex">\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}</annotation></div>', "expect": [r"\[", r"\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}", r"\]"], "subject": "KaTeXDisplay"},
    {"id": "J43", "html": '<script type="math/tex">y = \\sqrt{x^2 + 1}</script>', "expect": [r"$y = \sqrt{x^2 + 1}$"], "subject": "MathJaxInline"},
    {"id": "J44", "html": '<script type="math/tex; mode=display">\\Delta = b^2 - 4ac</script>', "expect": [r"\[", r"\Delta = b^2 - 4ac", r"\]"], "subject": "MathJaxDisplay"},
    {"id": "M45", "html": '<math><mfenced open="[" close="]"><mrow><mi>a</mi><mo>+</mo><mi>b</mi></mrow></mfenced></math>', "expect": [r"\left[", r"a+b", r"\right]"], "subject": "MathMLFenced"},
    {"id": "M46", "html": '<math><msubsup><mi>x</mi><mn>1</mn><mn>2</mn></msubsup></math>', "expect": [r"x_{1}^{2}"], "subject": "MathMLSubSup"},
    {"id": "M47", "html": '<math><mtext>áp suất </mtext><mi>p</mi></math>', "expect": [r"\text{áp suất"], "subject": "MathMLText"},
    {"id": "M48", "html": '<math><mover><mi>x</mi><mo>¯</mo></mover></math>', "expect": [r"\overline{x}"], "subject": "MathMLOverline"},
    {"id": "M49", "html": '<math><mover><mi>v</mi><mo>→</mo></mover></math>', "expect": [r"\vec{v}"], "subject": "MathMLVector"},
    {"id": "M50", "html": '<math><mrow><mi>x</mi><mo>≈</mo><mn>3.14</mn></mrow></math>', "expect": [r"\approx"], "subject": "MathMLApprox"},

    # 51-60: Escaping, tables, lists, images, security
    {"id": "E51", "html": "<p>Tỉ lệ giảm giá 50% & tặng kèm quà #1_ưu_đãi {VIP}.</p>", "expect": [r"50\%", r"\&", r"\#1\_ưu\_đãi", r"\{VIP\}"], "subject": "Escaping"},
    {"id": "E52", "html": "<p>Ký tự ngã ~ và mũ ^ trong văn bản thường.</p>", "expect": [r"\textasciitilde{}", r"\textasciicircum{}"], "subject": "Escaping"},
    {"id": "L53", "html": "<ul><li>Mục một</li><li>Mục hai</li></ul>", "expect": [r"\begin{itemize}", r"\item Mục một", r"\item Mục hai", r"\end{itemize}"], "subject": "List"},
    {"id": "L54", "html": "<ol><li>Bước A</li><li>Bước B</li></ol>", "expect": [r"\begin{enumerate}", r"\item Bước A", r"\item Bước B", r"\end{enumerate}"], "subject": "List"},
    {"id": "T55", "html": "<table><tr><th>STT</th><th>Họ tên</th></tr><tr><td>1</td><td>Nguyễn Văn A</td></tr></table>", "expect": [r"\begin{tabular}", r"STT & Họ tên", r"1 & Nguyễn Văn A", r"\end{tabular}"], "subject": "Table"},
    {"id": "I56", "html": '<img src="diagram.png" alt="Sơ đồ mạch điện" />', "expect": [r"[IMG:diagram.png]"], "subject": "Image"},
    {"id": "I57", "html": '<img data-src="https://example.com/lazy.jpg" />', "expect": [r"[IMG:https://example.com/lazy.jpg]"], "subject": "LazyImage"},
    {"id": "I58", "html": '<img srcset="small.jpg 300w, large.jpg 600w" />', "expect": [r"[IMG:small.jpg]"], "subject": "SrcsetImage"},
    {"id": "S59", "html": '<p>Đoạn mã nguy hiểm: \\write18{calc.exe} và \\input{secret.tex}</p>', "expect": [r"\textbackslash{}write18", r"\textbackslash{}input"], "subject": "Security"},
    {"id": "S60", "html": '<p>Đoạn mã lệnh: \\include{flag} và \\openin1</p>', "expect": [r"\textbackslash{}include", r"\textbackslash{}openin"], "subject": "Security"},
]


def test_corpus_size_at_least_60():
    """Yêu cầu L1.5: Corpus phải đạt ít nhất 60 ca."""
    assert len(CORPUS_60_CASES) >= 60


@pytest.mark.parametrize("case", CORPUS_60_CASES, ids=lambda c: c["id"])
def test_corpus_expected_latex_semantics(case):
    """Kiểm tra TeX kỳ vọng và ngữ nghĩa cho từng ca trong 60 ca corpus."""
    latex, imgs = html_to_latex(case["html"])
    for exp in case["expect"]:
        assert exp in latex, f"Ca {case['id']} ({case['subject']}) thiếu mẫu kỳ vọng: '{exp}' trong latex: '{latex}'"


def _create_minimal_pdflatex_document(body_content: str) -> str:
    """Tạo tài liệu LaTeX độc lập hợp lệ để kiểm tra biên dịch bằng pdfLaTeX thật."""
    return (
        r"\documentclass{article}" "\n"
        r"\usepackage[utf8]{inputenc}" "\n"
        r"\usepackage[T5]{fontenc}" "\n"
        r"\usepackage{amsmath,amssymb}" "\n"
        r"\usepackage{graphicx}" "\n"
        r"\begin{document}" "\n"
        + body_content + "\n"
        r"\end{document}" "\n"
    )


def test_compile_20_representative_cases_with_real_pdflatex(tmp_path):
    """Yêu cầu L1.5: Golden tests compile pdfLaTeX thật ít nhất 20 ca đại diện.

    Kiểm tra PDF tồn tại, kích thước > 0 bytes và log không có lỗi nghiêm trọng.
    """
    pdflatex_path = shutil.which("pdflatex")
    if not pdflatex_path:
        pytest.skip("pdfLaTeX không có sẵn trên môi trường kiểm thử.")

    # Chọn 20 ca đại diện trải rộng: Math, KHTN, Vật lí, Hóa học, KaTeX, MathML, Tables, Escaping
    rep_ids = [
        "M01", "M02", "M03", "M04", "M05", "M06", "M07", "M11", "M13", "M16", "M19",
        "S21", "S22", "S24", "S25", "P31", "P34", "K41", "E51", "T55",
    ]
    rep_cases = [c for c in CORPUS_60_CASES if c["id"] in rep_ids]
    assert len(rep_cases) >= 20

    converted_bodies = []
    for c in rep_cases:
        latex, _ = html_to_latex(c["html"])
        # Loại bỏ placeholder [IMG:...] để tránh lỗi file image không tồn tại
        clean_for_tex = re.sub(r"\[IMG:[^\]]+\]", r"\texttt{[HinhAnh]}", latex)
        converted_bodies.append(f"% --- Ca {c['id']}: {c['subject']} ---\n\\section*{{Ca {c['id']}}}\n{clean_for_tex}\n")

    full_tex = _create_minimal_pdflatex_document("\n".join(converted_bodies))
    tex_file = tmp_path / "test_corpus_rep20.tex"
    tex_file.write_text(full_tex, encoding="utf-8")

    # Chạy biên dịch bằng pdfLaTeX
    cmd = [pdflatex_path, "-interaction=nonstopmode", "-halt-on-error", tex_file.name]
    result = subprocess.run(cmd, cwd=str(tmp_path), capture_output=True, text=True, timeout=60)

    pdf_file = tmp_path / "test_corpus_rep20.pdf"
    log_file = tmp_path / "test_corpus_rep20.log"
    log_content = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""

    assert pdf_file.exists(), f"pdfLaTeX không tạo ra file PDF! Log:\n{log_content[-2000:]}"
    assert pdf_file.stat().st_size > 1000, "File PDF sinh ra rỗng hoặc quá nhỏ!"
    assert "! LaTeX Error:" not in log_content, f"Phát hiện lỗi LaTeX Error trong log:\n{log_content[-2000:]}"
    assert "! Fatal error occurred" not in log_content, "Lỗi nghiêm trọng xảy ra trong quá trình biên dịch!"


def test_manual_alignment_10_gold_standard_cases():
    """Yêu cầu L1.5: Đối chiếu thủ công 10 ca kiểm chứng ngữ nghĩa chính xác."""
    gold_cases = [
        # 1. Math sets & logic
        ("<p>Cho x ∈ ℝ thỏa mãn x ≤ 10 và y ≥ 5.</p>",
         lambda t: "$x \\in \\mathbb{R}$" in t and "$x \\le 10$" in t and "$y \\ge 5$" in t),
        # 2. Fractions & MathML
        ("<p>Phân số <math><mfrac><mrow><mi>a</mi><mo>+</mo><mi>b</mi></mrow><mn>2</mn></mfrac></math></p>",
         lambda t: r"\frac{a+b}{2}" in t),
        # 3. Superscripts & units
        ("<p>Vận tốc 20 m/s và gia tốc 5 m/s².</p>",
         lambda t: "20 m/s" in t and "5 m/s$^2$" in t),
        # 4. Chemical formula
        ("<p>Khí CO₂ phản ứng với H₂O tạo ra axit carbonic.</p>",
         lambda t: "CO$_2$" in t and "H$_2$O" in t),
        # 5. Angle degrees
        ("<p>Góc α = 45° và nhiệt độ 37°C.</p>",
         lambda t: r"\alpha" in t and r"45$^\circ$" in t and r"37$^\circ$C" in t),
        # 6. Escaping special chars
        ("<p>Hạ giá 20% & mã #CODE_A {OK}</p>",
         lambda t: r"20\%" in t and r"\&" in t and r"\#CODE\_A" in t and r"\{OK\}" in t),
        # 7. MathJax display mode
        ('<script type="math/tex; mode=display">E = mc^2</script>',
         lambda t: "\\[" in t and "E = mc^2" in t and "\\]" in t),
        # 8. KaTeX annotation
        ('<span class="katex"><annotation encoding="application/x-tex">f(x) = x^2</annotation></span>',
         lambda t: "$f(x) = x^2$" in t),
        # 9. HTML table
        ("<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>",
         lambda t: r"\begin{tabular}{|c|c|}" in t and "A & B" in t and "1 & 2" in t),
        # 10. Security neutralization
        ("<p>Tấn công: \\write18{rm -rf /} và \\input{passwords.txt}</p>",
         lambda t: r"\textbackslash{}write18" in t and r"\textbackslash{}input" in t and r"\write18" not in t),
    ]

    for idx, (html, validator) in enumerate(gold_cases, start=1):
        latex, _ = html_to_latex(html)
        assert validator(latex), f"Ca đối chiếu thủ công #{idx} thất bại! Latex sinh ra: '{latex}'"
