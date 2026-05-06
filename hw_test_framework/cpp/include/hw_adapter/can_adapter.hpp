#pragma once
/**
 * can_adapter.hpp
 * CAN bus adapter — supports standard (11-bit) and extended (29-bit) frames.
 * Thread-safe: all public methods are safe to call from multiple threads.
 */

#include "base_adapter.hpp"
#include <chrono>
#include <functional>
#include <memory>
#include <mutex>
#include <optional>
#include <atomic>

namespace hw_adapter {

// ─── CAN Frame ────────────────────────────────────────────────────────────────

struct CanFrame {
    DWord  id          = 0;       ///< 11-bit or 29-bit arbitration ID
    bool   is_extended = false;   ///< true = 29-bit extended ID
    bool   is_remote   = false;   ///< Remote Transmission Request frame
    bool   is_error    = false;   ///< Error frame
    uint8_t dlc        = 0;       ///< Data Length Code (0–8)
    Byte   data[8]     = {};      ///< Frame payload
    int64_t timestamp_us = 0;     ///< Receive timestamp (microseconds since epoch)

    /// Convenience: build a standard data frame
    static CanFrame make(DWord id, std::initializer_list<Byte> bytes, bool extended = false);

    /// Returns data as a vector<uint8_t>
    Buffer toBuffer() const { return Buffer(data, data + dlc); }
};

// ─── CAN Bit Rates ────────────────────────────────────────────────────────────

enum class CanBitrate : uint32_t {
    kbps_125  =  125000,
    kbps_250  =  250000,
    kbps_500  =  500000,
    Mbps_1    = 1000000,
};

// ─── CAN Filter ───────────────────────────────────────────────────────────────

struct CanFilter {
    DWord id   = 0;           ///< Target message ID
    DWord mask = 0xFFFFFFFF;  ///< Bit mask: 1 = must match, 0 = don't care
    bool  extended = false;

    /// Accept all messages (no filtering)
    static CanFilter acceptAll() { return {0, 0, false}; }

    /// Accept only a single ID
    static CanFilter exactId(DWord id, bool extended = false) {
        return {id, extended ? 0x1FFFFFFF : 0x7FF, extended};
    }
};

// ─── Receive callback type ────────────────────────────────────────────────────

using CanReceiveCallback = std::function<void(const CanFrame&)>;

// ─── CanAdapter ───────────────────────────────────────────────────────────────

class CanAdapter : public BaseAdapter {
public:
    explicit CanAdapter();
    ~CanAdapter() override;

    // ─── BaseAdapter interface ────────────────────────────────────────────────
    AdapterStatus open(const std::string& device_uri) override;
    AdapterStatus close() override;
    bool          isOpen()   const noexcept override;
    std::string   name()     const noexcept override { return "CAN"; }
    std::string   version()  const noexcept override;
    Stats         stats()    const noexcept override;
    void          resetStats() noexcept override;

    // ─── Configuration ────────────────────────────────────────────────────────

    /// Set bit rate — must be called before open().
    void setBitrate(CanBitrate bitrate) noexcept;

    /// Set hardware acceptance filter.
    AdapterStatus setFilter(const CanFilter& filter);

    // ─── Transmit ─────────────────────────────────────────────────────────────

    /// Transmit a single CAN frame. Blocking until the frame is queued.
    /// @param timeout_ms  0 = non-blocking; negative = wait forever
    AdapterStatus transmit(const CanFrame& frame, int timeout_ms = 100);

    /// Transmit multiple frames in sequence.
    AdapterStatus transmitBurst(const std::vector<CanFrame>& frames, int timeout_ms = 500);

    // ─── Receive ──────────────────────────────────────────────────────────────

    /// Blocking receive — waits up to timeout_ms.
    std::optional<CanFrame> receive(int timeout_ms = 1000);

    /// Register an async callback (called from the RX thread).
    void onReceive(CanReceiveCallback cb);

    /// Clear the internal RX queue.
    void flushRxQueue();

    // ─── Bus statistics ───────────────────────────────────────────────────────

    struct BusLoad {
        double percent      = 0.0;  ///< 0.0–100.0
        uint32_t error_count = 0;
        uint32_t tec         = 0;   ///< Transmit Error Counter
        uint32_t rec         = 0;   ///< Receive Error Counter
    };
    BusLoad busLoad() const noexcept;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace hw_adapter
