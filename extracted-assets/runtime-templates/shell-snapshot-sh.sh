echo '# Snapshot file'
if [ -n "${BASH_VERSINFO-}" ]; then
  echo '# Bash-backed sh'
  shopt -p || true
fi
echo '# Unset all aliases to avoid conflicts with functions'
unalias -a 2>/dev/null || true
echo '# Functions'
if command -v typeset >/dev/null 2>&1; then
  typeset -f
elif command -v declare >/dev/null 2>&1; then
  declare -f
fi
echo ''
SNAPSHOT_OPTIONS_BEGIN
SNAPSHOT_COMMAND_HELPER
if set -o >/dev/null 2>&1; then
  sh_opts=$(set -o | __codex_snapshot_command awk '$2=="on"{print $1}')
  sh_opt_count=$(printf '%s\n' "$sh_opts" | __codex_snapshot_command sed '/^$/d' | __codex_snapshot_command wc -l | __codex_snapshot_command tr -d ' ')
  echo "# setopts $sh_opt_count"
  if [ -n "$sh_opts" ]; then
    printf 'set -o %s\n' $sh_opts
  fi
else
  echo '# setopts 0'
fi
echo ''
printf '\0'
if alias >/dev/null 2>&1; then
  alias_count=$(alias | __codex_snapshot_command wc -l | __codex_snapshot_command tr -d ' ')
  echo "# aliases $alias_count"
  alias
  echo ''
else
  echo '# aliases 0'
fi
SNAPSHOT_ALIASES_END
printf '\0'
SNAPSHOT_EXPORTS
printf '\0'
SNAPSHOT_DECLARATION_ENVIRONMENT
printf '\0'
SNAPSHOT_ENVIRONMENT
