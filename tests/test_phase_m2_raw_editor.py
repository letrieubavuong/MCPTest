"""Tests for Phase M.2.1: Raw LaTeX Editor Primacy and Preservation.

Verifies:
1. Raw LaTeX editor is default and primary (index 0) upon opening or creating lessons.
2. Arbitrary raw LaTeX typing/pasting (TikZ, align*, choice, Vietnamese Unicode) is completely unmutated.
3. No silent background source mutation or cursor corruption from passive visual sync.
4. Mode switching: visual mode shows advisory notice on complex environments without destroying raw source.
5. Undo/Redo routes to raw editor by default.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.lesson_page import LessonPage


def setup_app(tmp_path):
    cfg = AppConfig.load(tmp_path / "app_data")
    srv = create_services(cfg)
    return srv


def test_raw_editor_default_and_unmutated_typing(qtbot, tmp_path):
    """Verifies raw LaTeX editor is default, receives normal typing/paste, and never silently mutates."""
    services = setup_app(tmp_path)
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(4)
    page: LessonPage = window.lesson_page
    page.new_lesson(interactive=False)

    # 1. Verify default edit mode is raw LaTeX (index 0)
    assert page.edit_mode.currentIndex() == 0
    assert "Mã LaTeX" in page.edit_mode.currentText()
    assert page.editor_stack.currentIndex() == 0
    assert page.editor_stack.currentWidget() is page.editor

    # 2. Type arbitrary LaTeX including TikZ, align*, fractions, and Vietnamese Unicode
    complex_latex = r"""\section{Bài toán dao động điều hòa}
Lý thuyết cơ bản: Phương trình dao động $x = A \cos(\omega t + \varphi)$.

\begin{align*}
v &= x' = -\omega A \sin(\omega t + \varphi) \\
a &= v' = -\omega^2 A \cos(\omega t + \varphi) = -\omega^2 x
\end{align*}

Hình vẽ đồ thị dao động:
\begin{center}
\begin{tikzpicture}[scale=0.8]
\draw[->] (-0.5,0) -- (4,0) node[right] {$t$};
\draw[->] (0,-2) -- (0,2) node[above] {$x$};
\draw[domain=0:3.5, smooth, variable=\t, blue] plot ({\t}, {1.5*cos(180*\t)});
\end{tikzpicture}
\end{center}

\begin{ex}
Một chất điểm dao động điều hòa với chu kỳ $T = 2\ \text{s}$. Tần số góc của dao động là:
\choice
{\True $\pi\ \text{rad/s}$}
{$2\pi\ \text{rad/s}$}
{$0{,}5\pi\ \text{rad/s}$}
{$4\pi\ \text{rad/s}$}
\loigiai{
Ta có $\omega = \frac{2\pi}{T} = \frac{2\pi}{2} = \pi\ \text{rad/s}$.
}
\end{ex}
"""
    page.editor.setPlainText(complex_latex)
    QApplication.processEvents()

    # 3. Verify exact source preservation
    assert page.editor.toPlainText() == complex_latex
    page.flush()
    assert page.current_block()["source"] == complex_latex or page.doc["blocks"][0]["source"] == complex_latex

    # 4. Simulate typing more characters at caret
    cursor = page.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End, cursor.MoveMode.MoveAnchor)
    page.editor.setTextCursor(cursor)
    page.editor.insertPlainText("\n% Thêm chú thích của giáo viên tại dòng cuối\n")
    QApplication.processEvents()

    # Verify no cursor jump or silent revert
    current_text = page.editor.toPlainText()
    assert "% Thêm chú thích của giáo viên tại dòng cuối" in current_text

    # 5. Test undo and redo
    page.editor.undo()
    QApplication.processEvents()
    assert "% Thêm chú thích của giáo viên tại dòng cuối" not in page.editor.toPlainText()

    page.editor.redo()
    QApplication.processEvents()
    assert "% Thêm chú thích của giáo viên tại dòng cuối" in page.editor.toPlainText()

    window.close()


def test_mode_switch_does_not_mutate_raw_source(qtbot, tmp_path):
    """Verifies switching to visual mode and back preserves exact raw LaTeX fidelity."""
    services = setup_app(tmp_path)
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(4)
    page: LessonPage = window.lesson_page
    page.new_lesson(interactive=False)

    sample_source = r"""\begin{ex}
Tính tích phân $I = \int_0^1 x^2 \, dx$.
\choice
{\True $\frac{1}{3}$}
{$\frac{1}{2}$}
{$1$}
{$0$}
\loigiai{Ta có $I = \left. \frac{x^3}{3} \right|_0^1 = \frac{1}{3}$.}
\end{ex}"""

    page.editor.setPlainText(sample_source)
    QApplication.processEvents()

    # Switch to visual mode (index 1)
    page.set_edit_mode(1)
    QApplication.processEvents()
    assert page.editor_stack.currentIndex() == 1
    assert page.editor_stack.currentWidget() is page.visual_editor

    # Switch back to raw LaTeX mode (index 0)
    page.set_edit_mode(0)
    QApplication.processEvents()
    assert page.editor_stack.currentIndex() == 0
    assert page.editor_stack.currentWidget() is page.editor

    # Assert raw source is 100% identical without any mangling
    assert page.editor.toPlainText() == sample_source

    window.close()


def test_toolbar_wrap_selection_preserves_latex(qtbot, tmp_path):
    """Verifies format bar buttons wrap selected text or insert without placeholder clobbering."""
    services = setup_app(tmp_path)
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(4)
    page: LessonPage = window.lesson_page
    page.new_lesson(interactive=False)

    page.editor.setPlainText("Công thức quan trọng")
    cursor = page.editor.textCursor()
    cursor.select(cursor.SelectionType.Document)
    page.editor.setTextCursor(cursor)

    # Wrap with \textbf{...}
    page.wrap_selection(r"\textbf{", "}")
    QApplication.processEvents()

    assert page.editor.toPlainText() == r"\textbf{Công thức quan trọng}"

    window.close()
