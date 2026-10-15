#!/usr/bin/env python3
"""
Builds the bidirectional Binary Virtual Address <-> Real Rust Source Function & Line Map
(`schemas/binary-address-map.json`) and Serde Reflection Catalog (`schemas/serde-reflection-catalog.json`).

Cross-references:
1. Local stripped ELF binaries (`bin/codex`, `bin/codex-code-mode-host`) and unstripped `codex-voice-host`
2. `.eh_frame_hdr` function boundaries `[vaddr_start, vaddr_end)`
3. `.data.rel.ro` `core::panic::Location(file, line, col)` and `tracing::Metadata(file, line, module, fields)`
4. Authentic Rust `.rs` source files in `src/` (Commit `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`),
   resolving stripped `.text` virtual addresses (previously `sub_xxxx`) to their exact real
   Rust `fn <name>` definitions and verifying line-level alignment.
"""

import bisect
import json
import os
import re
import struct

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
SCHEMAS_ROOT = os.path.join(PROJECT_ROOT, "schemas")

FN_PAT = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:const\s+)?(?:async\s+)?(?:unsafe\s+)?(?:extern\s+(?:\"[^\"]*\"\s+)?)?fn\s+([a-zA-Z0-9_]+)"
)


def index_rust_source_functions(rel_rs: str) -> tuple[int, list[tuple[int, int, str]]]:
    full_path = os.path.join(SRC_ROOT, rel_rs)
    if not os.path.exists(full_path):
        return 0, []
    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    fn_starts = []
    for idx, line in enumerate(lines, start=1):
        m = FN_PAT.match(line)
        if m:
            fn_starts.append((idx, m.group(1)))
    spans = []
    for i, (start_ln, fn_name) in enumerate(fn_starts):
        end_ln = fn_starts[i + 1][0] - 1 if i + 1 < len(fn_starts) else len(lines)
        spans.append((start_ln, end_ln, fn_name))
    return len(lines), spans


def resolve_fn_at_line(spans: list[tuple[int, int, str]], line_no: int) -> str | None:
    for s_ln, e_ln, name in spans:
        if s_ln <= line_no <= e_ln:
            return f"{name} (L{s_ln}..L{e_ln})"
    return None


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
    return s[len("codex-rs/") :] if s.startswith("codex-rs/") else s


def map_binary_functions(
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
    vaddr_delta: int,
    rs_cache: dict[str, tuple[int, list[tuple[int, int, str]]]],
):
    with open(bin_path, "rb") as f:
        data = f.read()

    relocated = {}
    for off in range(rela_off, rela_off + rela_sz, 24):
        r_offset, r_info, r_addend = struct.unpack_from("<QQq", data, off)
        if (r_info & 0xFFFFFFFF) == 8:
            relocated[r_offset] = r_addend

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
    func_index_map = {fv: i for i, fv in enumerate(func_starts)}

    meta_by_vaddr: dict[int, tuple[str, int, int, str]] = {}
    verified_locs = 0
    total_ws_locs = 0

    for f_addr in range(relro_s, relro_e - 24, 8):
        v_addr = f_addr + vaddr_delta
        if (
            v_addr in relocated
            and (v_addr + 8) not in relocated
            and (v_addr + 16) not in relocated
        ):
            p = relocated[v_addr]
            l = struct.unpack_from("<Q", data, f_addr + 8)[0]
            if 4 <= l <= 240 and ro_s <= p < ro_e and data[p + l - 3 : p + l] == b".rs":
                try:
                    s = data[p : p + l].decode("utf-8")
                except UnicodeDecodeError:
                    continue
                if is_workspace_rs(s):
                    norm_s = normalize_rs_path(s)
                    line, col = struct.unpack_from("<II", data, f_addr + 16)
                    if 1 <= line <= 100000 and 1 <= col <= 2000:
                        total_ws_locs += 1
                        if norm_s not in rs_cache:
                            rs_cache[norm_s] = index_rust_source_functions(norm_s)
                        max_ln, spans = rs_cache[norm_s]
                        if 1 <= line <= max_ln:
                            verified_locs += 1
                        fn_resolved = resolve_fn_at_line(spans, line) or "<top-level/macro>"
                        meta_by_vaddr[v_addr] = (norm_s, line, col, fn_resolved)

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
                    line_no = struct.unpack_from("<I", data, f_addr + 0x60)[0]
                    if norm_s not in rs_cache:
                        rs_cache[norm_s] = index_rust_source_functions(norm_s)
                    _, spans = rs_cache[norm_s]
                    fn_resolved = (
                        resolve_fn_at_line(spans, line_no)
                        if 1 <= line_no <= 100000
                        else None
                    ) or "<tracing-span>"
                    meta_by_vaddr[v_addr] = (
                        norm_s,
                        line_no if line_no < 100000 else 0,
                        0,
                        fn_resolved,
                    )

    lea_pat = re.compile(
        rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d](....)", re.DOTALL
    )
    func_mappings: dict[int, list[dict]] = {}
    for m in lea_pat.finditer(data, text_s, text_e):
        insn_vaddr = m.start() + vaddr_delta
        target = (m.end() + vaddr_delta) + struct.unpack("<i", m.group(1))[0]
        info = meta_by_vaddr.get(target)
        if info:
            f_idx = bisect.bisect_right(func_starts, insn_vaddr) - 1
            if f_idx >= 0:
                f_start = func_starts[f_idx]
                norm_s, ln, col, fn_resolved = info
                func_mappings.setdefault(f_start, []).append(
                    {
                        "source_file": f"src/{norm_s}",
                        "line": ln,
                        "column": col,
                        "rust_function": fn_resolved,
                    }
                )

    mapped_records = []
    for f_start, refs in sorted(func_mappings.items()):
        idx = func_index_map[f_start]
        f_end = (
            func_starts[idx + 1]
            if idx + 1 < len(func_starts)
            else (text_e + vaddr_delta)
        )
        # Deduplicate refs
        unique_refs = []
        seen = set()
        for r in refs:
            k = (r["source_file"], r["rust_function"], r["line"])
            if k not in seen:
                seen.add(k)
                unique_refs.append(r)
        primary = unique_refs[0]
        mapped_records.append(
            {
                "binary": binary_label,
                "vaddr_start": hex(f_start),
                "vaddr_end": hex(f_end),
                "size_bytes": f_end - f_start,
                "primary_source_file": primary["source_file"],
                "primary_rust_function": primary["rust_function"],
                "source_anchors": unique_refs[:8],
            }
        )

    return total_ws_locs, verified_locs, mapped_records


