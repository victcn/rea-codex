# 02. Core Agent Session & Turn Loop (`codex_core`)

- **Reconstructed Source Tree**: `src/core/src/` (226 `.rs` files)
  - Session lifecycle: `src/core/src/session/turn_input.rs`, `src/core/src/session/world_state.rs`, `src/core/src/session/startup_prewarm.rs`, `src/core/src/session/turn_suspension.rs`
  - Context & Compaction: `src/core/src/context/world_state/mod.rs`, `extracted-assets/prompts/context-checkpoint-compaction-prompt.md`
  - Prompts Assembly: `extracted-assets/prompts/base-cli-system-prompt.md`, `extracted-assets/prompts/general-agent-identity-prompt.md`, `extracted-assets/prompts/plan-mode-conversational-prompt.md`
