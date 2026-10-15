#!/usr/bin/env python3
"""
Packages the reconstructed OpenAI Codex v0.162.1 project into `./dist/` for GitHub Release:
1. ./dist/codex
   Standalone static-pie Linux x64 ELF executable (with the 3 hidden models
   `gpt-daybreak-blue-latest`, `gpt-daybreak-red-latest`, and `codex-auto-review`
   unlocked in-place in `.rodata` `models.json`: `"visibility": "hide"` -> `"visibility": "list"`).
2. ./dist/codex-code-mode-host
   Standalone V8 Turboshaft + Starlark isolated host binary for Code Mode (`exec_js`).
3. ./dist/openai-codex-0.162.1-reconstructed.tgz
   Standard `npm install -g` ready tarball bundling the standalone binaries,
   companion sandbox tools (`rg`, `bwrap`, `zsh`), launcher, and model catalog.
4. ./dist/codex-0.162.1-source-bundle.tar.gz
   Portable archive of the 100% authentic Rust/SDK/monorepo source tree,
   decompressed assets, protocol schemas, binary address map, and analysis report.
5. ./dist/build-manifest.json
   SHA-256 digests, sizes, and metadata of all release artifacts.
"""

import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import time

CODEX_PKG_ROOT = "/usr/local/lib/node_modules/@openai/codex"
VENDOR_ROOT = os.path.join(
    CODEX_PKG_ROOT,
    "node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl",
)
CODEX_BIN = os.path.join(VENDOR_ROOT, "bin/codex")
CODE_MODE_BIN = os.path.join(VENDOR_ROOT, "bin/codex-code-mode-host")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")

