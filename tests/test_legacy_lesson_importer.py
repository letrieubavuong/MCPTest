import pytest
from pathlib import Path
from latex_question_studio.application.legacy_lesson_importer import LegacyLessonImporter
from latex_question_studio.application.assets import AssetStore


def test_legacy_lesson_importer_preserves_theory_outside_exercises(tmp_path):
    store = AssetStore(tmp_path / "assets")
    importer = LegacyLessonImporter(asset_store=store)

    sample_tex = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{vietnam}
\usepackage{amsmath,amssymb}
\usepackage{graphicx,tikz}
\begin{document}
\title{Khúc xạ ánh sáng và định luật Snell}

\section{I. Hiện tượng khúc xạ ánh sáng}
Khi tia sáng truyền từ môi trường trong suốt này sang môi trường trong suốt khác, tia sáng bị gãy khúc tại mặt phân cách.
Hiện tượng đó gọi là hiện tượng khúc xạ ánh sáng.

\begin{equation}
n_1 \sin i = n_2 \sin r
\end{equation}

\begin{tikzpicture}
\draw[thick,->] (0,0) -- (2,2);
\node at (1,1) {Tia tới};
\end{tikzpicture}

\subsection{1. Chiết suất của môi trường}
Chiết suất tuyệt đối của một môi trường là chiết suất của môi trường đó đối với chân không.

\begin{vidu}
Chiếu một tia sáng từ không khí vào nước với góc tới $i = 60^\circ$. Biết chiết suất của nước là $n = \frac{4}{3}$. Tính góc khúc xạ $r$.
\loigiai{
Áp dụng định luật khúc xạ:
\[ \sin r = \frac{\sin i}{n} = \frac{\sin 60^\circ}{4/3} \approx 0.65 \implies r \approx 40.5^\circ \]
}
\end{vidu}

\subsection{2. Luyện tập củng cố}
\begin{ex}
Khi góc tới tăng dần từ $0^\circ$ đến $90^\circ$ thì góc khúc xạ:
\choice{Giảm dần}{\True Tăng dần nhưng luôn nhỏ hơn $90^\circ$}{Không đổi}{Bằng $0^\circ$}
\loigiai{Theo định luật Snell, khi $i$ tăng thì $\sin i$ tăng, dẫn đến $\sin r$ tăng nên $r$ tăng.}
\end{ex}

\end{document}
"""

    file_path = tmp_path / "khuc_xa.tex"
    file_path.write_text(sample_tex, encoding="utf-8")

    res = importer.parse_file(file_path, subject="KHTN", grade="9")

    assert res.title == "Khúc xạ ánh sáng và định luật Snell"
    assert res.subject == "KHTN"
    assert res.grade == "9"
    assert len(res.blocks) >= 5

    # Check theory block preservation
    theory_blocks = [b for b in res.blocks if b["kind"] == "theory"]
    assert len(theory_blocks) >= 2

    # Check TikZ inside theory source is preserved exactly
    tikz_block = next((b for b in theory_blocks if r"\begin{tikzpicture}" in b["source"]), None)
    assert tikz_block is not None
    assert "Tia tới" in tikz_block["source"]

    # Check Snell formula
    formula_block = next((b for b in theory_blocks if "n_1 \\sin i" in b["source"]), None)
    assert formula_block is not None

    # Check example block
    example_blocks = [b for b in res.blocks if b["kind"] == "example"]
    assert len(example_blocks) == 1
    assert "Chiếu một tia sáng" in example_blocks[0]["source"]
    assert r"\loigiai" in example_blocks[0]["source"]

    # Check exercise block
    ex_blocks = [b for b in res.blocks if b["kind"] == "exercise"]
    assert len(ex_blocks) >= 1
    q_block = next((b for b in ex_blocks if r"\choice" in b["source"]), None)
    assert q_block is not None

    # Coverage must be high
    assert res.coverage_percent >= 80.0
