# MCPTest — Phase M.2: Raw LaTeX Editor & Duplicate Deletion Repair

## Context and verified code findings
Repo: https://github.com/letrieubavuong/MCPTest. Baseline HEAD at audit: `58cd9d9`. Inspect current HEAD first; do not assume unchanged.

1. `src/latex_question_studio/ui/lesson_page.py`: edit-mode combo adds `['WYSIWYG','Mã LaTeX']`; stacked editor adds `visual_editor` at index 0 and `LatexEditor` at index 1. `visual_changed` calls `self.editor.setPlainText(source)` and `source_changed` triggers visual sync. Risk of unexpected source transformation; raw LaTeX must be primary.
2. `src/latex_question_studio/ui/pages/dedup_page.py`: `_delete_selected()` always calls `self.service.delete_selected(to_delete)` against DB, while file scanning uses `selected_files` and `_export_clean_tex()`. File-scanned items must not be passed to DB delete.
3. `src/latex_question_studio/application/dedup.py`: `delete_selected()` checks references, uses `DELETE FROM questions`, increments count after executing SQL without checking affected row count. Investigate and repair safely.

## Non-negotiable requirements
- User can type, paste, edit and save arbitrary **raw LaTeX** normally, including `\begin{ex}`, `\choice`, `\choiceTF`, `\shortans`, `\loigiai`, `\begin{tikzpicture}`, `\includegraphics`, custom macros, multiline environments and Vietnamese Unicode, under pdfLaTeX/MAPClass/ex_test.
- Raw editor is default on opening/creating a lesson, with syntax highlighting, line numbers, indentation, undo/redo, Ctrl+S, find/replace and non-destructive compile preview.
- Raw source is the single source of truth; no automatic round-trip through WYSIWYG. WYSIWYG optional and must warn before any potentially lossy conversion. Switching view must not change source, cursor or undo history unnecessarily. Avoid calling `setPlainText()` on the raw editor as a side effect of passive preview/sync.
- Autosave must preserve exact source and content for current block, on block switching, closing/reopening and restart. Preview errors must never overwrite editor content.
- No automatic syntax corrections or formula recovery without explicit user action; code completions are optional and must not steal typing or alter backslashes.
- UI on 1366×768 and 1920×1080: enough editor space, collapsible outline/preview, editor focus on click, keyboard shortcuts working.

## Phase M2.0 — Reproduce and instrument
- Open lesson editor, type/paste realistic LaTeX including nested braces, `\frac{}`, `\begin{ex}` and TikZ. Test keystrokes, backslash, braces, `%`, `&`, `$`, `^`, `_`, Vietnamese accents, multiline paste, undo/redo, tab, copy/paste, switch blocks, autosave, reopen.
- Identify precisely whether problems stem from default WYSIWYG, synchronization, keyboard interception, editor read-only/focus, or other logic. Record before/after source hash and screenshots.
- Inspect code and tests before modifying; do not invent a diagnosis.

## Phase M2.1 — Fix lesson authoring editor
- Make `LatexEditor` default and primary, reorder mode controls if needed. Label explicitly `LaTeX (mặc định)` and `Trực quan (tùy chọn)`.
- Separate passive visual rendering from source mutation; visual editor must not silently rewrite raw source. Require deliberate Apply action and clear diff/confirmation when a visual edit would replace source. Consider disabling unsupported macros in visual mode with non-destructive notice.
- Preserve raw bytes or text fidelity (line endings normalization only when clearly documented); protect cursor/selection, undo stack, and active block. Keep preview in separate pane and compile asynchronously with stale-result protection.
- Verify all insert buttons insert valid LaTeX at caret, not literal UI placeholders, and don't clobber selected text without intent.

## Phase M2.2 — Repair duplicate deletion by scope
### Bank (SQLite) mode
- Checkbox selection is explicit. Protect the retained primary question, show selected count and disabled-state reasons.
- Delete only confirmed selected question IDs, within transaction with correct row-count checks and proper FK handling. Show per-item success/failure; refresh groups from DB and update counts after deletion. Never report success for missing IDs or failed deletion.
- Preserve references from lessons/exams; when protected, explain exactly what references block deletion. Never use `force=True` to bypass integrity checks without a separately specified, audited policy.
- Provide a safe metadata-merge option with user confirmation, not automatic.
### .tex file mode
- Do NOT call SQLite `delete_selected` for file-scan entries. `Xóa câu đã chọn` should lead to a clear **Save As cleaned .tex** flow (or an explicit `Loại khỏi file .tex` action), leaving originals unchanged by default.
- Handle multiple input `.tex` files independently, not just `selected_files[0]`; let user choose output directory and produce one cleaned file per source, retaining filenames safely.
- Preserve entire original TeX outside removed question spans: preamble, theory, comments, macros, assets and order. Remove only exact selected question spans using stable file/path/span identifiers; do not rely on SQLite IDs or ambiguous content equality.
- Avoid stripping a question from the wrong file or removing all identical-looking questions accidentally. Keep a preview/diff of what will be removed; confirm with per-file counts. Reparse cleaned files and verify expected number of questions and no unrelated content changes.
- Clearly distinguish `Xóa khỏi ngân hàng` from `Xuất file .tex đã loại trùng` in buttons, confirmation dialogs, and status messages.

## Phase M2.3 — Tests and acceptance
- Add regression tests for raw typing/paste/switch/autosave/reopen/undo, WYSIWYG toggling without mutations, macro-heavy TikZ/ex_test, and PDF compilation on Windows/pdfLaTeX.
- Add UI tests for selecting duplicate cards and deleting; bank deletion successful, protected-reference case, nonexistent ID rowcount, cancellation, stale group refresh, and partial failure.
- Add file-mode tests: one file, multiple files, duplicates across files, identical text with distinct source spans, preserving non-question text and assets, no changes to originals, save-as, and no DB mutations.
- Run full pytest suite (not just focused tests), Windows UI smoke at 1366×768 and 1920×1080, and pdfLaTeX compilation of lesson with equations/TikZ/ex_test.
- Do not mark PASS on mocked-only tests; distinguish automated tests, live UI smoke and manual verification.

## Delivery
- Commit in logical increments, push to repo, avoid unrelated changes.
- Create `docs/PHASE_M2_EDITOR_DEDUP_REPORT.md` with reproduction, root causes, changed files, before/after UI captures, actual test commands/counts, per-scope deletion evidence, known limitations, commit SHAs.
- Acceptance: a teacher can type and save LaTeX naturally; select and remove specific duplicate questions in both DB and file workflows without loss of unrelated content or references.
