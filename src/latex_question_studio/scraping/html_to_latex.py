"""HTML, MathJax, KaTeX and MathML to pdfLaTeX converter for MCPTest."""
from html import unescape
from html.parser import HTMLParser
import re
import urllib.parse
from xml.etree import ElementTree as ET


UNICODE_TO_LATEX = {
    "∈": r"\in",
    "∉": r"\notin",
    "⊂": r"\subset",
    "⊆": r"\subseteq",
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
    "≤": r"\le",
    "≥": r"\ge",
    "≠": r"\ne",
    "≈": r"\approx",
    "≡": r"\equiv",
    "→": r"\to",
    "⇒": r"\Rightarrow",
    "⇔": r"\Leftrightarrow",
    "∞": r"\infty",
    "±": r"\pm",
    "∓": r"\mp",
    "°": r"^\circ",
    "∠": r"\angle",
    "⊥": r"\perp",
    "∥": r"\parallel",
    "×": r"\times",
    "·": r"\cdot",
    "…": r"\dots",
    "∀": r"\forall",
    "∃": r"\exists",
    "∑": r"\sum",
    "∫": r"\int",
    "∂": r"\partial",
}


def convert_mathjax_scripts(html: str) -> str:
    """Converts MathJax script tags to LaTeX math mode."""
    # Display mode
    html = re.sub(
        r'<script[^>]*type=["\']math/tex;\s*mode=display["\'][^>]*>(.*?)</script>',
        lambda m: f"\n\\[ {unescape(m.group(1)).strip()} \\]\n",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Inline mode
    html = re.sub(
        r'<script[^>]*type=["\']math/tex["\'][^>]*>(.*?)</script>',
        lambda m: f" ${unescape(m.group(1)).strip()}$ ",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return html


def convert_katex_spans(html: str) -> str:
    """Extracts TeX source from KaTeX annotations."""
    # Pattern: <annotation encoding="application/x-tex">...</annotation>
    html = re.sub(
        r'<span[^>]*class=["\'][^"\']*katex[^"\']*["\'][^>]*>[\s\S]*?<annotation[^>]*encoding=["\']application/x-tex["\'][^>]*>(.*?)</annotation>[\s\S]*?</span>',
        lambda m: f" ${unescape(m.group(1)).strip()}$ ",
        html,
        flags=re.IGNORECASE,
    )
    return html


def convert_mathml_element(elem: ET.Element) -> str:
    """Recursively converts MathML element to LaTeX math."""
    tag = elem.tag.split("}")[-1].lower()
    text = (elem.text or "").strip()

    if tag == "math":
        inner = "".join(convert_mathml_element(c) for c in elem)
        return f"${inner}$"
    elif tag == "mfrac":
        children = list(elem)
        num = convert_mathml_element(children[0]) if len(children) > 0 else ""
        den = convert_mathml_element(children[1]) if len(children) > 1 else ""
        return f"\\frac{{{num}}}{{{den}}}"
    elif tag == "msup":
        children = list(elem)
        base = convert_mathml_element(children[0]) if len(children) > 0 else ""
        exp = convert_mathml_element(children[1]) if len(children) > 1 else ""
        return f"{base}^{{{exp}}}"
    elif tag == "msub":
        children = list(elem)
        base = convert_mathml_element(children[0]) if len(children) > 0 else ""
        sub = convert_mathml_element(children[1]) if len(children) > 1 else ""
        return f"{base}_{{{sub}}}"
    elif tag == "msubsup":
        children = list(elem)
        base = convert_mathml_element(children[0]) if len(children) > 0 else ""
        sub = convert_mathml_element(children[1]) if len(children) > 1 else ""
        exp = convert_mathml_element(children[2]) if len(children) > 2 else ""
        return f"{base}_{{{sub}}}^{{{exp}}}"
    elif tag == "msqrt":
        inner = "".join(convert_mathml_element(c) for c in elem)
        return f"\\sqrt{{{inner or text}}}"
    elif tag == "mroot":
        children = list(elem)
        base = convert_mathml_element(children[0]) if len(children) > 0 else ""
        idx = convert_mathml_element(children[1]) if len(children) > 1 else ""
        return f"\\sqrt[{idx}]{{{base}}}"
    elif tag in ("mi", "mn", "mo", "mtext"):
        val = text or "".join(convert_mathml_element(c) for c in elem)
        return UNICODE_TO_LATEX.get(val, val)
    elif tag in ("mrow", "mstyle"):
        return "".join(convert_mathml_element(c) for c in elem)
    else:
        return text or "".join(convert_mathml_element(c) for c in elem)


def convert_mathml_tags(html: str) -> str:
    """Replaces <math>...</math> blocks with LaTeX."""
    def _replace_math(match):
        raw = match.group(0)
        try:
            elem = ET.fromstring(raw)
            return convert_mathml_element(elem)
        except Exception:
            return raw

    return re.sub(r"<math[\s\S]*?</math>", _replace_math, html, flags=re.IGNORECASE)


class ContentCleaner(HTMLParser):
    """Strips HTML formatting, preserves paragraph breaks and maps formatting to LaTeX."""

    def __init__(self, base_url: str = ""):
        super().__init__()
        self.base_url = base_url
        self.output = []
        self.images = []
        self.in_script = False
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        tag = tag.lower()

        if tag in ("script", "style"):
            self.in_script = True
        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
            self.output.append("\n")
        elif tag == "br":
            self.output.append("\n")
        elif tag in ("b", "strong"):
            self.output.append(r"\textbf{")
        elif tag in ("i", "em"):
            self.output.append(r"\textit{")
        elif tag == "sup":
            self.output.append(r"^{")
        elif tag == "sub":
            self.output.append(r"_{")
        elif tag == "img":
            src = attr_dict.get("src", "").strip()
            if src:
                resolved_url = urllib.parse.urljoin(self.base_url, src)
                self.images.append(resolved_url)
                self.output.append(f" [IMG:{resolved_url}] ")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("script", "style"):
            self.in_script = False
        elif tag in ("b", "strong", "i", "em", "sup", "sub"):
            self.output.append("}")
        elif tag in ("p", "div", "li"):
            self.output.append("\n")

    def handle_data(self, data):
        if not self.in_script and not self.in_style:
            self.output.append(data)


def html_to_latex(html_fragment: str, base_url: str = "") -> tuple[str, list[str]]:
    """Converts an HTML snippet into clean LaTeX.
    
    Returns:
        (latex_text, extracted_image_urls)
    """
    if not html_fragment:
        return "", []

    # 1. Convert MathJax script tags
    text = convert_mathjax_scripts(html_fragment)

    # 2. Convert KaTeX spans
    text = convert_katex_spans(text)

    # 3. Convert MathML
    text = convert_mathml_tags(text)

    # 4. Strip HTML tags with formatting preservation
    cleaner = ContentCleaner(base_url)
    cleaner.feed(text)
    cleaner.close()
    raw_text = "".join(cleaner.output)

    # 5. Replace Unicode symbols with LaTeX macros
    for char, macro in UNICODE_TO_LATEX.items():
        if char in raw_text:
            # If in math mode, macro without extra $; if outside, wrap in math
            raw_text = raw_text.replace(char, f" {macro} ")

    # 6. Clean and collapse spaces
    cleaned_lines = []
    for line in raw_text.splitlines():
        l_str = re.sub(r"[ \t]+", " ", line).strip()
        if l_str:
            cleaned_lines.append(l_str)
    res_text = "\n".join(cleaned_lines)

    # Fix double-dollar signs like $$ $ -> $
    res_text = re.sub(r"\$\s*\$", "", res_text)

    return res_text.strip(), cleaner.images
