#!/usr/bin/env python3
"""
REA Codex v0.162.1 Full Artifact & Architecture Reconstruction Pipeline.

Extracts and reconstructs from /usr/local/lib/node_modules/@openai/codex:
1. 45 embedded `include_dir::File` assets (5 official system skills: imagegen,
   openai-docs, review-agent, skill-creator, skill-installer) via .data.rel.ro
   R_X86_64_RELATIVE fat-pointer parsing.
2. 2 embedded Zstandard (.zst) App-Server Protocol archives from .rodata
   (0xe5c6d6f -> 4.88 MB Stable; 0xe5ed6c1 -> 5.43 MB Experimental), yielding
   888 TypeScript (ts-rs) definitions, 447 JSON Schemas, and RolloutLine.json.
3. Official embedded Model Catalog (`models.json`, 472,071 bytes @ 0xe833a82)
   covering 11 models (including 3 hidden models: gpt-daybreak-blue-latest,
   gpt-daybreak-red-latest, codex-auto-review) and their full instruction templates,
   guardian_v2 classifier prompts, token budgets, and confirmation policies.
4. 21+ standalone internal System Prompts, Agent Role Prompts, and Runtime Templates
   via exact .rodata anchor intervals (.rela.dyn + .text LEA [rip+disp32]).
5. All 75 `sqlx::migrate::Migration` SQLite scripts across 6 databases (Logs,
   Thread Goals, Thread Queue, Core State v1..v59, Memories, Thread History)
   with cryptographic 48-byte SHA-384 verification.
6. Complete App-Server JSON-RPC method & notification registry (185 entries),
   115 Feature Flags registry, 55 Connector Approval Templates, and Environment
   Variables index.
7. Workspace Crate & Function Attribution Map:
   - 338,251 functions recovered from .eh_frame_hdr
   - 42,947 core::panic::Location descriptors + 3,971 tracing::Metadata descriptors
   - 60,838 stripped .text functions attributed to exact .rs source files & lines
   - 27,892 unstripped symbols & DWARF metadata from codex-voice-host
"""

import bisect
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
CODE_MODE_BIN = os.path.join(VENDOR_ROOT, "bin/codex-code-mode-host")
VOICE_HOST_BIN = os.path.join(VENDOR_ROOT, "codex-resources/voice/bin/codex-voice-host")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "extracted-assets")
SCHEMAS_DIR = os.path.join(PROJECT_ROOT, "schemas")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def parse_rela_dyn(data: bytes, rela_off: int, rela_size: int) -> dict[int, int]:
    relocated = {}
    for off in range(rela_off, rela_off + rela_size, 24):
        r_offset, r_info, r_addend = struct.unpack_from("<QQq", data, off)
        if (r_info & 0xFFFFFFFF) == 8:  # R_X86_64_RELATIVE
            relocated[r_offset] = r_addend
    return relocated


def collect_rodata_anchors(
    data: bytes,
    relocated: dict[int, int],
    text_start: int,
    text_end: int,
    ro_start: int,
    ro_end: int,
) -> list[int]:
    anchors = {ro_start, ro_end}
    for target in relocated.values():
        if ro_start <= target < ro_end:
            anchors.add(target)
    lea_pat = re.compile(
        rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d](....)", re.DOTALL
    )
    for m in lea_pat.finditer(data, text_start, text_end):
        disp = struct.unpack("<i", m.group(1))[0]
        target = m.end() + disp
        if ro_start <= target < ro_end:
            anchors.add(target)
    return sorted(anchors)


