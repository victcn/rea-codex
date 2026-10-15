print '# Snapshot file'
print '# Unset all aliases to avoid conflicts with functions'
print 'unalias -a 2>/dev/null || true'
print '# Functions'
functions
print ''
SNAPSHOT_OPTIONS_BEGIN
SNAPSHOT_COMMAND_HELPER
setopt_count=$(setopt | __codex_snapshot_command wc -l | __codex_snapshot_command tr -d ' ')
print "# setopts $setopt_count"
setopt | __codex_snapshot_command sed 's/^/setopt /'
print ''
printf '\0'
alias_count=$(\alias -L | __codex_snapshot_command wc -l | __codex_snapshot_command tr -d ' ')
print "# aliases $alias_count"
SNAPSHOT_ZSH_ALIASES
print ''
SNAPSHOT_ALIASES_END
printf '\0'
SNAPSHOT_EXPORTS
printf '\0'
SNAPSHOT_ENVIRONMENT
