"""Script to import all Chapter 1 - Physics 12 questions and lessons into studio.db."""
import os
import sys
import glob
import re
import json
import uuid
import shutil
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.importing import ImportService, detect_cognitive_level
from latex_question_studio.application.lessons import LessonService, block, KINDS
from latex_question_studio.domain.curriculum import classification
from latex_question_studio.domain.question import Question
from latex_question_studio.persistence.analysis import record, PARSER_VERSION
from latex_question_studio.parsing.latex import parse_questions, normalized_source, ParsedQuestion
from latex_question_studio.application.assets import AssetResolver, AssetStore

TOPIC_DEFINITIONS = [
    # Lesson 1: Cấu trúc của chất. Sự chuyển thể
    ('curriculum:physics12:lesson:01:topic:01', 'curriculum:physics12:lesson:01', 'topic', 'Dạng 1: Chuyển động Brown & Mô hình động học phân tử', 'PHYSICS12-C01-B01-D01'),
    ('curriculum:physics12:lesson:01:topic:02', 'curriculum:physics12:lesson:01', 'topic', 'Dạng 2: Cấu tạo và cấu trúc các thể (rắn, lỏng, khí)', 'PHYSICS12-C01-B01-D02'),
    ('curriculum:physics12:lesson:01:topic:03', 'curriculum:physics12:lesson:01', 'topic', 'Dạng 3: Sự nóng chảy và sự đông đặc', 'PHYSICS12-C01-B01-D03'),
    ('curriculum:physics12:lesson:01:topic:04', 'curriculum:physics12:lesson:01', 'topic', 'Dạng 4: Sự bay hơi, sự sôi và sự ngưng tụ', 'PHYSICS12-C01-B01-D04'),

    # Lesson 2: Nội năng. Định luật I của nhiệt động lực học
    ('curriculum:physics12:lesson:02:topic:01', 'curriculum:physics12:lesson:02', 'topic', 'Dạng 1: Khái niệm nội năng & các cách biến đổi nội năng', 'PHYSICS12-C01-B02-D01'),
    ('curriculum:physics12:lesson:02:topic:02', 'curriculum:physics12:lesson:02', 'topic', 'Dạng 2: Định luật I của nhiệt động lực học (Q = ΔU + A)', 'PHYSICS12-C01-B02-D02'),
    ('curriculum:physics12:lesson:02:topic:03', 'curriculum:physics12:lesson:02', 'topic', 'Dạng 3: Động cơ nhiệt & hiệu suất', 'PHYSICS12-C01-B02-D03'),
    ('curriculum:physics12:lesson:02:topic:04', 'curriculum:physics12:lesson:02', 'topic', 'Dạng 4: Chuyển hóa cơ năng thành nội năng', 'PHYSICS12-C01-B02-D04'),

    # Lesson 3: Nhiệt độ. Thang nhiệt độ – nhiệt kế
    ('curriculum:physics12:lesson:03:topic:01', 'curriculum:physics12:lesson:03', 'topic', 'Dạng 1: Lí thuyết thang nhiệt độ & các loại nhiệt kế', 'PHYSICS12-C01-B03-D01'),
    ('curriculum:physics12:lesson:03:topic:02', 'curriculum:physics12:lesson:03', 'topic', 'Dạng 2: Tính toán và quy đổi các thang nhiệt độ', 'PHYSICS12-C01-B03-D02'),

    # Lesson 4: Nhiệt dung riêng
    ('curriculum:physics12:lesson:04:topic:01', 'curriculum:physics12:lesson:04', 'topic', 'Dạng 1: Lí thuyết nhiệt dung riêng', 'PHYSICS12-C01-B04-D01'),
    ('curriculum:physics12:lesson:04:topic:02', 'curriculum:physics12:lesson:04', 'topic', 'Dạng 2: Tính nhiệt lượng của một vật (Q = mcΔt)', 'PHYSICS12-C01-B04-D02'),
    ('curriculum:physics12:lesson:04:topic:03', 'curriculum:physics12:lesson:04', 'topic', 'Dạng 3: Phương trình cân bằng nhiệt - Bài toán truyền nhiệt', 'PHYSICS12-C01-B04-D03'),
    ('curriculum:physics12:lesson:04:topic:04', 'curriculum:physics12:lesson:04', 'topic', 'Dạng 4: Truyền nhiệt và thực hiện công', 'PHYSICS12-C01-B04-D04'),
    ('curriculum:physics12:lesson:04:topic:05', 'curriculum:physics12:lesson:04', 'topic', 'Dạng 5: Năng suất tỏa nhiệt của nhiên liệu & hiệu suất đun nấu', 'PHYSICS12-C01-B04-D05'),

    # Lesson 5: Nhiệt nóng chảy riêng
    ('curriculum:physics12:lesson:05:topic:01', 'curriculum:physics12:lesson:05', 'topic', 'Dạng 1: Lí thuyết nhiệt nóng chảy riêng', 'PHYSICS12-C01-B05-D01'),
    ('curriculum:physics12:lesson:05:topic:02', 'curriculum:physics12:lesson:05', 'topic', 'Dạng 2: Tính nhiệt nóng chảy riêng (Q = mλ) & đồ thị', 'PHYSICS12-C01-B05-D02'),

    # Lesson 6: Nhiệt hoá hơi riêng
    ('curriculum:physics12:lesson:06:topic:01', 'curriculum:physics12:lesson:06', 'topic', 'Dạng 1: Lí thuyết nhiệt hoá hơi riêng', 'PHYSICS12-C01-B06-D01'),
    ('curriculum:physics12:lesson:06:topic:02', 'curriculum:physics12:lesson:06', 'topic', 'Dạng 2: Tính nhiệt hoá hơi riêng (Q = mL) & đồ thị', 'PHYSICS12-C01-B06-D02'),

    # Lesson 7: Bài tập về vật lí nhiệt
    ('curriculum:physics12:lesson:07:topic:01', 'curriculum:physics12:lesson:07', 'topic', 'Dạng 1: Bài toán biến đổi nhiệt phức hợp nhiều giai đoạn', 'PHYSICS12-C01-B07-D01'),
    ('curriculum:physics12:lesson:07:topic:02', 'curriculum:physics12:lesson:07', 'topic', 'Dạng 2: Bài toán bảo toàn và chuyển hóa năng lượng toàn phần', 'PHYSICS12-C01-B07-D02'),
]

