"""
Phase J Reproducible Dataset Generator.
Extracts real questions from repository sources (3L1/Exercise/*.tex, benchmark templates)
and optionally generates synthetic questions with explicit labels for scale testing (1k, 10k).
"""
import glob
import json
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def get_real_questions(limit: int = 1000) -> List[Dict[str, Any]]:
    from latex_question_studio.parsing.latex import parse_questions
    
    questions = []
    exercise_files = sorted(glob.glob(str(PROJECT_ROOT / "3L1/Exercise/*.tex")))
    
    for fpath in exercise_files:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            parsed = parse_questions(content)
            for idx, q in enumerate(parsed):
                if not q.source or not q.source.strip():
                    continue
                questions.append({
                    "id": f"real_{Path(fpath).stem}_{idx:03d}",
                    "source": q.source.strip(),
                    "kind": "real_exercise",
                    "origin_file": Path(fpath).name
                })
                if len(questions) >= limit:
                    return questions
        except Exception as e:
            continue
            
    return questions


def generate_synthetic_questions(count: int, start_idx: int = 1) -> List[Dict[str, Any]]:
    synthetic = []
    categories = [
        ("algebra", r"\begin{{ex}} [SYNTHETIC-PHASE-J] Giải phương trình bậc hai $x^2 - {b}x + {c} = 0$. \choice{{$x = 1$}}{{\True $x = {root1}$}}{{$x = 5$}}{{$x = -2$}} \loigiai{{Nghiệm là $x_1 = {root1}, x_2 = {root2}$.}} \end{{ex}}"),
        ("physics", r"\begin{{ex}} [SYNTHETIC-PHASE-J] Một vật có khối lượng $m = {m}\,\text{{kg}}$ chuyển động với vận tốc $v = {v}\,\text{{m/s}}$. Động năng của vật là: \shortans{{{ke}}} \loigiai{{Áp dụng công thức $W_d = \frac{{1}}{{2}}mv^2 = {ke}\,\text{{J}}$.}} \end{{ex}}"),
        ("geometry", r"\begin{{ex}} [SYNTHETIC-PHASE-J] Cho hình chóp $S.ABC$ có đáy là tam giác vuông tại $A$, cạnh $AB = {a}$, $AC = {b_geom}$. \choiceTF{{\True Diện tích đáy là $\frac{{{ab}}}{{2}}$.}}{{Thể tích chóp luôn âm.}}{{\True Góc giữa các mặt phẳng xác định được.}}{{Cạnh $BC = 100$.}} \loigiai{{Tính diện tích tam giác vuông theo cạnh góc vuông.}} \end{{ex}}"),
        ("calculus", r"\begin{{ex}} [SYNTHETIC-PHASE-J] Tính tích phân $I = \int_0^{{{k}}} (2x + 1)\,dx$. \choice{{$I = {ans1}$}}{{\True $I = {ans2}$}}{{$I = {ans3}$}}{{$I = 0$}} \loigiai{{Nguyên hàm là $F(x) = x^2 + x$.}} \end{{ex}}")
    ]
    
    for i in range(count):
        idx = start_idx + i
        cat, template = categories[i % len(categories)]
        b = idx % 10 + 2
        c = (idx % 5 + 1) * (idx % 3 + 1)
        root1 = idx % 4 + 1
        root2 = idx % 3 + 2
        m = idx % 20 + 1
        v = (idx % 15 + 2) * 2
        ke = int(0.5 * m * v * v)
        a = idx % 8 + 3
        b_geom = idx % 6 + 4
        ab = a * b_geom
        k = idx % 5 + 1
        ans2 = k * k + k
        ans1 = ans2 + 2
        ans3 = ans2 - 1
        
        src = template.format(
            b=b, c=c, root1=root1, root2=root2,
            m=m, v=v, ke=ke, a=a, b_geom=b_geom, ab=ab,
            k=k, ans1=ans1, ans2=ans2, ans3=ans3
        )
        
        synthetic.append({
            "id": f"syn_{idx:06d}",
            "source": src,
            "kind": "synthetic_labeled",
            "category": cat
        })
        
    return synthetic


def build_dataset_summary():
    real_qs = get_real_questions(1000)
    print(f"Extracted {len(real_qs)} real questions from repository.")
    
    # Save 1000 reproducible questions (898 real + 102 synthetic labeled if needed)
    combined_1000 = list(real_qs)
    if len(combined_1000) < 1000:
        needed = 1000 - len(combined_1000)
        syn = generate_synthetic_questions(needed, start_idx=1)
        combined_1000.extend(syn)
        
    out_dir = PROJECT_ROOT / "scratch/phase_j_datasets"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    meta = {
        "total_count": len(combined_1000),
        "real_count": len(real_qs),
        "synthetic_count": len(combined_1000) - len(real_qs),
        "provenance": "Repository 3L1/Exercise/*.tex + synthetic generator with [SYNTHETIC-PHASE-J] tags"
    }
    
    (out_dir / "dataset_1000_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved dataset metadata: {meta}")

if __name__ == "__main__":
    build_dataset_summary()
