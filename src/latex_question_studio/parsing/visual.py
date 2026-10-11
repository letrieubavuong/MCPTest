"""Lossless visual projection. Wrappers and opaque TeX retain their original bytes."""
from dataclasses import dataclass, field
import re

from latex_question_studio.parsing.latex import commands, group, skip_space


@dataclass
class VisualRun:
    raw: str
    text: str
    kind: str = 'text'
    style: dict = field(default_factory=dict)
    protected: bool = False


def escape_text(text):
    replacements = {'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}',
                    '$': r'\$', '%': r'\%', '&': r'\&', '#': r'\#',
                    '_': r'\_', '^': r'\textasciicircum{}', '~': r'\textasciitilde{}'}
    return ''.join(replacements.get(char, char) for char in text)


def tex_input_spans(text):
    """Recognize complete math and supported authoring commands."""
    spans=[];offset=0
    for run in visual_runs(text):
        if run.kind in ('math','display_math','diagram','image'):
            spans.append((offset,offset+len(run.raw)))
        offset+=len(run.raw)
    grouped={'section','subsection','subsubsection','textbf','textit','emph','underline','loigiai','hdan','shortans','choice','choiceTF','choiceTFt'}
    for command in commands(text):
        if command.name not in grouped:continue
        cursor=command.end
        if cursor<len(text) and text[cursor]=='*':cursor+=1
        cursor=skip_space(text,cursor)
        try:
            if cursor<len(text) and text[cursor]=='[':_,cursor,_=group(text,cursor,'[',']')
            for _ in range(4 if command.name in ('choice','choiceTF','choiceTFt') else 1):
                _,cursor,_=group(text,cursor)
            spans.append((command.start,cursor))
        except ValueError:continue
    selected=[];boundary=-1
    for start,end in sorted(spans,key=lambda pair:(pair[0],-pair[1])):
        if start>=boundary:selected.append((start,end));boundary=end
    return selected


def encode_visual_input(text):
    pieces=[];boundary=0
    for start,end in tex_input_spans(text):
        pieces.extend((escape_text(text[boundary:start]),text[start:end]));boundary=end
    pieces.append(escape_text(text[boundary:]))
    return ''.join(pieces)


def recover_literal_tex(source):
    """Recover only recognized markup previously stored through escape_text."""
    preserved=tex_input_spans(source)
    pattern=re.compile(r'\\(textbackslash|textasciicircum|textasciitilde)\{\}|\\([{}$%&#_])')
    decoded=[];ranges=[];boundary=0
    for match in pattern.finditer(source):
        for position in range(boundary,match.start()):
            decoded.append(source[position]);ranges.append((position,position+1))
        decoded.append({'textbackslash':'\\','textasciicircum':'^','textasciitilde':'~'}.get(match.group(1),match.group(2)))
        ranges.append((match.start(),match.end()));boundary=match.end()
    for position in range(boundary,len(source)):
        decoded.append(source[position]);ranges.append((position,position+1))
    text=''.join(decoded);edits=[]
    for start,end in tex_input_spans(text):
        raw_start,raw_end=ranges[start][0],ranges[end-1][1]
        if any(a<=raw_start and raw_end<=b for a,b in preserved):continue
        if source[raw_start:raw_end]!=text[start:end]:edits.append((raw_start,raw_end,text[start:end]))
    for start,end,replacement in reversed(edits):source=source[:start]+replacement+source[end:]
    return source


def formula_source(text):
    text=text.strip()
    if not text:return ''
    runs=visual_runs(text)
    if len(runs)==1 and runs[0].kind in ('math','display_math'):return text
    return '$'+text+'$'