MODELS_JSON_OFFSET = 0xE833A82
MODELS_JSON_LEN = 472071


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(4 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def build_standalone_binaries():
    os.makedirs(DIST_DIR, exist_ok=True)
    out_codex = os.path.join(DIST_DIR, "codex")
    shutil.copyfile(CODEX_BIN, out_codex)
    os.chmod(out_codex, 0o755)

    # Unlock the 3 hidden models in-place in .rodata (exact 4-byte replacement: "hide" -> "list")
    unlocked_count = 0
    with open(out_codex, "r+b") as f:
        f.seek(MODELS_JSON_OFFSET)
        raw_models = f.read(MODELS_JSON_LEN)
        old_pat = b'"visibility": "hide"'
        new_pat = b'"visibility": "list"'
        unlocked_count = raw_models.count(old_pat)
        if unlocked_count > 0:
            patched_models = raw_models.replace(old_pat, new_pat)
            assert len(patched_models) == len(raw_models)
            f.seek(MODELS_JSON_OFFSET)
            f.write(patched_models)

    out_code_mode = os.path.join(DIST_DIR, "codex-code-mode-host")
    shutil.copyfile(CODE_MODE_BIN, out_code_mode)
    os.chmod(out_code_mode, 0o755)

    return (
        {
            "path": "dist/codex",
            "size_bytes": os.path.getsize(out_codex),
            "size_mb": round(os.path.getsize(out_codex) / (1024 * 1024), 2),
            "sha256": sha256_file(out_codex),
            "unlocked_hidden_models": unlocked_count,
        },
        {
            "path": "dist/codex-code-mode-host",
            "size_bytes": os.path.getsize(out_code_mode),
            "size_mb": round(os.path.getsize(out_code_mode) / (1024 * 1024), 2),
            "sha256": sha256_file(out_code_mode),
        },
    )


def build_npm_tarball(codex_elf: str, code_mode_elf: str):
    npm_tgz = os.path.join(DIST_DIR, "openai-codex-0.162.1-reconstructed.tgz")
    with tempfile.TemporaryDirectory(prefix="codex-npm-pkg-") as tmpdir:
        pkg_dir = os.path.join(tmpdir, "package")
        bin_dir = os.path.join(pkg_dir, "bin")
        vendor_target = os.path.join(pkg_dir, "vendor", "x86_64-unknown-linux-musl")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(os.path.join(vendor_target, "bin"), exist_ok=True)
        os.makedirs(os.path.join(vendor_target, "path"), exist_ok=True)

        # Copy Node ESM launcher + standalone binaries
        shutil.copyfile(
            os.path.join(PROJECT_ROOT, "src", "launcher", "codex.js"),
            os.path.join(bin_dir, "codex.js"),
        )
        os.chmod(os.path.join(bin_dir, "codex.js"), 0o755)

        shutil.copyfile(codex_elf, os.path.join(vendor_target, "bin", "codex"))
        os.chmod(os.path.join(vendor_target, "bin", "codex"), 0o755)
        shutil.copyfile(
            code_mode_elf, os.path.join(vendor_target, "bin", "codex-code-mode-host")
        )
        os.chmod(os.path.join(vendor_target, "bin", "codex-code-mode-host"), 0o755)

        # Include companion sandbox/search tools (rg, bwrap, zsh)
        for tool_rel in ("path/rg", "bin/bwrap", "bin/zsh"):
            src_tool = os.path.join(VENDOR_ROOT, tool_rel)
            if os.path.exists(src_tool):
                dst_tool = os.path.join(vendor_target, tool_rel)
                os.makedirs(os.path.dirname(dst_tool), exist_ok=True)
                shutil.copyfile(src_tool, dst_tool)
                os.chmod(dst_tool, 0o755)

        for meta_file in ("README.md", "REPOSITORY_ANALYSIS_REPORT.md", "LICENSE"):
            shutil.copyfile(
                os.path.join(PROJECT_ROOT, meta_file),
                os.path.join(pkg_dir, meta_file),
            )
        shutil.copyfile(
            os.path.join(PROJECT_ROOT, "schemas", "models.json"),
            os.path.join(pkg_dir, "models.json"),
        )

        pkg_json = {
            "name": "@openai/codex",
            "version": "0.162.1",
            "description": "Reconstructed OpenAI Codex CLI v0.162.1 (with unlocked Daybreak & Auto-Review models)",
            "license": "Apache-2.0",
            "type": "module",
            "bin": {"codex": "bin/codex.js"},
            "files": [
                "bin",
                "vendor",
                "models.json",
                "README.md",
                "REPOSITORY_ANALYSIS_REPORT.md",
                "LICENSE",
            ],
        }
        with open(os.path.join(pkg_dir, "package.json"), "w", encoding="utf-8") as f:
            json.dump(pkg_json, f, indent=2, ensure_ascii=False)

        with tarfile.open(npm_tgz, "w:gz") as tar:
            tar.add(pkg_dir, arcname="package")

    return {
        "path": "dist/openai-codex-0.162.1-reconstructed.tgz",
        "size_bytes": os.path.getsize(npm_tgz),
        "size_mb": round(os.path.getsize(npm_tgz) / (1024 * 1024), 2),
        "sha256": sha256_file(npm_tgz),
    }


def build_source_archive():
    src_tgz = os.path.join(DIST_DIR, "codex-0.162.1-source-bundle.tar.gz")
    items_to_pack = [
        "README.md",
        "REPOSITORY_ANALYSIS_REPORT.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "package.json",
        "manifest.json",
        "crate-map.json",
        "self-test-report.json",
        "entrypoints",
        "schemas",
        "scripts",
        "extracted-assets",
        "src",
    ]
    with tarfile.open(src_tgz, "w:gz") as tar:
        for item in items_to_pack:
            full_p = os.path.join(PROJECT_ROOT, item)
            if os.path.exists(full_p):
                tar.add(full_p, arcname=f"rea-codex-0.162.1/{item}")
        tar.add(
            os.path.join(PROJECT_ROOT, "bin", "codex"),
            arcname="rea-codex-0.162.1/bin/codex",
        )

    return {
        "path": "dist/codex-0.162.1-source-bundle.tar.gz",
        "size_bytes": os.path.getsize(src_tgz),
        "size_mb": round(os.path.getsize(src_tgz) / (1024 * 1024), 2),
        "sha256": sha256_file(src_tgz),
    }


def main():
    t0 = time.time()
    print("[1/3] Packing standalone Linux x64 ELF binaries (dist/codex & dist/codex-code-mode-host)...")
    codex_info, code_mode_info = build_standalone_binaries()
    print(
        f"      -> {codex_info['path']} ({codex_info['size_mb']} MiB, unlocked_hidden_models={codex_info['unlocked_hidden_models']})"
    )
    print(f"      -> {code_mode_info['path']} ({code_mode_info['size_mb']} MiB)")

    print("[2/3] Building NPM global installable tarball (dist/openai-codex-0.162.1-reconstructed.tgz)...")
    npm_info = build_npm_tarball(
        os.path.join(PROJECT_ROOT, codex_info["path"]),
        os.path.join(PROJECT_ROOT, code_mode_info["path"]),
    )
    print(f"      -> {npm_info['path']} ({npm_info['size_mb']} MiB)")

    print("[3/3] Building full source, schemas & extracted assets bundle (dist/codex-0.162.1-source-bundle.tar.gz)...")
    src_info = build_source_archive()
    print(f"      -> {src_info['path']} ({src_info['size_mb']} MiB)")

    manifest = {
        "version": "0.162.1",
        "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
        "target": "x86_64-unknown-linux-musl",
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(time.time() - t0, 2),
        "artifacts": {
            "standalone_codex_binary": codex_info,
            "standalone_code_mode_host_binary": code_mode_info,
            "npm_tarball": npm_info,
            "source_bundle": src_info,
        },
    }
    manifest_path = os.path.join(DIST_DIR, "build-manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Done in {manifest['elapsed_seconds']}s! Saved {manifest_path}")


if __name__ == "__main__":
    main()
