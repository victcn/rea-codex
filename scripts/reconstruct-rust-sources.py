#!/usr/bin/env python3
"""
Reconstructs the complete Rust workspace tree (`src/`) for @openai/codex v0.162.1
across all 3 native ELF binaries:
  - bin/codex (113 crates, 1,458 .rs files)
  - bin/codex-code-mode-host (code-mode-host, code-mode-runtime, otel-trace-websocket)
  - codex-resources/voice/bin/codex-voice-host (voice-host, realtime-webrtc with unstripped symbols)
plus `src/launcher/codex.js`.

For every reconstructed `.rs` file, embeds:
  1. Crate & module identity
  2. All recovered `tracing::Metadata` spans/events with line numbers & field schemas
  3. All recovered `core::panic::Location` source line/column checkpoints
  4. All attributed `.text` functions (`[vaddr_start, vaddr_end)`) from `.eh_frame_hdr`,
     including referenced `.rodata` string literals and direct `CALL rel32` edges
  5. For `voice-host` and `realtime-webrtc`, all unstripped demangled symbol signatures
"""

import bisect
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
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")


def is_workspace_rs(s: str) -> bool:
    if not s.endswith(".rs") or "/src/" not in s:
        return False
    if any(c in s for c in "\x00\n\r\t "):
        return False
    excluded = (
        "registry/src",
        "/rustc/",
        "rustlib/src",
        ".cargo-home/git",
        "/rust/deps/",
        "external/rules_rs",
        "library/",
    )
    return not any(ex in s for ex in excluded)


def normalize_rs_path(s: str) -> str:
    if s.startswith("codex-rs/"):
        return s[len("codex-rs/") :]
    return s


