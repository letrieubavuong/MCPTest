import sqlite3, os, sys, json
sys.stdout.reconfigure(encoding='utf-8')

p = os.path.expandvars(r'%LOCALAPPDATA%\LaTeXQuestionStudio\studio.db')
con = sqlite3.connect(p)
cur = con.cursor()

print("="*60)
print("DATABASE VERIFICATION REPORT")
print("="*60)

print("\n1. QUESTIONS BY CHAPTER 1 - PHYSICS 12 LESSON:")
rows = cur.execute("""
    SELECT json_extract(m.data_json, '$.lesson') as lesson_name,
           COUNT(*) as cnt
    FROM questions q
    JOIN question_metadata m ON m.question_id = q.id
    WHERE json_extract(m.data_json, '$.grade') = '12' 
      AND json_extract(m.data_json, '$.subject') = 'Vật lí'
    GROUP BY lesson_name
    ORDER BY lesson_name
""").fetchall()
for r in rows:
    print(f"  • {r[0]}: {r[1]} câu")

print("\n2. QUESTIONS BY TOPIC (DẠNG TOÁN):")
rows = cur.execute("""
    SELECT json_extract(m.data_json, '$.lesson') as lesson_name,
           json_extract(m.data_json, '$.topic') as topic_name,
           COUNT(*) as cnt
    FROM questions q
    JOIN question_metadata m ON m.question_id = q.id
    WHERE json_extract(m.data_json, '$.grade') = '12' 
      AND json_extract(m.data_json, '$.subject') = 'Vật lí'
    GROUP BY lesson_name, topic_name
    ORDER BY lesson_name, topic_name
""").fetchall()
current_lesson = ""
for r in rows:
    if r[0] != current_lesson:
        current_lesson = r[0]
        print(f"  [{current_lesson}]")
    print(f"    - {r[1]}: {r[2]} câu")

print("\n3. COGNITIVE LEVEL BREAKDOWN:")
rows = cur.execute("""
    SELECT cognitive_level, COUNT(*) 
    FROM questions 
    GROUP BY cognitive_level
    ORDER BY cognitive_level
""").fetchall()
for r in rows:
    print(f"  • Mức {r[0]}: {r[1]} câu")

print("\n4. QUESTION TYPES BREAKDOWN:")
rows = cur.execute("""
    SELECT question_type, COUNT(*) 
    FROM questions 
    GROUP BY question_type
    ORDER BY question_type
""").fetchall()
for r in rows:
    print(f"  • Loại {r[0]}: {r[1]} câu")

print("\n5. LESSONS IN DATABASE:")
rows = cur.execute("""
    SELECT id, title, revision, updated_at 
    FROM lessons 
    ORDER BY title
""").fetchall()
for r in rows:
    print(f"  • {r[1]} (id: {r[0][:8]}..., rev: {r[2]})")

print("\n6. LESSON FILES (CANONICAL TeX FILES):")
rows = cur.execute("""
    SELECT lf.title, lf.filename, lf.role, l.title as lesson_title
    FROM lesson_files lf
    JOIN lessons l ON l.id = lf.lesson_id
    ORDER BY l.title, lf.position
""").fetchall()
for r in rows[:15]:
    print(f"  • [{r[3]}] {r[0]} -> {r[1]} ({r[2]})")
print(f"  ... (total {len(rows)} files across lessons)")

print("\n7. FTS SEARCH TEST:")
for query in ["Brown", "nhiệt dung riêng", "nóng chảy", "động cơ nhiệt"]:
    search_q = query.replace('đ','d').replace('Đ','D')
    hits = cur.execute("SELECT COUNT(*) FROM questions_fts WHERE questions_fts MATCH ?", (search_q,)).fetchone()[0]
    print(f"  • Tìm kiếm '{query}': {hits} kết quả khớp")

con.close()
print("\nVerification completed successfully!")
