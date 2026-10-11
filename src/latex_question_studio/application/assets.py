"""Safe, source-preserving LaTeX resource resolution.

The resolver never rewrites source. It reports a deterministic mapping for the
caller to copy into the content-addressed store and keeps ambiguous or dynamic
references visible for review.
"""
from dataclasses import dataclass, asdict
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import shutil
import tempfile

from latex_question_studio.parsing.latex import commands, group, skip_space


IMAGE_EXTENSIONS = ('.pdf', '.png', '.jpg', '.jpeg')
RESOURCE_EXTENSIONS = IMAGE_EXTENSIONS + ('.tex', '.sty', '.cls')
STATUSES = ('RESOLVED', 'MISSING_ASSET', 'AMBIGUOUS_ASSET', 'NEEDS_REVIEW',
            'UNSUPPORTED_FORMAT', 'BLOCKED_PATH', 'CYCLE', 'DEPTH_LIMIT')


@dataclass(frozen=True)
class AssetReference:
    original_reference: str
    source_context: str
    dependency_type: str
    resolution_status: str
    candidates: tuple[str, ...] = ()
    selected_path: str | None = None
    content_hash: str | None = None
    bytes: int = 0
    message: str = ''

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ResourceGraph:
    root_source: str
    references: tuple[AssetReference, ...]
    files: tuple[str, ...]
    diagnostics: tuple[str, ...]

    @property
    def ready(self):
        return not any(reference.resolution_status != 'RESOLVED' for reference in self.references)

    def by_reference(self):
        result = {}
        for reference in self.references:
            result.setdefault(reference.original_reference, []).append(reference)
        return result

    def as_dict(self):
        return {'root_source': self.root_source,
                'references': [reference.as_dict() for reference in self.references],
                'files': list(self.files), 'diagnostics': list(self.diagnostics),
                'ready': self.ready}


