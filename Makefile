# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Cristian Cezar Moisés.

ifeq ($(origin CC),default)
CC := gcc
endif
PYTHON ?= python3
CODEC_DIR ?= ../vaptvupt-codec
BUILD ?= build
CFLAGS ?= -O2 -g -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter
CPPFLAGS += -I$(CODEC_DIR)/include -DVV_DISABLE_SIMD=1
CORE := vv_encoder vv_decoder vv_simd vv_xxh64 vv_huffman vv_ans vv_bcj
OBJECTS := $(addprefix $(BUILD)/,$(addsuffix .o,$(CORE)))
HARNESS := $(BUILD)/page_conformance
HEADERS := $(wildcard $(CODEC_DIR)/include/*.h)

.PHONY: all test check-provenance kernel-gate
all: $(HARNESS)

check-provenance:
	$(PYTHON) scripts/check_provenance.py --codec "$(CODEC_DIR)" --mode userspace

kernel-gate:
	$(PYTHON) scripts/check_provenance.py --codec "$(CODEC_DIR)" --mode kernel

$(BUILD):
	mkdir -p "$@"

$(BUILD)/%.o: $(CODEC_DIR)/src/%.c $(HEADERS) | $(BUILD) check-provenance
	$(CC) $(CPPFLAGS) $(CFLAGS) -c "$<" -o "$@"

$(BUILD)/page_conformance.o: tests/page_conformance.c $(HEADERS) | $(BUILD) check-provenance
	$(CC) $(CPPFLAGS) $(CFLAGS) -c "$<" -o "$@"

$(HARNESS): $(BUILD)/page_conformance.o $(OBJECTS) | check-provenance
	$(CC) $(CFLAGS) $^ $(LDFLAGS) -o "$@"

test: $(HARNESS)
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	"$(HARNESS)"
