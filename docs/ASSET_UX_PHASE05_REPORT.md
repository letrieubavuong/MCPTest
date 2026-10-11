# Phase 5 — Portable Export

Ngày: 10/10/2026.

Question-bank exam export now supports a `.zip` portable bundle with relative assets and `manifest.json` SHA-256 checksums. The snapshot records question IDs/revisions and audience; student bundles remove answer/solution spans from the document body, while teacher bundles preserve them. Existing TeX/PDF export paths remain available. The export writes through a temporary directory and atomically replaces the requested ZIP.

Validation: **22 passed in 26.03 seconds** for exam, lesson, TeX mixing and portable export tests. The portable test verifies a new extraction has all assets, manifest hashes match bytes and the student body contains no answer/solution content. PDF integration remains covered by existing tests with the installed TeX Live runtime.