class AssetResolver:
    def __init__(self, max_file_bytes=100 * 1024 * 1024, max_depth=24):
        self.max_file_bytes = max_file_bytes
        self.max_depth = max_depth

    @staticmethod
    def _safe_reference(value):
        value = value.strip().replace('\\', '/')
        path = PurePosixPath(value)
        if not value or path.is_absolute() or ':' in value or '..' in path.parts:
            return None
        return path

    @staticmethod
    def _graphicspath(source):
        prefixes = ['']
        for command in commands(source):
            if command.name != 'graphicspath' or command.depth != 0:
                continue
            try:
                value, _, _ = group(source, command.end)
                cursor = 0
                while cursor < len(value):
                    cursor = skip_space(value, cursor)
                    if cursor >= len(value):
                        break
                    folder, cursor, _ = group(value, cursor)
                    folder = folder.replace('\\', '/')
                    if folder and not folder.endswith('/'):
                        folder += '/'
                    if AssetResolver._safe_reference(folder.rstrip('/')) is not None or folder == '':
                        prefixes.append(folder)
            except ValueError:
                continue
        return prefixes

    @staticmethod
    def _argument(source, command):
        cursor = skip_space(source, command.end)
        if cursor < len(source) and source[cursor] == '*':
            cursor = skip_space(source, cursor + 1)
        if cursor < len(source) and source[cursor] == '[':
            _, cursor, _ = group(source, cursor, '[', ']')
        return group(source, cursor)[0]

    def _resolve(self, reference, base, prefixes, dependency_type):
        if any(token in reference for token in ('\\', '#', '$')):
            return AssetReference(reference, str(base), dependency_type, 'NEEDS_REVIEW',
                                  message='Tham chiếu động không thể xác định tĩnh.')
        safe = self._safe_reference(reference)
        if safe is None:
            return AssetReference(reference, str(base), dependency_type, 'BLOCKED_PATH',
                                  message='Đường dẫn tuyệt đối hoặc vượt thư mục nguồn.')
        suffix = safe.suffix.lower()
        if suffix and suffix not in RESOURCE_EXTENSIONS:
            return AssetReference(reference, str(base), dependency_type, 'UNSUPPORTED_FORMAT',
                                  message='Định dạng chưa được hỗ trợ: ' + suffix)
        suffixes = (suffix,) if suffix else IMAGE_EXTENSIONS if dependency_type == 'image' else ('.tex',)
        candidates = []
        for prefix in prefixes:
            for extension in suffixes:
                candidate_raw = base / (prefix + str(safe))
                if candidate_raw.is_symlink():
                    return AssetReference(reference, str(base), dependency_type, 'BLOCKED_PATH',
                                          message='Không nhận symlink trong cây tài nguyên.')
                candidate = candidate_raw.resolve()
                if not suffix:
                    candidate = candidate.with_suffix(extension)
                if candidate.is_file() and candidate not in candidates:
                    candidates.append(candidate)
        shown = tuple(str(candidate) for candidate in candidates)
        if len(candidates) > 1:
            return AssetReference(reference, str(base), dependency_type, 'AMBIGUOUS_ASSET', shown,
                                  message='Có nhiều file phù hợp; cần người dùng xác nhận.')
        if not candidates:
            return AssetReference(reference, str(base), dependency_type, 'MISSING_ASSET',
                                  message='Không tìm thấy tài nguyên trong phạm vi nguồn.')
        selected = candidates[0]
        try:
            relative = selected.relative_to(base.resolve())
        except ValueError:
            return AssetReference(reference, str(base), dependency_type, 'BLOCKED_PATH', shown,
                                  message='Tài nguyên nằm ngoài thư mục nguồn.')
        if selected.is_symlink() or any(part.is_symlink() for part in [base / part for part in relative.parts]):
            return AssetReference(reference, str(base), dependency_type, 'BLOCKED_PATH', shown,
                                  message='Không nhận symlink trong cây tài nguyên.')
        size = selected.stat().st_size
        if size > self.max_file_bytes:
            return AssetReference(reference, str(base), dependency_type, 'BLOCKED_PATH', shown,
                                  bytes=size, message='Tệp vượt giới hạn kích thước.')
        raw = selected.read_bytes()
        return AssetReference(reference, str(base), dependency_type, 'RESOLVED', shown,
                              str(selected), hashlib.sha256(raw).hexdigest(), size)

    def resolve(self, source, source_path, cancelled=lambda: False):
        source_path = Path(source_path).resolve()
        base = source_path if source_path.is_dir() else source_path.parent
        references, files, diagnostics, visiting = [], [], [], set()

        def visit(text, context, depth):
            if cancelled():
                raise InterruptedError('Đã hủy phân tích tài nguyên.')
            if depth > self.max_depth:
                diagnostics.append('DEPTH_LIMIT: ' + str(context))
                return
            context = Path(context).resolve()
            key = str(context)
            if key in visiting:
                diagnostics.append('CYCLE: ' + key)
                references.append(AssetReference(key, str(context), 'source', 'CYCLE', message='Vòng lặp input/include.'))
                return
            visiting.add(key)
            if context.is_file():
                files.append(str(context))
            local_base = context.parent if context.suffix or context.is_file() else context
            prefixes = self._graphicspath(text)
            for command in commands(text):
                if command.name == 'includegraphics':
                    try:
                        value = self._argument(text, command)
                        references.append(self._resolve(value, local_base, prefixes, 'image'))
                    except ValueError as error:
                        references.append(AssetReference('', str(context), 'image', 'NEEDS_REVIEW', message=str(error)))
                elif command.name in ('input', 'include'):
                    try:
                        value = self._argument(text, command)
                        result = self._resolve(value, local_base, prefixes, 'source')
                        references.append(result)
                        if result.resolution_status == 'RESOLVED' and result.selected_path:
                            child = Path(result.selected_path)
                            try:
                                child_text = child.read_text(encoding='utf-8-sig')
                            except UnicodeDecodeError:
                                references.append(AssetReference(value, str(context), 'source', 'NEEDS_REVIEW',
                                                                 message='File phụ không phải UTF-8.'))
                            else:
                                visit(child_text, child, depth + 1)
                    except ValueError as error:
                        references.append(AssetReference('', str(context), 'source', 'NEEDS_REVIEW', message=str(error)))
            visiting.remove(key)

        visit(source, source_path, 0)
        return ResourceGraph(str(source_path), tuple(references), tuple(dict.fromkeys(files)), tuple(diagnostics))


def serialize_graph(graph):
    return json.dumps(graph.as_dict(), ensure_ascii=False, sort_keys=True)