def write_file(rel_path: str, content: bytes | str) -> dict:
    full_path = os.path.join(PROJECT_ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    raw = content.encode("utf-8") if isinstance(content, str) else content
    with open(full_path, "wb") as f:
        f.write(raw)
    return {
        "path": rel_path,
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
    }


def main():
    print("[1/8] Reading Codex ELF binaries...")
    with open(CODEX_BIN, "rb") as f:
        codex_data = f.read()
    with open(CODE_MODE_BIN, "rb") as f:
        cm_data = f.read()

    # ELF section coordinates for bin/codex
    RO_START, RO_END = 0xE2F4000, 0xE2F4000 + 0xE44ACC
    TEXT_START, TEXT_END = 0x7420C0, 0xE2F3063
    RELRO_START, RELRO_END = 0x1135A900, 0x1135A900 + 0x50DE90

    relocated = parse_rela_dyn(codex_data, 0x288, 0x7417C8)
    sorted_anchors = collect_rodata_anchors(
        codex_data, relocated, TEXT_START, TEXT_END, RO_START, RO_END
    )
    anchor_index = {a: i for i, a in enumerate(sorted_anchors)}

    def get_anchored_slice(ro_addr: int) -> bytes:
        idx = anchor_index.get(ro_addr)
        if idx is not None and idx + 1 < len(sorted_anchors):
            return codex_data[ro_addr : sorted_anchors[idx + 1]].rstrip(b"\x00")
        nxt = bisect.bisect_right(sorted_anchors, ro_addr)
        return codex_data[ro_addr : sorted_anchors[nxt]].rstrip(b"\x00")

    manifest_files = []

    # 2. Extract Node ESM launcher & vendor metadata
    print("[2/8] Extracting Node ESM launcher and vendor metadata...")
    for src_rel, dst_rel in [
        ("bin/codex.js", "extracted-assets/launcher/codex.js"),
        ("package.json", "extracted-assets/launcher/package.json"),
        (
            "node_modules/@openai/codex-linux-x64/package.json",
            "extracted-assets/launcher/codex-linux-x64.package.json",
        ),
        (
            "node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-package.json",
            "extracted-assets/launcher/codex-package.json",
        ),
        (
            "node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-resources/voice/manifest.json",
            "extracted-assets/voice-runtime/manifest.json",
        ),
        (
            "node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-resources/voice/runtime.json",
            "extracted-assets/voice-runtime/runtime.json",
        ),
        (
            "node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex-resources/voice/sources.json",
            "extracted-assets/voice-runtime/sources.json",
        ),
    ]:
        with open(os.path.join(CODEX_PKG_ROOT, src_rel), "rb") as f:
            manifest_files.append(write_file(dst_rel, f.read()))

    # 3. Extract include_dir::DirEntry embedded system skills (0x1162f628..0x116300c8)
    print("[3/8] Extracting 45 embedded include_dir! system skill files...")
    skill_files_extracted = []
    for addr in range(0x1162F628, 0x116300F0, 0x28):
        tag = struct.unpack_from("<Q", codex_data, addr)[0]
        p_ptr = relocated.get(addr + 8)
        p_len = struct.unpack_from("<Q", codex_data, addr + 16)[0]
        c_ptr = relocated.get(addr + 24)
        c_len = struct.unpack_from("<Q", codex_data, addr + 32)[0]
        if tag == 1 and p_ptr and c_ptr:
            rel_skill_path = codex_data[p_ptr : p_ptr + p_len].decode("utf-8")
            blob = codex_data[c_ptr : c_ptr + c_len]
            rec = write_file(
                os.path.join("extracted-assets/system-skills", rel_skill_path), blob
            )
            rec["relro_vaddr"] = hex(addr)
            rec["rodata_vaddr"] = hex(c_ptr)
            manifest_files.append(rec)
            skill_files_extracted.append(rec)

    # 4. Decompress embedded Zstandard (.zst) App-Server Protocol bundles
    print("[4/8] Decompressing embedded Zstandard (.zst) App-Server Protocol bundles...")
    zst_bundles = [
        ("stable", 0xE5C6D6F, 158034),
        ("experimental", 0xE5ED6C1, 162901),
    ]
    zst_summary = {}
    for tier, ro_off, comp_len in zst_bundles:
        comp_bytes = codex_data[ro_off : ro_off + comp_len]
        proc = subprocess.run(
            ["zstd", "-d", "-c"], input=comp_bytes, capture_output=True, check=True
        )
        decomp_bytes = proc.stdout
        bundle_json_rel = f"schemas/app-server-protocol-{tier}.bundle.json"
        manifest_files.append(write_file(bundle_json_rel, decomp_bytes))
        bundle_obj = json.loads(decomp_bytes)
        ts_map = bundle_obj.get("typescript", {})
        js_map = bundle_obj.get("json_schema", {})
        int_map = bundle_obj.get("internal_json_schema", {})
        for fname, content in ts_map.items():
            write_file(f"schemas/app-server-protocol/{tier}/typescript/{fname}", content)
        for fname, content in js_map.items():
            write_file(f"schemas/app-server-protocol/{tier}/json_schema/{fname}", content)
        for fname, content in int_map.items():
            write_file(
                f"schemas/app-server-protocol/{tier}/internal_json_schema/{fname}",
                content,
            )
        zst_summary[tier] = {
            "rodata_vaddr": hex(ro_off),
            "compressed_bytes": comp_len,
            "decompressed_bytes": len(decomp_bytes),
            "sha256_compressed": sha256_bytes(comp_bytes),
            "sha256_decompressed": sha256_bytes(decomp_bytes),
            "typescript_files": len(ts_map),
            "json_schema_files": len(js_map),
            "internal_json_schema_files": len(int_map),
        }

    # 5. Extract models.json, connector-tool-templates.json, guardian-output.schema.json
    print("[5/8] Extracting embedded models.json (11 models) and JSON schemas...")
    models_raw_slice = codex_data[0xE833A82 : 0xE833A82 + 472079].decode("utf-8")
    models_obj, models_end = json.JSONDecoder().raw_decode(models_raw_slice)
    models_exact_str = models_raw_slice[:models_end]
    manifest_files.append(write_file("schemas/models.json", models_exact_str))

    model_summary_list = []
    for m in models_obj.get("models", []):
        slug = m["slug"]
        mm = m.get("model_messages") or {}
        tmpl = mm.get("instructions_template") or ""
        persist = mm.get("persistent_instructions") or ""
        if tmpl:
            manifest_files.append(
                write_file(
                    f"extracted-assets/prompts/model-instructions/{slug}.instructions.md",
                    tmpl,
                )
            )
        if persist:
            manifest_files.append(
                write_file(
                    f"extracted-assets/prompts/model-instructions/{slug}.persistent.md",
                    persist,
                )
            )
        gv2 = (mm.get("guardian_v2") or {}).get("classifier_instructions")
        if gv2 and slug == "gpt-6-astra":
            manifest_files.append(
                write_file(
                    "extracted-assets/prompts/model-instructions/guardian-v2-classifier.md",
                    gv2,
                )
            )
        conf_pol = mm.get("confirmation_policies") or {}
        if slug == "gpt-6-astra":
            for pol_name, pol_text in conf_pol.items():
                if pol_text:
                    manifest_files.append(
                        write_file(
                            f"extracted-assets/prompts/model-instructions/confirmation-policy-{pol_name}.md",
                            pol_text,
                        )
                    )
        model_summary_list.append(
            {
                "slug": slug,
                "display_name": m.get("display_name"),
                "description": m.get("description"),
                "visibility": m.get("visibility"),
                "context_window": m.get("context_window"),
                "max_context_window": m.get("max_context_window"),
                "default_reasoning_level": m.get("default_reasoning_level"),
                "supported_reasoning_levels": [
                    r.get("effort") for r in m.get("supported_reasoning_levels", [])
                ],
                "tool_mode": m.get("tool_mode"),
                "multi_agent_version": m.get("multi_agent_version"),
                "multi_agent_reasoning_effort": m.get("multi_agent_reasoning_effort"),
                "shell_type": m.get("shell_type"),
                "prefer_websockets": m.get("prefer_websockets"),
                "use_responses_lite": m.get("use_responses_lite"),
                "experimental_supported_tools": m.get("experimental_supported_tools"),
                "instructions_template_chars": len(tmpl),
                "persistent_instructions_chars": len(persist),
            }
        )
    manifest_files.append(
        write_file(
            "schemas/model-summary.json",
            json.dumps(model_summary_list, indent=2, ensure_ascii=False),
        )
    )

    templates_slice = codex_data[0xE6B578E : 0xE6B578E + 25723].decode("utf-8")
    _, t_end = json.JSONDecoder().raw_decode(templates_slice)
    manifest_files.append(
        write_file("schemas/connector-tool-templates.json", templates_slice[:t_end])
    )

    guardian_schema_slice = get_anchored_slice(0xE7B2CA3).decode("utf-8")
    manifest_files.append(
        write_file("schemas/guardian-output.schema.json", guardian_schema_slice)
    )

    # 6. Extract standalone prompts & runtime templates via exact .rodata anchors
    print("[6/8] Extracting standalone System Prompts, HTML/CSS templates, and V8 bootstrap...")
    prompt_anchors = [
        (0xE82E8AB, "extracted-assets/prompts/base-cli-system-prompt.md"),
        (0xE6FD5C6, "extracted-assets/prompts/general-agent-identity-prompt.md"),
        (0xE8C889C, "extracted-assets/prompts/plan-mode-conversational-prompt.md"),
        (0xE7A86DB, "extracted-assets/prompts/guardian-v2-async-reviewer-prompt.md"),
        (0xE8CE771, "extracted-assets/prompts/guardian-planned-action-judge-prompt.md"),
        (0xE8CC718, "extracted-assets/prompts/guardian-environment-profile-prompt.md"),
        (0xE80A296, "extracted-assets/prompts/memory-phase1-single-rollout-prompt.md"),
        (0xE7F824F, "extracted-assets/prompts/memory-phase2-consolidation-prompt.md"),
        (0xE811987, "extracted-assets/prompts/memory-rollout-extractor-prompt.md"),
        (0xE7F7232, "extracted-assets/prompts/memory-summary-consolidation-prompt.md"),
        (0xE7ECFFD, "extracted-assets/prompts/memory-subsystem-instructions.md"),
        (0xE771229, "extracted-assets/prompts/imported-external-agent-memory-rules.md"),
        (0xE6DB2D2, "extracted-assets/prompts/code-review-guidelines-prompt.md"),
        (0xE7878BD, "extracted-assets/prompts/active-thread-goal-continuation-prompt.md"),
        (0xE8C721C, "extracted-assets/prompts/sandbox-escalation-requests-prompt.md"),
        (0xE8D0D8B, "extracted-assets/prompts/computer-and-browser-use-prompt.md"),
        (0xE6874BF, "extracted-assets/prompts/code-mode-javascript-orchestration-prompt.md"),
        (0xEA324A4, "extracted-assets/prompts/web-search-internet-tool-prompt.md"),
        (0xE4877E1, "extracted-assets/prompts/proactivity-followup-prompt.md"),
        (0xEA24C80, "extracted-assets/prompts/side-conversation-prompt.md"),
        (0xE6A894C, "extracted-assets/prompts/task-catchup-summary-prompt.md"),
        (0xE976518, "extracted-assets/prompts/skills-discovery-instructions-v1.md"),
        (0xE975B35, "extracted-assets/prompts/skills-discovery-instructions-v2.md"),
        (0xEA1B290, "extracted-assets/runtime-templates/visualization-theme.css"),
        (0xEA19148, "extracted-assets/runtime-templates/visualization-fragment.html"),
        (0xE7CB2ED, "extracted-assets/runtime-templates/oauth-signin-page-1.html"),
        (0xE7C9611, "extracted-assets/runtime-templates/oauth-signin-page-2.html"),
        (0xE7CD98A, "extracted-assets/runtime-templates/oauth-signin-page-3.html"),
        (0xE6BF960, "extracted-assets/runtime-templates/shell-snapshot-expand.sh"),
        (0xE9DCAAE, "extracted-assets/runtime-templates/tui-tips.toml"),
    ]
    for ro_addr, out_rel in prompt_anchors:
        blob = get_anchored_slice(ro_addr)
        rec = write_file(out_rel, blob)
        rec["rodata_vaddr"] = hex(ro_addr)
        manifest_files.append(rec)

    # Extract macOS launchd plists (ada, babbage, curie, cushman, dali, davinci)
    for relro_addr in range(0x1166C508, 0x1166C5C0, 0x20):
        n_ptr = relocated[relro_addr]
        n_len = struct.unpack_from("<Q", codex_data, relro_addr + 8)[0]
        c_ptr = relocated[relro_addr + 16]
        c_len = struct.unpack_from("<Q", codex_data, relro_addr + 24)[0]
        name = codex_data[n_ptr : n_ptr + n_len].decode("utf-8")
        plist_bytes = codex_data[c_ptr : c_ptr + c_len]
        rec = write_file(
            f"extracted-assets/runtime-templates/macos-launchd-plists/{name}.plist",
            plist_bytes,
        )
        rec["rodata_vaddr"] = hex(c_ptr)
        manifest_files.append(rec)

    # Extract V8 promise combinator script from codex-code-mode-host @ 0x2f98b48
    v8_js = cm_data[0x2F98B48 : 0x2F98B48 + 1861]
    rec = write_file(
        "extracted-assets/runtime-templates/v8-promise-combinators.js", v8_js
    )
    rec["rodata_vaddr"] = "0x2f98b48 (codex-code-mode-host)"
    manifest_files.append(rec)

    # 7. Extract all 75 sqlx::migrate::Migration SQLite scripts & verify SHA-384
    print("[7/8] Extracting and verifying all 75 SQLite migration scripts...")
    COW_TAG = 0x8000000000000000
    migrations_meta = []
    db_group_idx = 0
    db_group_names = [
        "01-logs-db",
        "02-thread-goals-db",
        "03-thread-queue-db",
        "04-core-state-db",
        "05-memories-db",
        "06-thread-store-db",
    ]
    prev_ver = 999999
    for addr in range(RELRO_START, RELRO_END - 0x58, 8):
        if (
            struct.unpack_from("<Q", codex_data, addr)[0] == COW_TAG
            and struct.unpack_from("<Q", codex_data, addr + 0x18)[0] == COW_TAG
            and struct.unpack_from("<Q", codex_data, addr + 0x28)[0] == 48
            and struct.unpack_from("<Q", codex_data, addr + 0x30)[0] == COW_TAG
            and (addr + 0x08) in relocated
            and (addr + 0x20) in relocated
            and (addr + 0x38) in relocated
        ):
            desc_ptr = relocated[addr + 0x08]
            desc_len = struct.unpack_from("<Q", codex_data, addr + 0x10)[0]
            cksum_ptr = relocated[addr + 0x20]
            sql_ptr = relocated[addr + 0x38]
            sql_len = struct.unpack_from("<Q", codex_data, addr + 0x40)[0]
            ver = struct.unpack_from("<q", codex_data, addr + 0x48)[0]
            if ver <= prev_ver:
                db_group = (
                    db_group_names[db_group_idx]
                    if db_group_idx < len(db_group_names)
                    else f"db-{db_group_idx + 1}"
                )
                db_group_idx += 1
            prev_ver = ver
            desc = codex_data[desc_ptr : desc_ptr + desc_len].decode("utf-8")
            sql_bytes = codex_data[sql_ptr : sql_ptr + sql_len]
            expected_sha384 = codex_data[cksum_ptr : cksum_ptr + 48].hex()
            actual_sha384 = hashlib.sha384(sql_bytes).hexdigest()
            assert expected_sha384 == actual_sha384, f"SHA-384 mismatch at {hex(addr)}"
            safe_desc = re.sub(r"[^a-zA-Z0-9_-]+", "_", desc.strip()).strip("_")
            sql_rel = f"extracted-assets/sql-migrations/{db_group}/{ver:04d}_{safe_desc}.sql"
            write_file(sql_rel, sql_bytes)
            migrations_meta.append(
                {
                    "db_group": db_group,
                    "version": ver,
                    "description": desc,
                    "relro_vaddr": hex(addr),
                    "rodata_vaddr": hex(sql_ptr),
                    "bytes": sql_len,
                    "sha384": actual_sha384,
                    "sha384_verified": True,
                    "path": sql_rel,
                }
            )

    manifest_files.append(
        write_file(
            "schemas/sqlite-migrations.json",
            json.dumps(migrations_meta, indent=2, ensure_ascii=False),
        )
    )

    # 8. Extract App-Server RPC methods, Feature Flags, Env Vars, Voice Host symbols, and Crate/Function Map
    print("[8/8] Building RPC registry, Feature Flags, Env Vars, and Crate/Function Attribution Map...")
    rpc_entries = []
    for off in range(0x114B7D78, 0x114B8900, 0x10):
        if off in relocated and (off + 8) not in relocated:
            ptr = relocated[off]
            ln = struct.unpack_from("<Q", codex_data, off + 8)[0]
            if 1 <= ln <= 120 and RO_START <= ptr < RO_END:
                name = codex_data[ptr : ptr + ln].decode("utf-8")
                rpc_entries.append(
                    {
                        "relro_vaddr": hex(off),
                        "rodata_vaddr": hex(ptr),
                        "method_or_event": name,
                    }
                )
    manifest_files.append(
        write_file(
            "schemas/app-server-rpc-methods.json",
            json.dumps(rpc_entries, indent=2, ensure_ascii=False),
        )
    )

    # Feature flags via `codex features list`
    feat_proc = subprocess.run(
        [CODEX_BIN, "features", "list"], capture_output=True, text=True, check=True
    )
    feature_flags = []
    for line in feat_proc.stdout.splitlines():
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) == 3:
            feature_flags.append(
                {
                    "name": parts[0],
                    "stage": parts[1],
                    "default_enabled": parts[2] == "true",
                }
            )
    manifest_files.append(
        write_file(
            "schemas/feature-flags.json",
            json.dumps(feature_flags, indent=2, ensure_ascii=False),
        )
    )

    # Environment variables across binaries
    env_pat = re.compile(
        rb"\b((?:CODEX|OPENAI|OTEL|RUST|SSL|AWS)_[A-Z0-9_]{2,60})\b"
    )
    env_vars = sorted(
        set(
            m.decode("ascii")
            for m in env_pat.findall(codex_data) + env_pat.findall(cm_data)
        )
    )
    codex_env = [e for e in env_vars if e.startswith("CODEX_")]
    openai_env = [e for e in env_vars if e.startswith("OPENAI_")]
    other_env = [
        e
        for e in env_vars
        if not e.startswith("CODEX_") and not e.startswith("OPENAI_")
    ]
    manifest_files.append(
        write_file(
            "schemas/env-vars.json",
            json.dumps(
                {
                    "total_count": len(env_vars),
                    "codex_env_count": len(codex_env),
                    "openai_env_count": len(openai_env),
                    "other_env_count": len(other_env),
                    "CODEX": codex_env,
                    "OPENAI": openai_env,
                    "OTHER": other_env,
                },
                indent=2,
            ),
        )
    )

    # Unstripped codex-voice-host symbol analysis
    nm_proc = subprocess.run(
        ["nm", "-C", "--defined-only", VOICE_HOST_BIN],
        capture_output=True,
        text=True,
        check=True,
    )
    voice_symbols = []
    for line in nm_proc.stdout.splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) == 3:
            addr_hex, sym_type, sym_name = parts
            if "codex_voice_host" in sym_name or "codex_realtime_webrtc" in sym_name:
                voice_symbols.append(
                    {
                        "vaddr": f"0x{addr_hex}",
                        "type": sym_type,
                        "symbol": sym_name,
                    }
                )
    manifest_files.append(
        write_file(
            "schemas/voice-host-symbols.json",
            json.dumps(
                {
                    "binary": "codex-resources/voice/bin/codex-voice-host",
                    "stripped": False,
                    "total_defined_symbols": len(nm_proc.stdout.splitlines()),
                    "codex_voice_symbols_count": len(voice_symbols),
                    "codex_voice_symbols": voice_symbols,
                },
                indent=2,
            ),
        )
    )

    # Function table from .eh_frame_hdr + Location + tracing::Metadata attribution
    EH_HDR = 0xF139C60
    _, fde_count = struct.unpack_from("<ii", codex_data, EH_HDR + 4)
    func_starts = []
    table_base = EH_HDR + 12
    for i in range(fde_count):
        init_loc_rel, _ = struct.unpack_from("<ii", codex_data, table_base + i * 8)
        func_vaddr = EH_HDR + init_loc_rel
        if TEXT_START <= func_vaddr < TEXT_END:
            func_starts.append(func_vaddr)
    func_starts.sort()

    meta_targets = {}
    location_count = 0
    ws_location_count = 0
    for addr in range(RELRO_START, RELRO_END - 24, 8):
        if (
            addr in relocated
            and (addr + 8) not in relocated
            and (addr + 16) not in relocated
        ):
            f_ptr = relocated[addr]
            f_len = struct.unpack_from("<Q", codex_data, addr + 8)[0]
            if (
                4 <= f_len <= 240
                and RO_START <= f_ptr < RO_END
                and codex_data[f_ptr + f_len - 3 : f_ptr + f_len] == b".rs"
            ):
                line, col = struct.unpack_from("<II", codex_data, addr + 16)
                if 1 <= line <= 100000 and 1 <= col <= 2000:
                    f_str = codex_data[f_ptr : f_ptr + f_len].decode(
                        "utf-8", "replace"
                    )
                    meta_targets[addr] = ("location", f_str, line, col)
                    location_count += 1
                    if (
                        "registry/src" not in f_str
                        and "/rustc/" not in f_str
                        and "rustlib/src" not in f_str
                    ):
                        ws_location_count += 1

    tracing_count = 0
    crate_ident_to_dir = {}
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
            t_len = struct.unpack_from("<Q", codex_data, addr + 0x18)[0]
            m_len = struct.unpack_from("<Q", codex_data, addr + 0x48)[0]
            f_len = struct.unpack_from("<Q", codex_data, addr + 0x58)[0]
            if (
                t_ptr == m_ptr
                and t_len == m_len
                and 1 <= t_len <= 200
                and 1 <= f_len <= 250
                and RO_START <= f_ptr < RO_END
            ):
                file_s = codex_data[f_ptr : f_ptr + f_len].decode("utf-8", "replace")
                if file_s.endswith(".rs"):
                    mod_s = codex_data[m_ptr : m_ptr + m_len].decode("utf-8", "replace")
                    meta_targets[addr] = ("tracing", file_s, mod_s, 0)
                    tracing_count += 1
                    if "registry/src" not in file_s and "/src/" in file_s:
                        crate_ident_to_dir[mod_s.split("::")[0]] = file_s.split(
                            "/src/"
                        )[0]

    lea_pat = re.compile(
        rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d](....)", re.DOTALL
    )
    func_to_files: dict[int, set[str]] = {}
    for m in lea_pat.finditer(codex_data, TEXT_START, TEXT_END):
        disp = struct.unpack("<i", m.group(1))[0]
        target = m.end() + disp
        info = meta_targets.get(target)
        if info:
            idx = bisect.bisect_right(func_starts, m.start()) - 1
            if idx >= 0:
                func_to_files.setdefault(func_starts[idx], set()).add(info[1])

    # Build crate-map.json across all 3 binaries
    rs_pat = re.compile(rb"[a-zA-Z0-9_./-]+/src/[a-zA-Z0-9_./-]+\.rs")
    all_rs = sorted(set(m.decode("utf-8", "ignore") for m in rs_pat.findall(codex_data)))
    ws_rs = [
        p
        for p in all_rs
        if "registry/src" not in p
        and "/rustc/" not in p
        and "rustlib/src" not in p
        and ".cargo-home/git" not in p
    ]
    ext_crates = sorted(
        set(
            m.decode("utf-8", "ignore")
            for m in re.findall(
                rb"registry/src/[^/]+/([a-zA-Z0-9_-]+-[0-9]+\.[0-9]+\.[0-9]+[^/]*)/",
                codex_data,
            )
        )
    )

    crates_breakdown: dict[str, list[str]] = {}
    for p in ws_rs:
        cdir = p.split("/src/")[0]
        crates_breakdown.setdefault(cdir, []).append(p)

    # Count attributed functions per workspace crate
    crate_func_counts: dict[str, int] = {}
    for faddr, files in func_to_files.items():
        for f in files:
            if (
                "registry/src" not in f
                and "/rustc/" not in f
                and "rustlib/src" not in f
                and ".cargo-home/git" not in f
            ):
                cdir = f.split("/src/")[0]
                crate_func_counts[cdir] = crate_func_counts.get(cdir, 0) + 1

    crate_map_obj = {
        "version": "0.162.1",
        "build_commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
        "rust_toolchain": "1.95.0-x86_64-unknown-linux-gnu (target: x86_64-unknown-linux-musl)",
        "statistics": {
            "total_eh_frame_functions": len(func_starts),
            "panic_location_descriptors": location_count,
            "workspace_panic_location_descriptors": ws_location_count,
            "tracing_metadata_descriptors": tracing_count,
            "directly_attributed_functions": len(func_to_files),
            "workspace_source_files_recovered": len(ws_rs),
            "total_source_files_recovered": len(all_rs),
            "workspace_crates_count": len(crates_breakdown),
            "external_cargo_crates_count": len(ext_crates),
        },
        "crate_ident_to_directory": dict(sorted(crate_ident_to_dir.items())),
        "workspace_crates": [
            {
                "crate_dir": k,
                "source_file_count": len(v),
                "attributed_text_functions": crate_func_counts.get(k, 0),
                "source_files": sorted(v),
            }
            for k, v in sorted(
                crates_breakdown.items(), key=lambda x: (-len(x[1]), x[0])
            )
        ],
        "external_cargo_crates": ext_crates,
    }
    manifest_files.append(
        write_file(
            "crate-map.json",
            json.dumps(crate_map_obj, indent=2, ensure_ascii=False),
        )
    )

    manifest_obj = {
        "package": "@openai/codex",
        "version": "0.162.1",
        "build_commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
        "target_triple": "x86_64-unknown-linux-musl",
        "binaries": {
            "bin/codex": {
                "path": CODEX_BIN,
                "bytes": len(codex_data),
                "sha256": sha256_bytes(codex_data),
                "type": "ELF 64-bit LSB pie executable, x86-64, static-pie linked, stripped",
                "eh_frame_functions": len(func_starts),
                "attributed_functions": len(func_to_files),
            },
            "bin/codex-code-mode-host": {
                "path": CODE_MODE_BIN,
                "bytes": len(cm_data),
                "sha256": sha256_bytes(cm_data),
                "type": "ELF 64-bit LSB pie executable, x86-64, static-pie linked, stripped (Embedded V8 Turboshaft + Starlark 0.14.2)",
            },
            "codex-resources/voice/bin/codex-voice-host": {
                "path": VOICE_HOST_BIN,
                "bytes": os.path.getsize(VOICE_HOST_BIN),
                "sha256": sha256_file(VOICE_HOST_BIN),
                "type": "ELF 64-bit LSB pie executable, x86-64, dynamically linked, with debug_info, not stripped (WebRTC + GStreamer 1.28.6 + Sonora AEC3)",
                "defined_symbols": len(nm_proc.stdout.splitlines()),
            },
        },
        "protocol_zst_bundles": zst_summary,
        "extracted_counts": {
            "system_skill_files": len(skill_files_extracted),
            "models_in_catalog": len(model_summary_list),
            "sqlite_migrations": len(migrations_meta),
            "app_server_rpc_entries": len(rpc_entries),
            "feature_flags": len(feature_flags),
            "environment_variables": len(env_vars),
            "workspace_crates": len(crates_breakdown),
            "workspace_rs_files": len(ws_rs),
        },
        "rea_evidence": {
            "bundle_path": "rea-evidence-bundle.json",
            "javascript_application_evidence_id": "ev_732d0c22822a8007d519589185e9469498c80dbf42d535fc28ee9d40e16f0fdc",
            "feature_trace_evidence_id": "ev_ed2c0374964ea2778affaaf165687dc0d8d39cf7b874c292c4d42da842e7d24e",
            "semantic_trace_evidence_id": "ev_c0a2905b773f881d97b306546efa6c85b0ea1db5fdc2a372f16063d44841df97",
            "process_captures": {
                "version": "ev_cd7c8ab29136a1e7470c9bf978476f7a28d204a0bebf9fbd9ee8329394da8b36",
                "help": "ev_840c693c5ec6debbfeb66f537eed81d4f8e6bdfdb25056aa4d1c9b181de9172a",
                "features_list": "ev_f20f755c5a7a1c7408f52a01d9e7b66f5a3249ee7d0c4d14ad8ecb90ccf374c9",
                "debug_help": "ev_4dd6b20f7f170fc2870561cd6afef13d591b14304fcc4bd4f264ac96e7c546ef",
                "app_server_help": "ev_c6634e0bcf4997f26ae6827c22c72e0c61659c1bc7ba08eab4e95c7dbda6fecb",
                "sandbox_help": "ev_0bf219745cc2206aa2f426909f5745a3a71cebd34d45a97f74f1047471857025",
                "debug_prompt_input_default": "ev_7d5b45ed8b4298554495c03aa0d1b9f7550446d56d872e0c49df9d59e4c8b179",
                "debug_prompt_input_unrestricted": "ev_605cbbff0e7caa994463d5a5144a6424b4720c38e2dbd5ddc6a71898e1f06ec8",
            },
            "residual_unknown_id": "unk_fa3b4e8a95072375ddcfc256ac80215f105e5551dd11672b24a2db959a116628",
        },
        "files": manifest_files,
    }
    write_file(
        "manifest.json", json.dumps(manifest_obj, indent=2, ensure_ascii=False)
    )
    print("Extraction complete! Total manifest entries:", len(manifest_files))


if __name__ == "__main__":
    main()
