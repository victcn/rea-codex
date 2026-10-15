#!/usr/bin/env python3
"""
Read-only CLI Inspector for @openai/codex v0.162.1 Binary Assets & Stripped Function Addresses.
Usage:
  python3 scripts/inspect-binary-assets.py                   # Verify all embedded asset regions & print summary
  python3 scripts/inspect-binary-assets.py --addr 0x1a08d90  # Resolve a virtual address (sub_xxxx) to exact Rust source & fn
"""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path("/code/custom-dev/rea-codex-demo")
SCHEMAS = ROOT / "schemas"
VENDOR = Path("/usr/local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl")


def lookup_address(addr_str: str):
    target_va = int(addr_str, 16) if addr_str.startswith("0x") else int(addr_str)
    addr_map = json.loads((SCHEMAS / "binary-address-map.json").read_text(encoding="utf-8"))
    for rec in addr_map.get("functions", []):
        s = int(rec["vaddr_start"], 16)
        e = int(rec["vaddr_end"], 16)
        if s <= target_va < e:
            print(json.dumps(rec, indent=2, ensure_ascii=False))
            return True
    fork_map = json.loads((SCHEMAS / "git-fork-dependencies.json").read_text(encoding="utf-8"))
    for fork in fork_map.get("git_forks", []):
        for rec in fork.get("mapped_native_functions", []):
            s = int(rec["vaddr_start"], 16)
            e = int(rec["vaddr_end"], 16)
            if s <= target_va < e:
                print(json.dumps({"git_fork": fork["github_repo"], **rec}, indent=2, ensure_ascii=False))
                return True
    print(f"Address {hex(target_va)} not found in mapped workspace or git-fork function ranges.")
    return False


def verify_all():
    ver = json.loads((SCHEMAS / "binary-asset-verification.json").read_text(encoding="utf-8"))
    print(f"Verifying {ver['verified_asset_regions']} embedded binary asset regions...")
    for reg in ver["regions"]:
        bin_path = VENDOR / reg["binary"]
        off = int(reg["offset"], 16)
        length = reg["length"]
        with bin_path.open("rb") as f:
            f.seek(off)
            chunk = f.read(length)
        actual_sha = hashlib.sha256(chunk).hexdigest()
        ok = actual_sha == reg["sha256"]
        status = "OK" if ok else "MISMATCH"
        print(f"  [{status}] {reg['name']:48s} @ {reg['offset']} ({length:10,d} B) sha256={actual_sha[:16]}...")
        if not ok:
            raise AssertionError(f"Digest mismatch for {reg['name']}")


def main():
    parser = argparse.ArgumentParser(description="Inspect @openai/codex binary assets and stripped addresses.")
    parser.add_argument("--addr", help="Hex virtual address (e.g. 0x1a08d90) to resolve to real Rust source function")
    args = parser.parse_args()
    if args.addr:
        lookup_address(args.addr)
    else:
        verify_all()


if __name__ == "__main__":
    main()
