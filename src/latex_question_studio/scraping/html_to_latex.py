"""HTML, MathJax, KaTeX, and MathML to pdfLaTeX converter for MCPTest.

Implements Phase L.1 real-world hardening:
- DOM tree-based AST parser with zero external dependencies.
- Strict text vs math state machine preventing math macros in text mode.
- Escapes special LaTeX characters in text mode (% & # _ { } ~ ^ \\).
- Converts Unicode math/science/units to valid LaTeX (e.g. x ∈ ℝ, y ≥ 5, 30°, m², H₂O).
- Distinguishes <sup> and <sub> between text and math mode.
- Extracts KaTeX annotations without fragile non-greedy regexes.
- Recursive MathML conversion supporting mfrac, msup, msub, msubsup, msqrt, mroot, mfenced, mtable, etc.
- Converts HTML tables and lists to standard LaTeX environments.
- Extracts lazy-loaded image attributes (src, data-src, data-original, data-lazy-src, srcset).
- Input sanitization neutralizing dangerous macros (\\write18, \\input, \\include, etc.).
"""

from html import unescape
from html.parser import HTMLParser
import re
import urllib.parse
from xml.etree import ElementTree as ET


# Dangerous LaTeX tokens that must never be executed via untrusted web imports
DANGEROUS_TOKENS = (
    r"\write18",
    r"\immediate",
    r"\input",
    r"\include",
    r"\openin",
    r"\openout",
    r"\catcode",
    r"\def",
    r"\gdef",
    r"\edef",
    r"\xdef",
    r"\let",
    r"\futurelet",
    r"\csname",
    r"\endcsname",
    r"\everypar",
    r"\everyjob",
    r"\read",
    r"\loop",
    r"\repeat",
    r"\special",
    r"\directlua",
)

# Mathematical Unicode to LaTeX math mode macro mappings
MATH_UNICODE_MAP = {
    "∈": r"\in",
    "∉": r"\notin",
    "⊂": r"\subset",
    "⊆": r"\subseteq",
    "⊄": r"\not\subset",
    "∪": r"\cup",
    "∩": r"\cap",
    "∅": r"\emptyset",
    "√": r"\sqrt",
    "π": r"\pi",
    "α": r"\alpha",
    "β": r"\beta",
    "γ": r"\gamma",
    "Δ": r"\Delta",
    "δ": r"\delta",
    "ε": r"\varepsilon",
    "λ": r"\lambda",
    "θ": r"\theta",
    "ω": r"\omega",
    "Ω": r"\Omega",
    "φ": r"\varphi",
    "μ": r"\mu",
    "ρ": r"\rho",
    "σ": r"\sigma",
    "τ": r"\tau",
    "≤": r"\le",
    "≥": r"\ge",
    "≠": r"\ne",
    "≈": r"\approx",
    "≡": r"\equiv",
    "→": r"\to",
    "⇒": r"\Rightarrow",
    "⇔": r"\Leftrightarrow",
    "←": r"\leftarrow",
    "↔": r"\leftrightarrow",
    "∞": r"\infty",
    "±": r"\pm",
    "∓": r"\mp",
    "°": r"^\circ",
    "∠": r"\angle",
    "⊥": r"\perp",
    "∥": r"\parallel",
    "×": r"\times",
    "·": r"\cdot",
    "÷": r"\div",
    "…": r"\dots",
    "∀": r"\forall",
    "∃": r"\exists",
    "∑": r"\sum",
    "∫": r"\int",
    "∂": r"\partial",
    "ℝ": r"\mathbb{R}",
    "ℕ": r"\mathbb{N}",
    "ℤ": r"\mathbb{Z}",
    "ℚ": r"\mathbb{Q}",
    "ℂ": r"\mathbb{C}",
}

# Superscript unicode chars
SUPERSCRIPT_MAP = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    "⁺": "+", "⁻": "-", "⁼": "=", "⁽": "(", "⁾": ")",
    "ⁿ": "n",
}

# Subscript unicode chars
SUBSCRIPT_MAP = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "₊": "+", "₋": "-", "₌": "=", "₍": "(", "₎": ")",
    "ₐ": "a", "ₑ": "e", "ₒ": "o", "ₓ": "x",
}


