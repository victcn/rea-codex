# 04. Code Mode (`exec_js`) V8 Turboshaft + Starlark Isolated Host

- **Host Binary**: `bin/codex-code-mode-host` (74.0 MB static-pie ELF)
- **Reconstructed Crates**:
  - `src/code-mode/src/` (14 `.rs` files in `bin/codex`)
  - `src/code-mode-host/src/` (12 `.rs` files in `bin/codex-code-mode-host`)
  - `src/code-mode-runtime/src/` (7 `.rs` files in `bin/codex-code-mode-host`)
  - `src/code-mode-protocol/src/` (2 `.rs` files)
- **Embedded V8 Runtime Bootstrap**: `extracted-assets/runtime-templates/v8-promise-combinators.js` (`0x2f98b48`)
- **System Prompt**: `extracted-assets/prompts/code-mode-javascript-orchestration-prompt.md` (`0xe6874bf`)