def prepare_images():
    img_dir = Path('3L1/Images')
    target_dir = Path('3L1/Exercise/Images')
    if not target_dir.exists():
        shutil.copytree(img_dir, target_dir)
        print(f"Copied {img_dir} to {target_dir}")
    # Remove conflicting duplicate extensions in exercise images
    for dup in [target_dir / 'bongban.jpeg', target_dir / '2024_05_29_ddddee3750d8eb1e627bg-13.PNG']:
        if dup.exists():
            dup.unlink()
            print(f"Removed redundant image candidate: {dup.name}")

def ensure_topics(services):
    with services.database.transaction() as c:
        for node_id, parent_id, kind, name, code in TOPIC_DEFINITIONS:
            c.execute("INSERT OR REPLACE INTO taxonomy_nodes VALUES (?,?,?,?,?,NULL)",
                      (node_id, parent_id, kind, name, code))
    print(f"Ensured {len(TOPIC_DEFINITIONS)} topic nodes in taxonomy_nodes.")

def split_compound_questions(content: str) -> str:
    """Split compound questions containing \\begin{chc}...\\end{chc} into individual \\begin{ex}."""
    pattern = re.compile(r'\\begin\{ex\}(.*?)\\begin\{chc\}(.*?)\\end\{ex\}', re.DOTALL)
    def replacer(match):
        stem = match.group(1).strip()
        body = '\\begin{chc}' + match.group(2)
        # Find all chc blocks
        chcs = re.findall(r'\\begin\{chc\}(.*?)\\end\{chc\}', body, re.DOTALL)
        if not chcs:
            return match.group(0)
        result = []
        for c in chcs:
            single = f"\\begin{{ex}}\n{stem}\n{c.strip()}\n\\end{{ex}}\n"
            result.append(single)
        return '\n'.join(result)

    content = pattern.sub(replacer, content)
    # Fix Error 4: missing \True in "Khái niệm nhiệt độ có thể được gán cho chân không"
    content = content.replace(
        '{Không, vì nhiệt độ là đại lượng đặc trưng cho mức độ chuyển động nhiệt của các phân tử, trong chân không không có phân tử}',
        '{\\True Không, vì nhiệt độ là đại lượng đặc trưng cho mức độ chuyển động nhiệt của các phân tử, trong chân không không có phân tử}'
    )
    return content