def visual_runs(source):
    runs = []
    styles = {'textbf': {'bold': True}, 'textit': {'italic': True},
              'emph': {'italic': True}, 'underline': {'underline': True},
              'section': {'bold': True, 'size': 18},
              'subsection': {'bold': True, 'size': 15},
              'subsubsection': {'bold': True, 'size': 13}}

    def add(raw, text='', kind='anchor', style=None, protected=True):
        runs.append(VisualRun(raw, text, kind, dict(style or {}), protected))

    def opaque_end(text, command):
        cursor = command.end
        if cursor < len(text) and text[cursor] == '*':
            cursor += 1
        while True:
            start = skip_space(text, cursor)
            if start >= len(text) or text[start] not in '[{':
                break
            opening = text[start]
            _, cursor, _ = group(text, start, opening, ']' if opening == '[' else '}')
        return cursor

    def scan(text, style, depth=0):
        if depth > 64:
            add(text, 'LaTeX', 'opaque', style, False)
            return
        i = 0
        while i < len(text):
            start = i
            if text[i] == '%':
                end = text.find('\n', i)
                i = len(text) if end < 0 else end
                add(text[start:i])
                continue
            if text[i] == '$' or text.startswith((r'\(', r'\['), i):
                opening = '$$' if text.startswith('$$', i) else '$' if text[i] == '$' else text[i:i+2]
                closing = {'\\(': r'\)', '\\[': r'\]'}.get(opening, opening)
                stop = i + len(opening)
                while True:
                    end = text.find(closing, stop)
                    if end < 0:
                        i = len(text)
                        add(text[start:i], 'Công thức chưa đóng', 'opaque', style, False)
                        break
                    preceding = end - 1
                    while preceding >= 0 and text[preceding] == '\\':
                        preceding -= 1
                    if (end - preceding - 1) % 2 == 0:
                        i = end + len(closing)
                        add(text[start:i], 'Công thức', 'display_math' if opening in ('$$', r'\[') else 'math', style, False)
                        break
                    stop = end + len(closing)
                continue
            if text[i] == '\\':
                command = next(commands(text[i:]))
                name = command.name
                end = i + command.end
                try:
                    if len(name) == 1 and name in '{}$%&#_':
                        add(text[i:end], name, 'text', style, False)
                        i = end
                        continue
                    if name == '\\':
                        add(text[i:end], '\n', 'break', style)
                        i = end
                        continue
                    if name in styles or name in ('loigiai', 'hdan'):
                        cursor = end + (1 if end < len(text) and text[end] == '*' else 0)
                        value, finish, opening = group(text, cursor)
                        merged = {**style, **styles.get(name, {})}
                        add(text[i:opening+1], 'Lời giải' if name in ('loigiai', 'hdan') else '', 'heading' if name in ('loigiai', 'hdan') else 'anchor')
                        scan(value, merged, depth + 1)
                        add(text[finish-1:finish])
                        i = finish
                        continue
                    if name in ('choice', 'choiceTF', 'choiceTFt'):
                        cursor = skip_space(text, end)
                        if cursor < len(text) and text[cursor] == '[':
                            _, cursor, _ = group(text, cursor, '[', ']')
                        options = []
                        for number in range(4):
                            value, finish, opening = group(text, cursor)
                            options.append((cursor, opening, finish, value))
                            cursor = finish
                        boundary = i
                        for number, (_, opening, finish, value) in enumerate(options):
                            add(text[boundary:opening+1], (chr(65+number) if name == 'choice' else chr(97+number)) + '.', 'option')
                            scan(value, style, depth + 1)
                            add(text[finish-1:finish])
                            boundary = finish
                        i = cursor
                        continue
                    if name == 'shortans':
                        cursor = skip_space(text, end)
                        if cursor < len(text) and text[cursor] == '[':
                            _, cursor, _ = group(text, cursor, '[', ']')
                        value, finish, opening = group(text, cursor)
                        add(text[i:opening+1], 'Đáp án:', 'option')
                        scan(value, style, depth + 1)
                        add(text[finish-1:finish])
                        i = finish
                        continue
                    if name == 'True':
                        add(text[i:end], 'Đúng', 'correct')
                        i = end
                        continue
                    if name in ('begin', 'end'):
                        environment, finish, _ = group(text, end)
                        simple = ('ex', 'ex*', 'vidu', 'vidu*', 'center', 'itemize', 'enumerate')
                        if name == 'begin' and environment not in simple:
                            stack = 1
                            for nested in commands(text[finish:]):
                                if nested.name in ('begin', 'end'):
                                    nested_name, nested_end, _ = group(text[finish:], nested.end)
                                    if nested_name == environment:
                                        stack += 1 if nested.name == 'begin' else -1
                                        if stack == 0:
                                            i = finish + nested_end
                                            kind='diagram' if environment=='tikzpicture' else 'display_math' if environment in ('equation','equation*','align','align*','gather','gather*','displaymath') else 'opaque'
                                            add(text[start:i], environment, kind, style, False)
                                            break
                            else:
                                i = len(text)
                                add(text[start:i], environment, 'opaque', style, False)
                            continue
                        label = 'Câu hỏi' if environment.startswith('ex') else 'Ví dụ' if environment.startswith('vidu') else ''
                        if name == 'end':
                            label = ''
                        add(text[i:finish], label, 'heading' if label else 'anchor')
                        i = finish
                        continue
                    if name == 'item':
                        add(text[i:end], '•', 'option')
                        i = end
                        continue
                    if name in ('par', 'medskip', 'smallskip', 'bigskip', 'newpage', 'clearpage'):
                        add(text[i:end], '\n', 'break')
                        i = end
                        continue
                    if name in ('noindent', 'centering'):
                        add(text[i:end])
                        i = end
                        continue
                    if name in ('verb', 'verb*') and end < len(text):
                        stop = text.find(text[end], end + 1)
                        i = len(text) if stop < 0 else stop + 1
                    else:
                        i += opaque_end(text[start:], command)
                    add(text[start:i], 'Hình ảnh' if name == 'includegraphics' else '\\' + name, 'image' if name == 'includegraphics' else 'opaque', style, False)
                    continue
                except (ValueError, StopIteration):
                    add(text[i:end], '\\' + name, 'opaque', style, False)
                    i = end
                    continue
            if text[i] in '{}':
                add(text[i:i+1])
                i += 1
                continue
            while i < len(text) and text[i] not in '$\\%{}':
                i += 1
            add(text[start:i], text[start:i], 'text', style, False)

    scan(source, {})
    assert ''.join(run.raw for run in runs) == source
    return runs
