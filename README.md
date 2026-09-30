<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Cristian Cezar Moisés. -->
# VaptVupt Linux development package

[Português brasileiro](README.pt-BR.md)

Version **0.1.0-dev.1**. This small repository provides a C userspace page
conformance harness and a scoped provenance/license checker for evaluating
an external canonical VaptVupt Codec **2.65.13** checkout. It contains no
Linux source, codec copy, kernel module, zram/zswap backend, or kernel ABI.

Kernel integration is **BLOCKED**. Apache-2.0 for the current codec and this
tooling is not a GPL-2.0-only kernel implementation grant. The codec's
BSD-2-Clause XXH64 notice remains applicable. No grant is inferred from a
module label or from successful userspace tests. See [development notes](docs/development.md)
and [provenance](PROVENANCE.json).

## Run the userspace checks

Prerequisites: GNU Make, GCC or Clang with a C11 compiler/linker, Python 3.9+
and the external codec checkout. No root access or kernel changes are needed.
Keep the dependency's LICENSE and NOTICE with any redistributed linked binary.

```sh
make -j2 test CODEC_DIR=/absolute/path/to/vaptvupt-codec
make -j2 test CC=clang BUILD=build-clang CODEC_DIR=/absolute/path/to/vaptvupt-codec
make -j2 test CC=clang BUILD=build-sanitize \
  CFLAGS='-O1 -g -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined' CODEC_DIR=/absolute/path/to/vaptvupt-codec
python3 scripts/check_provenance.py --codec /absolute/path/to/vaptvupt-codec --mode kernel
```

The final command intentionally exits **2** and prints `BLOCKED`. A metadata
or license inventory error exits **1** with `FAIL`; a userspace scope check
exits **0** with `PASS`. `make kernel-gate` exposes the same blocked check
(GNU Make itself exits 2 for a failed recipe). Separate build directories
prevent objects built with different compilers or sanitizer flags from mixing.

The harness checks 4, 16 and 64 KiB pages with five deterministic fixtures,
with checksums both off and on: 30 cases. It verifies exact decoded lengths,
byte equality, independent dictionary/history reset, fresh and reused context
agreement, compression/decompression capacities, malformed/truncated frames,
and canaries around input, output and caller-owned context storage. It uses
the scalar build of the actual external codec, not a replacement algorithm.
These are finite conformance tests, not throughput results or proof of safety.

## Release archives

New release archives use the Zupt `.zupt` container, not a raw codec frame.
Use a separately installed Zupt CLI to list, test and extract an archive into
a new directory; this development package is not a kernel module:

```sh
zupt list vaptvuptlinux-0.1.0-dev.1-source.zupt
zupt test vaptvuptlinux-0.1.0-dev.1-source.zupt
zupt extract vaptvuptlinux-0.1.0-dev.1-source.zupt -o ./vaptvuptlinux-source
```

Verify the release checksums and their detached OpenPGP signature first.
Source and executable archives are distinct; any executable is limited to
the architecture and validation stated in its release notes.

License: [Apache-2.0](LICENSE). Copyright 2026 Cristian Cezar Moisés.
