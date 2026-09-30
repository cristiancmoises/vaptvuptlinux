#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Cristian Cezar Moisés.
"""Check the declared userspace dependency scope; kernel integration stays blocked."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CORE = ("vv_encoder.c", "vv_decoder.c", "vv_simd.c", "vv_xxh64.c",
        "vv_huffman.c", "vv_ans.c", "vv_bcj.c")
MAX_FILE = 2 * 1024 * 1024


def read_regular(root, relative):
    path = root / relative
    # Reject symlinked directories as well as symlinked leaf files.
    for candidate in (path, *path.parents):
        if candidate == root.parent:
            break
        if candidate.is_symlink():
            raise ValueError(f"symlink in dependency path: {relative}")
    if not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ValueError(f"missing, nonregular, or oversized file: {relative}")
    return path.read_text(encoding="utf-8")


def license_of(text):
    ids = re.findall(r"^\s*(?:/\*|\*|//|#)\s*SPDX-License-Identifier:\s*([^\n]+)",
                     text[:8192], re.MULTILINE)
    ids = [value.strip().removesuffix("*/").strip() for value in ids]
    if len(ids) != 1:
        raise ValueError("expected exactly one leading SPDX license declaration")
    return ids[0]


def check(codec):
    metadata = json.loads(read_regular(ROOT, "PROVENANCE.json"))
    if metadata["schema"] != 1 or metadata["package_version"] != "0.1.0-dev.1":
        raise ValueError("unsupported package provenance schema/version")
    if metadata["tooling_license"] != "Apache-2.0":
        raise ValueError("tooling license does not match this package")
    if metadata["kernel_implementation_grant"] is not None:
        raise ValueError("this development package has no reviewed kernel implementation grant")
    if metadata["original_snapshot"]["upstream_commit"] is not None:
        raise ValueError("the original non-Git snapshot has no verified upstream commit")
    if metadata["codec"]["required_version"] != "2.65.13":
        raise ValueError("unsupported codec version declaration")

    # Only first-party tools are shipped; never silently admit codec/kernel code.
    tooling = sorted((ROOT / "scripts").glob("*.py")) + sorted((ROOT / "tests").glob("*.py"))
    tooling += [ROOT / "Makefile", ROOT / "tests/page_conformance.c"]
    for path in tooling:
        source = read_regular(ROOT, str(path.relative_to(ROOT)))
        if license_of(source) != "Apache-2.0" or "Copyright 2026 Cristian Cezar Moisés" not in source[:8192]:
            raise ValueError(f"unexpected tooling license/copyright: {path.relative_to(ROOT)}")
    for folder in (ROOT / "src", ROOT / "include", ROOT / "kernel"):
        if folder.exists():
            raise ValueError(f"unreviewed implementation directory: {folder.name}")

    header = read_regular(codec, "include/vaptvupt.h")
    versions = re.findall(r'^#define\s+VV_VERSION_STRING\s+"([^"]+)"', header, re.MULTILINE)
    if versions != [metadata["codec"]["required_version"]]:
        raise ValueError("external codec version mismatch")
    license_text = read_regular(codec, "LICENSE")
    if "Apache License" not in license_text or "Version 2.0, January 2004" not in license_text:
        raise ValueError("external Apache license text is missing")
    notice = read_regular(codec, "NOTICE")
    if not all(value in notice for value in ("xxHash", "Yann Collet", "Redistribution and use in source and binary forms")):
        raise ValueError("external xxHash notice is missing")
    sources = ["src/" + name for name in CORE]
    headers = sorted("include/" + item.name for item in (codec / "include").glob("*.h"))
    if "include/vaptvupt.h" not in headers:
        raise ValueError("external public header is missing")
    digest = hashlib.sha256()
    for relative in sources + headers:
        source = read_regular(codec, relative)
        expected = "BSD-2-Clause" if relative == "src/vv_xxh64.c" else "Apache-2.0"
        actual = license_of(source)
        if actual != expected:
            raise ValueError(f"external license drift: {relative}: {actual}, expected {expected}")
        digest.update(relative.encode("utf-8") + b"\0" + source.encode("utf-8") + b"\0")
    pin = metadata["codec"]["commit"]
    if pin is not None:
        if not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{40}", pin):
            raise ValueError("invalid codec commit pin")
        command = ["git", "-c", "core.fsmonitor=false", "-C", str(codec)]
        head = subprocess.run(command + ["rev-parse", "--verify", "HEAD"],
                              capture_output=True, text=True, check=False)
        if head.returncode or head.stdout.strip() != pin:
            raise ValueError("external codec HEAD does not match the provenance commit pin")
        inventory = sources + headers + ["LICENSE", "NOTICE"]
        tracked = subprocess.run(command + ["ls-files", "--error-unmatch", "--"] + inventory,
                                 capture_output=True, text=True, check=False)
        clean = subprocess.run(command + ["diff", "--no-ext-diff", "--quiet", "HEAD", "--"] + inventory,
                               capture_output=True, text=True, check=False)
        if tracked.returncode or clean.returncode:
            raise ValueError("external codec source/header inventory is untracked or differs from its pinned commit")
    return len(sources), len(headers), digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codec", type=Path, required=True, help="external canonical codec checkout")
    parser.add_argument("--mode", choices=("userspace", "kernel"), default="userspace")
    args = parser.parse_args()
    try:
        codec = args.codec.absolute()
        sources, headers, digest = check(codec)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL: provenance/license check: {error}", file=sys.stderr)
        return 1
    print(f"PASS: scoped inventory: {sources} external C sources, {headers} headers; sha256={digest}")
    if args.mode == "kernel":
        print("BLOCKED: codec Apache-2.0 is not a GPL-2.0-only kernel implementation grant; "
              "no kernel backend or reviewed compatible grant is supplied.")
        return 2
    print("PASS: userspace tooling scope only; this check is not a legal audit or kernel approval.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
