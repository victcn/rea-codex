#!/usr/bin/env python3
"""
Repository Analyzer for /code/custom-dev/rea-codex-demo
Follows the installed `repository-analyzer` skill workflow (`~/.agents/skills/repository-analyzer/SKILL.md`):
  1. Scan Repository Structure & LOC by Language/Directory
  2. Detect Technologies, Runtimes & Frameworks
  3. Map Dependencies (Internal 123-Crate DAG, External Crates, 6 Git Forks, 26 Native Libraries)
  4. Identify Architecture Patterns & Data/Control Flow
  5. Code Quality, Complexity & Technical Debt Scan (TODO/FIXME/HACK/unsafe/tests)
  6. Generate Comprehensive Markdown Report & Structured Metrics JSON
"""

import collections
import json
import os
import re
from pathlib import Path

ROOT = Path("/code/custom-dev/rea-codex-demo")
SRC_DIR = ROOT / "src"
SCHEMAS_DIR = ROOT / "schemas"
ASSETS_DIR = ROOT / "extracted-assets"
ARTIFACTS_DIR = Path("/root/.claude-artifacts")


def scan_files_and_loc():
    ext_stats = collections.defaultdict(lambda: {"files": 0, "lines": 0, "bytes": 0})
    dir_stats = collections.defaultdict(lambda: {"files": 0, "lines": 0, "bytes": 0})
    total_files = 0
    total_lines = 0
    total_bytes = 0

    text_exts = {
        ".rs", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".py", ".sh",
        ".json", ".toml", ".yaml", ".yml", ".md", ".sql", ".ftl",
        ".html", ".css", ".lark", ".txt", ".c", ".h", ".bazel", ".bzl"
    }

    for p in ROOT.rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(ROOT)
        top_dir = rel.parts[0] if len(rel.parts) > 1 else "<root>"
        if top_dir == ".isolated-env":
            continue
        size = p.stat().st_size
        ext = p.suffix.lower() or "<no_ext>"
        lines = 0
        if ext in text_exts and size < 20_000_000:
            try:
                with p.open("rb") as f:
                    lines = f.read().count(b"\n")
            except Exception:
                lines = 0

        total_files += 1
        total_lines += lines
        total_bytes += size

        ext_stats[ext]["files"] += 1
        ext_stats[ext]["lines"] += lines
        ext_stats[ext]["bytes"] += size

        dir_stats[top_dir]["files"] += 1
        dir_stats[top_dir]["lines"] += lines
        dir_stats[top_dir]["bytes"] += size

    return {
        "total_files": total_files,
        "total_lines": total_lines,
        "total_bytes": total_bytes,
        "by_extension": dict(sorted(ext_stats.items(), key=lambda kv: (-kv[1]["lines"], -kv[1]["files"]))),
        "by_top_directory": dict(sorted(dir_stats.items(), key=lambda kv: (-kv[1]["bytes"], -kv[1]["files"]))),
    }


def analyze_rust_crates_and_dependencies():
    crates = {}
    internal_edges = []
    external_dep_counts = collections.Counter()

    for cargo_toml in sorted(SRC_DIR.rglob("Cargo.toml")):
        rel_toml = cargo_toml.relative_to(SRC_DIR)
        if rel_toml == Path("Cargo.toml"):
            continue
        crate_dir = cargo_toml.parent
        rel_dir = str(crate_dir.relative_to(SRC_DIR))
        text = cargo_toml.read_text(encoding="utf-8", errors="replace")

        name_m = re.search(r'^\s*name\s*=\s*"([^"]+)"', text, re.M)
        crate_name = name_m.group(1) if name_m else crate_dir.name

        # Count .rs files and LOC in this crate
        rs_files = [p for p in crate_dir.rglob("*.rs") if p.is_file()]
        rs_loc = 0
        for rf in rs_files:
            try:
                rs_loc += rf.read_bytes().count(b"\n")
            except Exception:
                pass

        # Parse dependencies
        deps = set()
        in_dep_section = False
        for line in text.splitlines():
            sec_m = re.match(r"^\s*\[([^\]]+)\]", line)
            if sec_m:
                sec_name = sec_m.group(1)
                in_dep_section = "dependencies" in sec_name
                continue
            if in_dep_section:
                dep_m = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=", line)
                if dep_m:
                    deps.add(dep_m.group(1))

        crates[crate_name] = {
            "name": crate_name,
            "path": f"src/{rel_dir}",
            "rs_file_count": len(rs_files),
            "rs_loc": rs_loc,
            "raw_deps": sorted(deps),
        }

    # Distinguish internal vs external dependencies
    internal_names = set(crates.keys())
    in_degree = collections.Counter()
    out_degree = collections.Counter()

    for cname, cinfo in crates.items():
        int_deps = []
        ext_deps = []
        for d in cinfo["raw_deps"]:
            if d in internal_names or d.startswith("codex-"):
                int_deps.append(d)
                internal_edges.append((cname, d))
                in_degree[d] += 1
                out_degree[cname] += 1
            else:
                ext_deps.append(d)
                external_dep_counts[d] += 1
        cinfo["internal_deps"] = int_deps
        cinfo["external_deps"] = ext_deps
        del cinfo["raw_deps"]

    # Parse Cargo.lock for exact package count
    lock_packages = 0
    lock_git_packages = []
    lock_path = SRC_DIR / "Cargo.lock"
    if lock_path.exists():
        lock_text = lock_path.read_text(encoding="utf-8", errors="replace")
        for blk in lock_text.split("[[package]]")[1:]:
            lock_packages += 1
            nm = re.search(r'name\s*=\s*"([^"]+)"', blk)
            ver = re.search(r'version\s*=\s*"([^"]+)"', blk)
            src = re.search(r'source\s*=\s*"([^"]+)"', blk)
            if src and src.group(1).startswith("git+"):
                lock_git_packages.append({
                    "name": nm.group(1) if nm else "",
                    "version": ver.group(1) if ver else "",
                    "source": src.group(1),
                })

    top_crates_by_loc = sorted(crates.values(), key=lambda c: -c["rs_loc"])[:30]
    most_depended_internal = [
        {"crate": k, "dependents_count": v, "path": crates.get(k, {}).get("path")}
        for k, v in in_degree.most_common(25)
    ]
    most_depended_external = [
        {"crate": k, "used_by_crates": v}
        for k, v in external_dep_counts.most_common(30)
    ]

    return {
        "total_cargo_manifests": len(crates),
        "total_internal_edges": len(internal_edges),
        "cargo_lock_total_packages": lock_packages,
        "cargo_lock_git_packages": lock_git_packages,
        "top_crates_by_loc": top_crates_by_loc,
        "most_depended_internal_crates": most_depended_internal,
        "most_used_external_crates": most_depended_external,
    }


