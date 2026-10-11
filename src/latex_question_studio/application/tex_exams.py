"""Generate exam codes from a pinned TeX document, preserving section boundaries."""
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import random
import shutil
import tempfile
import uuid

from latex_question_studio.application.exams import shuffled_question
from latex_question_studio.application.lessons import student_source, without_comments
from latex_question_studio.parsing.latex import commands, group, parse_questions, skip_space
from latex_question_studio.preview.compiler import Compiler, MAPCLASS_PREAMBLE, default_profile_root


TYPE_NAMES = {'mcq': 'Trắc nghiệm', 'true_false': 'Đúng / sai',
              'short_answer': 'Trả lời ngắn', 'essay': 'Tự luận'}
HIDE_FILE_ANSWERS = r"""
\ifcsname True\endcsname\renewcommand{\True}{}\fi
\ifcsname loigiai\endcsname\renewcommand{\loigiai}[1]{}\fi
\ifcsname hdan\endcsname\renewcommand{\hdan}[1]{}\fi
\ifcsname shortans\endcsname\renewcommand{\shortans}[2][]{}\fi
\ifcsname hideansEX\endcsname\AtBeginDocument{\hideansEX{ex}}\fi
"""


def document_bounds(source):
    begins, ends = [], []
    for command in commands(source):
        if command.depth or command.name not in ('begin', 'end'):
            continue
        name, end, _ = group(source, command.end)
        if name == 'document':
            (begins if command.name == 'begin' else ends).append((command.start, end))
    if not begins and not ends:
        return None
    if len(begins) != 1 or len(ends) != 1 or begins[0][1] > ends[0][0]:
        raise ValueError('File phải có đúng một cặp begin/end document.')
    return begins[0][0], begins[0][1], ends[0][0], ends[0][1]


def graphics_references(source):
    for command in commands(source):
        if command.name != 'includegraphics':
            continue
        cursor = skip_space(source, command.end)
        if cursor < len(source) and source[cursor] == '*':
            cursor = skip_space(source, cursor + 1)
        if cursor < len(source) and source[cursor] == '[':
            _, cursor, _ = group(source, cursor, '[', ']')
        yield group(source, cursor)[0]


def section_break(gap):
    gap = without_comments(gap)
    edits = []
    for command in commands(gap):
        if command.name not in ('newpage', 'clearpage', 'pagebreak', 'nopagebreak',
                                'par', 'noindent', 'smallskip', 'medskip', 'bigskip', 'vspace', 'hspace'):
            return True
        end = command.end
        cursor = skip_space(gap, end)
        if command.name in ('vspace', 'hspace') and cursor < len(gap) and gap[cursor] == '*':
            cursor = skip_space(gap, cursor + 1)
        if cursor < len(gap) and gap[cursor] in '{[':
            opening = gap[cursor]
            _, end, _ = group(gap, cursor, opening, '}' if opening == '{' else ']')
        edits.append((command.start, end))
    for start, end in reversed(edits):
        gap = gap[:start] + gap[end:]
    return bool(gap.strip())


def set_exam_code(source, code):
    replacements = []
    for command in commands(source):
        if command.depth or command.name not in ('newcommand', 'renewcommand', 'providecommand', 'def'):
            continue
        cursor = skip_space(source, command.end)
        if cursor < len(source) and source[cursor] == '*':
            cursor = skip_space(source, cursor + 1)
        try:
            if cursor < len(source) and source[cursor] == '{':
                name, cursor, _ = group(source, cursor)
            else:
                target = next(commands(source[cursor:]))
                name = '\\' + target.name
                cursor += target.end
            if name not in (r'\made', r'\maDe', r'\madethi', r'\madeThi'):
                continue
            cursor = skip_space(source, cursor)
            if cursor < len(source) and source[cursor] == '[':
                continue
            _, end, start = group(source, cursor)
            replacements.append((start + 1, end - 1, code))
        except (ValueError, StopIteration):
            continue
    if replacements:
        for start, end, value in reversed(replacements):
            source = source[:start] + value + source[end:]
        return source
    bounds = document_bounds(source)
    offset = bounds[1] if bounds else 0
    label = '\n\\noindent\\textbf{' + code + '}\\par\n'
    return source[:offset] + label + source[offset:]