def classify_question(source: str, origin_filename: str, origin_section: str = "") -> str:
    """Return the most specific topic taxonomy ID for a question."""
    lower = source.lower()
    fn = origin_filename.lower()
    sec = origin_section.lower()

    # 1. Lesson 04: Nhiệt dung riêng
    if '3l1-5' in fn or 'nhiệt dung riêng' in sec:
        if '3l1-5.5' in fn or 'bếp' in lower or 'xăng' in lower or 'dầu' in lower or 'năng suất tỏa nhiệt' in lower or 'nhiên liệu' in lower:
            return 'curriculum:physics12:lesson:04:topic:05'
        if '3l1-5.4' in fn or 'cơ năng' in lower or 'thực hiện công' in lower or 'rơi từ độ cao' in lower or 'đạn' in lower:
            return 'curriculum:physics12:lesson:04:topic:04'
        if '3l1-5.3' in fn or 'cân bằng nhiệt' in lower or 'thau' in lower or 'thỏi đồng' in lower or 'trao đổi nhiệt' in lower:
            return 'curriculum:physics12:lesson:04:topic:03'
        if '3l1-5.2' in fn or 'j/kg.k' in lower or 'tính nhiệt lượng' in lower or 'cung cấp nhiệt lượng' in lower:
            return 'curriculum:physics12:lesson:04:topic:02'
        return 'curriculum:physics12:lesson:04:topic:01'

    # 2. Lesson 05 & 06 & 07: Nhiệt nóng chảy riêng, Nhiệt hóa hơi riêng, Bài tập tổng hợp
    if '3l1-6' in fn or 'nóng chảy riêng' in sec or 'hóa hơi riêng' in sec or 'nóng chảy' in sec:
        if ('nóng chảy' in lower and 'hóa hơi' in lower) or 'tổng hợp cả quá trình' in lower:
            return 'curriculum:physics12:lesson:07:topic:01'
        if '3l1-6.3' in fn or 'hóa hơi' in lower or 'bay hơi' in lower or 'ấm điện' in lower or 'sôi' in lower:
            if 'j/kg' in lower or 'l =' in lower or 'tính' in lower:
                return 'curriculum:physics12:lesson:06:topic:02'
            return 'curriculum:physics12:lesson:06:topic:01'
        if '3l1-6.2' in fn or 'nóng chảy' in lower or 'nước đá' in lower or 'băng' in lower or 'thép' in lower or '\\lambda' in lower:
            if 'j/kg' in lower or '\\lambda' in lower or 'tính' in lower:
                return 'curriculum:physics12:lesson:05:topic:02'
            return 'curriculum:physics12:lesson:05:topic:01'
        return 'curriculum:physics12:lesson:05:topic:01'

    # 3. Lesson 03: Nhiệt độ, thang nhiệt độ
    if '3l1-4' in fn or 'nhiệt độ' in sec:
        if '3l1-4.2' in fn or 'kelvin' in lower or 'fahrenheit' in lower or 'celsius' in lower or '^\\circ f' in lower or '^\\circ c' in lower or 'quy đổi' in lower:
            return 'curriculum:physics12:lesson:03:topic:02'
        return 'curriculum:physics12:lesson:03:topic:01'

    # 4. Lesson 02: Nội năng & Định luật 1 NĐLH
    if '3l1-3' in fn or 'nội năng' in sec or 'định luật 1' in sec:
        if 'cơ năng' in lower or 'va chạm' in lower or 'vật rơi' in lower:
            return 'curriculum:physics12:lesson:02:topic:04'
        if '3l1-3.4' in fn or 'hiệu suất' in lower or 'động cơ nhiệt' in lower or 'q_1' in lower or 'q_2' in lower:
            return 'curriculum:physics12:lesson:02:topic:03'
        if '3l1-3.2' in fn or 'xi-lanh' in lower or 'pit-tông' in lower or 'nhận nhiệt' in lower or 'sinh công' in lower or '\\delta u' in lower or 'công $a$' in lower:
            return 'curriculum:physics12:lesson:02:topic:02'
        return 'curriculum:physics12:lesson:02:topic:01'

    # 5. Lesson 01: Cấu trúc chất & Sự chuyển thể
    if '3l1-2' in fn or 'chuyển thể' in sec:
        if 'bay hơi' in lower or 'ngưng tụ' in lower or 'sôi' in lower:
            return 'curriculum:physics12:lesson:01:topic:04'
        return 'curriculum:physics12:lesson:01:topic:03'

    if '3l1-1' in fn or 'cấu trúc của chất' in sec:
        if 'nóng chảy' in lower or 'đông đặc' in lower:
            return 'curriculum:physics12:lesson:01:topic:03'
        if 'bay hơi' in lower or 'sôi' in lower or 'ngưng tụ' in lower:
            return 'curriculum:physics12:lesson:01:topic:04'
        if 'brown' in lower or 'động học' in lower:
            return 'curriculum:physics12:lesson:01:topic:01'
        return 'curriculum:physics12:lesson:01:topic:02'

    # Default fallback to Lesson 07
    return 'curriculum:physics12:lesson:07:topic:01'


def collect_raw_questions():
    """Gather parsed questions from all relevant files in 3L1/Exercise."""
    exercise_files = sorted(glob.glob('3L1/Exercise/*.tex'))
    raw_list = []
    
    # Priority order: split files first, then master file
    split_files = [f for f in exercise_files if os.path.basename(f).startswith('3L1-') and not any(x in f for x in ('DESKTOP', 'GPT'))]
    extra_files = [f for f in exercise_files if any(x in f for x in ('DESKTOP', 'GPT'))]
    master_file = [f for f in exercise_files if os.path.basename(f) == '3L1.tex']
    
    ordered_files = split_files + extra_files + master_file
    print(f"Processing {len(ordered_files)} files in priority order...")
    
    for f in ordered_files:
        fname = os.path.basename(f)
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()
            
        content = split_compound_questions(content)
        
        # Check sections if master file
        if fname == '3L1.tex':
            parts = re.split(r'\\section\*?\{([^}]+)\}', content)
            for i in range(1, len(parts), 2):
                sec_title = parts[i]
                sec_body = parts[i+1]
                qs = parse_questions(sec_body)
                for q in qs:
                    raw_list.append((q, fname, sec_title, Path(f).resolve()))
        else:
            qs = parse_questions(content)
            for q in qs:
                raw_list.append((q, fname, "", Path(f).resolve()))
                
    print(f"Collected {len(raw_list)} raw parsed questions across all sources.")
    return raw_list


