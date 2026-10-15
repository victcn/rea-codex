(
  unsetopt rcquotes
  # The bundled Zsh does not include the zsh/parameter module.
  for __codex_snapshot_export_name in ${(f)"$(typeset +x)"}; do
    case "$__codex_snapshot_export_name" in
      ""|[0-9]*|*[!A-Za-z0-9_]*|PWD|OLDPWD) continue ;;
    esac
    case "${(tP)__codex_snapshot_export_name}" in
      *readonly*) continue ;;
      *export*) ;;
      *) continue ;;
    esac
    RECORD_START
    typeset -xp "$__codex_snapshot_export_name"
    RECORD_END
  done
)