class AssetStore:
    """Content-addressed storage with batch staging and integrity checks."""
    def __init__(self, data_dir):
        self.root = Path(data_dir).resolve()
        self.asset_root = self.root / 'assets'
        self.staging_root = self.root / '.asset-staging'

    @staticmethod
    def _suffix(suffix):
        suffix = str(suffix or '').lower()
        return suffix if suffix in IMAGE_EXTENSIONS + ('.tex', '.sty', '.cls') else '.bin'

    def _paths(self, digest, suffix):
        suffix = self._suffix(suffix)
        relative = Path('assets') / digest[:2] / (digest + suffix)
        return relative, self.root / relative

    def stage_bytes(self, raw, suffix, batch_id):
        if not raw:
            raise ValueError('Tài nguyên rỗng')
        digest = hashlib.sha256(raw).hexdigest()
        relative, final = self._paths(digest, suffix)
        staging = self.staging_root / str(batch_id) / relative.relative_to('assets')
        staging.parent.mkdir(parents=True, exist_ok=True)
        if not staging.exists():
            fd, temporary = tempfile.mkstemp(prefix='.asset-', dir=staging.parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, staging)
            finally:
                Path(temporary).unlink(missing_ok=True)
        if hashlib.sha256(staging.read_bytes()).hexdigest() != digest:
            raise IOError('Checksum asset staging không đúng')
        return {'hash': digest, 'relative_path': relative.as_posix(), 'staging_path': str(staging),
                'bytes': len(raw)}

    def promote(self, staged):
        final = self.root / staged['relative_path']
        final.parent.mkdir(parents=True, exist_ok=True)
        source = Path(staged.get('staging_path', ''))
        if final.exists():
            if hashlib.sha256(final.read_bytes()).hexdigest() != staged['hash']:
                raise IOError('Asset kho đã tồn tại nhưng checksum khác')
        elif source.is_file():
            os.replace(source, final)
        else:
            raise FileNotFoundError('Thiếu asset staging: ' + staged['hash'])
        if hashlib.sha256(final.read_bytes()).hexdigest() != staged['hash']:
            raise IOError('Checksum asset kho không đúng')
        return final

    def cleanup_batch(self, batch_id):
        path = self.staging_root / str(batch_id)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    def verify(self, relative_path, content_hash):
        path = self.root / relative_path
        if not path.is_file():
            return {'ok': False, 'status': 'MISSING_ASSET', 'path': str(path)}
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        return {'ok': actual == content_hash, 'status': 'RESOLVED' if actual == content_hash else 'CORRUPT_ASSET',
                'path': str(path), 'actual_hash': actual, 'expected_hash': content_hash}

    def integrity_report(self, connection):
        rows = connection.execute('SELECT a.id,a.content_hash,a.relative_path,a.bytes,count(qa.question_id) AS links FROM assets a LEFT JOIN question_assets qa ON qa.asset_id=a.id GROUP BY a.id').fetchall()
        assets = []
        for row in rows:
            check = self.verify(row['relative_path'], row['content_hash'])
            assets.append({**dict(row), **check})
        manifest_refs = self._manifest_references(connection)
        for row in assets:
            row['manifest_referenced'] = row['relative_path'] in manifest_refs or row['content_hash'] in manifest_refs
        return {'asset_count': len(assets), 'bytes': sum(int(row['bytes'] or 0) for row in rows),
                'missing': sum(row['status'] == 'MISSING_ASSET' for row in assets),
                'corrupt': sum(row['status'] == 'CORRUPT_ASSET' for row in assets),
                'unlinked': sum(row['links'] == 0 and not row['manifest_referenced'] for row in assets),
                'manifest_references': len(manifest_refs), 'assets': assets}

    @staticmethod
    def _manifest_references(connection):
        references=set()
        for table,column in (('lessons','document_json'),('lesson_exports','snapshot_json'),('exam_versions','snapshot_json')):
            if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                continue
            for row in connection.execute(f'SELECT {column} FROM {table}'):
                text=str(row[0] or '')
                for token in text.replace('\\','/').replace('"',' ').replace("'",' ').split():
                    if 'assets/' in token:
                        candidate=token[token.find('assets/'):].strip(',]}')
                        references.add(candidate)
                        references.add(Path(candidate).stem)
        return references

    def garbage_collect(self, connection, dry_run=True):
        report = self.integrity_report(connection)
        removable = [row for row in report['assets'] if row['links'] == 0 and not row.get('manifest_referenced')]
        if not dry_run:
            for row in removable:
                path = self.root / row['relative_path']
                path.unlink(missing_ok=True)
                connection.execute('DELETE FROM assets WHERE id=?', (row['id'],))
            connection.commit()
        report['removable'] = [row['relative_path'] for row in removable]
        report['dry_run'] = dry_run
        return report
