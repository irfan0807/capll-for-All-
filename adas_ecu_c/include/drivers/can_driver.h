/**
 * @file  can_driver.h
 * @brief CAN bus driver — bxCAN peripheral abstraction.
 *
 * C patterns used:
 *   - Module-level static state (no global objects)
 *   - Explicit init function instead of constructor
 *   - Function prefix convention: can_xxx()
 *   - Ring buffer implemented as fixed-size array + head/tail indices
 *   - PACKED struct for hardware-compatible frame layout
 */

#ifndef CAN_DRIVER_H
#define CAN_DRIVER_H

#include "hal/hal_types.h"

/* ── CAN Frame ───────────────────────────────────────────────────────────── */
typedef struct PACKED {
    uint32_t id;        /* 11-bit standard ID */
    uint8_t  dlc;       /* Data Length Code 0–8 */
    uint8_t  data[8];
} CanFrame_t;

/* ── Bitrate selection ───────────────────────────────────────────────────── */
typedef enum {
    CAN_BITRATE_125KBPS = 125u,
    CAN_BITRATE_250KBPS = 250u,
    CAN_BITRATE_500KBPS = 500u,
    CAN_BITRATE_1MBPS   = 1000u
} CanBitrate_t;

/* ── Configuration ───────────────────────────────────────────────────────── */
typedef struct {
    CanBitrate_t bitrate;
    uint8_t      channel;   /* 1 = CAN1, 2 = CAN2 */
    bool         loopback;  /* true in simulation */
} CanConfig_t;

/* ── ID filter entry ─────────────────────────────────────────────────────── */
typedef struct {
    uint32_t id;
    uint32_t mask;
} CanFilter_t;

#define CAN_RX_BUFFER_SIZE  64u
#define CAN_MAX_FILTERS     16u

/* ── Public API ──────────────────────────────────────────────────────────── */

/* Initialise driver (call once). */
Status_t can_init    (const CanConfig_t *cfg);

/* Transmit a frame. Returns STATUS_BUSY if no mailbox free. */
Status_t can_transmit(const CanFrame_t *frame);

/* Pop one frame from Rx ring buffer. Returns STATUS_ERROR when empty. */
Status_t can_receive (CanFrame_t *out);

/* Add an acceptance filter (id & mask pattern). */
Status_t can_add_filter(uint32_t id, uint32_t mask);

/* Called from bxCAN Rx ISR — push frame into ring buffer. */
void     can_on_rx_isr(const CanFrame_t *frame);

/* Return true if bus-off error active. */
bool     can_is_bus_off(void);

/* TX and RX error counters (diagnostic). */
uint8_t  can_get_tx_err(void);
uint8_t  can_get_rx_err(void);

/* Reset driver (re-init after bus-off recovery). */
Status_t can_reset(void);

/* ── Helper: get 16-bit big-endian signal from frame data ──────────────── */
static inline uint16_t can_get_u16_be(const CanFrame_t *f, uint8_t byte_pos) {
    return (uint16_t)((f->data[byte_pos] << 8u) | f->data[byte_pos + 1u]);
}

/* Helper: extract arbitrary bit range */
static inline uint32_t can_get_bits(const CanFrame_t *f,
                                    uint8_t start_bit,
                                    uint8_t len) {
    uint32_t raw = 0u;
    for (uint8_t i = 0u; i < len; i++) {
        uint8_t bit = start_bit + i;
        if (f->data[bit / 8u] & (uint8_t)(1u << (bit % 8u))) {
            raw |= (1u << i);
        }
    }
    return raw;
}

#endif /* CAN_DRIVER_H */