def main():
    print("[1/2] Mapping binary virtual addresses to real Rust functions in src/...")
    rs_cache = {}
    tot1, ver1, recs1 = map_binary_functions(
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
        0,
        rs_cache,
    )
    tot2, ver2, recs2 = map_binary_functions(
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
        0,
        rs_cache,
    )
    tot3, ver3, recs3 = map_binary_functions(
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
        0x2000,
        rs_cache,
    )

    all_recs = recs1 + recs2 + recs3
    total_locs = tot1 + tot2 + tot3
    verified_locs = ver1 + ver2 + ver3

    addr_map_obj = {
        "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
        "total_workspace_location_checkpoints": total_locs,
        "verified_in_bounds_source_checkpoints": verified_locs,
        "alignment_rate": round(verified_locs / max(1, total_locs), 6),
        "total_mapped_native_functions": len(all_recs),
        "mapped_functions_by_binary": {
            "bin/codex": len(recs1),
            "bin/codex-code-mode-host": len(recs2),
            "codex-voice-host": len(recs3),
        },
        "functions": all_recs,
    }
    out_map_path = os.path.join(SCHEMAS_ROOT, "binary-address-map.json")
    with open(out_map_path, "w", encoding="utf-8") as f:
        json.dump(addr_map_obj, f, indent=2, ensure_ascii=False)
    print(
        f"  Mapped {len(all_recs):,} native functions -> real Rust functions! "
        f"Location alignment: {verified_locs:,}/{total_locs:,} ({addr_map_obj['alignment_rate']*100:.2f}%)"
    )

    print("[2/2] Extracting Serde Reflection Catalog from .rodata...")
    with open(CODEX_BIN, "rb") as f:
         f.seek(0xE2F4000)
         rodata = f.read(0xE44ACC)

    structs = sorted(
        set(
            m.decode("utf-8", "ignore")
            for m in re.findall(rb"struct [A-Z][a-zA-Z0-9_]* with [0-9]+ elements?", rodata)
        )
    )
    variants = sorted(
        set(
            m.decode("utf-8", "ignore")
            for m in re.findall(
                rb"struct variant [A-Z][a-zA-Z0-9_:]* with [0-9]+ elements?", rodata
            )
        )
    )
    tagged_enums = sorted(
        set(
            m.decode("utf-8", "ignore")
            for m in re.findall(rb"internally tagged enum [A-Z][a-zA-Z0-9_:]*", rodata)
        )
    )
    untagged_enums = sorted(
        set(
            m.decode("utf-8", "ignore")
            for m in re.findall(rb"untagged enum [A-Z][a-zA-Z0-9_:]*", rodata)
        )
    )

    serde_obj = {
        "counts": {
            "structs": len(structs),
            "struct_variants": len(variants),
            "internally_tagged_enums": len(tagged_enums),
            "untagged_enums": len(untagged_enums),
        },
        "structs": structs,
        "struct_variants": variants,
        "internally_tagged_enums": tagged_enums,
        "untagged_enums": untagged_enums,
    }
    with open(os.path.join(SCHEMAS_ROOT, "serde-reflection-catalog.json"), "w", encoding="utf-8") as f:
        json.dump(serde_obj, f, indent=2, ensure_ascii=False)
    print("  Saved schemas/serde-reflection-catalog.json!")


if __name__ == "__main__":
    main()
