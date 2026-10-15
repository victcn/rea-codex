#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISOLATED_HOME="${PROJECT_ROOT}/.isolated-env/home"
ISOLATED_CODEX_HOME="${ISOLATED_HOME}/.codex"
mkdir -p "${ISOLATED_CODEX_HOME}"

exec env -i \
  HOME="${ISOLATED_HOME}" \
  CODEX_HOME="${ISOLATED_CODEX_HOME}" \
  PATH="/usr/local/bin:/usr/bin:/bin" \
  TERM="${TERM:-xterm-256color}" \
  LANG="${LANG:-C.UTF-8}" \
  OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
  OPENAI_BASE_URL="${OPENAI_BASE_URL:-}" \
  "${PROJECT_ROOT}/bin/codex" "$@"
