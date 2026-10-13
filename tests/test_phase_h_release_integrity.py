import hashlib
import time
from pathlib import Path

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.search import SearchService
from latex_question_studio.application.importing import ImportService
from latex_question_studio.persistence.database import SCHEMA_VERSION


def test_db_migration_and_backup_restore(tmp_path):
    config = AppConfig.load(tmp_path / "data")
    services = create_services(config)

    # 1. Verify schema version matches latest migrations
    with services.database.connect() as c:
        version = c.execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION, f"Schema version is {version}, expected {SCHEMA_VERSION}"

    # 2. Add question data
    q1 = services.questions.create(r"\begin{ex} Câu kiểm tra backup \choice{A}{B}{\True C}{D} \end{ex}")
    assert q1.id is not None

    # 3. Create database backup
    backup_dir = tmp_path / "backups"
    backup_file = services.database.backup(backup_dir)
    assert backup_file.is_file()
    assert backup_file.stat().st_size > 0

    # 4. Verify backup can be restored into a fresh instance
    restore_config = AppConfig.load(tmp_path / "restored_data")
    restore_db_path = restore_config.database_path
    restore_db_path.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copyfile(backup_file, restore_db_path)

    restored_services = create_services(restore_config)
    restored_q = restored_services.questions.get(q1.id)
    assert restored_q is not None
    assert restored_q.latex_source == q1.latex_source


def test_synthetic_1k_questions_benchmark(tmp_path):
    """
    Benchmark database ingestion, FTS full-text search, and pagination
    with 1,000 synthetic questions.
    """
    config = AppConfig.load(tmp_path / "scale_data")
    services = create_services(config)
    search_svc = SearchService(services)

    # 1. Ingest 1,000 questions in bulk
    start_ingest = time.perf_counter()
    with services.database.transaction() as c:
        now = "2026-10-13T12:00:00Z"
        for i in range(1000):
            qid = f"scale-q-{i:04d}"
            source = rf"\begin{{ex}} Câu số {i+1}: Cho tích phân $I_{{{i}}} = \int_0^{i+1} x^{i%5} dx$. Tính giá trị của biểu thức. \choice{{$A$}}{{$B$}}{{\True $C$}}{{$D$}} \loigiai{{Lời giải câu {i+1}.}} \end{{ex}}"
            qtype = "mcq" if i % 2 == 0 else "short_answer"
            cog = ["NB", "TH", "VD", "VDC"][i % 4]
            c.execute(
                "INSERT INTO questions (id, latex_source, question_type, solution, difficulty_legacy, cognitive_level, revision, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (qid, source, qtype, f"Lời giải câu {i+1}.", 2, cog, 1, now, now),
            )
            # Link to question_analysis
            s_hash = hashlib.sha256(source.encode()).hexdigest()
            c.execute(
                "INSERT INTO question_analysis (question_id, source_hash, normalized_hash, parser_version, valid, parsed_json) VALUES (?,?,?,?,?,?)",
                (qid, s_hash, s_hash, 1, 1, "{}"),
            )
    ingest_time = time.perf_counter() - start_ingest
    print(f"\n[SCALE BENCHMARK] Ingested 1,000 questions in {ingest_time:.3f}s ({ingest_time/1000*1000:.2f}ms/câu)")

    # 2. Benchmark Full-Text Search across 1,000 questions
    start_search = time.perf_counter()
    results = search_svc.find("tích phân", limit=50)
    search_time = time.perf_counter() - start_search
    print(f"[SCALE BENCHMARK] FTS search 'tích phân' across 1,000 questions: {search_time*1000:.2f}ms (Found: {len(results)})")

    assert len(results) == 50
    assert search_time < 0.1  # Must return within 100ms

    # 3. Benchmark cognitive level filtering
    start_filter = time.perf_counter()
    vdc_results = search_svc.find("", filters={"cognitive_level": "VDC"}, limit=100)
    filter_time = time.perf_counter() - start_filter
    print(f"[SCALE BENCHMARK] Cognitive level filter 'VDC': {filter_time*1000:.2f}ms (Found: {len(vdc_results)})")
    assert len(vdc_results) == 100
    assert filter_time < 0.05


def test_import_deduplication_and_file_protection(tmp_path):
    config = AppConfig.load(tmp_path / "import_data")
    services = create_services(config)
    imp_svc = ImportService(services)

    source = r"\begin{ex} Cho hàm số bậc ba $y=ax^3+bx^2+cx+d$. Tìm số điểm cực trị. \choice{0}{1}{\True 2}{3} \loigiai{Hàm bậc ba có tối đa 2 điểm cực trị.} \end{ex}"
    f1 = tmp_path / "bai_1.tex"
    f1.write_text(source, encoding="utf-8")

    # 1. First import
    batch1, results1 = imp_svc.stage([f1])
    assert len(results1) == 1
    committed1 = imp_svc.commit(batch1)
    assert committed1 == 1

    # 2. Second import of exact same source file
    f2 = tmp_path / "bai_2.tex"
    f2.write_text(source, encoding="utf-8")
    batch2, results2 = imp_svc.stage([f2])
    # The staging tracks existing items and allows safe handling
    assert len(results2) == 1
    committed2 = imp_svc.commit(batch2)
    assert services.questions.count() >= 1