def import_questions_to_db(services):
    """Import all collected unique questions into the database."""
    resolver = AssetResolver()
    store = AssetStore(services.config.data_dir)
    
    # Pre-load existing normalized hashes from database
    existing_hashes = set()
    with services.database.connect() as c:
        for row in c.execute("SELECT normalized_hash FROM question_analysis"):
            existing_hashes.add(row[0])
    print(f"Found {len(existing_hashes)} existing questions in database.")
    
    raw_questions = collect_raw_questions()
    
    taxonomy_nodes_lookup = {}
    with services.database.connect() as c:
        nodes = [dict(r) for r in c.execute('SELECT t.*,p.subject AS profile_subject,p.grade AS profile_grade FROM taxonomy_nodes t LEFT JOIN curriculum_profiles p ON p.root_id=t.id')]
        for n in nodes:
            taxonomy_nodes_lookup[n['id']] = classification(nodes, n['id'])

    imported_count = 0
    skipped_duplicates = 0
    error_count = 0
    
    seen_in_batch = set(existing_hashes)
    now = datetime.now(timezone.utc).isoformat()
    
    # Collect questions per lesson for Lesson creation later
    questions_by_lesson = {f'curriculum:physics12:lesson:{i:02d}': [] for i in range(1, 8)}
    
    with services.database.transaction() as conn:
        for q, fname, sec_title, fpath in raw_questions:
            norm_hash = hashlib.sha256(normalized_source(q.source).encode()).hexdigest()
            if norm_hash in seen_in_batch:
                skipped_duplicates += 1
                continue
                
            if q.diagnostics:
                error_count += 1
                continue
                
            seen_in_batch.add(norm_hash)
            
            # Resolve taxonomy
            topic_id = classify_question(q.source, fname, sec_title)
            class_vals = dict(taxonomy_nodes_lookup.get(topic_id, {}))
            class_vals['taxonomy_id'] = topic_id
            
            cog_level = detect_cognitive_level(q.source, q.question_type) or 'TH'
            class_vals['cognitive_level'] = cog_level
            
            # Resolve assets
            graph = resolver.resolve(q.source, fpath, lambda: False)
            graph_by_ref = graph.by_reference()
            assets = []
            for ref in q.assets:
                res = next((e for e in graph_by_ref.get(ref, ()) if e.dependency_type == 'image'), None)
                if res and res.resolution_status == 'RESOLVED' and res.selected_path:
                    raw_bytes = Path(res.selected_path).read_bytes()
                    h = hashlib.sha256(raw_bytes).hexdigest()
                    stored = store.stage_bytes(raw_bytes, Path(res.selected_path).suffix.lower(), 'import')
                    store.promote(stored)
                    assets.append({'ref': ref, 'hash': h, 'rel': stored['relative_path'], 'bytes': len(raw_bytes)})
            
            # Insert question
            q_id = str(uuid.uuid4())
            conn.execute('INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?)',
                         (q_id, q.source, q.question_type, q.solution, None, cog_level, 1, now, now))
                         
            meta_json = json.dumps({'answer': q.answer, 'environment': q.environment, 'source_origin': fname, **class_vals}, ensure_ascii=False)
            conn.execute('INSERT INTO question_metadata VALUES (?,?)', (q_id, meta_json))
            conn.execute('INSERT INTO question_taxonomy VALUES (?,?)', (q_id, topic_id))
            
            snapshot = {'id': q_id, 'latex_source': q.source, 'question_type': q.question_type,
                        'solution': q.solution, 'cognitive_level': cog_level, 'revision': 1, 'metadata': json.loads(meta_json)}
            conn.execute('INSERT INTO question_revisions VALUES (?,?,?,?)',
                         (q_id, 1, json.dumps(snapshot, ensure_ascii=False), now))
                         
            # Analysis cache
            cached = [ParsedQuestion(q.source, 0, len(q.source), q.environment, q.question_type, q.solution, q.answer, q.assets, [])]
            record(conn, q_id, q.source, cached)
            
            # Assets
            for a in assets:
                conn.execute('INSERT OR IGNORE INTO assets VALUES (?,?,?,?)', (a['hash'], a['hash'], a['rel'], a['bytes']))
                conn.execute('INSERT INTO question_assets(question_id,asset_id,original_reference,source_context,dependency_type,resolution_status,candidates_json) VALUES (?,?,?,?,?,?,?)',
                             (q_id, a['hash'], a['ref'], 'source', 'image', 'RESOLVED', '[]'))
                             
            imported_count += 1
            
            # Find lesson id
            # Parent of topic_id is lesson_id
            lesson_id = ':'.join(topic_id.split(':')[:4])
            if lesson_id in questions_by_lesson:
                questions_by_lesson[lesson_id].append({
                    'id': q_id, 'source': q.source, 'type': q.question_type,
                    'topic_id': topic_id, 'cog': cog_level
                })
                
    print(f"\n=== Question Import Summary ===")
    print(f"Successfully imported: {imported_count} questions")
    print(f"Skipped duplicates: {skipped_duplicates}")
    print(f"Skipped with diagnostics: {error_count}")
    return questions_by_lesson


