/* SPDX-License-Identifier: Apache-2.0 */
/* Copyright 2026 Cristian Cezar Moisés. */
/* Userspace independent-page conformance, not a kernel backend. */
#include "vaptvupt.h"

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GUARD 32u
#define MARK 0xA5u
#define COUNT(a) (sizeof(a) / sizeof((a)[0]))

struct buffer {
    uint8_t *allocation;
    uint8_t *data;
    size_t capacity;
};

static unsigned checks;

#define REQUIRE(condition) do { \
    checks++; \
    if (!(condition)) { \
        fprintf(stderr, "FAIL: line %d: %s\n", __LINE__, #condition); \
        exit(1); \
    } \
} while (0)

static struct buffer allocate_buffer(size_t capacity, size_t alignment)
{
    struct buffer b;
    REQUIRE(alignment > 0);
    b.allocation = malloc(capacity + 2 * GUARD + alignment);
    REQUIRE(b.allocation != NULL);
    uintptr_t start = (uintptr_t)(b.allocation + GUARD);
    size_t remainder = start % alignment;
    b.data = (uint8_t *)(start + (remainder ? alignment - remainder : 0));
    b.capacity = capacity;
    memset(b.data - GUARD, MARK, capacity + 2 * GUARD);
    return b;
}

static void poison(struct buffer *b)
{
    memset(b->data - GUARD, MARK, b->capacity + 2 * GUARD);
}

static void check_guards(const struct buffer *b, size_t used)
{
    REQUIRE(used <= b->capacity);
    for (size_t i = 0; i < GUARD; i++) REQUIRE(b->data[-(ptrdiff_t)GUARD + (ptrdiff_t)i] == MARK);
    for (size_t i = used; i < b->capacity + GUARD; i++) REQUIRE(b->data[i] == MARK);
}

static void release(struct buffer *b)
{
    free(b->allocation);
    memset(b, 0, sizeof(*b));
}

static void make_page(uint8_t *dst, size_t size, unsigned fixture)
{
    uint32_t state = 0xD39127A5u;
    static const char phrase[] = "independent page: VaptVupt userspace conformance\n";
    for (size_t i = 0; i < size; i++) {
        state ^= state << 13;
        state ^= state >> 17;
        state ^= state << 5;
        if (fixture == 0) dst[i] = 0;
        else if (fixture == 1) dst[i] = (uint8_t)phrase[i % (sizeof(phrase) - 1)];
        else if (fixture == 2) dst[i] = (uint8_t)state;
        else if (fixture == 3) dst[i] = (uint8_t)((i / 64) % 7);
        else dst[i] = (i % 512 < 256) ? (uint8_t)state : 0;
    }
}

static void decode_exact(const uint8_t *encoded, size_t length,
                         const struct buffer *input, struct buffer *decoded)
{
    poison(decoded);
    int64_t result = vv_decompress(encoded, length, decoded->data, input->capacity);
    REQUIRE(result == (int64_t)input->capacity);
    REQUIRE(memcmp(decoded->data, input->data, input->capacity) == 0);
    check_guards(decoded, input->capacity);
}

static void malformed_cases(struct buffer *encoded, size_t length,
                            const struct buffer *input, struct buffer *decoded,
                            int checksum)
{
    const size_t cuts[] = {0, 1, sizeof(vv_frame_header_t) - 1, length - 1};
    for (size_t i = 0; i < COUNT(cuts); i++) {
        poison(decoded);
        REQUIRE(vv_decompress(encoded->data, cuts[i], decoded->data, input->capacity) < 0);
        check_guards(decoded, input->capacity);
    }
    poison(decoded);
    REQUIRE(vv_decompress(encoded->data, length, decoded->data, input->capacity - 1) < 0);
    check_guards(decoded, input->capacity - 1);
    poison(decoded);
    REQUIRE(vv_decompress(encoded->data, length, decoded->data, 0) < 0);
    check_guards(decoded, 0);

    uint8_t saved = encoded->data[0];
    encoded->data[0] ^= 0xFF;
    poison(decoded);
    REQUIRE(vv_decompress(encoded->data, length, decoded->data, input->capacity) < 0);
    check_guards(decoded, input->capacity);
    encoded->data[0] = saved;
    saved = encoded->data[offsetof(vv_frame_header_t, window_log)];
    encoded->data[offsetof(vv_frame_header_t, window_log)] = 9;
    poison(decoded);
    REQUIRE(vv_decompress(encoded->data, length, decoded->data, input->capacity) < 0);
    check_guards(decoded, input->capacity);
    encoded->data[offsetof(vv_frame_header_t, window_log)] = saved;
    if (checksum) {
        size_t offset = length - sizeof(vv_frame_footer_t);
        saved = encoded->data[offset];
        encoded->data[offset] ^= 1;
        poison(decoded);
        REQUIRE(vv_decompress(encoded->data, length, decoded->data, input->capacity) < 0);
        check_guards(decoded, input->capacity);
        encoded->data[offset] = saved;
    }
    decode_exact(encoded->data, length, input, decoded);
}

