# Phase 1 — Asset Resolver

Ngày: 09/10/2026.

Implemented `application/assets.py` with safe resolution for relative images, extensionless images, `graphicspath`, nested `input/include`, cycles, depth limit, path traversal, symlink/size checks, unsupported formats and dynamic references. Resolution returns source context, dependency type, candidate paths, SHA-256 and explicit status.

`ImportService.stage()` now records the resource graph and refuses READY status for missing/ambiguous/dynamic/blocked dependencies. Existing source bytes and question spans remain unchanged. Migration schema 18 adds nullable-compatible resolution metadata to `question_assets`; historical links default to `legacy/RESOLVED`. Migration is idempotent when a test or recovery database has been downgraded without removing newer columns.

Validation: **39 passed** in 4.85 seconds for resolver/import/persistence/stabilization tests. This includes source move independence, shared content identity, ambiguity rejection and schema preservation. No real user database was opened.