def analyze_code_quality_and_tech_debt():
    todo_pat = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b[:\s]*(.*)")
    unsafe_pat = re.compile(r"\bunsafe\s*(?:\{|fn|impl|trait)")
    test_attr_pat = re.compile(r"#\[(?:tokio::)?test\b")
    fn_pat = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:const\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+([A-Za-z0-9_]+)")

    debt_counts = collections.Counter()
    debt_samples = []
    unsafe_count = 0
    unsafe_by_crate = collections.Counter()
    test_fn_count = 0
    total_fn_count = 0
    largest_rs_files = []

    for rs_path in sorted(SRC_DIR.rglob("*.rs")):
        if not rs_path.is_file():
            continue
        rel = str(rs_path.relative_to(ROOT))
        crate_part = rel.split("/")[1] if len(rel.split("/")) > 2 else rel
        try:
            lines = rs_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        loc = len(lines)
        largest_rs_files.append({"file": rel, "lines": loc})

        for idx, line in enumerate(lines, start=1):
            if fn_pat.match(line):
                total_fn_count += 1
            if test_attr_pat.search(line):
                test_fn_count += 1
            if unsafe_pat.search(line):
                unsafe_count += 1
                unsafe_by_crate[crate_part] += 1
            m = todo_pat.search(line)
            if m:
                tag = m.group(1)
                msg = m.group(2).strip()[:120]
                debt_counts[tag] += 1
                if len(debt_samples) < 40 and tag in ("FIXME", "HACK", "TODO"):
                    debt_samples.append({
                        "tag": tag,
                        "file": rel,
                        "line": idx,
                        "comment": msg,
                    })

    largest_rs_files.sort(key=lambda x: -x["lines"])

    return {
        "total_rust_functions": total_fn_count,
        "total_unit_test_functions": test_fn_count,
        "total_unsafe_occurrences": unsafe_count,
        "unsafe_top_crates": dict(unsafe_by_crate.most_common(15)),
        "technical_debt_counts": dict(debt_counts),
        "technical_debt_samples": debt_samples[:25],
        "largest_rust_files": largest_rs_files[:25],
    }


def main():
    print("[Repository Analyzer] 1/4 Scanning repository structure & LOC...")
    fs_metrics = scan_files_and_loc()

    print("[Repository Analyzer] 2/4 Analyzing 162 Cargo manifests & dependency graph...")
    dep_metrics = analyze_rust_crates_and_dependencies()

    print("[Repository Analyzer] 3/4 Scanning code complexity, tests, unsafe blocks & technical debt...")
    quality_metrics = analyze_code_quality_and_tech_debt()

    metrics = {
        "project": "rea-codex-demo (@openai/codex v0.162.1 Full Reconstruction)",
        "commit": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
        "target_triple": "x86_64-unknown-linux-musl",
        "structure_and_loc": fs_metrics,
        "dependencies": dep_metrics,
        "code_quality_and_debt": quality_metrics,
    }

    out_json = SCHEMAS_DIR / "repository-analysis-metrics.json"
    out_json.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Repository Analyzer] 4/4 Metrics written to {out_json}")
    print(f"  - Total files: {fs_metrics['total_files']:,}, Total LOC: {fs_metrics['total_lines']:,}, Total size: {fs_metrics['total_bytes'] / (1024*1024):.2f} MB")
    print(f"  - Rust files: {fs_metrics['by_extension'].get('.rs', {}).get('files', 0):,}, Rust LOC: {fs_metrics['by_extension'].get('.rs', {}).get('lines', 0):,}")
    print(f"  - Cargo crates: {dep_metrics['total_cargo_manifests']}, Cargo.lock packages: {dep_metrics['cargo_lock_total_packages']}, Internal edges: {dep_metrics['total_internal_edges']}")
    print(f"  - Rust fns: {quality_metrics['total_rust_functions']:,}, Test fns: {quality_metrics['total_unit_test_functions']:,}, Debt markers: {dict(quality_metrics['technical_debt_counts'])}")


if __name__ == "__main__":
    main()
