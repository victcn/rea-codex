#!/usr/bin/env python3
"""
Extracts all additional embedded assets into /code/custom-dev/rea-codex-demo:
1. All 23 Hook Command Input/Output JSON Schemas (0xe7b1c5c..0xe7b84f9) -> schemas/hooks-wire-schemas/
2. All 7 embedded Fluent (.ftl) i18n files (0x113b19e8..0x113b1a48) -> extracted-assets/i18n-ftl/
3. Additional prompts, subagent role TOMLs, apply_patch Lark grammars, shell snapshots,
   default packaged config.toml, and agent-message-board SQL schema -> extracted-assets/
4. Complete 3,971 tracing::Metadata catalog -> schemas/tracing-metadata-catalog.json
5. CLI recursive subcommand help tree -> schemas/cli-command-tree.json
"""

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess

CODEX_PKG_ROOT = "/usr/local/lib/node_modules/@openai/codex"
VENDOR_ROOT = os.path.join(
    CODEX_PKG_ROOT,
    "node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl",
)
CODEX_BIN = os.path.join(VENDOR_ROOT, "bin/codex")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_file(rel_path: str, content: bytes | str) -> dict:
    full_path = os.path.join(PROJECT_ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    raw = content.encode("utf-8") if isinstance(content, str) else content
    with open(full_path, "wb") as f:
        f.write(raw)
    return {
        "path": rel_path,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def main():
    with open(CODEX_BIN, "rb") as f:
        data = f.read()

    RO_START, RO_END = 0xE2F4000, 0xE2F4000 + 0xE44ACC
    TEXT_START, TEXT_END = 0x7420C0, 0xE2F3063
    RELRO_START, RELRO_END = 0x1135A900, 0x1135A900 + 0x50DE90

    relocated = {}
    for off in range(0x288, 0x288 + 0x7417C8, 24):
        r_offset, r_info, r_addend = struct.unpack_from("<QQq", data, off)
        if (r_info & 0xFFFFFFFF) == 8:
            relocated[r_offset] = r_addend

    ro_anchors = {RO_START, RO_END}
    for t in relocated.values():
        if RO_START <= t < RO_END:
            ro_anchors.add(t)
    lea_pat = re.compile(
        rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d](....)", re.DOTALL
    )
    for m in lea_pat.finditer(data, TEXT_START, TEXT_END):
        target = m.end() + struct.unpack("<i", m.group(1))[0]
        if RO_START <= target < RO_END:
            ro_anchors.add(target)
    sorted_anchors = sorted(ro_anchors)
    anchor_index = {a: i for i, a in enumerate(sorted_anchors)}

    def get_anchored_slice(ro_addr: int) -> bytes:
        idx = anchor_index.get(ro_addr)
        if idx is not None and idx + 1 < len(sorted_anchors):
            return data[ro_addr : sorted_anchors[idx + 1]].rstrip(b"\x00")
        return b""

    # 1. Extract all 23 Hook JSON Schemas
    print("[1/5] Extracting 23 Hook Command Input/Output JSON Schemas...")
    hooks_index = []
    for m in re.finditer(rb'\{\s*"\$schema"', data):
        off = m.start()
        if 0xE7B1000 <= off <= 0xE7B9000:
            raw_s = data[off : off + 10000].decode("utf-8", "ignore")
            obj, end = json.JSONDecoder().raw_decode(raw_s)
            exact_json = raw_s[:end]
            title = obj.get("title") or f"hook-schema-{hex(off)}"
            rel = f"schemas/hooks-wire-schemas/{title}.schema.json"
            rec = write_file(rel, exact_json)
            rec["rodata_vaddr"] = hex(off)
            rec["title"] = title
            hooks_index.append(rec)
    write_file(
        "schemas/hooks-wire-schemas/index.json",
        json.dumps(hooks_index, indent=2, ensure_ascii=False),
    )

    # 2. Extract 7 embedded Fluent (.ftl) i18n files
    print("[2/5] Extracting 7 embedded Fluent (.ftl) i18n localization files...")
    ftl_addrs = [
        ("en-US/age.ftl", 0xE3E2689, 3885),
        ("es-AR/age.ftl", 0xE3E35C0, 7637),
        ("fr/age.ftl", 0xE3E539F, 7347),
        ("it/age.ftl", 0xE3E705C, 10863),
        ("ru/age.ftl", 0xE3E9AD8, 3465),
        ("zh-CN/age.ftl", 0xE3EA86E, 3465),
        ("zh-TW/age.ftl", 0xE3E08CE, 7598),
    ]
    for rel_name, ro_addr, ln in ftl_addrs:
        write_file(f"extracted-assets/i18n-ftl/{rel_name}", data[ro_addr : ro_addr + ln])

    # 3. Extract additional prompts, agent role TOMLs, grammars, shell snapshots, and SQL
    print("[3/5] Extracting additional prompts, subagent roles, grammars, and shell snapshots...")
    extra_slices = [
        (0xE7001FD, "extracted-assets/prompts/subagent-roles/awaiter.toml"),
        (0xE7006BA, "extracted-assets/prompts/subagent-roles/explorer-role-guidance.md"),
        (0xE700AA7, "extracted-assets/prompts/subagent-roles/worker-role-guidance.md"),
        (0xE8C6758, "extracted-assets/prompts/subagent-roles/root-primary-agent-prompt.md"),
        (0xE8C6B25, "extracted-assets/prompts/subagent-roles/team-subagent-prompt.md"),
        (0xE8C6FC1, "extracted-assets/prompts/subagent-roles/proactive-delegation-prompt.md"),
        (0xE8D1CCA, "extracted-assets/prompts/subagent-roles/code-mode-collab-restriction.md"),
        (0xE7018D5, "extracted-assets/runtime-templates/apply-patch-freeform.lark"),
        (0xE701B39, "extracted-assets/runtime-templates/apply-patch-env.lark"),
        (0xE486FF6, "extracted-assets/runtime-templates/default-packaged-config.toml"),
        (0xE92AFD4, "extracted-assets/runtime-templates/shell-snapshot-sh.sh"),
        (0xE92B7BD, "extracted-assets/runtime-templates/shell-snapshot-bash.sh"),
        (0xE92B4CF, "extracted-assets/runtime-templates/shell-snapshot-zsh.sh"),
        (0xE92BAD8, "extracted-assets/runtime-templates/shell-snapshot-zsh-env.sh"),
        (0xE92BDD6, "extracted-assets/runtime-templates/shell-snapshot-posix-export.sh"),
        (0xE6E80E4, "extracted-assets/sql-migrations/07-agent-message-board-db/0001_message_board.sql"),
        (0xE734775, "extracted-assets/prompts/guardian-conversation-history-retrieval.md"),
        (0xE7BFF5F, "extracted-assets/prompts/imagegen-tool-instructions.md"),
        (0xE7EC7B2, "extracted-assets/prompts/memory-summary-injection-prompt.md"),
        (0xEA10276, "extracted-assets/prompts/init-agents-md-generator-prompt.md"),
        (0xE8CB5AB, "extracted-assets/prompts/permission-requests-guidance.md"),
        (0xEA24639, "extracted-assets/prompts/side-conversation-boundary-prompt.md"),
        (0xE78666F, "extracted-assets/prompts/update-goal-tool-description.md"),
        (0xE8C8394, "extracted-assets/prompts/collaboration-mode-default-prompt.md"),
        (0xE77E090, "extracted-assets/prompts/git-commit-and-pr-attribution-prompt.md"),
        (0xE6BCBFC, "extracted-assets/prompts/windows-safety-rules-prompt.md"),
        (0xE7F7E86, "extracted-assets/prompts/memory-rollout-summary-slug-prompt.md"),
        (0xE7F7056, "extracted-assets/prompts/memory-raw-rollout-analyzer-prompt.md"),
        (0xE709565, "extracted-assets/prompts/plugins-usage-instructions.md"),
        (0xE6DDBE5, "extracted-assets/prompts/tool-suggest-plugin-install-prompt.md"),
        (0xE70919D, "extracted-assets/prompts/realtime-conversation-backend-prompt.md"),
        (0xE819E7E, "extracted-assets/prompts/memory-adhoc-notes-extension-prompt.md"),
        (0xE7875D3, "extracted-assets/prompts/thread-goal-budget-reached-prompt.md"),
        (0xE789205, "extracted-assets/prompts/thread-goal-objective-edited-prompt.md"),
        (0xE708F14, "extracted-assets/prompts/execution-environments-instructions.md"),
        (0xE702EBD, "extracted-assets/prompts/context-checkpoint-compaction-prompt.md"),
        (0xE702C13, "extracted-assets/prompts/context-compaction-handoff-prefix.md"),
        (0xE8CB48C, "extracted-assets/prompts/request-permissions-tool-prompt.md"),
    ]
    for ro_addr, out_rel in extra_slices:
        blob = get_anchored_slice(ro_addr)
        if blob:
            write_file(out_rel, blob)

    # Copy voice notices and licenses
    voice_src = os.path.join(VENDOR_ROOT, "codex-resources/voice")
    if os.path.exists(os.path.join(voice_src, "NOTICE.md")):
        with open(os.path.join(voice_src, "NOTICE.md"), "rb") as f:
            write_file("extracted-assets/voice-runtime/NOTICE.md", f.read())
    lic_dir = os.path.join(voice_src, "licenses")
    if os.path.isdir(lic_dir):
        for fn in os.listdir(lic_dir):
            with open(os.path.join(lic_dir, fn), "rb") as f:
                write_file(f"extracted-assets/voice-runtime/licenses/{fn}", f.read())

    # 4. Extract all 3,971 tracing::Metadata structs with fields
    print("[4/5] Extracting all 3,971 tracing::Metadata descriptors...")
    tracing_catalog = []
    for addr in range(RELRO_START, RELRO_END - 0x68, 8):
        if (
            addr in relocated
            and (addr + 0x10) in relocated
            and (addr + 0x40) in relocated
            and (addr + 0x50) in relocated
        ):
            t_ptr = relocated[addr + 0x10]
            m_ptr = relocated[addr + 0x40]
            f_ptr = relocated[addr + 0x50]
            t_len = struct.unpack_from("<Q", data, addr + 0x18)[0]
            m_len = struct.unpack_from("<Q", data, addr + 0x48)[0]
            f_len = struct.unpack_from("<Q", data, addr + 0x58)[0]
            if (
                t_ptr == m_ptr
                and t_len == m_len
                and 1 <= t_len <= 200
                and 1 <= f_len <= 250
                and RO_START <= f_ptr < RO_END
            ):
                file_s = data[f_ptr : f_ptr + f_len].decode("utf-8", "replace")
                if file_s.endswith(".rs"):
                    n_ptr = relocated[addr]
                    n_len = struct.unpack_from("<Q", data, addr + 0x08)[0]
                    name_s = data[n_ptr : n_ptr + n_len].decode("utf-8", "replace")
                    mod_s = data[m_ptr : m_ptr + m_len].decode("utf-8", "replace")
                    line_no = struct.unpack_from("<I", data, addr + 0x60)[0]
                    fields_ptr = relocated.get(addr + 0x20)
                    fields_len = struct.unpack_from("<Q", data, addr + 0x28)[0]
                    fields = []
                    if (
                        fields_ptr
                        and RELRO_START <= fields_ptr < RELRO_END
                        and 0 < fields_len <= 32
                    ):
                        for fi in range(fields_len):
                            fp = relocated.get(fields_ptr + fi * 16)
                            fl = struct.unpack_from(
                                "<Q", data, fields_ptr + fi * 16 + 8
                            )[0]
                            if fp and RO_START <= fp < RO_END and 1 <= fl <= 80:
                                fields.append(
                                    data[fp : fp + fl].decode("utf-8", "replace")
                                )
                    tracing_catalog.append(
                        {
                            "relro_vaddr": hex(addr),
                            "name": name_s,
                            "module_path": mod_s,
                            "file": file_s,
                            "line": line_no if line_no < 100000 else None,
                            "fields": fields,
                        }
                    )
    write_file(
        "schemas/tracing-metadata-catalog.json",
        json.dumps(
            {
                "total_records": len(tracing_catalog),
                "records": tracing_catalog,
            },
            indent=2,
            ensure_ascii=False,
        ),
    )

    # 5. Extract recursive CLI command tree
    print("[5/5] Building CLI command & subcommand help catalog...")
    subcommands = [
        [],
        ["agents"],
        ["exec"],
        ["review"],
        ["login"],
        ["logout"],
        ["mcp"],
        ["plugin"],
        ["app-server"],
        ["app-server", "daemon"],
        ["remote-control"],
        ["completion"],
        ["update"],
        ["doctor"],
        ["sandbox"],
        ["debug"],
        ["debug", "models"],
        ["debug", "app-server"],
        ["debug", "prompt-input"],
        ["apply"],
        ["resume"],
        ["queue"],
        ["archive"],
        ["delete"],
        ["migrate-rollouts"],
        ["unarchive"],
        ["fork"],
        ["cloud"],
        ["exec-server"],
        ["features"],
    ]
    cli_tree = []
    for cmd in subcommands:
        proc = subprocess.run(
            [CODEX_BIN, *cmd, "--help"], capture_output=True, text=True
        )
        cli_tree.append(
            {
                "command": " ".join(["codex", *cmd]),
                "exit_code": proc.returncode,
                "help_text": proc.stdout,
            }
        )
    write_file(
        "schemas/cli-command-tree.json",
        json.dumps(cli_tree, indent=2, ensure_ascii=False),
    )
    print("Done extracting all additional assets!")


if __name__ == "__main__":
    main()
