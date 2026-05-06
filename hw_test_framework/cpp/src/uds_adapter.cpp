/**
 * uds_adapter.cpp
 * UDS adapter implementation — ISO 15765-2 transport layer + ISO 14229 services.
 */

#include "hw_adapter/uds_adapter.hpp"

#include <algorithm>
#include <cassert>
#include <chrono>
#include <sstream>
#include <thread>

namespace hw_adapter {

// ─── DtcRecord::hex() ─────────────────────────────────────────────────────────

std::string DtcRecord::hex() const {
    std::ostringstream oss;
    oss << std::hex << std::uppercase;
    oss << ((dtc_number >> 16) & 0xFF) << std::setfill('0') << std::setw(2)
        << ((dtc_number >>  8) & 0xFF) << std::setw(2)
        <<  (dtc_number        & 0xFF);
    return oss.str();
}

// ─── UdsAdapter::Impl ─────────────────────────────────────────────────────────

struct UdsAdapter::Impl {
    std::shared_ptr<CanAdapter> can_;
    IsoTpConfig                 cfg_;
    bool                        open_    = false;
    std::string                 version_ = "hw_adapter-UDS/1.0";

    BaseAdapter::Stats          stats_   = {};
    mutable std::mutex          stats_mutex_;

    // ─── ISO 15765-2 segmented send ───────────────────────────────────────────

    AdapterStatus isoTpSend(const Buffer& data) {
        if (data.size() <= 7) {
            // Single frame
            CanFrame f;
            f.id  = cfg_.tx_id;
            f.dlc = static_cast<uint8_t>(data.size() + 1);
            f.data[0] = static_cast<uint8_t>(data.size());  // PCI: SF, length
            std::copy_n(data.begin(), data.size(), f.data + 1);
            return can_->transmit(f, cfg_.timeout_ms);
        }

        // First frame
        size_t total = data.size();
        CanFrame ff;
        ff.id     = cfg_.tx_id;
        ff.dlc    = 8;
        ff.data[0] = static_cast<uint8_t>(0x10 | ((total >> 8) & 0x0F));
        ff.data[1] = static_cast<uint8_t>(total & 0xFF);
        std::copy_n(data.begin(), 6, ff.data + 2);
        auto s = can_->transmit(ff, cfg_.timeout_ms);
        if (s != AdapterStatus::OK) return s;

        // Wait for flow control
        auto fc = can_->receive(cfg_.timeout_ms);
        if (!fc || fc->data[0] != 0x30) return AdapterStatus::ERR_TIMEOUT;

        // Consecutive frames
        size_t offset  = 6;
        uint8_t sn     = 1;
        while (offset < total) {
            CanFrame cf;
            cf.id     = cfg_.tx_id;
            size_t chunk = std::min(size_t(7), total - offset);
            cf.dlc    = static_cast<uint8_t>(chunk + 1);
            cf.data[0] = static_cast<uint8_t>(0x20 | (sn & 0x0F));
            std::copy_n(data.begin() + offset, chunk, cf.data + 1);
            offset += chunk;
            ++sn;
            s = can_->transmit(cf, cfg_.timeout_ms);
            if (s != AdapterStatus::OK) return s;
            if (cfg_.st_min_ms > 0)
                std::this_thread::sleep_for(std::chrono::milliseconds(cfg_.st_min_ms));
        }
        return AdapterStatus::OK;
    }

    // ─── ISO 15765-2 receive ──────────────────────────────────────────────────

    std::optional<Buffer> isoTpReceive() {
        auto deadline = std::chrono::steady_clock::now()
                      + std::chrono::milliseconds(cfg_.timeout_ms);

        auto waitFrame = [&]() -> std::optional<CanFrame> {
            int remaining = static_cast<int>(
                std::chrono::duration_cast<std::chrono::milliseconds>(
                    deadline - std::chrono::steady_clock::now()).count());
            if (remaining <= 0) return std::nullopt;
            return can_->receive(remaining);
        };

        auto first = waitFrame();
        if (!first) return std::nullopt;

        // Filter for our response ID
        while (first && first->id != cfg_.rx_id)
            first = waitFrame();
        if (!first) return std::nullopt;

        uint8_t pci_type = (first->data[0] >> 4) & 0x0F;

        if (pci_type == 0) {
            // Single frame
            uint8_t len = first->data[0] & 0x0F;
            return Buffer(first->data + 1, first->data + 1 + len);
        }

        if (pci_type == 1) {
            // First frame of multi-frame
            size_t total = (static_cast<size_t>(first->data[0] & 0x0F) << 8)
                         |  first->data[1];
            Buffer result;
            result.reserve(total);
            result.insert(result.end(), first->data + 2, first->data + 8);

            // Send flow control
            CanFrame fc;
            fc.id = cfg_.tx_id;
            fc.dlc = 3;
            fc.data[0] = 0x30;  // ContinueToSend
            fc.data[1] = cfg_.block_size;
            fc.data[2] = cfg_.st_min_ms;
            can_->transmit(fc, 100);

            // Receive consecutive frames
            uint8_t expected_sn = 1;
            while (result.size() < total) {
                auto cf = waitFrame();
                if (!cf || cf->id != cfg_.rx_id) return std::nullopt;
                if ((cf->data[0] >> 4) != 2) return std::nullopt;
                if ((cf->data[0] & 0x0F) != (expected_sn & 0x0F)) return std::nullopt;
                size_t chunk = std::min(size_t(7), total - result.size());
                result.insert(result.end(), cf->data + 1, cf->data + 1 + chunk);
                ++expected_sn;
            }
            return result;
        }

        return std::nullopt;
    }