class TexExamService:
    def __init__(self, services):
        self.services = services
        self.root = services.config.data_dir / 'tex-exams'

    def load(self, path, cancelled=lambda: False):
        path = Path(path).resolve()
        raw = path.read_bytes()
        if len(raw) > 20 * 1024 * 1024:
            raise ValueError('File TeX vượt giới hạn 20 MB.')
        try:
            source = raw.decode('utf-8-sig')
        except UnicodeDecodeError as error:
            raise ValueError('File TeX cần mã hóa UTF-8; file gốc chưa bị sửa.') from error
        items = parse_questions(source)
        errors = [f'Dòng {d.line}: {d.message}' for item in items for d in item.diagnostics]
        if errors:
            raise ValueError('\n'.join(errors[:8]))
        if len(items) > 500:
            raise ValueError('Mỗi đề tối đa 500 câu.')
        bounds = document_bounds(source)
        if bounds and any(item.start < bounds[1] or item.end > bounds[2] for item in items):
            raise ValueError('Các câu phải nằm trong phần document của file TeX.')
        sections, slots = [], []
        previous = None
        for index, item in enumerate(items):
            if previous is None or item.question_type != previous.question_type or section_break(source[previous.end:item.start]):
                sections.append({'number': len(sections) + 1, 'type': item.question_type, 'indices': []})
            sections[-1]['indices'].append(index)
            slots.append({'section': len(sections), 'number': len(sections[-1]['indices'])})
            previous = item
        resources, assets = self._resources(path.parent, source, cancelled)
        if not bounds:
            profile_root = default_profile_root()
            for name in ('Class/MAPClass.cls', 'Packages/ex_test.sty'):
                logical = 'MAPClass.cls' if name.endswith('.cls') else name
                resources[logical] = {'raw': (profile_root / name).read_bytes(), 'kind': 'dependency'}
        digest = hashlib.sha256(raw)
        for name, entry in sorted(resources.items()):
            digest.update(name.encode('utf-8'))
            digest.update(entry['raw'])
        project = self.root / 'resources' / digest.hexdigest()
        for name, entry in resources.items():
            if cancelled():
                raise InterruptedError('Đã hủy đọc file TeX.')
            target = project / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_bytes(entry['raw'])
            entry['path'] = str(target)
        if cancelled():
            raise InterruptedError('Đã hủy đọc file TeX.')
        project.mkdir(parents=True, exist_ok=True)
        return {'source_path': str(path), 'source': source, 'source_sha256': hashlib.sha256(raw).hexdigest(),
                'resource_root': str(project), 'resources': {name: {k: v for k, v in entry.items() if k != 'raw'} for name, entry in resources.items()},
                'assets': {reference: str(project / name) for reference, name in assets.items()},
                'sections': sections, 'slots': slots, 'question_count': len(items), 'full_document': bool(bounds)}

    def _resources(self, folder, source, cancelled):
        resources, assets, visited = {}, {}, set()
        graphic_paths = ['']
        for command in commands(source):
            if command.name == 'graphicspath':
                value = group(source, command.end)[0]
                cursor = 0
                while skip_space(value, cursor) < len(value):
                    part, cursor, _ = group(value, cursor)
                    graphic_paths.append(part)

        def logical_path(name):
            value = PurePosixPath(name.replace('\\', '/'))
            if value.is_absolute() or '..' in value.parts or ':' in name:
                raise ValueError('Tài nguyên phải dùng đường dẫn tương đối trong thư mục đề: ' + name)
            return str(value)

        def scan(text, dependency=False):
            if cancelled():
                raise InterruptedError('Đã hủy đọc tài nguyên.')
            for command in commands(text):
                if command.name not in ('includegraphics', 'input', 'include', 'documentclass', 'usepackage', 'RequirePackage', 'LoadClass'):
                    continue
                cursor = skip_space(text, command.end)
                if cursor < len(text) and text[cursor] == '*':
                    cursor = skip_space(text, cursor + 1)
                if cursor < len(text) and text[cursor] == '[':
                    _, cursor, _ = group(text, cursor, '[', ']')
                if cursor >= len(text) or text[cursor] != '{':
                    if not dependency and command.name in ('input', 'include'):
                        raise ValueError('input/include cần đường dẫn đặt trong ngoặc nhọn.')
                    continue
                value = group(text, cursor)[0]
                if '\\' in value or '#' in value:
                    continue
                refs = value.split(',') if command.name in ('usepackage', 'RequirePackage') else [value]
                for reference in refs:
                    reference = reference.strip()
                    name = logical_path(reference)
                    image = command.name == 'includegraphics'
                    suffix = '' if image else '.cls' if command.name in ('documentclass', 'LoadClass') else '.sty' if command.name in ('usepackage', 'RequirePackage') else '.tex'
                    if suffix and not name.endswith(suffix) and (suffix != '.tex' or not Path(name).suffix):
                        name += suffix
                    prefixes = graphic_paths if image else ['', 'Class/'] if suffix == '.cls' else ['', 'Packages/'] if suffix == '.sty' else ['']
                    candidates = [(folder / (prefix + name), prefix + name) for prefix in prefixes]
                    if not image and suffix in ('.cls', '.sty'):
                        candidates += [(default_profile_root() / (prefix + name), name) for prefix in prefixes]
                    if image and not Path(name).suffix:
                        candidates = [(candidate.with_suffix(ext), logical + ext) for candidate, logical in candidates for ext in ('.pdf', '.png', '.jpg', '.jpeg')]
                    found = next(((candidate, logical) for candidate, logical in candidates if candidate.is_file()), None)
                    if found is None:
                        if not dependency and (image or command.name in ('input', 'include')):
                            raise ValueError('Thiếu tài nguyên: ' + reference)
                        continue
                    candidate, stored_name = found
                    stored_name = name if suffix in ('.cls', '.sty') else logical_path(stored_name)
                    raw = candidate.read_bytes()
                    previous_kind = resources.get(stored_name, {}).get('kind')
                    resources[stored_name] = {'raw': raw, 'kind': 'dependency' if not image or dependency else 'image'}
                    if previous_kind == 'dependency':
                        resources[stored_name]['kind'] = 'dependency'
                    if image:
                        assets[reference] = stored_name
                    if candidate.resolve() in visited:
                        continue
                    visited.add(candidate.resolve())
                    if not image:
                        try:
                            child = raw.decode('utf-8-sig')
                        except UnicodeDecodeError:
                            child = raw.decode('latin-1')
                        if suffix == '.tex' and any(item.environment != 'unknown' for item in parse_questions(child)):
                            raise ValueError('Câu hỏi qua input/include chưa hỗ trợ; chọn file chứa trực tiếp các câu ex/vidu.')
                        scan(child, True)
        scan(source)
        return resources, assets

    def generate(self, document, codes, seed=2027, shuffle_questions=True, shuffle_options=True, cancelled=lambda: False, progress=lambda a, b: None):
        if not codes or len(codes) > 100 or len({code.casefold() for code in codes}) != len(codes):
            raise ValueError('Cần 1 đến 100 mã đề không trùng nhau.')
        if any(not code or len(code) > 16 or not code.isascii() or not code.isalnum() for code in codes):
            raise ValueError('Mã đề chỉ gồm chữ và số, tối đa 16 ký tự.')
        items = parse_questions(document['source'])
        variants = []
        for number, code in enumerate(codes):
            if cancelled():
                raise InterruptedError('Đã hủy trộn mã đề.')
            rng = random.Random(hashlib.sha256(f'{seed}:{code}'.encode()).digest())
            order = list(range(len(items)))
            for section in document['sections']:
                indices = list(section['indices'])
                if shuffle_questions:
                    rng.shuffle(indices)
                for slot, original in zip(section['indices'], indices):
                    order[slot] = original
            questions, edits = [], []
            for index, original in enumerate(order):
                if cancelled():
                    raise InterruptedError('Đã hủy trộn mã đề.')
                shuffled = shuffled_question(items[original], rng, shuffle_options)
                edits.append((items[index].start, items[index].end, shuffled['source']))
                questions.append({**shuffled, **document['slots'][index], 'original_number': original + 1, 'type': items[original].question_type})
            source = document['source']
            for start, end, value in reversed(edits):
                source = source[:start] + value + source[end:]
            variants.append({'exam_code': code, 'source': set_exam_code(source, code), 'questions': questions})
            progress(number + 1, len(codes))
        return {'source_kind': 'tex_file', 'document': document, 'seed': seed,
                'shuffle_questions': shuffle_questions, 'shuffle_options': shuffle_options, 'variants': variants}

    def preview(self, batch, variant, solutions=False):
        source = variant['source']
        if not solutions:
            edits = [(item.start, item.end, student_source(item.source, hide_answers=True)) for item in parse_questions(source)]
            for start, end, value in reversed(edits):
                source = source[:start] + value + source[end:]
            source = without_comments(source)
        bounds = document_bounds(source)
        preamble = source[:bounds[0]] if bounds else MAPCLASS_PREAMBLE
        body = source[bounds[1]:bounds[2]] if bounds else source
        if not solutions:
            preamble += HIDE_FILE_ANSWERS
        profile = Path(batch['document']['resource_root']) / ('preview-' + hashlib.sha256(preamble.encode()).hexdigest()[:16] + '.tex')
        profile.write_text(preamble, encoding='utf-8')
        if not bounds:
            source = preamble + '\n\\begin{document}\n' + body + '\n\\end{document}\n'
        elif not solutions:
            source = preamble + source[bounds[0]:]
        return source, body, profile, batch['document']['assets']

    def export(self, batch, folder, pdf=True, solutions=False, engine='pdflatex', cancelled=lambda: False, progress=lambda a, b: None):
        folder = Path(folder).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / ('ma-de-' + uuid.uuid4().hex[:8])
        with tempfile.TemporaryDirectory(prefix='.trong-de-', dir=folder) as temporary:
            staging = Path(temporary)
            papers = staging / ('teacher' if solutions else 'student')
            papers.mkdir()
            for number, variant in enumerate(batch['variants']):
                if cancelled():
                    raise InterruptedError('Đã hủy xuất mã đề.')
                source, body, profile, assets = self.preview(batch, variant, solutions)
                references = set(graphics_references(source))
                used_images = {str(Path(assets[reference]).resolve()) for reference in references if reference in assets}
                for name, entry in batch['document']['resources'].items():
                    if entry['kind'] == 'image' and str(Path(entry['path']).resolve()) not in used_images:
                        continue
                    destination = papers / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(entry['path'], destination)
                tex_path = papers / ('de-' + variant['exam_code'] + '.tex')
                tex_path.write_text(source, encoding='utf-8')
                if pdf:
                    result = Compiler(self.services.config.data_dir, engine=engine, preamble_file=profile).compile(body, assets, cancelled)
                    if not result.ok:
                        if result.cancelled:
                            raise InterruptedError('Đã hủy xuất PDF.')
                        raise ValueError('Mã đề ' + variant['exam_code'] + ':\n' + result.log)
                    shutil.copyfile(result.pdf, tex_path.with_suffix('.pdf'))
                progress(number + 1, len(batch['variants']))
            mapping = []
            with (staging / 'dap-an.csv').open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['Mã đề', 'Phần', 'Câu', 'Câu gốc', 'Loại', 'Đáp án'])
                for variant in batch['variants']:
                    for question in variant['questions']:
                        answer = question['answer']
                        value = answer.get('correct_letter', answer.get('value', ' '.join('Đ' if v else 'S' for v in answer.get('truth', [])) or 'Tự luận'))
                        writer.writerow([variant['exam_code'], question['section'], question['number'], question['original_number'], TYPE_NAMES[question['type']], value])
                        mapping.append({'exam_code': variant['exam_code'], **{key: question[key] for key in ('section', 'number', 'original_number', 'type', 'permutation', 'answer')}})
            manifest = {'source_sha256': batch['document']['source_sha256'], 'seed': batch['seed'], 'mapping': mapping}
            (staging / 'doi-chieu-ma-de.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
            if cancelled():
                raise InterruptedError('Đã hủy xuất mã đề.')
            shutil.move(str(staging), str(target))
        return target
