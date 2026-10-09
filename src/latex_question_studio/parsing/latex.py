"""Non-expanding LaTeX scanner; original source spans are never normalized."""
from dataclasses import dataclass, field
import re

@dataclass(frozen=True)
class Diagnostic:
    message: str
    offset: int
    line: int
    column: int

@dataclass(frozen=True)
class Command:
    name: str
    start: int
    end: int
    depth: int

@dataclass
class ParsedQuestion:
    source: str
    start: int
    end: int
    environment: str
    question_type: str = "unknown"
    solution: str = ""
    answer: dict = field(default_factory=dict)
    assets: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def diagnostic(source, offset, message):
    return Diagnostic(message, offset, source.count("\n", 0, offset) + 1,
                      offset - source.rfind("\n", 0, offset))


def commands(source):
    i, depth = 0, 0
    while i < len(source):
        char = source[i]
        if char == '%':
            end = source.find('\n', i)
            i = len(source) if end < 0 else end + 1
            continue
        if char == '\\':
            start = i
            i += 1
            if i < len(source) and (source[i].isalpha() or source[i] == '@'):
                while i < len(source) and (source[i].isalpha() or source[i] == '@'):
                    i += 1
            elif i < len(source):
                i += 1
            name = source[start + 1:i]
            if name=='verb' and i<len(source) and source[i]=='*':name='verb*';i+=1
            yield Command(name, start, i, depth)
            if name in ('verb', 'verb*') and i < len(source):
                delimiter = source[i]
                stop = source.find(delimiter, i + 1)
                i = len(source) if stop < 0 else stop + 1
            continue
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        i += 1


def skip_space(source, i):
    while i < len(source):
        if source[i].isspace():
            i += 1
        elif source[i] == '%':
            end = source.find('\n', i)
            i = len(source) if end < 0 else end + 1
        else:
            break
    return i


def group(source, i, opening='{', closing='}'):
    i = skip_space(source, i)
    if i >= len(source) or source[i] != opening:
        raise ValueError(f"Expected {opening} at offset {i}")
    start, level = i, 1
    i += 1
    braces = 0
    while i < len(source):
        char = source[i]
        if char == '\\':
            i += 2
            continue
        if char == '%':
            end = source.find('\n', i)
            i = len(source) if end < 0 else end + 1
            continue
        if opening == '[':
            if char == '{': braces += 1
            if char == '}': braces -= 1
        if braces == 0:
            if char == opening: level += 1
            elif char == closing:
                level -= 1
                if level == 0:
                    return source[start + 1:i], i + 1, start
        i += 1
    raise ValueError(f"Unclosed {opening} at offset {start}")


def brace_error(source):
    i, stack = 0, []
    while i < len(source):
        if source[i] == '\\':
            match=re.match(r'\\verb\*?([^a-zA-Z\s])',source[i:])
            if match:
                stop=source.find(match.group(1),i+match.end());i=len(source) if stop<0 else stop+1
            else:i+=2
            continue
        if source[i] == '%':
            j = source.find('\n', i); i = len(source) if j < 0 else j + 1; continue
        if source[i] == '{': stack.append(i)
        elif source[i] == '}':
            if not stack: return i
            stack.pop()
        i += 1
    return stack[0] if stack else None


def analyze(item, whole_source=None):
    source = item.source
    macro_commands = list(commands(source))
    answer_seen=False
    for command in macro_commands:
        try:
            if command.name in ('choice','choiceTF','choiceTFt','shortans') and command.depth==0:
                if answer_seen:raise ValueError('Multiple answer macros; ambiguous question cannot be shuffled')
                answer_seen=True
            if command.name in ('loigiai', 'hdan') and command.depth == 0:
                item.solution = group(source, command.end)[0]
            elif command.name == 'includegraphics':
                cursor = skip_space(source, command.end)
                if cursor < len(source) and source[cursor] == '*': cursor += 1
                cursor = skip_space(source, cursor)
                if cursor < len(source) and source[cursor] == '[':
                    _, cursor, _ = group(source, cursor, '[', ']')
                item.assets.append(group(source, cursor)[0])
            elif command.name in ('choice', 'choiceTF', 'choiceTFt') and command.depth == 0:
                cursor = skip_space(source, command.end)
                if cursor < len(source) and source[cursor] == '[':
                    _, cursor, _ = group(source, cursor, '[', ']')
                options = []
                for _ in range(4):
                    value, cursor, start = group(source, cursor)
                    options.append({'source': value, 'start': start, 'end': cursor,
                                    'correct': any(c.name == 'True' for c in commands(value))})
                item.question_type = 'mcq' if command.name == 'choice' else 'true_false'
                item.answer = {'options': options, 'macro': command.name, 'macro_start': command.start, 'options_end': cursor}
                if item.question_type == 'mcq' and sum(o['correct'] for o in options) != 1:
                    raise ValueError('MCQ requires exactly one True option')
            elif command.name == 'shortans' and command.depth == 0:
                cursor = skip_space(source, command.end)
                if cursor < len(source) and source[cursor] == '[':
                    _, cursor, _ = group(source, cursor, '[', ']')
                value, _, _ = group(source, cursor)
                item.question_type, item.answer = 'short_answer', {'value': value}
        except ValueError as error:
            base = whole_source if whole_source is not None else source
            item.diagnostics.append(diagnostic(base, item.start + command.start, str(error)))
    if item.question_type == 'unknown' and not item.diagnostics:
        item.question_type = 'essay'
    bad_brace = brace_error(source)
    if bad_brace is not None:
        item.diagnostics.append(diagnostic(whole_source or source, item.start + bad_brace, 'Unbalanced brace'))
    return item


def parse_questions(source):
    items, stack, active = [], [], None
    supported = {'ex', 'ex*', 'vidu', 'vidu*'}
    for command in commands(source):
        if command.name not in ('begin', 'end'):
            continue
        try:
            name, end, _ = group(source, command.end)
        except ValueError:
            continue
        if command.name == 'begin':
            if name in supported and active is None and command.depth==0:
                active = (command.start, name, [])
                stack = []
            elif name in supported and active:
                active[2].append(diagnostic(source, command.start, 'Nested question environment'))
            if active:
                stack.append(name)
        elif active:
            if not stack or stack[-1] != name:
                active[2].append(diagnostic(source, command.start, f'Mismatched environment {name}'))
            else:
                stack.pop()
            if name == active[1]:
                start, environment, errors = active
                item = ParsedQuestion(source[start:end], start, end, environment, diagnostics=errors)
                items.append(analyze(item, source))
                active, stack = None, []
    if active:
        start, environment, errors = active
        errors.append(diagnostic(source, start, 'Unclosed question environment'))
        items.append(analyze(ParsedQuestion(source[start:], start, len(source), environment, diagnostics=errors), source))
    if not items:
        items.append(ParsedQuestion(source, 0, len(source), 'unknown', diagnostics=[diagnostic(source, 0, 'No supported question environment')]))
    return items


def normalized_source(source):
    # Whitespace collapse is only used for a duplicate suggestion; the raw source remains authoritative.
    # Preserve newlines because comment boundaries are semantically significant.
    return '\n'.join(re.sub(r'[ \t]+', ' ', line).rstrip() for line in source.replace('\r\n','\n').split('\n')).strip()