    // ─── Core send+receive ────────────────────────────────────────────────────

    UdsResponse sendRaw(const Buffer& req) {
        UdsResponse resp;
        auto t0 = std::chrono::steady_clock::now();

        can_->flushRxQueue();
        if (isoTpSend(req) != AdapterStatus::OK) {
            resp.positive = false;
            return resp;
        }

        // Handle 0x78 NRC (ResponsePending) — re-wait with extended timeout
        for (int attempt = 0; attempt < 10; ++attempt) {
            auto payload = isoTpReceive();
            if (!payload) break;

            if ((*payload)[0] == 0x7F) {
                // Negative response
                if ((*payload).size() >= 3 &&
                    static_cast<UdsNrc>((*payload)[2]) == UdsNrc::ResponsePending) {
                    // Extend timeout and retry
                    cfg_.timeout_ms = cfg_.timeout_ext_ms;
                    continue;
                }
                resp.positive  = false;
                resp.service_id = (*payload).size() > 1 ? (*payload)[1] : 0;
                resp.nrc        = (*payload).size() > 2
                                  ? static_cast<UdsNrc>((*payload)[2])
                                  : UdsNrc::ServiceNotSupported;
                break;
            } else {
                resp.positive   = true;
                resp.service_id = (*payload)[0];
                resp.payload    = Buffer(payload->begin() + 1, payload->end());
                break;
            }
        }

        auto t1 = std::chrono::steady_clock::now();
        resp.elapsed_us = std::chrono::duration_cast<std::chrono::microseconds>(t1 - t0).count();
        return resp;
    }
};

// ─── UdsAdapter public interface ──────────────────────────────────────────────

UdsAdapter::UdsAdapter(std::shared_ptr<CanAdapter> can)
    : impl_(std::make_unique<Impl>()) {
    impl_->can_ = std::move(can);
}
UdsAdapter::~UdsAdapter() = default;

AdapterStatus UdsAdapter::open(const std::string&) {
    if (!impl_->can_->isOpen()) return AdapterStatus::ERR_NOT_INIT;
    impl_->open_ = true;
    return AdapterStatus::OK;
}

AdapterStatus UdsAdapter::close() { impl_->open_ = false; return AdapterStatus::OK; }
bool          UdsAdapter::isOpen() const noexcept { return impl_->open_; }
std::string   UdsAdapter::version() const noexcept { return impl_->version_; }

void UdsAdapter::configure(const IsoTpConfig& cfg) { impl_->cfg_ = cfg; }
IsoTpConfig UdsAdapter::config() const noexcept { return impl_->cfg_; }

BaseAdapter::Stats UdsAdapter::stats() const noexcept {
    std::lock_guard<std::mutex> lk(impl_->stats_mutex_);
    return impl_->stats_;
}
void UdsAdapter::resetStats() noexcept {
    std::lock_guard<std::mutex> lk(impl_->stats_mutex_);
    impl_->stats_ = {};
}

UdsResponse UdsAdapter::send(const Buffer& request) {
    requireOpen();
    auto r = impl_->sendRaw(request);
    {
        std::lock_guard<std::mutex> lk(impl_->stats_mutex_);
        impl_->stats_.tx_count++;
        if (r.positive) impl_->stats_.rx_count++;
        else             impl_->stats_.error_count++;
    }
    return r;
}

UdsResponse UdsAdapter::openSession(UdsSession session) {
    return send({static_cast<Byte>(UdsService::DiagnosticSessionControl),
                 static_cast<Byte>(session)});
}

UdsResponse UdsAdapter::testerPresent(bool suppress) {
    return send({static_cast<Byte>(UdsService::DiagnosticSessionControl),
                 suppress ? Byte(0x80) : Byte(0x00)});
}

UdsResponse UdsAdapter::ecuReset(uint8_t reset_type) {
    return send({static_cast<Byte>(UdsService::ECUReset), reset_type});
}

UdsResponse UdsAdapter::readDataByIdentifier(uint16_t did) {
    return send({static_cast<Byte>(UdsService::ReadDataByIdentifier),
                 static_cast<Byte>((did >> 8) & 0xFF),
                 static_cast<Byte>(did & 0xFF)});
}

UdsResponse UdsAdapter::writeDataByIdentifier(uint16_t did, const Buffer& data) {
    Buffer req = {static_cast<Byte>(UdsService::WriteDataByIdentifier),
                  static_cast<Byte>((did >> 8) & 0xFF),
                  static_cast<Byte>(did & 0xFF)};
    req.insert(req.end(), data.begin(), data.end());
    return send(req);
}

UdsResponse UdsAdapter::clearDTCs(uint32_t group) {
    return send({static_cast<Byte>(UdsService::ClearDiagnosticInfo),
                 static_cast<Byte>((group >> 16) & 0xFF),
                 static_cast<Byte>((group >>  8) & 0xFF),
                 static_cast<Byte>( group        & 0xFF)});
}

std::vector<DtcRecord> UdsAdapter::readDTCs(uint8_t status_mask) {
    auto resp = send({static_cast<Byte>(UdsService::ReadDTCInformation),
                      0x02, status_mask});
    std::vector<DtcRecord> result;
    if (!resp.positive || resp.payload.size() < 1) return result;
    // Response: [status_availability_mask, DTC_hi, DTC_mid, DTC_lo, status, ...]
    size_t i = 1;
    while (i + 3 < resp.payload.size()) {
        DtcRecord r;
        r.dtc_number  = (static_cast<uint32_t>(resp.payload[i])     << 16)
                      | (static_cast<uint32_t>(resp.payload[i + 1]) <<  8)
                      |  static_cast<uint32_t>(resp.payload[i + 2]);
        r.status_byte = resp.payload[i + 3];
        result.push_back(r);
        i += 4;
    }
    return result;
}

UdsResponse UdsAdapter::startRoutine(uint16_t rid, const Buffer& params) {
    Buffer req = {static_cast<Byte>(UdsService::RoutineControl), 0x01,
                  static_cast<Byte>((rid >> 8) & 0xFF),
                  static_cast<Byte>(rid & 0xFF)};
    req.insert(req.end(), params.begin(), params.end());
    return send(req);
}

UdsResponse UdsAdapter::stopRoutine(uint16_t rid) {
    return send({static_cast<Byte>(UdsService::RoutineControl), 0x02,
                 static_cast<Byte>((rid >> 8) & 0xFF),
                 static_cast<Byte>(rid & 0xFF)});
}

UdsResponse UdsAdapter::requestRoutineResults(uint16_t rid) {
    return send({static_cast<Byte>(UdsService::RoutineControl), 0x03,
                 static_cast<Byte>((rid >> 8) & 0xFF),
                 static_cast<Byte>(rid & 0xFF)});
}

UdsResponse UdsAdapter::securityAccess(uint8_t level,
                                        std::function<Buffer(const Buffer&)> seed_to_key) {
    // Request seed
    auto seed_resp = send({static_cast<Byte>(UdsService::SecurityAccess), level});
    if (!seed_resp.positive) return seed_resp;

    Buffer seed(seed_resp.payload.begin(), seed_resp.payload.end());
    Buffer key = seed_to_key(seed);

    // Send key
    Buffer req = {static_cast<Byte>(UdsService::SecurityAccess),
                  static_cast<Byte>(level + 1)};
    req.insert(req.end(), key.begin(), key.end());
    return send(req);
}

UdsResponse UdsAdapter::inputOutputControl(uint16_t did, uint8_t ctrl, const Buffer& data) {
    Buffer req = {static_cast<Byte>(UdsService::InputOutputControlByID),
                  static_cast<Byte>((did >> 8) & 0xFF),
                  static_cast<Byte>(did & 0xFF), ctrl};
    req.insert(req.end(), data.begin(), data.end());
    return send(req);
}

UdsResponse UdsAdapter::readMemoryByAddress(uint32_t address, uint8_t length) {
    return send({static_cast<Byte>(UdsService::ReadMemoryByAddress),
                 0x14,  // addressAndLengthFormatIdentifier: 1 byte length, 4 byte address
                 static_cast<Byte>((address >> 24) & 0xFF),
                 static_cast<Byte>((address >> 16) & 0xFF),
                 static_cast<Byte>((address >>  8) & 0xFF),
                 static_cast<Byte>( address        & 0xFF),
                 length});
}

} // namespace hw_adapter
