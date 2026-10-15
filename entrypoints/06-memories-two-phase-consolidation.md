# 06. Two-Phase Agent Memory System (`ext/memories` & `memories/write`)

- **Reconstructed Crates**:
  - `src/ext/memories/src/` (14 `.rs` files)
  - `src/memories/write/src/` (14 `.rs` files)
- **Extracted Memory Prompts**:
  - Phase 1 (Single Rollout Extraction): `extracted-assets/prompts/memory-phase1-single-rollout-prompt.md` (`0xe80a296`, 30,449 bytes)
  - Phase 2 (Global Consolidation): `extracted-assets/prompts/memory-phase2-consolidation-prompt.md` (`0xe7f824f`, 51,237 bytes)
  - Rollout Extractor & Summary Consolidation: `extracted-assets/prompts/memory-rollout-extractor-prompt.md`, `extracted-assets/prompts/memory-summary-consolidation-prompt.md`
  - Memory Injection & Ad-hoc Notes: `extracted-assets/prompts/memory-subsystem-instructions.md`, `extracted-assets/prompts/memory-summary-injection-prompt.md`, `extracted-assets/prompts/memory-adhoc-notes-extension-prompt.md`
- **SQLite Schema**: `extracted-assets/sql-migrations/05-memories-db/`