def analyze_elf_binary(
    bin_path: str,
    binary_label: str,
    rela_off: int,
    rela_sz: int,
    text_s: int,
    text_e: int,
    ro_s: int,
    ro_e: int,
    relro_s: int,
    relro_e: int,
    eh_hdr_off: int,
    vaddr_delta: int = 0,
):
    with open(bin_path, "rb") as f:
        data = f.read()

    relocated = {}
    for off in range(rela_off, rela_off + rela_sz, 24):
        r_offset, r_info, r_addend = struct.unpack_from("<QQq", data, off)
        if (r_info & 0xFFFFFFFF) == 8:
            relocated[r_offset] = r_addend

    # Collect .rodata anchors for string extraction
    ro_anchors = {ro_s, ro_e}
    for t in relocated.values():
        if ro_s <= t < ro_e:
            ro_anchors.add(t)

    lea_pat = re.compile(
        rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d](....)", re.DOTALL
    )
    for m in lea_pat.finditer(data, text_s, text_e):
        target = (m.end() + vaddr_delta) + struct.unpack("<i", m.group(1))[0]
        if ro_s <= target < ro_e:
            ro_anchors.add(target)
    sorted_anchors = sorted(ro_anchors)

    # Parse .eh_frame_hdr functions
    _, fde_count = struct.unpack_from("<ii", data, eh_hdr_off + 4)
    func_starts = []
    table_base = eh_hdr_off + 12
    eh_hdr_vaddr = eh_hdr_off + vaddr_delta
    for i in range(fde_count):
        init_loc_rel, _ = struct.unpack_from("<ii", data, table_base + i * 8)
        fv = eh_hdr_vaddr + init_loc_rel
        if (text_s + vaddr_delta) <= fv < (text_e + vaddr_delta):
            func_starts.append(fv)
    func_starts.sort()

    # Collect exact .rs files, Locations, and tracing::Metadata from .data.rel.ro
    file_set = set()
    file_locations: dict[str, list[tuple[int, int, int]]] = {}
    file_tracings: dict[str, list[dict]] = {}
    meta_by_vaddr: dict[int, str] = {}
    crate_ident_map: dict[str, str] = {}

    for f_addr in range(relro_s, relro_e - 24, 8):
        v_addr = f_addr + vaddr_delta
        if v_addr in relocated and (v_addr + 8) not in relocated:
            p = relocated[v_addr]
            l = struct.unpack_from("<Q", data, f_addr + 8)[0]
            if 4 <= l <= 240 and ro_s <= p < ro_e and data[p + l - 3 : p + l] == b".rs":
                try:
                    s = data[p : p + l].decode("utf-8")
                except UnicodeDecodeError:
                    continue
                if is_workspace_rs(s):
                    norm_s = normalize_rs_path(s)
                    file_set.add(norm_s)
                    if (v_addr + 16) not in relocated:
                        line, col = struct.unpack_from("<II", data, f_addr + 16)
                        if 1 <= line <= 100000 and 1 <= col <= 2000:
                            file_locations.setdefault(norm_s, []).append(
                                (line, col, v_addr)
                            )
                            meta_by_vaddr[v_addr] = norm_s

    for f_addr in range(relro_s, relro_e - 0x68, 8):
        v_addr = f_addr + vaddr_delta
        if (
            v_addr in relocated
            and (v_addr + 0x10) in relocated
            and (v_addr + 0x40) in relocated
            and (v_addr + 0x50) in relocated
        ):
            t_ptr = relocated[v_addr + 0x10]
            m_ptr = relocated[v_addr + 0x40]
            fl_ptr = relocated[v_addr + 0x50]
            t_len = struct.unpack_from("<Q", data, f_addr + 0x18)[0]
            m_len = struct.unpack_from("<Q", data, f_addr + 0x48)[0]
            fl_len = struct.unpack_from("<Q", data, f_addr + 0x58)[0]
            if (
                t_ptr == m_ptr
                and t_len == m_len
                and 1 <= t_len <= 200
                and 1 <= fl_len <= 250
                and ro_s <= fl_ptr < ro_e
            ):
                file_s = data[fl_ptr : fl_ptr + fl_len].decode("utf-8", "replace")
                if is_workspace_rs(file_s):
                    norm_s = normalize_rs_path(file_s)
                    file_set.add(norm_s)
                    n_ptr = relocated[v_addr]
                    n_len = struct.unpack_from("<Q", data, f_addr + 0x08)[0]
                    name_s = data[n_ptr : n_ptr + n_len].decode("utf-8", "replace")
                    mod_s = data[m_ptr : m_ptr + m_len].decode("utf-8", "replace")
                    line_no = struct.unpack_from("<I", data, f_addr + 0x60)[0]
                    fields_ptr = relocated.get(v_addr + 0x20)
                    fields_len = struct.unpack_from("<Q", data, f_addr + 0x28)[0]
                    fields = []
                    if (
                        fields_ptr
                        and (relro_s + vaddr_delta)
                        <= fields_ptr
                        < (relro_e + vaddr_delta)
                        and 0 < fields_len <= 32
                    ):
                        for fi in range(fields_len):
                            fp_v = fields_ptr + fi * 16
                            fp_f = fp_v - vaddr_delta
                            fp = relocated.get(fp_v)
                            fl = struct.unpack_from("<Q", data, fp_f + 8)[0]
                            if fp and ro_s <= fp < ro_e and 1 <= fl <= 80:
                                fields.append(
                                    data[fp : fp + fl].decode("utf-8", "replace")
                                )
                    cdir = norm_s.split("/src/")[0]
                    crate_ident_map[cdir] = mod_s.split("::")[0]
                    file_tracings.setdefault(norm_s, []).append(
                        {
                            "vaddr": hex(v_addr),
                            "name": name_s,
                            "module_path": mod_s,
                            "line": line_no if line_no < 100000 else 0,
                            "fields": fields,
                        }
                    )
                    meta_by_vaddr[v_addr] = norm_s

    # Attribute .text functions to workspace .rs files and collect referenced strings inside those functions
    func_to_files: dict[int, set[str]] = {}
    func_ro_refs: dict[int, list[int]] = {}
    for m in lea_pat.finditer(data, text_s, text_e):
        insn_vaddr = m.start() + vaddr_delta
        target = (m.end() + vaddr_delta) + struct.unpack("<i", m.group(1))[0]
        f_idx = bisect.bisect_right(func_starts, insn_vaddr) - 1
        if f_idx < 0:
            continue
        f_start = func_starts[f_idx]
        norm_s = meta_by_vaddr.get(target)
        if norm_s:
            func_to_files.setdefault(f_start, set()).add(norm_s)
        elif ro_s <= target < ro_e:
            func_ro_refs.setdefault(f_start, []).append(target)

    file_functions: dict[str, list[dict]] = {}
    func_index_map = {fv: i for i, fv in enumerate(func_starts)}
    for f_start, f_files in sorted(func_to_files.items()):
        idx = func_index_map[f_start]
        f_end = (
            func_starts[idx + 1]
            if idx + 1 < len(func_starts)
            else (text_e + vaddr_delta)
        )
        strings = []
        seen_ro = set()
        for ro_t in func_ro_refs.get(f_start, [])[:24]:
            if ro_t in seen_ro:
                continue
            seen_ro.add(ro_t)
            a_idx = bisect.bisect_right(sorted_anchors, ro_t)
            a_end = sorted_anchors[a_idx] if a_idx < len(sorted_anchors) else ro_t + 120
            raw = data[ro_t : min(a_end, ro_t + 160)].rstrip(b"\x00")
            if 3 <= len(raw) <= 160 and b"\x00" not in raw:
                try:
                    st = raw.decode("utf-8")
                    if st.isprintable() or "\n" in st:
                        strings.append(st)
                except UnicodeDecodeError:
                    pass
        f_rec = {
            "binary": binary_label,
            "vaddr_start": hex(f_start),
            "vaddr_end": hex(f_end),
            "size_bytes": f_end - f_start,
            "strings": strings[:12],
        }
        for nf in f_files:
            file_functions.setdefault(nf, []).append(f_rec)

    return file_set, file_locations, file_tracings, file_functions, crate_ident_map


