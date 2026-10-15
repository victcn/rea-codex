#!/usr/bin/env python3
"""
Fetches and verifies the exact Rust source code for the 6 patched Git fork dependencies
referenced in `src/Cargo.lock` and embedded in `bin/codex` `.rodata` panic/tracing tables,
and maps their `.text` stripped native functions (`sub_xxxx`) to real Rust `fn` definitions.
"""

import bisect
import io
import json
import re
import struct
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path("/code/custom-dev/rea-codex-demo")
VENDOR_ROOT = Path("/usr/local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl")
BIN_CODEX = VENDOR_ROOT / "bin" / "codex"
OUT_DIR = ROOT / "extracted-assets" / "git-fork-sources"
SCHEMAS_DIR = ROOT / "schemas"

FORK_REPOS = {
    "crossterm-ce0318b92aca4e8d": {
        "repo": "openai-oss-forks/crossterm",
        "commit": "ed1cdab335221515706178d68495bba2aed1924f",
        "commit_short": "ed1cdab",
    },
    "h3-24d7712dbc030d43": {
        "repo": "hyperium/h3",
        "commit": "e07e69412876f7e26f026bd75a48b2704d8c8283",
        "commit_short": "e07e694",
    },
    "nucleo-425d994cd74b3654": {
        "repo": "helix-editor/nucleo",
        "commit": "4253de9faabb4e5c6d81d946a5e35a90f87347ee",
        "commit_short": "4253de9",
    },
    "rust-sdk-773cd6d57c4837f3": {
        "repo": "modelcontextprotocol/rust-sdk",
        "commit": "3e636cab26c013eca5131103c03d20237f12c4df",
        "commit_short": "3e636ca",
    },
    "tokio-tungstenite-ea4445d9acecae62": {
        "repo": "openai-oss-forks/tokio-tungstenite",
        "commit": "0e5b2d73aa18dd9f0a50ee9ff199d5aef7594186",
        "commit_short": "0e5b2d7",
    },
    "tungstenite-rs-006aed970da0a0a9": {
        "repo": "openai-oss-forks/tungstenite-rs",
        "commit": "4fffad30fe373adbdcffab9545e9e9bf4f2fc19f",
        "commit_short": "4fffad3",
    },
}