static void run_pages(size_t size, int checksum)
{
    vv_options_t options;
    vv_default_options(&options);
    options.mode = VV_MODE_ULTRA_FAST;
    options.window_log = 16;
    options.checksum = checksum;
    size_t bound = vv_compress_bound(size);
    size_t workspace = vv_fast_context_size(size);
    size_t alignment = vv_fast_context_alignment();
    REQUIRE(workspace != 0);
    struct buffer storage = allocate_buffer(workspace, alignment);
    struct buffer fresh_storage = allocate_buffer(workspace, alignment);
    struct buffer input = allocate_buffer(size, 1);
    struct buffer snapshot = allocate_buffer(size, 1);
    struct buffer encoded = allocate_buffer(bound, 1);
    struct buffer reference = allocate_buffer(bound, 1);
    struct buffer fresh_output = allocate_buffer(bound, 1);
    /* Extra capacity permits checking the exact number of produced bytes. */
    struct buffer decoded = allocate_buffer(size + 16, 1);
    vv_fast_context_t *context = NULL;
    REQUIRE(vv_fast_context_init(storage.data, workspace - 1, size, &options, &context) == VV_ERR_OVERFLOW);
    REQUIRE(context == NULL);
    check_guards(&storage, 0);
    REQUIRE(vv_fast_context_init(storage.data, workspace, size, &options, &context) == VV_OK);
    REQUIRE(context != NULL);
    check_guards(&storage, workspace);

    for (unsigned fixture = 0; fixture < 5; fixture++) {
        make_page(input.data, size, fixture);
        memcpy(snapshot.data, input.data, size);
        poison(&encoded);
        REQUIRE(vv_fast_context_compress(context, input.data, size, encoded.data, bound - 1) == VV_ERR_OVERFLOW);
        check_guards(&encoded, 0);
        REQUIRE(vv_fast_context_compress(context, input.data, size, encoded.data, 0) == VV_ERR_OVERFLOW);
        check_guards(&encoded, 0);
        REQUIRE(vv_fast_context_compress(context, input.data, size + 1, encoded.data, bound) == VV_ERR_PARAM);
        check_guards(&encoded, 0);
        REQUIRE(vv_fast_context_compress(context, NULL, size, encoded.data, bound) == VV_ERR_PARAM);
        check_guards(&encoded, 0);

        int64_t length = vv_fast_context_compress(context, input.data, size, encoded.data, bound);
        REQUIRE(length > 0 && (uint64_t)length <= bound);
        check_guards(&encoded, (size_t)length);
        check_guards(&storage, workspace);
        REQUIRE(memcmp(input.data, snapshot.data, size) == 0);
        check_guards(&input, size);
        decode_exact(encoded.data, (size_t)length, &input, &decoded);

        /* Fresh one-shot and fresh caller storage independently confirm reset. */
        poison(&reference);
        int64_t ordinary = vv_compress(input.data, size, reference.data, bound, &options);
        REQUIRE(ordinary == length);
        REQUIRE(memcmp(reference.data, encoded.data, (size_t)length) == 0);
        check_guards(&reference, (size_t)ordinary);
        poison(&fresh_storage);
        vv_fast_context_t *fresh = NULL;
        REQUIRE(vv_fast_context_init(fresh_storage.data, workspace, size, &options, &fresh) == VV_OK);
        poison(&fresh_output);
        int64_t fresh_length = vv_fast_context_compress(fresh, input.data, size, fresh_output.data, bound);
        REQUIRE(fresh_length == length);
        REQUIRE(memcmp(fresh_output.data, encoded.data, (size_t)length) == 0);
        check_guards(&fresh_output, (size_t)fresh_length);
        check_guards(&fresh_storage, workspace);

        malformed_cases(&encoded, (size_t)length, &input, &decoded, checksum);
        /* Previous errors and intervening pages cannot alter the next frame. */
        poison(&fresh_output);
        REQUIRE(vv_fast_context_compress(context, input.data, size, fresh_output.data, bound) == length);
        REQUIRE(memcmp(fresh_output.data, encoded.data, (size_t)length) == 0);
        check_guards(&fresh_output, (size_t)length);
        printf("PASS page=%zu fixture=%u checksum=%d produced=%" PRId64
               " reset=independent capacity=checked malformed=checked canaries=checked\n",
               size, fixture, checksum, length);
    }
    release(&storage);
    release(&fresh_storage);
    release(&input);
    release(&snapshot);
    release(&encoded);
    release(&reference);
    release(&fresh_output);
    release(&decoded);
}

int main(void)
{
    const size_t pages[] = {4096, 16384, 65536};
    REQUIRE(vv_fast_context_size(0) == 0);
    REQUIRE(vv_fast_context_size(65537) == 0);
    for (size_t i = 0; i < COUNT(pages); i++) {
        for (int checksum = 0; checksum <= 1; checksum++) run_pages(pages[i], checksum);
    }
    printf("PASS: codec=%s cases=30 assertions=%u; userspace only\n", VV_VERSION_STRING, checks);
    return 0;
}
