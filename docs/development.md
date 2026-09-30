<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Cristian Cezar Moisés. -->
# Scope, provenance and kernel gate

[Português brasileiro](development.pt-BR.md)

The 0.1.0-dev.1 deliverable is userspace tooling. First-party tooling uses
Apache-2.0 under the copyright holder's authorization. That authorization
does not license a kernel implementation. No codec or kernel files have been
imported or relicensed in this package.

The inherited local non-Git snapshot claims Linux 7.2.7 in its Makefile and
contains a VaptVupt 2.65.11 amalgamation labeled GPL-3.0-or-later. Its exact
upstream commit is unknown. The hashes in PROVENANCE.json identify four
observed local files, not a complete tree, upstream release or verified build.
The historical wrapper is not the backend for this package.

The external canonical 2.65.13 codec currently declares Apache-2.0 for
first-party code and BSD-2-Clause for its XXH64 implementation derived from
xxHash. The source inventory compiled by the Makefile is seven C files plus
all public include headers. The checker rejects absent/multiple license
declarations, unexpected licenses or codec version, missing notices,
symlinked dependency files/directories and files above 2 MiB. It reports a
digest over the ordered source/header inventory. This limited check is not
an exhaustive copyright audit, authenticity attestation or compatible
implementation grant. It does not scan unrelated projects or the full kernel.

The [kernel licensing rules](https://docs.kernel.org/process/license-rules.html)
specify GPL version 2 only for the kernel as a whole and require compatible
file licenses. Apache-2.0 is listed for dual licensing, with a compatible
alternative. This package therefore has a hard kernel gate: no reviewed
compatible grant and no backend. Changing a module's license string would
not change the rights in its linked implementation. Even a passing userspace
inventory cannot make `--mode kernel` succeed in this development version.

On 2026-09-30, a read-only upstream ref query returned Torvalds Linux master
`551c722f40809618230001baccf219193e22fc5a`. The
[licensing document at that commit](https://github.com/torvalds/linux/blob/551c722f40809618230001baccf219193e22fc5a/Documentation/process/license-rules.rst)
was inspected. This is a documentation reference, not a selected integration
base, a source import, a kernel test, or provenance for the inherited snapshot.

## Format and resource limits

The release codec pin is `e30dc9329be7cf9f233b1ac0b1fc9ed31f530391`
(version 2.65.13). When a commit is recorded, the checker requires that exact
Git HEAD and a tracked, unmodified source/header and LICENSE/NOTICE inventory.

The test configuration fixes FAST mode and window log 16, disables BCJ
filters, uses the scalar codec build, and treats every page as a separate
current codec frame. The caller-owned encoder context supports at most
65,536 input bytes, needs the queried alignment and workspace size, and is
exclusive to one call at a time. Its reset behavior is checked against
fresh contexts and fresh one-shot calls. Output must provide the codec's
compression bound; decoded capacity is checked against the expected page
size rather than trusting a frame's content size.

This repository defines no stable on-disk page container or kernel format.
It does not promise interoperability with the old embedded 2.65.11 codec,
older decoders, cross-endian builds or other architectures. Current tests
cover only the linked checkout and host compiler configuration. Checksums
detect the exercised corruption; disabling them permits undetected payload
corruption, so that configuration is only a conformance comparison here.
The tests do not exercise allocation failure, concurrency, every malformed
stream, kernel reclaim, atomic context or a device backend.

## Requirements before any future kernel work

Resolve a written compatible implementation grant and complete a dependency
provenance/license review before importing implementation code. Select a
verified upstream commit, record its source URL and hash, and design the
target compression interface against that source. Establish allocation and
locking behavior, bound the workspace and stack for each page size, define
incompressible/error handling and any durable format, and test in isolated
kernel builds and virtual machines. Kernel builds, KUnit, zram/zswap, boot,
reclaim stress and upstream submission are **NOT RUN** by this package.
No production kernel readiness or upstream acceptance is claimed.

## Optional static userspace build

The ordinary local Guix GCC build uses a Guix store interpreter and should
not be copied to a conventional distribution as a portable executable.
An optional musl build can use an existing `musl-gcc`, or a temporary Guix
shell without installing it into the user's profile:

```sh
guix shell musl make -- make -j2 test CC=musl-gcc BUILD=build-musl \
  LDFLAGS='-static -Wl,-Map,build-musl/link.map -Wl,-t' \
  CODEC_DIR=/absolute/path/to/vaptvupt-codec
readelf -l build-musl/page_conformance
readelf -d build-musl/page_conformance
```

The Guix package observed here is musl 1.2.6, from
`https://www.musl-libc.org/releases/musl-1.2.6.tar.gz`, with Guix SHA-256
base32 `0ajic0jgiyfk2sk3brn1wsshq0kp9za8x7i4qcgiariwc4xzv1fm` and the package's
`musl-CVE-2026-40200.patch`. Its complete installed COPYRIGHT text is
preserved in [LICENSES/musl.txt](../LICENSES/musl.txt). Include this notice
and the external codec's LICENSE/NOTICE with redistributed static binaries.
Keep the link map and compiler/linker trace when selecting a binary; a
static libc alone does not establish which runtime objects were included.
Actual test results and architecture belong with each selected build.

The observed GCC 14.3.0 link includes `crtbeginS.o` and `crtendS.o` from
the GCC runtime. Its GPL-3.0-or-later terms and GCC Runtime Library
Exception 3.1 are preserved in LICENSES; the exception permits an eligible
GCC compilation to combine the covered runtime with independent modules
under their own compatible terms. The observed link map selects no
`libgcc.a`/`libgcc_eh.a` archive members and no glibc runtime objects. No
external compiler plugins or intermediate-representation transforms are
used by these build commands. See the [GCC runtime exception](https://gcc.gnu.org/onlinedocs/libstdc++/manual/license.html).