FN_PAT = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:const\s+)?(?:async\s+)?(?:unsafe\s+)?(?:extern\s+(?:\"[^\"]*\"\s+)?)?fn\s+([a-zA-Z0-9_]+)"
)


def index_rust_file(path: Path):
    if not path.exists():
        return 0, []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    fn_starts = []
    for idx, line in enumerate(lines, start=1):
        m = FN_PAT.match(line)
        if m:
            fn_starts.append((idx, m.group(1)))
    spans = []
    for i, (s_ln, fn_name) in enumerate(fn_starts):
        e_ln = fn_starts[i + 1][0] - 1 if i + 1 < len(fn_starts) else len(lines)
        spans.append((s_ln, e_ln, fn_name))
    return len(lines), spans


def resolve_fn(spans, line_no: int):
    for s_ln, e_ln, name in spans:
        if s_ln <= line_no <= e_ln:
            return f"{name} (L{s_ln}..L{e_ln})"
    return "<top-level/macro>"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for checkout_id, meta in FORK_REPOS.items():
        dest = OUT_DIR / checkout_id / meta["commit_short"]
        if dest.exists() and any(dest.rglob("*.rs")):
            print(f"  [cached] {checkout_id} ({meta['repo']} @ {meta['commit_short']})")
            continue
        url = f"https://codeload.github.com/{meta['repo']}/tar.gz/{meta['commit']}"
        print(f"  [downloading] {url} -> {dest}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            tar_bytes = resp.read()
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                parts = Path(member.name).parts
                if len(parts) <= 1:
                    continue
                rel = Path(*parts[1:])
                target_path = dest / rel
                target_path.parent.mkdir(parents=True, exist_ok=True)
                extracted = tf.extractfile(member)
                if extracted:
                    target_path.write_bytes(extracted.read())

    data = BIN_CODEX.read_bytes()
    RELA_OFF = 0x288
    RELA_SZ = 0x7417C8
    TEXT_S = 0x7420C0
    TEXT_E = 0xE2F3063
    RO_S = 0xE2F4000
    RO_E = 0xE2F4000 + 0xE44ACC
    RELRO_S = 0x1135A900
    RELRO_E = 0x1135A900 + 0x50DE90
    EH_HDR_OFF = 0xF139C60

    relocated = {}
    for off in range(RELA_OFF, RELA_OFF + RELA_SZ, 24):
        r_offset, r_info, r_addend = struct.unpack_from("<QQq", data, off)
        if (r_info & 0xFFFFFFFF) == 8:
            relocated[r_offset] = r_addend

    _, fde_count = struct.unpack_from("<ii", data, EH_HDR_OFF + 4)
    func_starts = []
    table_base = EH_HDR_OFF + 12
    for i in range(fde_count):
        init_loc_rel, _ = struct.unpack_from("<ii", data, table_base + i * 8)
        fv = EH_HDR_OFF + init_loc_rel
        if TEXT_S <= fv < TEXT_E:
            func_starts.append(fv)
    func_starts.sort()
    func_index_map = {fv: i for i, fv in enumerate(func_starts)}

    git_pat = re.compile(r"\.cargo-home/git/checkouts/([A-Za-z0-9_.-]+-[0-9a-f]{16})/([0-9a-f]+)/(.+\.rs)$")

    rs_cache = {}
    meta_by_vaddr = {}
    per_fork_locations = {k: [] for k in FORK_REPOS}
    total_locations = 0
    verified_locations = 0

    for f_addr in range(RELRO_S, RELRO_E - 24, 8):
        if f_addr in relocated and (f_addr + 8) not in relocated and (f_addr + 16) not in relocated:
            p = relocated[f_addr]
            l = struct.unpack_from("<Q", data, f_addr + 8)[0]
            if 10 <= l <= 300 and RO_S <= p < RO_E and data[p + l - 3:p + l] == b".rs":
                s = data[p:p + l].decode("utf-8", errors="ignore")
                m = git_pat.search(s)
                if m:
                    checkout_id, commit_short, rel_rs = m.groups()
                    line, col = struct.unpack_from("<II", data, f_addr + 16)
                    if 1 <= line <= 100000 and 1 <= col <= 2000 and checkout_id in FORK_REPOS:
                        total_locations += 1
                        local_rs = OUT_DIR / checkout_id / commit_short / rel_rs
                        if local_rs not in rs_cache:
                            rs_cache[local_rs] = index_rust_file(local_rs)
                        max_ln, spans = rs_cache[local_rs]
                        valid = 1 <= line <= max_ln
                        if valid:
                            verified_locations += 1
                        fn_resolved = resolve_fn(spans, line)
                        meta_by_vaddr[f_addr] = (checkout_id, commit_short, rel_rs, line, col, fn_resolved)
                        per_fork_locations[checkout_id].append({
                            "location_va": hex(f_addr),
                            "file": rel_rs,
                            "line": line,
                            "col": col,
                            "rust_function": fn_resolved,
                            "verified_in_source": valid,
                        })

    # Map .text functions referencing these Git fork panic locations
    lea_pat = re.compile(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d](....)", re.DOTALL)
    per_fork_functions = {k: {} for k in FORK_REPOS}
    for m in lea_pat.finditer(data, TEXT_S, TEXT_E):
        insn_vaddr = m.start()
        target = m.end() + struct.unpack("<i", m.group(1))[0]
        info = meta_by_vaddr.get(target)
        if info:
            checkout_id, commit_short, rel_rs, ln, col, fn_resolved = info
            f_idx = bisect.bisect_right(func_starts, insn_vaddr) - 1
            if f_idx >= 0:
                f_start = func_starts[f_idx]
                f_end = func_starts[f_idx + 1] if f_idx + 1 < len(func_starts) else TEXT_E
                per_fork_functions[checkout_id][f_start] = {
                    "vaddr_start": hex(f_start),
                    "vaddr_end": hex(f_end),
                    "size_bytes": f_end - f_start,
                    "source_file": f"extracted-assets/git-fork-sources/{checkout_id}/{commit_short}/{rel_rs}",
                    "line": ln,
                    "rust_function": fn_resolved,
                }

    # Scan .rodata for all `.cargo-home/git/checkouts/...` strings
    raw_pat = re.compile(rb"(/[^\x00\n\r\"']*?\.cargo-home/git/checkouts/([A-Za-z0-9_.-]+-[0-9a-f]{16})/([0-9a-f]+)/([^\x00\n\r\"':]+\.rs))")
    referenced_by_fork = {k: set() for k in FORK_REPOS}
    for m in raw_pat.finditer(data, RO_S, RO_E):
        cid = m.group(2).decode("ascii")
        rel_rs = m.group(4).decode("utf-8")
        if cid in referenced_by_fork:
            referenced_by_fork[cid].add(rel_rs)

    tracing_cat = json.loads((SCHEMAS_DIR / "tracing-metadata-catalog.json").read_text(encoding="utf-8"))
    fork_list = []
    total_files = 0
    total_mapped_fns = 0
    for checkout_id, meta in sorted(FORK_REPOS.items()):
        dest = OUT_DIR / checkout_id / meta["commit_short"]
        all_rs = sorted(str(p.relative_to(dest)) for p in dest.rglob("*.rs"))
        referenced_rs = sorted(referenced_by_fork[checkout_id])
        existing_ref_rs = [r for r in referenced_rs if (dest / r).exists()]
        total_files += len(all_rs)

        t_recs = [
            {
                "name": rec.get("name"),
                "target": rec.get("target"),
                "level": rec.get("level"),
                "file": rec.get("file"),
                "line": rec.get("line"),
            }
            for rec in tracing_cat.get("records", [])
            if checkout_id in rec.get("file", "")
        ]

        locs = per_fork_locations[checkout_id]
        mapped_fns = list(per_fork_functions[checkout_id].values())
        total_mapped_fns += len(mapped_fns)

        fork_list.append({
            "cargo_checkout_id": checkout_id,
            "github_repo": meta["repo"],
            "commit_sha": meta["commit"],
            "commit_short": meta["commit_short"],
            "extracted_source_dir": f"extracted-assets/git-fork-sources/{checkout_id}/{meta['commit_short']}",
            "total_rust_files_in_repo": len(all_rs),
            "binary_referenced_file_count": len(referenced_rs),
            "verified_existing_file_count": len(existing_ref_rs),
            "binary_referenced_files": referenced_rs,
            "panic_location_count": len(locs),
            "verified_panic_location_count": sum(1 for l in locs if l["verified_in_source"]),
            "mapped_native_function_count": len(mapped_fns),
            "mapped_native_functions": mapped_fns[:50],
            "panic_locations_sample": locs[:25],
            "tracing_record_count": len(t_recs),
            "tracing_records_sample": t_recs[:25],
        })

    report = {
        "total_git_fork_repositories": len(fork_list),
        "total_extracted_rust_files": total_files,
        "total_binary_referenced_files": sum(f["binary_referenced_file_count"] for f in fork_list),
        "total_verified_referenced_files": sum(f["verified_existing_file_count"] for f in fork_list),
        "total_panic_locations": total_locations,
        "verified_panic_locations": verified_locations,
        "panic_verification_accuracy": f"{(verified_locations / total_locations * 100.0) if total_locations else 100.0:.2f}%",
        "total_mapped_native_functions": total_mapped_fns,
        "git_forks": fork_list,
    }
    (SCHEMAS_DIR / "git-fork-dependencies.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"Verified {verified_locations}/{total_locations} ({report['panic_verification_accuracy']}) panic locations, "
        f"{report['total_verified_referenced_files']}/{report['total_binary_referenced_files']} referenced .rs files, "
        f"and mapped {total_mapped_fns} native .text functions across {len(fork_list)} Git forks ({total_files} total .rs files extracted)!"
    )


if __name__ == "__main__":
    main()
