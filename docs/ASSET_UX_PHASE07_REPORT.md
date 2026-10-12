# Phase 7 — Integration and Benchmark

Ngày: 10/10/2026.

Added integration coverage for relative/extensionless images, `graphicspath`, same-name different bytes, shared assets, nested input/cycle, dynamic/traversal/unsupported paths, source relocation, content-addressed corruption, safe GC, portable ZIP and student-answer filtering. The synthetic benchmark script measures parser and resolver work without touching user data.

Measured on this machine (Python 3.14.6, PySide6 6.11.2):

| Questions | Parse | Resolve | Peak traced memory |
|---:|---:|---:|---:|
| 1,000 | 0.0790 s | 0.8844 s | 1.12 MB |
| 10,000 | 0.8340 s | 7.1804 s | 11.20 MB |
| 50,000 | 3.7132 s | 30.5712 s | 56.08 MB |

Integration subset: **20 passed in 8.00 seconds**. The 50,000 case is a synthetic resolver measurement; it is not a claim about full UI import responsiveness. The JSON evidence is `artifacts/asset-benchmark.json`.
