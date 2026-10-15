if export -p >/dev/null 2>&1; then
export -p | __codex_snapshot_command awk '
/^(export|declare -x|typeset -x) [A-Za-z_][A-Za-z0-9_]*$/ {
  name=$0
  sub(/^(export|declare -x|typeset -x) /, "", name)
  if (name ~ /^(PWD|OLDPWD)$/) {
    next
  }
  if (!seen[name]++) {
    print name
  }
}' | while IFS= read -r __codex_snapshot_export_name; do
  # Only the validated identifier enters eval. Set values come from the bulk environment.
  if eval '[ "${'"$__codex_snapshot_export_name"'+x}" = x ]'; then
    continue
  fi
  # Only preserve an unset export if the native shell confirms it already exists.
  if (
    set +a
    set -- "$__codex_snapshot_export_name" "$(export -p)"
    export "$1"
    [ "$2" = "$(export -p)" ]
  ); then
    RECORD_START
    printf 'export %s\n' "$__codex_snapshot_export_name"
    RECORD_END
  fi
done
fi