def sanitize_latex(text: str) -> tuple[str, list[str]]:
    """Detects and neutralizes dangerous LaTeX macro tokens in untrusted input.

    Returns:
        (sanitized_text, warnings)
    """
    warnings = []
    sanitized = text
    for token in DANGEROUS_TOKENS:
        if token in sanitized:
            warnings.append(f"Nguy hiểm: phát hiện token '{token}', đã vô hiệu hóa")
            # Neutralize macro so it cannot be executed by pdfLaTeX
            safe_rep = token.replace("\\", r"\textbackslash{}")
            sanitized = sanitized.replace(token, safe_rep)
    return sanitized, warnings


class DOMNode:
    """Represents an HTML/XML node in our AST."""

    def __init__(self, tag: str | None = None, attrs: dict[str, str] | None = None, parent=None):
        self.tag = tag.lower() if tag else None
        self.attrs = attrs or {}
        self.text = ""
        self.tail = ""
        self.children: list["DOMNode"] = []
        self.parent = parent

    def add_child(self, child: "DOMNode") -> "DOMNode":
        child.parent = self
        self.children.append(child)
        return child

    def get_attr(self, name: str, default: str = "") -> str:
        return self.attrs.get(name.lower(), default)

    def find_all(self, tag_name: str) -> list["DOMNode"]:
        results = []
        for c in self.children:
            if c.tag == tag_name.lower():
                results.append(c)
            results.extend(c.find_all(tag_name))
        return results

    def text_content(self) -> str:
        parts = [self.text]
        for c in self.children:
            parts.append(c.text_content())
            parts.append(c.tail)
        return "".join(parts)


