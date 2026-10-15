echo '# Snapshot file'
echo '# Unset all aliases to avoid conflicts with functions'
echo 'unalias -a 2>/dev/null || true'
shopt -p || true
echo '# Functions'
declare -f
echo ''
SNAPSHOT_OPTIONS_BEGIN
SNAPSHOT_COMMAND_HELPER
bash_opts=$(set -o | __codex_snapshot_command awk '$2=="on"{print $1}')
bash_opt_count=$(printf '%s\n' "$bash_opts" | __codex_snapshot_command sed '/^$/d' | __codex_snapshot_command wc -l | __codex_snapshot_command tr -d ' ')
echo "# setopts $bash_opt_count"
if [ -n "$bash_opts" ]; then
  printf 'set -o %s\n' $bash_opts
fi
echo ''
printf '\0'
alias_count=$(\alias -p | __codex_snapshot_command wc -l | __codex_snapshot_command tr -d ' ')
echo "# aliases $alias_count"
\alias -p
echo ''
SNAPSHOT_ALIASES_END
printf '\0'
SNAPSHOT_EXPORTS
printf '\0'
SNAPSHOT_ENVIRONMENT
