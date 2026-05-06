#pragma once
/**
 * base_adapter.hpp
 * Abstract base for all hardware protocol adapters.
 * All concrete adapters (CAN, LIN, UDS, SPI, I2C) inherit from this.
 */

#include <cstdint>
#include <string>
#include <vector>
#include <functional>
#include <stdexcept>

namespace hw_adapter {

// ─── Common data types ────────────────────────────────────────────────────────

using Byte   = uint8_t;
using Word   = uint16_t;
using DWord  = uint32_t;
using Buffer = std::vector<Byte>;

// ─── Adapter status codes ─────────────────────────────────────────────────────

enum class AdapterStatus : int {
    OK               =  0,
    ERR_NOT_INIT     = -1,
    ERR_TIMEOUT      = -2,
    ERR_BUS_ERROR    = -3,
    ERR_INVALID_ARG  = -4,
    ERR_OVERFLOW     = -5,
    ERR_NACK         = -6,
    ERR_DISCONNECTED = -7,
};

inline const char* statusToString(AdapterStatus s) {
    switch (s) {
        case AdapterStatus::OK:               return "OK";
        case AdapterStatus::ERR_NOT_INIT:     return "ERR_NOT_INIT";
        case AdapterStatus::ERR_TIMEOUT:      return "ERR_TIMEOUT";
        case AdapterStatus::ERR_BUS_ERROR:    return "ERR_BUS_ERROR";
        case AdapterStatus::ERR_INVALID_ARG:  return "ERR_INVALID_ARG";
        case AdapterStatus::ERR_OVERFLOW:     return "ERR_OVERFLOW";
        case AdapterStatus::ERR_NACK:         return "ERR_NACK";
        case AdapterStatus::ERR_DISCONNECTED: return "ERR_DISCONNECTED";
        default:                               return "UNKNOWN";
    }
}

// ─── AdapterException ─────────────────────────────────────────────────────────

class AdapterException : public std::runtime_error {
public:
    explicit AdapterException(AdapterStatus code, const std::string& msg)
        : std::runtime_error(std::string(statusToString(code)) + ": " + msg)
        , code_(code) {}

    AdapterStatus code() const noexcept { return code_; }

private:
    AdapterStatus code_;
};

// ─── BaseAdapter ──────────────────────────────────────────────────────────────

class BaseAdapter {
public:
    virtual ~BaseAdapter() = default;

    /// Open and initialise the adapter (e.g., open port, configure baud rate).
    virtual AdapterStatus open(const std::string& device_uri) = 0;

    /// Close and release all resources.
    virtual AdapterStatus close() = 0;

    /// Returns true if the adapter is currently open and operational.
    virtual bool isOpen() const noexcept = 0;

    /// Human-readable name of this adapter (e.g., "CAN", "LIN", "UDS").
    virtual std::string name() const noexcept = 0;

    /// Hardware / firmware version string (populated after open()).
    virtual std::string version() const noexcept = 0;

    // ─── Statistics ───────────────────────────────────────────────────────────

    struct Stats {
        uint64_t tx_count     = 0;
        uint64_t rx_count     = 0;
        uint64_t error_count  = 0;
        uint64_t timeout_count = 0;
    };

    virtual Stats stats() const noexcept = 0;
    virtual void  resetStats() noexcept  = 0;

protected:
    void requireOpen() const {
        if (!isOpen())
            throw AdapterException(AdapterStatus::ERR_NOT_INIT,
                                   name() + " adapter is not open");
    }
};

} // namespace hw_adapter