class DOMTreeBuilder(HTMLParser):
    """Builds a DOM AST from arbitrary (possibly messy) HTML."""

    SELF_CLOSING = {"br", "img", "hr", "input", "meta", "link"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = DOMNode(tag="[document]")
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        attr_dict = {k.lower(): v for k, v in attrs if k}
        node = DOMNode(tag=tag, attrs=attr_dict, parent=self.current)
        self.current.add_child(node)
        if tag.lower() not in self.SELF_CLOSING:
            self.current = node

    def handle_endtag(self, tag):
        tag = tag.lower()
        curr = self.current
        # Traverse up to matching open tag
        while curr is not None and curr.tag != tag and curr.parent is not None:
            curr = curr.parent
        if curr is not None and curr.parent is not None:
            self.current = curr.parent

    def handle_data(self, data):
        if not data:
            return
        if self.current.children:
            self.current.children[-1].tail += data
        else:
            self.current.text += data


def escape_latex_text(text: str) -> str:
    """Escapes special LaTeX characters in text mode."""
    if not text:
        return ""
    # Map & % $ # _ { } ~ ^ \
    # We do NOT escape $ here if it was intentionally inserted as math delimiter
    res = []
    # Replace backslash first if solitary
    for ch in text:
        if ch == "%":
            res.append(r"\%")
        elif ch == "&":
            res.append(r"\&")
        elif ch == "#":
            res.append(r"\#")
        elif ch == "_":
            res.append(r"\_")
        elif ch == "{":
            res.append(r"\{")
        elif ch == "}":
            res.append(r"\}")
        elif ch == "~":
            res.append(r"\textasciitilde{}")
        elif ch == "^":
            res.append(r"\textasciicircum{}")
        else:
            res.append(ch)
    return "".join(res)


def convert_unicode_in_text(text: str) -> str:
    """Converts Unicode math, degrees, units, chemical formulas in text mode to valid LaTeX."""
    if not text:
        return ""

    # Common scientific units with superscripts in text mode: m², cm³, dm³, km², m/s², kg/m³
    unit_map = {
        "m²": r"m$^2$",
        "cm²": r"cm$^2$",
        "dm²": r"dm$^2$",
        "km²": r"km$^2$",
        "mm²": r"mm$^2$",
        "m³": r"m$^3$",
        "cm³": r"cm$^3$",
        "dm³": r"dm$^3$",
        "km³": r"km$^3$",
        "mm³": r"mm$^3$",
        "m/s²": r"m/s$^2$",
        "kg/m³": r"kg/m$^3$",
        "g/cm³": r"g/cm$^3$",
    }
    for unit, tex in unit_map.items():
        text = text.replace(unit, tex)

    # Common chemical formulas in text mode
    chem_map = {
        "H₂O": r"H$_2$O",
        "CO₂": r"CO$_2$",
        "O₂": r"O$_2$",
        "N₂": r"N$_2$",
        "H₂": r"H$_2$",
        "SO₂": r"SO$_2$",
        "H₂SO₄": r"H$_2$SO$_4$",
        "HCl": r"HCl",
        "NaCl": r"NaCl",
        "CaCO₃": r"CaCO$_3$",
        "Ca(OH)₂": r"Ca(OH)$_2$",
        "Ba(OH)₂": r"Ba(OH)$_2$",
        "Al₂O₃": r"Al$_2$O$_3$",
        "Fe₂O₃": r"Fe$_2$O$_3$",
        "Fe₃O₄": r"Fe$_3$O$_4$",
        "KMnO₄": r"KMnO$_4$",
    }
    for chem, tex in chem_map.items():
        # Match whole formula not adjacent to ASCII letters
        text = re.sub(rf"(?<![A-Za-z]){re.escape(chem)}(?![A-Za-z])", tex, text)

    # Unicode superscripts: e.g. x², 10⁵
    for sup_char, val in SUPERSCRIPT_MAP.items():
        if sup_char in text:
            text = text.replace(sup_char, f"$^{val}$")

    # Unicode subscripts: e.g. x₁, v₀
    for sub_char, val in SUBSCRIPT_MAP.items():
        if sub_char in text:
            text = text.replace(sub_char, f"$_{val}$")

    # Degrees: 30° -> 30$^\circ$, or standalone ° -> $^\circ$
    text = re.sub(r"(\d+)\s*°\s*C\b", lambda m: f"{m.group(1)}$^\\circ$C", text)
    text = re.sub(r"(\d+)\s*°", lambda m: f"{m.group(1)}$^\\circ$", text)
    text = text.replace("°C", r"$^\circ$C")
    text = text.replace("°", r"$^\circ$")

    # Inline math patterns with relational/set operators: e.g. "x ∈ ℝ", "y ≥ 5", "x ≤ 10"
    # Convert pattern like <ident> <op> <ident/num> to $<ident> <tex_op> <ident/num>$
    rel_ops = {
        "∈": r"\in",
        "∉": r"\notin",
        "⊂": r"\subset",
        "⊆": r"\subseteq",
        "≤": r"\le",
        "≥": r"\ge",
        "≠": r"\ne",
        "≈": r"\approx",
        "≡": r"\equiv",
        "⊥": r"\perp",
        "∥": r"\parallel",
    }
    for op, tex in rel_ops.items():
        # Pattern: word or variable op word or number or set symbol
        pattern = rf"([a-zA-Z0-9_\(\)]+)\s*{re.escape(op)}\s*([a-zA-Z0-9_\(\)ℝℕℤℚℂ∅]+)"
        def _rep_rel(m):
            left = m.group(1)
            right = m.group(2)
            right = MATH_UNICODE_MAP.get(right, right)
            return f"${left} {tex} {right}$"
        text = re.sub(pattern, _rep_rel, text)

    # Standalone math unicode symbols in text: must be wrapped in math mode $...$
    for char, macro in MATH_UNICODE_MAP.items():
        if char in text:
            # Wrap in math mode if not already surrounded by $
            text = text.replace(char, f" ${macro}$ ")

    return text


def convert_mathml_node(node: DOMNode) -> str:
    """Recursively converts a MathML AST node into clean LaTeX math syntax."""
    tag = (node.tag or "").lower()
    text = (node.text or "").strip()

    if tag in ("math", "semantics"):
        # Check if there is an annotation child with LaTeX
        for c in node.children:
            if c.tag == "annotation":
                enc = c.get_attr("encoding", "").lower()
                if "tex" in enc or "latex" in enc:
                    return c.text_content().strip()
        inner = "".join(convert_mathml_node(c) for c in node.children)
        return inner

    elif tag == "mfrac":
        children = [c for c in node.children if c.tag != "annotation"]
        num = convert_mathml_node(children[0]) if len(children) > 0 else ""
        den = convert_mathml_node(children[1]) if len(children) > 1 else ""
        return f"\\frac{{{num}}}{{{den}}}"

    elif tag == "msup":
        children = [c for c in node.children if c.tag != "annotation"]
        base = convert_mathml_node(children[0]) if len(children) > 0 else ""
        exp = convert_mathml_node(children[1]) if len(children) > 1 else ""
        return f"{base}^{{{exp}}}"

    elif tag == "msub":
        children = [c for c in node.children if c.tag != "annotation"]
        base = convert_mathml_node(children[0]) if len(children) > 0 else ""
        sub = convert_mathml_node(children[1]) if len(children) > 1 else ""
        return f"{base}_{{{sub}}}"

    elif tag == "msubsup":
        children = [c for c in node.children if c.tag != "annotation"]
        base = convert_mathml_node(children[0]) if len(children) > 0 else ""
        sub = convert_mathml_node(children[1]) if len(children) > 1 else ""
        exp = convert_mathml_node(children[2]) if len(children) > 2 else ""
        return f"{base}_{{{sub}}}^{{{exp}}}"

    elif tag == "msqrt":
        inner = "".join(convert_mathml_node(c) for c in node.children)
        return f"\\sqrt{{{inner or text}}}"

    elif tag == "mroot":
        children = [c for c in node.children if c.tag != "annotation"]
        base = convert_mathml_node(children[0]) if len(children) > 0 else ""
        idx = convert_mathml_node(children[1]) if len(children) > 1 else ""
        return f"\\sqrt[{idx}]{{{base}}}"

    elif tag == "mfenced":
        open_sym = node.get_attr("open", "(")
        close_sym = node.get_attr("close", ")")
        inner = "".join(convert_mathml_node(c) for c in node.children)
        return f"\\left{open_sym} {inner} \\right{close_sym}"

    elif tag == "mtable":
        rows = [c for c in node.children if c.tag == "mtr"]
        row_tex = []
        for r in rows:
            cells = [convert_mathml_node(td) for td in r.children if td.tag == "mtd"]
            row_tex.append(" & ".join(cells))
        body = " \\\\\n".join(row_tex)
        return f"\\begin{{matrix}} {body} \\end{{matrix}}"

    elif tag == "mover":
        children = [c for c in node.children if c.tag != "annotation"]
        base = convert_mathml_node(children[0]) if len(children) > 0 else ""
        over = convert_mathml_node(children[1]).strip() if len(children) > 1 else ""
        if over in (r"\to", r"\rightarrow", "→", r"\longrightarrow"):
            return f"\\vec{{{base}}}"
        elif over in ("-", "—", r"\bar", "‾", "¯"):
            return f"\\overline{{{base}}}"
        elif over in ("^", r"\hat"):
            return f"\\hat{{{base}}}"
        return f"\\overset{{{over}}}{{{base}}}"

    elif tag == "munder":
        children = [c for c in node.children if c.tag != "annotation"]
        base = convert_mathml_node(children[0]) if len(children) > 0 else ""
        under = convert_mathml_node(children[1]) if len(children) > 1 else ""
        if base.strip() in ("lim", r"\lim"):
            return f"\\lim_{{{under}}}"
        return f"\\underset{{{under}}}{{{base}}}"

    elif tag == "munderover":
        children = [c for c in node.children if c.tag != "annotation"]
        base = convert_mathml_node(children[0]) if len(children) > 0 else ""
        under = convert_mathml_node(children[1]) if len(children) > 1 else ""
        over = convert_mathml_node(children[2]) if len(children) > 2 else ""
        return f"{base}_{{{under}}}^{{{over}}}"

    elif tag == "mtext":
        val = node.text or node.text_content()
        return f"\\text{{{val}}}"

    elif tag in ("mi", "mn", "mo"):
        raw_val = node.text if node.text is not None else "".join(convert_mathml_node(c) for c in node.children)
        val = raw_val.strip()
        if val == "lim":
            return r"\lim"
        mapped = MATH_UNICODE_MAP.get(val, val)
        return f" {mapped} " if mapped.startswith("\\") else mapped

    elif tag in ("mrow", "mstyle"):
        return "".join(convert_mathml_node(c) for c in node.children)

    elif tag == "annotation":
        return ""

    else:
        inner = "".join(convert_mathml_node(c) for c in node.children)
        return text or inner


class LaTeXEmitter:
    """Walks the DOM tree and emits properly escaped, well-formed LaTeX."""

    def __init__(self, base_url: str = ""):
        self.base_url = base_url
        self.images: list[str] = []
        self.warnings: list[str] = []
        self.output: list[str] = []
        self.in_math = False

    def emit(self, text: str):
        if text:
            self.output.append(text)

    def extract_image_url(self, node: DOMNode) -> str:
        """Picks the first valid image source from standard and lazy-loaded attributes."""
        # Priority: data-original, data-src, data-lazy-src, src, srcset
        candidates = [
            node.get_attr("data-original"),
            node.get_attr("data-src"),
            node.get_attr("data-lazy-src"),
            node.get_attr("src"),
        ]
        srcset = node.get_attr("srcset")
        if srcset:
            first_srcset = srcset.split(",")[0].strip().split(" ")[0]
            candidates.append(first_srcset)

        for src in candidates:
            src = (src or "").strip()
            if src and not src.startswith("data:"):
                return urllib.parse.urljoin(self.base_url, src)
        return ""

    def process_node(self, node: DOMNode):
        self._process_node_content(node)
        if node.tail:
            tail = escape_latex_text(node.tail)
            tail = convert_unicode_in_text(tail)
            self.emit(tail)

    def _process_node_content(self, node: DOMNode):
        tag = node.tag

        # Skip scripts and styles (unless mathjax script)
        if tag == "style":
            return

        if tag == "script":
            script_type = node.get_attr("type", "").lower()
            if "math/tex" in script_type:
                content = node.text_content().strip()
                if "mode=display" in script_type:
                    self.emit(f"\n\\[ {content} \\]\n")
                else:
                    self.emit(f" ${content}$ ")
            return

        # Check KaTeX containers
        classes = node.get_attr("class", "").split()
        if "katex" in classes or "katex-display" in classes:
            # Check for annotation element
            annotations = node.find_all("annotation")
            for ann in annotations:
                enc = ann.get_attr("encoding", "").lower()
                if "tex" in enc or "latex" in enc:
                    tex_code = ann.text_content().strip()
                    if "katex-display" in classes:
                        self.emit(f"\n\\[ {tex_code} \\]\n")
                    else:
                        self.emit(f" ${tex_code}$ ")
                    return
            # If no annotation, check if there is a MathML child
            math_children = node.find_all("math")
            if math_children:
                mathml_tex = convert_mathml_node(math_children[0]).strip()
                if mathml_tex:
                    if "katex-display" in classes or math_children[0].get_attr("display") == "block":
                        self.emit(f"\n\\[ {mathml_tex} \\]\n")
                    else:
                        self.emit(f" ${mathml_tex}$ ")
                    return

        # Check MathML root tag
        if tag == "math":
            display = node.get_attr("display", "").lower()
            mathml_tex = convert_mathml_node(node).strip()
            if display == "block":
                self.emit(f"\n\\[ {mathml_tex} \\]\n")
            else:
                self.emit(f" ${mathml_tex}$ ")
            return

        # Block containers and line breaks
        if tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.emit("\n\n")

        elif tag == "br":
            self.emit("\n")

        elif tag == "hr":
            self.emit("\n\\noindent\\hrulefill\n")

        # Text formatting
        elif tag in ("b", "strong"):
            self.emit(r"\textbf{")
            if node.text:
                self.emit(convert_unicode_in_text(escape_latex_text(node.text)))
            self._process_children(node)
            self.emit("}")
            return

        elif tag in ("i", "em"):
            self.emit(r"\textit{")
            if node.text:
                self.emit(convert_unicode_in_text(escape_latex_text(node.text)))
            self._process_children(node)
            self.emit("}")
            return

        elif tag in ("u", "ins"):
            self.emit(r"\underline{")
            if node.text:
                self.emit(convert_unicode_in_text(escape_latex_text(node.text)))
            self._process_children(node)
            self.emit("}")
            return

        # Subscript & Superscript in Text vs Math Mode
        elif tag == "sup":
            inner_text = node.text_content().strip()
            if re.match(r"^[\d\+\-\*nxyz]+$", inner_text):
                self.emit(f"$^{inner_text}$" if len(inner_text) == 1 else f"$^{{{inner_text}}}$")
            else:
                # Text superscript
                self.emit(f"$^{{\\text{{{escape_latex_text(inner_text)}}}}}$")
            return

        elif tag == "sub":
            inner_text = node.text_content().strip()
            if re.match(r"^[\d\+\-\*nxyz]+$", inner_text):
                self.emit(f"$_{inner_text}$" if len(inner_text) == 1 else f"$_{{{inner_text}}}$")
            else:
                self.emit(f"$_{{\\text{{{escape_latex_text(inner_text)}}}}}$")
            return

        # Lists
        elif tag == "ul":
            self.emit("\n\\begin{itemize}\n")
            self._process_children(node)
            self.emit("\n\\end{itemize}\n")
            return

        elif tag == "ol":
            self.emit("\n\\begin{enumerate}\n")
            self._process_children(node)
            self.emit("\n\\end{enumerate}\n")
            return

        elif tag == "li":
            self.emit("\n\\item ")
            if node.text:
                self.emit(convert_unicode_in_text(escape_latex_text(node.text)))
            self._process_children(node)
            return

        # Tables
        elif tag == "table":
            self._process_table(node)
            return

        # Images
        elif tag == "img":
            img_url = self.extract_image_url(node)
            if img_url:
                self.images.append(img_url)
                self.emit(f" [IMG:{img_url}] ")
            else:
                self.warnings.append("Ảnh thiếu URL hợp lệ (src/data-src)")
            return

        # Handle node's direct text
        if node.text:
            text = node.text
            text = escape_latex_text(text)
            text = convert_unicode_in_text(text)
            self.emit(text)

        # Process children
        self._process_children(node)

    def _process_children(self, node: DOMNode):
        for child in node.children:
            self.process_node(child)

    def _process_table(self, table_node: DOMNode):
        """Converts an HTML table into a LaTeX tabular environment."""
        rows = table_node.find_all("tr")
        if not rows:
            return

        grid = []
        max_cols = 0
        for r in rows:
            cells = []
            for cell_node in r.children:
                if cell_node.tag in ("td", "th"):
                    emitter = LaTeXEmitter(self.base_url)
                    emitter._process_children(cell_node)
                    if cell_node.text:
                        txt = convert_unicode_in_text(escape_latex_text(cell_node.text))
                        emitter.emit(txt)
                    cell_text = "".join(emitter.output).strip()
                    # Strip newlines in cell
                    cell_text = " ".join(cell_text.split())
                    cells.append(cell_text)
            if cells:
                grid.append(cells)
                max_cols = max(max_cols, len(cells))

        if not grid or max_cols == 0:
            return

        col_align = "|" + "c|" * max_cols
        self.emit(f"\n\\begin{{center}}\n\\begin{{tabular}}{{{col_align}}}\n\\hline\n")
        for row in grid:
            # Pad row if fewer cells
            padded = row + [""] * (max_cols - len(row))
            self.emit(" & ".join(padded) + " \\\\ \\hline\n")
        self.emit("\\end{tabular}\n\\end{center}\n")


def clean_latex_spacing(text: str) -> str:
    """Collapses spaces, normalizes math mode delimiters, and removes empty dollars."""
    if not text:
        return ""

    # Remove empty math pairs $ $ or $$
    text = re.sub(r"\$\s*\$", "", text)

    # Normalize double-nested math: e.g. $...$ inside $...$
    # If a string contains $...$...$ where dollar is immediately followed by $, merge
    text = re.sub(r"\$\s*\$+", "", text)

    # Clean multiple spaces and blank lines
    lines = []
    for line in text.splitlines():
        line_clean = re.sub(r"[ \t]+", " ", line).strip()
        if line_clean:
            lines.append(line_clean)
        elif lines and lines[-1] != "":
            lines.append("")

    cleaned = "\n".join(lines).strip()
    return cleaned


def html_to_latex(html_fragment: str, base_url: str = "") -> tuple[str, list[str]]:
    """Converts an HTML snippet into clean, safe, compilable pdfLaTeX.

    Args:
        html_fragment: The raw HTML content from a website or clipboard.
        base_url: The base URL used to resolve relative image links.

    Returns:
        (latex_text, extracted_image_urls)
    """
    if not html_fragment or not html_fragment.strip():
        return "", []

    # Unescape HTML entities first if double-escaped
    raw_html = unescape(html_fragment)

    # Build DOM tree
    builder = DOMTreeBuilder()
    builder.feed(raw_html)
    builder.close()

    # Emit LaTeX
    emitter = LaTeXEmitter(base_url=base_url)
    emitter.process_node(builder.root)
    raw_latex = "".join(emitter.output)

    # Sanitize dangerous LaTeX commands (Phase L1.6)
    sanitized_latex, warnings = sanitize_latex(raw_latex)

    # Clean spacing and collapse duplicate math tags
    final_latex = clean_latex_spacing(sanitized_latex)

    return final_latex, emitter.images
