/**
 * @file  can_driver.c
 * @brief CAN driver implementation.
 *
 * Embedded: bxCAN peripheral (STM32F4 CAN1 registers shown in comments).
 * Simulation: loopback — every transmitted frame is echoed into Rx ring buffer.
 *
 * C patterns:
 *   - Module-static state (not exposed in header = hidden implementation)
 *   - Ring buffer with head/tail indices, power-of-two size
 *   - ISR pushes into ring; application pops via can_receive()
 */

#include "drivers/can_driver.h"
#include "hal/hal_types.h"
#include <string.h>

/* ── Module-private state ─────────────────────────────────────────────────── */
static CanConfig_t s_cfg;
static bool        s_initialized = false;
static bool        s_bus_off     = false;
static uint8_t     s_tx_err      = 0u;
static uint8_t     s_rx_err      = 0u;

/* Rx ring buffer */
static CanFrame_t  s_rx_buf[CAN_RX_BUFFER_SIZE];
static uint8_t     s_rx_head = 0u;
static uint8_t     s_rx_tail = 0u;

static CanFilter_t s_filters[CAN_MAX_FILTERS];
static uint8_t     s_filter_count = 0u;

/* ── Ring buffer helpers ──────────────────────────────────────────────────── */
static inline uint8_t rb_next(uint8_t idx) {
    return (uint8_t)((idx + 1u) & (CAN_RX_BUFFER_SIZE - 1u));
}

static bool rb_push(const CanFrame_t *frame) {
    uint8_t next = rb_next(s_rx_head);
    if (next == s_rx_tail) { return false; }  /* full */
    s_rx_buf[s_rx_head] = *frame;
    s_rx_head = next;
    return true;
}

static bool rb_pop(CanFrame_t *out) {
    if (s_rx_head == s_rx_tail) { return false; }  /* empty */
    *out       = s_rx_buf[s_rx_tail];
    s_rx_tail  = rb_next(s_rx_tail);
    return true;
}

/* ── Filter check ────────────────────────────────────────────────────────── */
static bool filter_pass(uint32_t id) {
    if (s_filter_count == 0u) { return true; }   /* accept-all if none set */
    for (uint8_t i = 0u; i < s_filter_count; i++) {
        if ((id & s_filters[i].mask) == (s_filters[i].id & s_filters[i].mask)) {
            return true;
        }
    }
    return false;
}

/* ── Public API ──────────────────────────────────────────────────────────── */

Status_t can_init(const CanConfig_t *cfg) {
    if (!cfg) { return STATUS_ERROR; }
    s_cfg         = *cfg;
    s_rx_head     = 0u;
    s_rx_tail     = 0u;
    s_filter_count= 0u;
    s_bus_off     = false;
    s_tx_err      = 0u;
    s_rx_err      = 0u;
    s_initialized = true;

#ifndef SIMULATION_BUILD
    /* Embedded: configure bxCAN peripheral
     *
     * 1. Enable CAN1 clock:  RCC->APB1ENR |= RCC_APB1ENR_CAN1EN;
     * 2. Exit sleep mode:    CAN1->MCR &= ~CAN_MCR_SLEEP;
     * 3. Enter init mode:    CAN1->MCR |=  CAN_MCR_INRQ;
     *                        while (!(CAN1->MSR & CAN_MSR_INAK));
     * 4. Set bit timing (500 kbps @ 42 MHz APB1):
     *                        CAN1->BTR = (2u << 24) | (12u << 16) |
     *                                    (5u  << 20) | (3u - 1u);
     * 5. Leave init:         CAN1->MCR &= ~CAN_MCR_INRQ;
     *                        while (CAN1->MSR & CAN_MSR_INAK);
     * 6. Enable Rx FIFO0 IRQ: NVIC_EnableIRQ(CAN1_RX0_IRQn);
     *                          CAN1->IER |= CAN_IER_FMPIE0;
     */
#endif

    return STATUS_OK;
}

Status_t can_transmit(const CanFrame_t *frame) {
    if (!s_initialized || !frame) { return STATUS_ERROR; }
    if (s_bus_off)                { return STATUS_FAULT; }

#ifdef SIMULATION_BUILD
    /* Loopback: push directly into Rx ring */
    (void)rb_push(frame);
#else
    /* Embedded: fill TX mailbox 0
     *   CAN1->sTxMailBox[0].TIR  = (frame->id << 21u) | CAN_TI0R_TXRQ;
     *   CAN1->sTxMailBox[0].TDTR = frame->dlc & 0x0Fu;
     *   CAN1->sTxMailBox[0].TDLR = *(uint32_t *)&frame->data[0];
     *   CAN1->sTxMailBox[0].TDHR = *(uint32_t *)&frame->data[4];
     *   CAN1->sTxMailBox[0].TIR |= CAN_TI0R_TXRQ;    // request TX
     */
    UNUSED(frame);
#endif

    return STATUS_OK;
}

Status_t can_receive(CanFrame_t *out) {
    if (!out) { return STATUS_ERROR; }
    return rb_pop(out) ? STATUS_OK : STATUS_ERROR;
}

Status_t can_add_filter(uint32_t id, uint32_t mask) {
    if (s_filter_count >= CAN_MAX_FILTERS) { return STATUS_ERROR; }
    s_filters[s_filter_count].id   = id;
    s_filters[s_filter_count].mask = mask;
    s_filter_count++;

#ifndef SIMULATION_BUILD
    /* Embedded: program acceptance filter bank
     *   CAN1->FMR  |=  CAN_FMR_FINIT;      // filter init mode
     *   CAN1->FA1R &= ~(1u << bank);        // deactivate bank
     *   CAN1->sFilterRegister[bank].FR1 = id   << 21u;
     *   CAN1->sFilterRegister[bank].FR2 = mask << 21u;
     *   CAN1->FA1R |=  (1u << bank);        // activate bank
     *   CAN1->FMR  &= ~CAN_FMR_FINIT;
     */
#endif

    return STATUS_OK;
}

/* Called from CAN1_RX0_IRQHandler */
void can_on_rx_isr(const CanFrame_t *frame) {
    if (filter_pass(frame->id)) {
        rb_push(frame);
    }

#ifndef SIMULATION_BUILD
    /* Embedded: release FIFO to allow next message
     *   CAN1->RF0R |= CAN_RF0R_RFOM0;
     */
#endif
}

bool    can_is_bus_off(void) { return s_bus_off; }
uint8_t can_get_tx_err(void) { return s_tx_err;  }
uint8_t can_get_rx_err(void) { return s_rx_err;  }

Status_t can_reset(void) {
    s_bus_off = false;
    s_tx_err  = 0u;
    s_rx_err  = 0u;
    return can_init(&s_cfg);
}