def main():
    if os.path.exists(SRC_ROOT):
        shutil.rmtree(SRC_ROOT)
    os.makedirs(SRC_ROOT, exist_ok=True)

    print("[1/4] Analyzing bin/codex, bin/codex-code-mode-host, and codex-voice-host...")
    c_files, c_locs, c_traces, c_funcs, c_crates = analyze_elf_binary(
        CODEX_BIN,
        "bin/codex",
        0x288,
        0x7417C8,
        0x7420C0,
        0xE2F3063,
        0xE2F4000,
        0xE2F4000 + 0xE44ACC,
        0x1135A900,
        0x1135A900 + 0x50DE90,
        0xF139C60,
    )
    cm_files, cm_locs, cm_traces, cm_funcs, cm_crates = analyze_elf_binary(
        CODE_MODE_BIN,
        "bin/codex-code-mode-host",
        0x288,
        0x342780,
        0x344000,
        0x344000 + 0x2B6E16E,
        0x2EB3000,
        0x2EB3000 + 0xF0301C,
        0x449CDE0,
        0x449CDE0 + 0x1C7D70,
        0x3DB71BC,
    )
    vh_files, vh_locs, vh_traces, vh_funcs, vh_crates = analyze_elf_binary(
        VOICE_HOST_BIN,
        "codex-voice-host",
        0x3EF0,
        0x68028,
        0x2E3980,
        0x2E3980 + 0x6D3A00,
        0x6D000,
        0x6D000 + 0x130CA0,
        0x9B8020,
        0x9B8020 + 0x410E8,
        0x205FF8,
        vaddr_delta=0x2000,
    )

    all_files = sorted(c_files | cm_files | vh_files)
    all_crates = {**vh_crates, **cm_crates, **c_crates}

    # Load voice-host unstripped symbols for voice-host/ and realtime-webrtc/
    with open(os.path.join(PROJECT_ROOT, "schemas/voice-host-symbols.json")) as f:
        vh_sym_data = json.load(f)
    vh_syms_by_mod: dict[str, list[dict]] = {}
    for sym in vh_sym_data.get("codex_voice_symbols", []):
        sname = sym["symbol"]
        if "codex_realtime_webrtc::protocol" in sname:
            vh_syms_by_mod.setdefault("realtime-webrtc/src/protocol.rs", []).append(sym)
        elif "codex_voice_host::" in sname:
            after = sname.split("codex_voice_host::", 1)[1]
            submod = after.split("::")[0]
            target_file = f"voice-host/src/{submod}.rs"
            if target_file not in vh_files:
                target_file = "voice-host/src/main.rs"
            vh_syms_by_mod.setdefault(target_file, []).append(sym)

    print(f"[2/4] Materializing {len(all_files)} reconstructed .rs files into src/...")
    crates_to_files: dict[str, list[str]] = {}
    for rel_rs in all_files:
        cdir = rel_rs.split("/src/")[0]
        crates_to_files.setdefault(cdir, []).append(rel_rs)

        locs = sorted(
            set(c_locs.get(rel_rs, []) + cm_locs.get(rel_rs, []) + vh_locs.get(rel_rs, []))
        )
        traces = c_traces.get(rel_rs, []) + cm_traces.get(rel_rs, []) + vh_traces.get(rel_rs, [])
        funcs = c_funcs.get(rel_rs, []) + cm_funcs.get(rel_rs, []) + vh_funcs.get(rel_rs, [])
        demangled_syms = vh_syms_by_mod.get(rel_rs, [])

        crate_ident = all_crates.get(cdir, "codex_" + cdir.replace("/", "_").replace("-", "_"))
        lines = [
            f"//! Reconstructed Rust source skeleton for `{rel_rs}`",
            f"//! Crate: `{crate_ident}` (`{cdir}`)",
            "//! Target: `@openai/codex` v0.162.1 (`092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`)",
            f"//! Recovered: {len(funcs)} attributed `.text` functions, {len(traces)} tracing spans/events, {len(locs)} panic locations",
            "",
            "#![allow(dead_code, unused_variables, non_snake_case)]",
            "",
        ]

        if traces:
            lines.append("// === Recovered `tracing::Metadata` Spans & Events ===")
            for tr in sorted(traces, key=lambda x: x["line"] or 0):
                fld_s = ", ".join(f'"{k}"' for k in tr["fields"])
                lines.append(
                    f'// [line {tr["line"] or "?"}] target="{tr["module_path"]}" name={tr["name"]!r} fields=[{fld_s}] @ {tr["vaddr"]}'
                )
            lines.append("")

        if locs:
            lines.append("// === Recovered `core::panic::Location` Checkpoints ===")
            for ln_no, col_no, vaddr in locs[:80]:
                lines.append(f"// [line {ln_no}:{col_no}] Location descriptor @ {hex(vaddr)}")
            if len(locs) > 80:
                lines.append(f"// ... ({len(locs) - 80} more Location checkpoints)")
            lines.append("")

        if demangled_syms:
            lines.append("// === Unstripped Demangled Symbols (`codex-voice-host` DWARF/.symtab) ===")
            for sym in demangled_syms:
                lines.append(f'// [{sym["vaddr"]}] ({sym["type"]}) {sym["symbol"]}')
            lines.append("")

        if funcs:
            lines.append("// === Attributed Native `.text` Functions (`.eh_frame_hdr` + `LEA` Xrefs) ===")
            for fn_idx, fn_rec in enumerate(funcs):
                fn_ident = f'sub_{fn_rec["vaddr_start"][2:]}'
                lines.append(
                    f"/// Binary: `{fn_rec['binary']}` | Range: `{fn_rec['vaddr_start']}..{fn_rec['vaddr_end']}` ({fn_rec['size_bytes']} bytes)"
                )
                for st in fn_rec["strings"]:
                    lines.append(f"/// String literal: {json.dumps(st, ensure_ascii=False)}")
                lines.append(f"pub fn {fn_ident}() {{")
                for st in fn_rec["strings"][:5]:
                    lines.append(f"    let _lit = {json.dumps(st, ensure_ascii=False)};")
                lines.append("}")
                lines.append("")

        out_path = os.path.join(SRC_ROOT, rel_rs)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # 3. Generate Cargo.toml for every crate + root workspace Cargo.toml
    print(f"[3/4] Generating Cargo.toml manifests for {len(crates_to_files)} crates...")
    workspace_members = []
    for cdir, flist in sorted(crates_to_files.items()):
        workspace_members.append(cdir)
        pkg_name = all_crates.get(cdir, "codex-" + cdir.replace("/", "-")).replace("_", "-")
        has_main = any(f.endswith("/src/main.rs") for f in flist)
        has_lib = any(f.endswith("/src/lib.rs") for f in flist)
        cargo_lines = [
            "[package]",
            f'name = "{pkg_name}"',
            'version = "0.162.1"',
            'edition = "2024"',
            'license = "Apache-2.0"',
            "",
        ]
        if has_lib or not has_main:
            entry = "src/lib.rs" if has_lib else flist[0][len(cdir) + 1 :]
            cargo_lines += ["[lib]", f'path = "{entry}"', ""]
        if has_main:
            cargo_lines += ["[[bin]]", f'name = "{pkg_name}"', 'path = "src/main.rs"', ""]
        cargo_path = os.path.join(SRC_ROOT, cdir, "Cargo.toml")
        os.makedirs(os.path.dirname(cargo_path), exist_ok=True)
        with open(cargo_path, "w", encoding="utf-8") as f:
            f.write("\n".join(cargo_lines))

    root_cargo = [
        "[workspace]",
        'resolver = "2"',
        "members = [",
        *[f'    "{m}",' for m in workspace_members],
        "]",
        "",
        "[workspace.package]",
        'version = "0.162.1"',
        'edition = "2024"',
        'license = "Apache-2.0"',
        'repository = "https://github.com/openai/codex"',
        "",
    ]
    with open(os.path.join(SRC_ROOT, "Cargo.toml"), "w", encoding="utf-8") as f:
        f.write("\n".join(root_cargo))

    # Copy Node launcher into src/launcher/codex.js
    print("[4/4] Copying Node ESM launcher into src/launcher/codex.js...")
    os.makedirs(os.path.join(SRC_ROOT, "launcher"), exist_ok=True)
    shutil.copy2(
        os.path.join(CODEX_PKG_ROOT, "bin/codex.js"),
        os.path.join(SRC_ROOT, "launcher/codex.js"),
    )
    print(
        f"Reconstruction complete: {len(all_files)} .rs files across {len(crates_to_files)} crates + src/launcher/codex.js!"
    )


if __name__ == "__main__":
    main()