def create_chapter1_lessons(services, questions_by_lesson):
    """Create complete pedagogical lessons for Chapter 1 - Physics 12."""
    lesson_service = LessonService(services)
    
    lesson_configs = [
        {
            'id': 'curriculum:physics12:lesson:01',
            'title': 'Bài 1: Cấu trúc của chất. Sự chuyển thể',
            'theory_text': r"""\begin{itemize}
    \item \textbf{Mô hình động học phân tử:} Các chất được cấu tạo từ các hạt riêng biệt gọi là phân tử. Các phân tử chuyển động không ngừng (chuyển động nhiệt). Tốc độ chuyển động càng nhanh thì nhiệt độ của vật càng cao. Giữa các phân tử có lực tương tác (hút và đẩy).
    \item \textbf{Cấu trúc các thể của chất:}
    \begin{itemize}
        \item \textit{Thể rắn:} Các phân tử ở rất gần nhau, dao động quanh vị trí cân bằng cố định. Thể tích và hình dạng xác định. Gồm chất rắn kết tinh (có nhiệt độ nóng chảy xác định) và chất rắn vô định hình (không có nhiệt độ nóng chảy xác định).
        \item \textit{Thể lỏng:} Các phân tử ở gần nhau, dao động quanh các vị trí cân bằng có thể dịch chuyển. Thể tích xác định, hình dạng không xác định.
        \item \textit{Thể khí:} Các phân tử ở rất xa nhau, chuyển động hỗn loạn hỗn độn không ngừng. Không có hình dạng và thể tích xác định, chiếm toàn bộ thể tích bình chứa.
    \end{itemize}
    \item \textbf{Các quá trình chuyển thể:} Nóng chảy $\leftrightarrow$ Đông đặc; Hóa hơi (bay hơi, sôi) $\leftrightarrow$ Ngưng tụ; Thăng hoa $\leftrightarrow$ Ngưng kết.
\end{itemize}""",
            'methods': [
                ('Dạng 1: Chuyển động Brown & Mô hình động học phân tử', 'curriculum:physics12:lesson:01:topic:01'),
                ('Dạng 2: Cấu trúc và đặc điểm các thể (rắn, lỏng, khí)', 'curriculum:physics12:lesson:01:topic:02'),
                ('Dạng 3: Sự nóng chảy và sự đông đặc', 'curriculum:physics12:lesson:01:topic:03'),
                ('Dạng 4: Sự bay hơi, sự ngưng tụ và sự sôi', 'curriculum:physics12:lesson:01:topic:04'),
            ]
        },
        {
            'id': 'curriculum:physics12:lesson:02',
            'title': 'Bài 2: Nội năng. Định luật I của nhiệt động lực học',
            'theory_text': r"""\begin{itemize}
    \item \textbf{Nội năng:} Tổng động năng chuyển động nhiệt và thế năng tương tác của các phân tử cấu tạo nên vật: $U = E_đ + E_t$. Nội năng phụ thuộc vào nhiệt độ và thể tích của vật: $U = f(T, V)$.
    \item \textbf{Các cách làm biến đổi nội năng:}
    \begin{itemize}
        \item \textit{Thực hiện công:} Có sự chuyển hóa từ cơ năng thành nội năng (hoặc ngược lại).
        \item \textit{Truyền nhiệt:} Không có sự chuyển hóa năng lượng, chỉ có sự truyền nội năng từ vật này sang vật khác. Số đo độ biến thiên nội năng trong quá trình truyền nhiệt gọi là nhiệt lượng ($Q$).
    \end{itemize}
    \item \textbf{Định luật I của nhiệt động lực học:} $\Delta U = Q + A$.
    \item \textbf{Quy ước dấu:}
    \begin{itemize}
        \item $Q > 0$: Hệ nhận nhiệt lượng; $Q < 0$: Hệ tỏa nhiệt lượng.
        \item $A > 0$: Hệ nhận công; $A < 0$: Hệ sinh công.
    \end{itemize}
    \item \textbf{Động cơ nhiệt:} Thiết bị biến đổi nội năng của nhiên liệu thành cơ năng. Hiệu suất: $H = \dfrac{|A|}{Q_1} = \dfrac{Q_1 - Q_2}{Q_1} < 1$.
\end{itemize}""",
            'methods': [
                ('Dạng 1: Khái niệm nội năng & các cách biến đổi nội năng', 'curriculum:physics12:lesson:02:topic:01'),
                ('Dạng 2: Định luật I của nhiệt động lực học (Q = ΔU + A)', 'curriculum:physics12:lesson:02:topic:02'),
                ('Dạng 3: Động cơ nhiệt & hiệu suất động cơ nhiệt', 'curriculum:physics12:lesson:02:topic:03'),
                ('Dạng 4: Chuyển hóa cơ năng thành nội năng', 'curriculum:physics12:lesson:02:topic:04'),
            ]
        },
        {
            'id': 'curriculum:physics12:lesson:03',
            'title': 'Bài 3: Nhiệt độ. Thang nhiệt độ – nhiệt kế',
            'theory_text': r"""\begin{itemize}
    \item \textbf{Khái niệm nhiệt độ:} Đại lượng vật lí đặc trưng cho mức độ chuyển động nhiệt hỗn loạn của các phân tử cấu tạo nên vật. Khi hai vật có cùng nhiệt độ thì chúng ở trạng thái cân bằng nhiệt.
    \item \textbf{Thang đo nhiệt độ:}
    \begin{itemize}
        \item \textit{Thang Celsius ($^\circ\text{C}$):} Điểm đóng băng của nước tinh khiết là $0^\circ\text{C}$, điểm sôi là $100^\circ\text{C}$.
        \item \textit{Thang Kelvin ($\text{K}$):} Nhiệt độ tuyệt đối. Độ không tuyệt đối ($0\text{K}$) là nhiệt độ thấp nhất mà vật chất có thể đạt tới. Công thức: $T(\text{K}) = t(^\circ\text{C}) + 273,15$. Lưu ý: $\Delta T = \Delta t$.
        \item \textit{Thang Fahrenheit ($^\circ\text{F}$):} $t(^\circ\text{F}) = 1,8 \cdot t(^\circ\text{C}) + 32$.
    \end{itemize}
    \item \textbf{Nhiệt kế:} Thiết bị dùng để đo nhiệt độ, hoạt động dựa trên sự phụ thuộc của một số tính chất vật lí theo nhiệt độ (sự dãn nở vì nhiệt của chất lỏng, điện trở của kim loại hoặc bán dẫn, bức xạ nhiệt,...).
\end{itemize}""",
            'methods': [
                ('Dạng 1: Lí thuyết thang nhiệt độ & các loại nhiệt kế', 'curriculum:physics12:lesson:03:topic:01'),
                ('Dạng 2: Tính toán và quy đổi các thang nhiệt độ', 'curriculum:physics12:lesson:03:topic:02'),
            ]
        },
        {
            'id': 'curriculum:physics12:lesson:04',
            'title': 'Bài 4: Nhiệt dung riêng',
            'theory_text': r"""\begin{itemize}
    \item \textbf{Định nghĩa nhiệt dung riêng:} Nhiệt dung riêng ($c$) của một chất là nhiệt lượng cần truyền cho $1\text{kg}$ chất đó để nhiệt độ của nó tăng thêm $1\text{K}$ (hoặc $1^\circ\text{C}$). Đơn vị: $\text{J}/(\text{kg}\cdot\text{K})$.
    \item \textbf{Công thức tính nhiệt lượng:} $Q = mc\Delta t = mc(t_2 - t_1)$.
    \item \textbf{Phương trình cân bằng nhiệt:} $Q_{\text{tỏa}} = Q_{\text{thu}}$.
    \begin{itemize}
        \item $Q_{\text{tỏa}} = m_1 c_1 (t_1 - t_{\text{cb}})$ (với $t_1 > t_{\text{cb}}$)
        \item $Q_{\text{thu}} = m_2 c_2 (t_{\text{cb}} - t_2)$ (với $t_{\text{cb}} > t_2$)
    \end{itemize}
    \item \textbf{Năng suất tỏa nhiệt của nhiên liệu:} Nhiệt lượng tỏa ra khi đốt cháy hoàn toàn $1\text{kg}$ nhiên liệu: $Q_{\text{tp}} = q \cdot m$.
    \item \textbf{Hiệu suất đun nấu:} $H = \dfrac{Q_{\text{ích}}}{Q_{\text{tp}}} \cdot 100\% = \dfrac{mc\Delta t}{q \cdot m_{\text{nhiên liệu}}} \cdot 100\%$.
\end{itemize}""",
            'methods': [
                ('Dạng 1: Lí thuyết và đặc điểm của nhiệt dung riêng', 'curriculum:physics12:lesson:04:topic:01'),
                ('Dạng 2: Tính nhiệt lượng của một vật (Q = mcΔt)', 'curriculum:physics12:lesson:04:topic:02'),
                ('Dạng 3: Phương trình cân bằng nhiệt - Bài toán truyền nhiệt', 'curriculum:physics12:lesson:04:topic:03'),
                ('Dạng 4: Truyền nhiệt và thực hiện công', 'curriculum:physics12:lesson:04:topic:04'),
                ('Dạng 5: Năng suất tỏa nhiệt của nhiên liệu & hiệu suất', 'curriculum:physics12:lesson:04:topic:05'),
            ]
        },
        {
            'id': 'curriculum:physics12:lesson:05',
            'title': 'Bài 5: Nhiệt nóng chảy riêng',
            'theory_text': r"""\begin{itemize}
    \item \textbf{Sự nóng chảy:} Quá trình chuyển từ thể rắn sang thể lỏng của chất. Trong suốt quá trình nóng chảy của chất rắn kết tinh, nhiệt độ không đổi (nhiệt độ nóng chảy).
    \item \textbf{Nhiệt nóng chảy riêng:} Nhiệt nóng chảy riêng ($\lambda$) của một chất là nhiệt lượng cần cung cấp cho $1\text{kg}$ chất đó nóng chảy hoàn toàn ở nhiệt độ nóng chảy. Đơn vị: $\text{J}/\text{kg}$.
    \item \textbf{Công thức tính nhiệt lượng nóng chảy:} $Q = m\lambda$.
    \item \textbf{Đồ thị quá trình nóng chảy:} Giai đoạn tăng nhiệt độ của chất rắn (đoạn dốc lên), giai đoạn nóng chảy (đoạn nằm ngang ứng với nhiệt độ không đổi), giai đoạn tăng nhiệt độ của chất lỏng.
\end{itemize}""",
            'methods': [
                ('Dạng 1: Lí thuyết nhiệt nóng chảy riêng', 'curriculum:physics12:lesson:05:topic:01'),
                ('Dạng 2: Tính nhiệt nóng chảy riêng (Q = mλ) & đồ thị nóng chảy', 'curriculum:physics12:lesson:05:topic:02'),
            ]
        },
        {
            'id': 'curriculum:physics12:lesson:06',
            'title': 'Bài 6: Nhiệt hoá hơi riêng',
            'theory_text': r"""\begin{itemize}
    \item \textbf{Sự hóa hơi:} Quá trình chuyển từ thể lỏng sang thể khí. Gồm hai hình thức:
    \begin{itemize}
        \item \textit{Sự bay hơi:} Xảy ra ở bề mặt chất lỏng, tại mọi nhiệt độ.
        \item \textit{Sự sôi:} Xảy ra cả ở bề mặt và trong lòng khối chất lỏng, ở nhiệt độ sôi xác định (phụ thuộc áp suất khí quyển).
    \end{itemize}
    \item \textbf{Nhiệt hoá hơi riêng:} Nhiệt hoá hơi riêng ($L$) của một chất là nhiệt lượng cần cung cấp cho $1\text{kg}$ chất lỏng đó hóa hơi hoàn toàn ở nhiệt độ sôi. Đơn vị: $\text{J}/\text{kg}$.
    \item \textbf{Công thức tính nhiệt lượng hóa hơi:} $Q = mL$.
    \item \textbf{Nhiệt lượng tỏa ra khi ngưng tụ:} $Q_{\text{ngưng tụ}} = mL$.
\end{itemize}""",
            'methods': [
                ('Dạng 1: Lí thuyết nhiệt hoá hơi riêng', 'curriculum:physics12:lesson:06:topic:01'),
                ('Dạng 2: Tính nhiệt hoá hơi riêng (Q = mL) & đồ thị hoá hơi', 'curriculum:physics12:lesson:06:topic:02'),
            ]
        },
        {
            'id': 'curriculum:physics12:lesson:07',
            'title': 'Bài 7: Bài tập về vật lí nhiệt',
            'theory_text': r"""\begin{itemize}
    \item \textbf{Phương pháp giải bài toán nhiệt phức hợp:}
    \begin{itemize}
        \item Xác định các giai đoạn biến đổi của từng chất trong hệ: tăng nhiệt độ ($Q = mc\Delta t$), nóng chảy ($Q = m\lambda$), hóa hơi ($Q = mL$).
        \item Lập phương trình cân bằng nhiệt: tổng nhiệt lượng tỏa ra bằng tổng nhiệt lượng thu vào: $\sum Q_{\text{tỏa}} = \sum Q_{\text{thu}}$.
    \end{itemize}
    \item \textbf{Bài toán kết hợp nhiệt lượng và công suất / điện năng:}
    \begin{itemize}
        \item Nhiệt lượng do dòng điện tỏa ra: $Q = \mathcal{P} \cdot t = I^2 R t$.
        \item Hiệu suất của thiết bị đun điện: $H = \dfrac{Q_{\text{ích}}}{Q_{\text{điện}}} \cdot 100\%$.
    \end{itemize}
\end{itemize}""",
            'methods': [
                ('Dạng 1: Bài toán biến đổi nhiệt phức hợp nhiều giai đoạn', 'curriculum:physics12:lesson:07:topic:01'),
                ('Dạng 2: Bài toán bảo toàn và chuyển hóa năng lượng (cơ, điện, nhiệt)', 'curriculum:physics12:lesson:07:topic:02'),
            ]
        },
    ]

    print("\n=== Creating Lessons in Database ===")
    created_lessons = []
    
    with services.database.connect() as c:
        existing_lesson_titles = {r[0] for r in c.execute("SELECT title FROM lessons")}

    for cfg in lesson_configs:
        lesson_id = cfg['id']
        title = cfg['title']
        
        # Check if lesson already exists
        if title in existing_lesson_titles:
            print(f"Lesson '{title}' already exists, skipping creation.")
            continue
            
        blocks = []
        # 1. Theory block
        theory_b = block('theory', 'A. Lý thuyết trọng tâm', source=cfg['theory_text'])
        blocks.append(theory_b)
        
        # 2. Methods and exercises
        available_qs = questions_by_lesson.get(lesson_id, [])
        # If no questions directly under lesson_id (e.g. Lesson 7), pool from other lessons
        if not available_qs:
            for qs_list in questions_by_lesson.values():
                available_qs.extend(qs_list)
                
        for m_idx, (m_title, m_topic) in enumerate(cfg['methods'], 1):
            method_b = block('method', m_title)
            blocks.append(method_b)
            
            # Find matching questions for this topic
            topic_qs = [q for q in available_qs if q.get('topic_id') == m_topic]
            if not topic_qs:
                topic_qs = available_qs
                
            # Pick 1 example and 2 exercises
            if topic_qs:
                ex_q = topic_qs[0]
                ex_block = block('example', f'Ví dụ {m_idx}: Minh họa phương pháp', parent=method_b['id'], source=ex_q['source'])
                ex_block['question'] = {'id': ex_q['id'], 'revision': 1, 'original_source': ex_q['source']}
                blocks.append(ex_block)
                
            train_qs = topic_qs[1:4] if len(topic_qs) > 1 else topic_qs[:2]
            for t_idx, t_q in enumerate(train_qs, 1):
                tr_block = block('exercise', f'Bài tập rèn luyện {m_idx}.{t_idx}', parent=method_b['id'], source=t_q['source'])
                tr_block['question'] = {'id': t_q['id'], 'revision': 1, 'original_source': t_q['source']}
                blocks.append(tr_block)
                
        # 3. Overall exercises section
        sec_b = block('section', 'B. Bài tập vận dụng tổng hợp')
        blocks.append(sec_b)
        
        # Add 3 general exercises to the section
        gen_qs = available_qs[:5]
        for g_idx, g_q in enumerate(gen_qs, 1):
            g_block = block('exercise', f'Bài tập tổng hợp {g_idx}', parent=sec_b['id'], source=g_q['source'])
            g_block['question'] = {'id': g_q['id'], 'revision': 1, 'original_source': g_q['source']}
            blocks.append(g_block)

        # Create and save document
        doc = lesson_service.create(
            title=title,
            subject='Vật lí',
            grade='12',
            chapter='Chương 1: Vật lí nhiệt',
            blocks=blocks,
            taxonomy_id=lesson_id,
            template_key='methods',
            num_methods=len(cfg['methods'])
        )
        created_lessons.append(doc)
        print(f"Created lesson: '{title}' with {len(blocks)} blocks and {len(doc.get('files', []))} files.")
        
    return created_lessons


