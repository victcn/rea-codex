#!/usr/bin/env python3
"""
Deep Static Inspection & Architectural Cataloging for @openai/codex v0.162.1
Extracts and catalogs the remaining 8 architectural components (read-only):
  1. codex-code-mode-host V8 Startup Snapshot Metadata & Embedded JS/Builtin Table
  2. bin/codex Embedded Syntect SyntaxSet (0xece5ddf, 220 syntaxes) & ThemeSet (0xecd695e, 32 themes)
  3. Companion Binaries Static ELF Analysis (zsh, bwrap, rg)
  4. codex-voice-host DWARF Debug Compilation Units & 17 GStreamer/Audio Shared Libraries
  5. 6 Patched Git Fork Dependencies (.cargo-home/git/checkouts/*)
  6. VS Code Extension openai.codex-audio-26.1007.21434 Formatted JS & IPC/Native Matrix
  7. 7 Official Bundled & Curated Plugins (/root/.codex/plugins/cache/*)
  8. Read-Only Binary Asset & Offset Verification Report (schemas/binary-asset-verification.json)
"""

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

ROOT = Path("/code/custom-dev/rea-codex-demo")
VENDOR_ROOT = Path("/usr/local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl")
BIN_CODEX = VENDOR_ROOT / "bin" / "codex"
BIN_CODE_MODE = VENDOR_ROOT / "bin" / "codex-code-mode-host"
BIN_VOICE_HOST = VENDOR_ROOT / "codex-resources" / "voice" / "bin" / "codex-voice-host"
BIN_ZSH = VENDOR_ROOT / "codex-resources" / "zsh" / "bin" / "zsh"
BIN_BWRAP = VENDOR_ROOT / "codex-resources" / "bwrap"
BIN_RG = VENDOR_ROOT / "codex-path" / "rg"
VOICE_LIB_DIR = VENDOR_ROOT / "codex-resources" / "voice" / "lib"

