# 01. CLI Entrypoint & `arg0` Multicall Dispatcher

- **Node ESM Launcher**: `src/launcher/codex.js` (`bin/codex`)
- **Rust CLI Crate**: `src/cli/src/main.rs`, `src/cli/src/lib.rs` (29 `.rs` files)
- **Multicall `arg0` Dispatcher**: `src/arg0/src/lib.rs`
  - Inspects `argv[0]` and internal flags to dispatch a single static-pie binary (`bin/codex`) as:
    - `codex-linux-sandbox` -> Linux Landlock + Seccomp + Bubblewrap sandbox runner
    - `codex-execve-wrapper` -> `execve` policy wrapper
    - `apply_patch` / `applypatch` (`--codex-run-as-apply-patch`) -> Freeform patch engine
    - `--codex-run-as-arg0-exec-helper` -> Internal execution helper
- **CLI Subcommand Tree**: `schemas/cli-command-tree.json`