def reset_chapter1(services):
    print("Resetting previous Chapter 1 Physics 12 data for clean import...")
    with services.database.transaction() as c:
        # Delete lessons for Chapter 1 Physics 12 first (cascades to lesson_files and lesson_file_exercises)
        c.execute("DELETE FROM lessons WHERE title LIKE 'Bài %: %' AND (title LIKE '%Vật lí%' OR title LIKE '%nhiệt%' OR title LIKE '%chất%')")
        # Then delete questions belonging to Physics 12
        c.execute("""
            DELETE FROM questions WHERE id IN (
                SELECT question_id FROM question_metadata 
                WHERE json_extract(data_json, '$.subject') = 'Vật lí'
                  AND json_extract(data_json, '$.grade') = '12'
            )
        """)
    print("Reset completed.")

def main():
    print("=== POPULATING CHAPTER 1 - PHYSICS 12 INTO DATABASE ===")
    prepare_images()
    
    app_config = AppConfig.load()
    print(f"Database target: {app_config.database_path}")
    services = create_services(app_config)
    
    reset_chapter1(services)
    ensure_topics(services)
    questions_by_lesson = import_questions_to_db(services)
    created_lessons = create_chapter1_lessons(services, questions_by_lesson)
    
    # Verification
    with services.database.connect() as c:
        total_q = c.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        total_l = c.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        total_lf = c.execute("SELECT COUNT(*) FROM lesson_files").fetchone()[0]
        total_lfe = c.execute("SELECT COUNT(*) FROM lesson_file_exercises").fetchone()[0]
        
    print("\n=== FINAL DATABASE VERIFICATION ===")
    print(f"Total questions in DB: {total_q}")
    print(f"Total lessons in DB: {total_l}")
    print(f"Total lesson_files in DB: {total_lf}")
    print(f"Total lesson_file_exercises in DB: {total_lfe}")
    print("DONE! All Chapter 1 - Physics 12 content has been successfully populated.")

if __name__ == '__main__':
    main()