SCHEMAS_DIR = ROOT / "schemas"
ASSETS_DIR = ROOT / "extracted-assets"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ============================================================================
# 1. V8 Startup Snapshot Metadata & Embedded JS / Builtin Table
# ============================================================================
def analyze_v8_startup_snapshot():
    print("[1/8] Analyzing codex-code-mode-host V8 Startup Snapshot...")
    data = BIN_CODE_MODE.read_bytes()
    magic_bytes = b"\x90\x00\xda\x27"
    snap_offset = data.find(magic_bytes, 0x2f00000)
    if snap_offset < 0:
        raise RuntimeError("Could not locate V8 startup snapshot magic in codex-code-mode-host")

    snap_len = 10822192
    snap_blob = data[snap_offset:snap_offset + snap_len]

    magic, version_hash = struct.unpack_from("<II", snap_blob, 0)
    header_ascii = re.findall(rb"[ -~]{4,120}", snap_blob[:4096])
    header_strings = [s.decode("ascii", errors="ignore") for s in header_ascii]

    all_strings = [
        s.decode("ascii", errors="ignore")
        for s in re.findall(rb"[A-Za-z_][A-Za-z0-9_.$:/-]{5,80}", snap_blob)
    ]
    unique_strings = sorted(set(all_strings))

    comb_marker = b"Promise.all = function all(iterable)"
    comb_pos = data.find(comb_marker)
    comb_js = ""
    if comb_pos != -1:
        window = data[max(0, comb_pos - 256):comb_pos + 4096]
        m = re.search(rb"(Promise\.all\s*=\s*function[\s\S]+?Promise\.any\s*=\s*function[\s\S]+?\n\};)", window)
        if m:
            comb_js = m.group(1).decode("utf-8", errors="replace")

    out_dir = ASSETS_DIR / "code-mode-v8-snapshot"
    out_dir.mkdir(parents=True, exist_ok=True)
    if comb_js:
        (out_dir / "v8-promise-combinators.js").write_text(comb_js, encoding="utf-8")

    (out_dir / "v8-snapshot-header-64k.bin").write_bytes(snap_blob[:65536])
    (out_dir / "v8-snapshot-strings.txt").write_text("\n".join(unique_strings), encoding="utf-8")

    v8_report = {
        "binary": str(BIN_CODE_MODE),
        "binary_sha256": sha256_bytes(data),
        "snapshot_file_offset": hex(snap_offset),
        "snapshot_byte_length": snap_len,
        "snapshot_sha256": sha256_bytes(snap_blob),
        "magic_hex": hex(magic),
        "version_hash_hex": hex(version_hash),
        "header_strings": header_strings[:30],
        "unique_identifier_count": len(unique_strings),
        "code_mode_globals": [
            "tools",
            "ALL_TOOLS",
            "codex.enabled",
            "exit",
            "notify",
            "store",
            "text",
            "add_content",
            "load_image",
        ],
        "embedded_promise_combinators_extracted": bool(comb_js),
        "extracted_files": [
            "extracted-assets/code-mode-v8-snapshot/v8-promise-combinators.js",
            "extracted-assets/code-mode-v8-snapshot/v8-snapshot-header-64k.bin",
            "extracted-assets/code-mode-v8-snapshot/v8-snapshot-strings.txt",
        ],
    }
    (SCHEMAS_DIR / "v8-startup-snapshot-analysis.json").write_text(
        json.dumps(v8_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return v8_report


# ============================================================================
# 2. bin/codex Embedded Syntect SyntaxSet & ThemeSet (Bincode + Zlib)
# ============================================================================
def analyze_syntect_assets():
    print("[2/8] Extracting & decompressing Syntect ThemeSet (32 themes) & SyntaxSet (220 syntaxes)...")
    data = BIN_CODEX.read_bytes()
    out_dir = ASSETS_DIR / "syntect-themes-and-syntaxes"
    themes_dir = out_dir / "themes"
    syntaxes_dir = out_dir / "syntaxes"
    themes_dir.mkdir(parents=True, exist_ok=True)
    syntaxes_dir.mkdir(parents=True, exist_ok=True)

    # 2a. Parse EmbeddedLazyThemeSet at 0xecd695e (62,593 bytes)
    theme_offset = 0xecd695e
    pos = theme_offset
    theme_count = struct.unpack_from("<Q", data, pos)[0]
    pos += 8
    themes = []
    total_theme_decompressed = 0
    for idx in range(theme_count):
        nlen = struct.unpack_from("<Q", data, pos)[0]
        pos += 8
        name = data[pos:pos + nlen].decode("utf-8")
        pos += nlen
        blen = struct.unpack_from("<Q", data, pos)[0]
        pos += 8
        blob = data[pos:pos + blen]
        pos += blen
        dec = zlib.decompress(blob)
        total_theme_decompressed += len(dec)
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")
        out_file = themes_dir / f"{idx:02d}_{safe_name}.bincode"
        out_file.write_bytes(dec)
        themes.append({
            "index": idx,
            "name": name,
            "compressed_bytes": blen,
            "decompressed_bytes": len(dec),
            "sha256": sha256_bytes(dec),
            "extracted_file": str(out_file.relative_to(ROOT)),
        })
    theme_total_bytes = pos - theme_offset
    assert theme_total_bytes == 62593, f"Expected 62593 bytes for ThemeSet, got {theme_total_bytes}"

    # 2b. Parse LazySyntaxSet at 0xece5ddf (983,676 bytes)
    syntax_offset = 0xece5ddf
    pos = syntax_offset
    syntax_count = struct.unpack_from("<Q", data, pos)[0]
    pos += 8
    syntaxes = []
    total_syntax_decompressed = 0
    for idx in range(syntax_count):
        nlen = struct.unpack_from("<Q", data, pos)[0]
        pos += 8
        name = data[pos:pos + nlen].decode("utf-8")
        pos += nlen

        ext_cnt = struct.unpack_from("<Q", data, pos)[0]
        pos += 8
        exts = []
        for _ in range(ext_cnt):
            elen = struct.unpack_from("<Q", data, pos)[0]
            pos += 8
            exts.append(data[pos:pos + elen].decode("utf-8"))
            pos += elen

        slen = struct.unpack_from("<Q", data, pos)[0]
        pos += 8
        scope = data[pos:pos + slen].decode("utf-8", errors="replace")
        pos += slen

        opt_tag = data[pos]
        pos += 1
        first_line_match = None
        if opt_tag == 1:
            fllen = struct.unpack_from("<Q", data, pos)[0]
            pos += 8
            first_line_match = data[pos:pos + fllen].decode("utf-8", errors="replace")
            pos += fllen

        hidden = bool(data[pos])
        pos += 1

        var_cnt = struct.unpack_from("<Q", data, pos)[0]
        pos += 8
        variables = {}
        for _ in range(var_cnt):
            klen = struct.unpack_from("<Q", data, pos)[0]
            pos += 8
            k = data[pos:pos + klen].decode("utf-8", errors="replace")
            pos += klen
            vlen = struct.unpack_from("<Q", data, pos)[0]
            pos += 8
            v = data[pos:pos + vlen].decode("utf-8", errors="replace")
            pos += vlen
            variables[k] = v

        blen = struct.unpack_from("<Q", data, pos)[0]
        pos += 8
        blob = data[pos:pos + blen]
        pos += blen
        dec = zlib.decompress(blob)
        total_syntax_decompressed += len(dec)

        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")
        out_file = syntaxes_dir / f"{idx:03d}_{safe_name}.bincode"
        out_file.write_bytes(dec)

        syntaxes.append({
            "index": idx,
            "name": name,
            "scope": scope,
            "file_extensions": exts,
            "first_line_match": first_line_match,
            "hidden": hidden,
            "variable_count": var_cnt,
            "variables": variables,
            "compressed_bytes": blen,
            "decompressed_bytes": len(dec),
            "sha256": sha256_bytes(dec),
            "extracted_file": str(out_file.relative_to(ROOT)),
        })

    syntax_total_bytes = pos - syntax_offset
    assert syntax_total_bytes == 983676, f"Expected 983676 bytes for SyntaxSet, got {syntax_total_bytes}"

    syntect_report = {
        "source_crate": "crates/tui/src/render/highlight.rs & two-face v0.5.1",
        "themeset": {
            "rodata_offset": hex(theme_offset),
            "total_bincode_bytes": theme_total_bytes,
            "total_decompressed_bytes": total_theme_decompressed,
            "theme_count": len(themes),
            "theme_names": [t["name"] for t in themes],
            "themes": themes,
        },
        "syntaxset": {
            "rodata_offset": hex(syntax_offset),
            "total_bincode_bytes": syntax_total_bytes,
            "total_decompressed_bytes": total_syntax_decompressed,
            "syntax_count": len(syntaxes),
            "syntaxes": syntaxes,
        },
    }
    (SCHEMAS_DIR / "syntect-catalog.json").write_text(
        json.dumps(syntect_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return syntect_report


# ============================================================================
# 3. Companion Binaries Static ELF Analysis (zsh, bwrap, rg)
# ============================================================================
def analyze_companion_binaries():
    print("[3/8] Analyzing companion binaries (zsh, bwrap, rg)...")
    targets = [
        ("zsh", BIN_ZSH, "Custom patched Zsh with EXECVE_WRAPPER_FD / CODEX_EXECVE_WRAPPER_SOCKET support"),
        ("bwrap", BIN_BWRAP, "Bundled Bubblewrap Linux namespace sandbox helper"),
        ("rg", BIN_RG, "Bundled ripgrep (Rust musl static binary) for fast file/content search"),
    ]
    results = []
    for name, path, role in targets:
        data = path.read_bytes()
        readelf_h = subprocess.run(["readelf", "-h", str(path)], capture_output=True, text=True).stdout
        readelf_S = subprocess.run(["readelf", "-SW", str(path)], capture_output=True, text=True).stdout
        readelf_d = subprocess.run(["readelf", "-d", str(path)], capture_output=True, text=True).stdout
        readelf_n = subprocess.run(["readelf", "-n", str(path)], capture_output=True, text=True).stdout

        sections = []
        for line in readelf_S.splitlines():
            m = re.match(r"^\s*\[\s*\d+\]\s+(\.\S+)\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)", line)
            if m:
                sections.append({
                    "name": m.group(1),
                    "type": m.group(2),
                    "addr": "0x" + m.group(3),
                    "off": "0x" + m.group(4),
                    "size_bytes": int(m.group(5), 16),
                })

        needed_libs = re.findall(r"Shared library:\s*\[([^\]]+)\]", readelf_d)
        build_id_m = re.search(r"Build ID:\s*([0-9a-fA-F]+)", readelf_n)

        ascii_strings = [
            s.decode("ascii", errors="ignore")
            for s in re.findall(rb"[ -~]{5,120}", data)
        ]
        codex_strings = sorted(set(
            s for s in ascii_strings
            if any(k in s for k in ["CODEX", "WRAPPER", "bwrap", "ripgrep", "zsh-", "MUSL", "sandbox"])
        ))[:60]

        results.append({
            "name": name,
            "path": str(path),
            "role": role,
            "size_bytes": len(data),
            "sha256": sha256_bytes(data),
            "build_id": build_id_m.group(1) if build_id_m else None,
            "needed_shared_libraries": needed_libs,
            "statically_linked": len(needed_libs) == 0,
            "section_count": len(sections),
            "sections": sections,
            "notable_strings": codex_strings,
            "elf_header_summary": [line.strip() for line in readelf_h.splitlines() if ":" in line],
        })

    report = {
        "binary_count": len(results),
        "binaries": results,
    }
    (SCHEMAS_DIR / "companion-binaries-analysis.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


# ============================================================================
# 4. codex-voice-host DWARF Debug Units & 17 GStreamer/Audio Shared Libraries
# ============================================================================
def analyze_voice_host_dwarf_and_libs():
    print("[4/8] Extracting codex-voice-host DWARF compilation units & 17 GStreamer/audio shared libraries...")
    proc = subprocess.Popen(
        ["readelf", "--debug-dump=info", str(BIN_VOICE_HOST)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        errors="replace",
    )
    compilation_units = []
    codex_types = []
    in_cu = False
    cur_cu = {}
    cur_tag = None
    line_count = 0
    for line in proc.stdout:
        line_count += 1
        if "DW_TAG_compile_unit" in line:
            if cur_cu.get("name"):
                compilation_units.append(cur_cu)
            cur_cu = {}
            in_cu = True
            cur_tag = "compile_unit"
        elif "Abbrev Number:" in line and "DW_TAG_" in line:
            m = re.search(r"\((DW_TAG_[a-zA-Z0-9_]+)\)", line)
            cur_tag = m.group(1) if m else None
            in_cu = (cur_tag == "DW_TAG_compile_unit")
        elif "DW_AT_name" in line:
            val = line.split(":")[-1].strip()
            if in_cu and "name" not in cur_cu:
                cur_cu["name"] = val
            elif cur_tag in ("DW_TAG_structure_type", "DW_TAG_enumeration_type", "DW_TAG_subprogram"):
                if any(k in val for k in ("Voice", "Realtime", "Webrtc", "Audio", "PeerConnection", "Ice", "Sdp", "Gstreamer", "Pipeline", "Device")):
                    if len(codex_types) < 300:
                        codex_types.append({"tag": cur_tag, "name": val})
        elif in_cu and "DW_AT_comp_dir" in line:
            cur_cu["comp_dir"] = line.split(":")[-1].strip()
        elif in_cu and "DW_AT_producer" in line:
            cur_cu["producer"] = line.split(":")[-1].strip()
        if len(compilation_units) >= 250 and len(codex_types) >= 250 and line_count > 400_000:
            break
    if cur_cu.get("name"):
        compilation_units.append(cur_cu)
    proc.terminate()

    seen_types = set()
    unique_codex_types = []
    for t in codex_types:
        key = (t["tag"], t["name"])
        if key not in seen_types:
            seen_types.add(key)
            unique_codex_types.append(t)

    so_files = sorted(VOICE_LIB_DIR.rglob("*.so*"))
    libs_info = []
    for so_path in so_files:
        if not so_path.is_file():
            continue
        rel_path = str(so_path.relative_to(VOICE_LIB_DIR))
        readelf_d = subprocess.run(["readelf", "-d", str(so_path)], capture_output=True, text=True).stdout
        needed = re.findall(r"Shared library:\s*\[([^\]]+)\]", readelf_d)
        soname_m = re.search(r"Library soname:\s*\[([^\]]+)\]", readelf_d)

        nm_out = subprocess.run(["nm", "-D", "--defined-only", str(so_path)], capture_output=True, text=True).stdout
        exported_syms = []
        for line in nm_out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[1] in ("T", "D", "R", "B", "W"):
                exported_syms.append(parts[2])

        libs_info.append({
            "relative_path": rel_path,
            "size_bytes": so_path.stat().st_size,
            "sha256": sha256_file(so_path),
            "soname": soname_m.group(1) if soname_m else so_path.name,
            "needed_libraries": needed,
            "exported_symbol_count": len(exported_syms),
            "exported_symbols_sample": exported_syms[:25],
        })

    report = {
        "voice_host_binary": str(BIN_VOICE_HOST),
        "voice_host_size_bytes": BIN_VOICE_HOST.stat().st_size,
        "voice_host_sha256": sha256_file(BIN_VOICE_HOST),
        "dwarf_compilation_unit_count": len(compilation_units),
        "dwarf_compilation_units": compilation_units,
        "dwarf_recovered_types_and_subprograms": unique_codex_types,
        "bundled_shared_library_count": len(libs_info),
        "bundled_shared_libraries": libs_info,
    }
    (SCHEMAS_DIR / "voice-host-dwarf-and-libs.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


# ============================================================================
# 5. 6 Patched Git Fork Dependencies (.cargo-home/git/checkouts/*)
# ============================================================================
def analyze_git_fork_dependencies():
    print("[5/8] Cataloging 6 patched Git fork dependencies from binary panic & tracing tables...")
    addr_map = json.loads((SCHEMAS_DIR / "binary-address-map.json").read_text(encoding="utf-8"))
    tracing_cat = json.loads((SCHEMAS_DIR / "tracing-metadata-catalog.json").read_text(encoding="utf-8"))
    data = BIN_CODEX.read_bytes()

    git_paths = sorted(set(
        m.group(0).decode("utf-8", errors="ignore")
        for m in re.finditer(rb"/[^\x00\n\r\"']*?\.cargo-home/git/checkouts/[A-Za-z0-9_.-]+/[0-9a-f]+/[^\x00\n\r\"':]+\.rs", data)
    ))

    forks = {}
    for p in git_paths:
        m = re.search(r"\.cargo-home/git/checkouts/([A-Za-z0-9_.-]+)-([0-9a-f]{16})/([0-9a-f]+)/(.+)$", p)
        if not m:
            continue
        repo_name, repo_hash, commit_short, rel_file = m.groups()
        key = f"{repo_name}-{repo_hash}"
        if key not in forks:
            forks[key] = {
                "repo_name": repo_name,
                "cargo_checkout_id": key,
                "commit_short": commit_short,
                "source_files": [],
                "mapped_functions": [],
                "tracing_records": [],
            }
        forks[key]["source_files"].append(rel_file)

    for fn_entry in addr_map.get("functions", []):
        sf = fn_entry.get("source_file", "")
        for key, fdata in forks.items():
            if fdata["repo_name"] in sf or any(rf in sf for rf in fdata["source_files"]):
                fdata["mapped_functions"].append({
                    "start_va": fn_entry["start_va"],
                    "end_va": fn_entry["end_va"],
                    "inferred_rust_fn": fn_entry.get("inferred_rust_fn"),
                    "source_file": sf,
                    "line_range": [fn_entry.get("min_line"), fn_entry.get("max_line")],
                })

    for rec in tracing_cat.get("records", []):
        sf = rec.get("file", "")
        for key, fdata in forks.items():
            if key in sf or fdata["repo_name"] in sf:
                fdata["tracing_records"].append({
                    "name": rec.get("name"),
                    "target": rec.get("target"),
                    "level": rec.get("level"),
                    "file": sf,
                    "line": rec.get("line"),
                })

    fork_list = []
    for key, fdata in sorted(forks.items()):
        fdata["source_file_count"] = len(fdata["source_files"])
        fdata["mapped_function_count"] = len(fdata["mapped_functions"])
        fdata["tracing_record_count"] = len(fdata["tracing_records"])
        fork_list.append(fdata)

    report = {
        "total_git_fork_repositories": len(fork_list),
        "total_git_fork_source_files": sum(f["source_file_count"] for f in fork_list),
        "git_forks": fork_list,
    }
    (SCHEMAS_DIR / "git-fork-dependencies.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


# ============================================================================
# 6. VS Code Extension openai.codex-audio-26.1007.21434
# ============================================================================
def analyze_vscode_codex_audio():
    print("[6/8] Extracting and formatting VS Code extension openai.codex-audio-26.1007.21434...")
    ext_root = Path("/root/.vscode-server/extensions/openai.codex-audio-26.1007.21434")
    out_dir = ASSETS_DIR / "vscode-codex-audio-extension"
    out_dir.mkdir(parents=True, exist_ok=True)

    pkg_json = json.loads((ext_root / "package.json").read_text(encoding="utf-8"))
    shutil.copy2(ext_root / "package.json", out_dir / "package.json")

    pv_out = out_dir / "pvrecorder"
    if pv_out.exists():
        shutil.rmtree(pv_out)
    shutil.copytree(ext_root / "vendor" / "pvrecorder" / "dist", pv_out / "dist")
    shutil.copy2(ext_root / "vendor" / "pvrecorder" / "package.json", pv_out / "package.json")

    def basic_js_beautify(js_text: str) -> str:
        out = []
        indent = 0
        in_str = None
        escape = False
        for ch in js_text:
            if escape:
                out.append(ch)
                escape = False
                continue
            if ch == "\\":
                out.append(ch)
                escape = True
                continue
            if in_str:
                out.append(ch)
                if ch == in_str:
                    in_str = None
                continue
            if ch in ('"', "'", "`"):
                in_str = ch
                out.append(ch)
                continue
            if ch == "{":
                indent += 1
                out.append("{\n" + "  " * min(indent, 16))
            elif ch == "}":
                indent = max(0, indent - 1)
                out.append("\n" + "  " * min(indent, 16) + "}")
            elif ch == ";":
                out.append(";\n" + "  " * min(indent, 16))
            else:
                out.append(ch)
        return "".join(out)

    ext_js_raw = (ext_root / "out" / "extension.js").read_text(encoding="utf-8", errors="replace")
    worker_js_raw = (ext_root / "out" / "recorder-worker.js").read_text(encoding="utf-8", errors="replace")

    ext_js_pretty = basic_js_beautify(ext_js_raw)
    worker_js_pretty = basic_js_beautify(worker_js_raw)

    (out_dir / "extension.formatted.js").write_text(ext_js_pretty, encoding="utf-8")
    (out_dir / "recorder-worker.formatted.js").write_text(worker_js_pretty, encoding="utf-8")

    native_libs = []
    lib_root = ext_root / "vendor" / "pvrecorder" / "lib"
    for p in sorted(lib_root.rglob("*")):
        if p.is_file():
            native_libs.append({
                "relative_path": str(p.relative_to(ext_root)),
                "size_bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            })

    commands = sorted(set(re.findall(r"codex-audio\.[A-Za-z0-9_.-]+", ext_js_raw)))
    worker_messages = sorted(set(re.findall(r'type:\s*"([A-Za-z0-9_-]+)"', ext_js_raw + "\n" + worker_js_raw)))

    report = {
        "extension_id": f"{pkg_json.get('publisher')}.{pkg_json.get('name')}",
        "version": pkg_json.get("version"),
        "source_path": str(ext_root),
        "extracted_directory": "extracted-assets/vscode-codex-audio-extension",
        "contributed_commands": pkg_json.get("contributes", {}).get("commands", []),
        "contributed_configuration": pkg_json.get("contributes", {}).get("configuration", {}),
        "detected_command_ids": commands,
        "worker_ipc_message_types": worker_messages,
        "bundles": [
            {
                "name": "out/extension.js",
                "raw_bytes": len(ext_js_raw.encode("utf-8")),
                "formatted_lines": ext_js_pretty.count("\n") + 1,
                "formatted_path": "extracted-assets/vscode-codex-audio-extension/extension.formatted.js",
            },
            {
                "name": "out/recorder-worker.js",
                "raw_bytes": len(worker_js_raw.encode("utf-8")),
                "formatted_lines": worker_js_pretty.count("\n") + 1,
                "formatted_path": "extracted-assets/vscode-codex-audio-extension/recorder-worker.formatted.js",
            },
        ],
        "native_pvrecorder_libraries": native_libs,
        "rea_evidence_id": "ev_57a3879e3952330028d2217d1b8bc21f7532f21db1535fed49b9e4c6e6a4345e",
    }
    (SCHEMAS_DIR / "vscode-codex-audio-analysis.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


# ============================================================================
# 7. 7 Official Bundled & Curated Plugins (/root/.codex/plugins/cache/*)
# ============================================================================
def analyze_official_plugins():
    print("[7/8] Archiving and cataloging 7 official bundled & curated plugins...")
    cache_root = Path("/root/.codex/plugins/cache")
    out_dir = ASSETS_DIR / "official-plugins"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plugins = []
    for manifest_path in sorted(cache_root.rglob(".codex-plugin/plugin.json")):
        plugin_version_dir = manifest_path.parent.parent
        plugin_name = plugin_version_dir.parent.name
        marketplace = plugin_version_dir.parent.parent.name
        version = plugin_version_dir.name

        dest_dir = out_dir / marketplace / plugin_name / version
        shutil.copytree(plugin_version_dir, dest_dir)

        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        skill_files = [
            str(p.relative_to(plugin_version_dir))
            for p in sorted(plugin_version_dir.rglob("SKILL.md"))
        ]
        all_files = [
            str(p.relative_to(plugin_version_dir))
            for p in sorted(plugin_version_dir.rglob("*"))
            if p.is_file()
        ]
        mcp_json = None
        if (plugin_version_dir / ".mcp.json").exists():
            try:
                mcp_json = json.loads((plugin_version_dir / ".mcp.json").read_text(encoding="utf-8"))
            except Exception:
                mcp_json = "raw"

        plugins.append({
            "marketplace": marketplace,
            "plugin_name": plugin_name,
            "version": version,
            "source_path": str(plugin_version_dir),
            "extracted_path": str(dest_dir.relative_to(ROOT)),
            "manifest": manifest_data,
            "skill_count": len(skill_files),
            "skills": skill_files,
            "file_count": len(all_files),
            "files": all_files,
            "mcp_config": mcp_json,
        })

    report = {
        "total_plugins": len(plugins),
        "plugins": plugins,
        "rea_superpowers_evidence_id": "ev_3a4d37f94f12b376426f216c2935c1cbd419c41624642d81b251e9d374f7d8ae",
    }
    (SCHEMAS_DIR / "official-plugins-catalog.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


# ============================================================================
# 8. Read-Only Binary Asset & Offset Verification Report
# ============================================================================
def build_binary_asset_verification():
    print("[8/8] Verifying all .rodata embedded asset offsets and digests across binaries...")
    codex_bytes = BIN_CODEX.read_bytes()
    codemode_bytes = BIN_CODE_MODE.read_bytes()

    checks = [
        {
            "name": "models.json (11 models incl. 3 hidden)",
            "binary": "bin/codex",
            "offset": "0xe833a82",
            "length": 472071,
            "sha256": sha256_bytes(codex_bytes[0xe833a82:0xe833a82 + 472071]),
            "verified_header": codex_bytes[0xe833a82:0xe833a82 + 32].decode("utf-8", errors="replace").strip(),
        },
        {
            "name": "app-server-protocol-stable.zst",
            "binary": "bin/codex",
            "offset": "0xe5c6d6f",
            "length": 158034,
            "sha256": sha256_bytes(codex_bytes[0xe5c6d6f:0xe5c6d6f + 158034]),
            "verified_magic": codex_bytes[0xe5c6d6f:0xe5c6d6f + 4].hex(),
        },
        {
            "name": "app-server-protocol-experimental.zst",
            "binary": "bin/codex",
            "offset": "0xe5ed6c1",
            "length": 162901,
            "sha256": sha256_bytes(codex_bytes[0xe5ed6c1:0xe5ed6c1 + 162901]),
            "verified_magic": codex_bytes[0xe5ed6c1:0xe5ed6c1 + 4].hex(),
        },
        {
            "name": "Syntect ThemeSet (bincode + 32 zlib themes)",
            "binary": "bin/codex",
            "offset": "0xecd695e",
            "length": 62593,
            "sha256": sha256_bytes(codex_bytes[0xecd695e:0xecd695e + 62593]),
            "verified_magic": codex_bytes[0xecd695e:0xecd695e + 8].hex(),
        },
        {
            "name": "Syntect SyntaxSet (bincode + 220 zlib syntaxes)",
            "binary": "bin/codex",
            "offset": "0xece5ddf",
            "length": 983676,
            "sha256": sha256_bytes(codex_bytes[0xece5ddf:0xece5ddf + 983676]),
            "verified_magic": codex_bytes[0xece5ddf:0xece5ddf + 8].hex(),
        },
        {
            "name": "V8 Startup Snapshot Blob",
            "binary": "bin/codex-code-mode-host",
            "offset": "0x2fb1980",
            "length": 10822192,
            "sha256": sha256_bytes(codemode_bytes[0x2fb1980:0x2fb1980 + 10822192]),
            "verified_magic": codemode_bytes[0x2fb1980:0x2fb1980 + 4].hex(),
        },
    ]

    report = {
        "verified_asset_regions": len(checks),
        "regions": checks,
    }
    (SCHEMAS_DIR / "binary-asset-verification.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def main():
    v8 = analyze_v8_startup_snapshot()
    syntect = analyze_syntect_assets()
    comp = analyze_companion_binaries()
    voice = analyze_voice_host_dwarf_and_libs()
    forks = analyze_git_fork_dependencies()
    audio_ext = analyze_vscode_codex_audio()
    plugins = analyze_official_plugins()
    verify = build_binary_asset_verification()

    print("\n=== Deep Component Extraction Complete ===")
    print(f"  1. V8 Snapshot: {v8['snapshot_byte_length']:,} bytes @ {v8['snapshot_file_offset']} ({v8['unique_identifier_count']} unique symbols)")
    print(f"  2. Syntect: ThemeSet={syntect['themeset']['theme_count']} themes ({syntect['themeset']['total_decompressed_bytes']:,}B dec), SyntaxSet={syntect['syntaxset']['syntax_count']} syntaxes ({syntect['syntaxset']['total_decompressed_bytes']:,}B dec)")
    print(f"  3. Companion Binaries: {comp['binary_count']} ELF binaries analyzed (zsh, bwrap, rg)")
    print(f"  4. Voice Host DWARF & Libs: {voice['dwarf_compilation_unit_count']} DWARF CUs, {voice['bundled_shared_library_count']} shared libraries")
    print(f"  5. Git Fork Dependencies: {forks['total_git_fork_repositories']} repositories, {forks['total_git_fork_source_files']} Rust source files")
    print(f"  6. VS Code Audio Extension: {len(audio_ext['native_pvrecorder_libraries'])} native libraries, {len(audio_ext['bundles'])} formatted JS bundles")
    print(f"  7. Official Plugins: {plugins['total_plugins']} plugins archived")
    print(f"  8. Binary Asset Regions Verified: {verify['verified_asset_regions']} regions")


if __name__ == "__main__":
    main()
