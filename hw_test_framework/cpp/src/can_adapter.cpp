/**
 * can_adapter.cpp
 * CAN adapter implementation using SocketCAN (Linux) or Vector XL-Driver (Windows).
 * Compile with -DUSE_SOCKETCAN (default) or -DUSE_VECTOR_XL.
 *
 * For HIL bench use, a mock/stub implementation is active when
 * neither backend is available (allows unit testing without hardware).
 */

#include "hw_adapter/can_adapter.hpp"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <deque>
#include <mutex>
#include <sstream>
#include <thread>

#ifdef USE_SOCKETCAN
#  include <fcntl.h>
#  include <net/if.h>
#  include <sys/ioctl.h>
#  include <sys/socket.h>
#  include <linux/can.h>
#  include <linux/can/raw.h>
#  include <unistd.h>
#endif

namespace hw_adapter {

// ─── CanFrame helpers ─────────────────────────────────────────────────────────

CanFrame CanFrame::make(DWord id, std::initializer_list<Byte> bytes, bool extended) {
    CanFrame f;
    f.id          = id;
    f.is_extended = extended;
    f.dlc         = static_cast<uint8_t>(std::min(bytes.size(), size_t(8)));
    std::copy_n(bytes.begin(), f.dlc, f.data);
    return f;
}

// ─── CanAdapter::Impl ─────────────────────────────────────────────────────────

struct CanAdapter::Impl {
    // ── state ────────────────────────────────────────────────────────────────
    std::atomic<bool>   open_    {false};
    std::string         device_uri_;
    std::string         version_  = "hw_adapter-CAN/1.0";
    CanBitrate          bitrate_  = CanBitrate::kbps_500;
    CanFilter           filter_   = CanFilter::acceptAll();

    // ── RX queue ─────────────────────────────────────────────────────────────
    std::deque<CanFrame>        rx_queue_;
    std::mutex                  rx_mutex_;
    std::condition_variable     rx_cv_;
    static constexpr size_t     RX_QUEUE_MAX = 1024;

    // ── async RX thread ───────────────────────────────────────────────────────
    std::thread              rx_thread_;
    std::atomic<bool>        rx_stop_ {false};
    CanReceiveCallback       rx_cb_;
    std::mutex               cb_mutex_;

    // ── stats ─────────────────────────────────────────────────────────────────
    std::atomic<uint64_t>   tx_count_      {0};
    std::atomic<uint64_t>   rx_count_      {0};
    std::atomic<uint64_t>   error_count_   {0};
    std::atomic<uint64_t>   timeout_count_ {0};

    // ── SocketCAN handle ─────────────────────────────────────────────────────
#ifdef USE_SOCKETCAN
    int sock_fd_ = -1;
#endif

    // ─── Frame matching against filter ────────────────────────────────────────
    bool matchesFilter(const CanFrame& f) const noexcept {
        return (f.id & filter_.mask) == (filter_.id & filter_.mask);
    }

    // ─── Push a received frame into the queue ─────────────────────────────────
    void pushRx(const CanFrame& f) {
        {
            std::lock_guard<std::mutex> lk(rx_mutex_);
            if (rx_queue_.size() >= RX_QUEUE_MAX) {
                rx_queue_.pop_front();  // drop oldest on overflow
                ++error_count_;
            }
            rx_queue_.push_back(f);
            ++rx_count_;
        }
        rx_cv_.notify_one();

        // Invoke async callback (if registered) outside the queue lock
        std::lock_guard<std::mutex> cb_lk(cb_mutex_);
        if (rx_cb_) rx_cb_(f);
    }

    // ─── SocketCAN open ───────────────────────────────────────────────────────
    AdapterStatus openSocketCan(const std::string& iface) {
#ifdef USE_SOCKETCAN
        sock_fd_ = ::socket(PF_CAN, SOCK_RAW, CAN_RAW);
        if (sock_fd_ < 0) return AdapterStatus::ERR_NOT_INIT;

        struct ifreq ifr;
        std::strncpy(ifr.ifr_name, iface.c_str(), IFNAMSIZ - 1);
        if (::ioctl(sock_fd_, SIOCGIFINDEX, &ifr) < 0) {
            ::close(sock_fd_);
            sock_fd_ = -1;
            return AdapterStatus::ERR_NOT_INIT;
        }

        // Apply hardware filter
        struct can_filter raw_filter[1];
        raw_filter[0].can_id   = filter_.id;
        raw_filter[0].can_mask = filter_.mask;
        ::setsockopt(sock_fd_, SOL_CAN_RAW, CAN_RAW_FILTER,
                     raw_filter, sizeof(raw_filter));

        struct sockaddr_can addr{};
        addr.can_family  = AF_CAN;
        addr.can_ifindex = ifr.ifr_ifindex;
        if (::bind(sock_fd_, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr)) < 0) {
            ::close(sock_fd_);
            sock_fd_ = -1;
            return AdapterStatus::ERR_NOT_INIT;
        }

        // Set non-blocking for the RX thread's poll loop
        int flags = ::fcntl(sock_fd_, F_GETFL, 0);
        ::fcntl(sock_fd_, F_SETFL, flags | O_NONBLOCK);
        return AdapterStatus::OK;
#else
        (void)iface;
        // Stub: succeed silently for environments without SocketCAN
        return AdapterStatus::OK;
#endif
    }

    // ─── RX thread body ───────────────────────────────────────────────────────
    void rxLoop() {
#ifdef USE_SOCKETCAN
        struct can_frame raw{};
        while (!rx_stop_.load(std::memory_order_relaxed)) {
            ssize_t n = ::read(sock_fd_, &raw, sizeof(raw));
            if (n < 0) {
                if (errno == EAGAIN) {
                    std::this_thread::sleep_for(std::chrono::microseconds(200));
                    continue;
                }
                ++error_count_;
                continue;
            }
            if (n < static_cast<ssize_t>(sizeof(struct can_frame))) continue;

            CanFrame f;
            f.is_extended  = (raw.can_id & CAN_EFF_FLAG) != 0;
            f.is_remote    = (raw.can_id & CAN_RTR_FLAG) != 0;
            f.is_error     = (raw.can_id & CAN_ERR_FLAG) != 0;
            f.id           = raw.can_id & (f.is_extended ? CAN_EFF_MASK : CAN_SFF_MASK);
            f.dlc          = raw.can_dlc;
            std::memcpy(f.data, raw.data, std::min(raw.can_dlc, uint8_t(8)));
            auto now = std::chrono::steady_clock::now().time_since_epoch();
            f.timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(now).count();

            if (matchesFilter(f)) pushRx(f);
        }
#else
        // Stub RX loop: nothing to do without hardware
        while (!rx_stop_.load(std::memory_order_relaxed))
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
#endif
    }
};

// ─── CanAdapter public interface ──────────────────────────────────────────────

CanAdapter::CanAdapter() : impl_(std::make_unique<Impl>()) {}
CanAdapter::~CanAdapter() { if (isOpen()) close(); }

AdapterStatus CanAdapter::open(const std::string& device_uri) {
    if (impl_->open_.load()) return AdapterStatus::ERR_NOT_INIT;
    impl_->device_uri_ = device_uri;

    AdapterStatus s = impl_->openSocketCan(device_uri);
    if (s != AdapterStatus::OK) return s;

    impl_->rx_stop_.store(false);
    impl_->rx_thread_ = std::thread([this]{ impl_->rxLoop(); });
    impl_->open_.store(true);
    return AdapterStatus::OK;
}

AdapterStatus CanAdapter::close() {
    if (!impl_->open_.load()) return AdapterStatus::OK;
    impl_->rx_stop_.store(true);
    impl_->rx_cv_.notify_all();
    if (impl_->rx_thread_.joinable()) impl_->rx_thread_.join();
#ifdef USE_SOCKETCAN
    if (impl_->sock_fd_ >= 0) { ::close(impl_->sock_fd_); impl_->sock_fd_ = -1; }
#endif
    impl_->open_.store(false);
    return AdapterStatus::OK;
}

bool CanAdapter::isOpen() const noexcept { return impl_->open_.load(); }

std::string CanAdapter::version() const noexcept { return impl_->version_; }

void CanAdapter::setBitrate(CanBitrate bitrate) noexcept { impl_->bitrate_ = bitrate; }

AdapterStatus CanAdapter::setFilter(const CanFilter& f) {
    impl_->filter_ = f;
    return AdapterStatus::OK;
}

AdapterStatus CanAdapter::transmit(const CanFrame& frame, int timeout_ms) {
    requireOpen();
#ifdef USE_SOCKETCAN
    struct can_frame raw{};
    raw.can_id  = frame.id;
    if (frame.is_extended) raw.can_id |= CAN_EFF_FLAG;
    if (frame.is_remote)   raw.can_id |= CAN_RTR_FLAG;
    raw.can_dlc = frame.dlc;
    std::memcpy(raw.data, frame.data, frame.dlc);

    ssize_t n = ::write(impl_->sock_fd_, &raw, sizeof(raw));
    if (n < 0) { ++impl_->error_count_; return AdapterStatus::ERR_BUS_ERROR; }
#endif
    ++impl_->tx_count_;
    (void)timeout_ms;
    return AdapterStatus::OK;
}

AdapterStatus CanAdapter::transmitBurst(const std::vector<CanFrame>& frames, int timeout_ms) {
    for (const auto& f : frames) {
        auto s = transmit(f, timeout_ms);
        if (s != AdapterStatus::OK) return s;
    }
    return AdapterStatus::OK;
}

std::optional<CanFrame> CanAdapter::receive(int timeout_ms) {
    requireOpen();
    std::unique_lock<std::mutex> lk(impl_->rx_mutex_);
    bool got = impl_->rx_cv_.wait_for(
        lk,
        std::chrono::milliseconds(timeout_ms),
        [this]{ return !impl_->rx_queue_.empty(); });

    if (!got) { ++impl_->timeout_count_; return std::nullopt; }
    auto f = impl_->rx_queue_.front();
    impl_->rx_queue_.pop_front();
    return f;
}

void CanAdapter::onReceive(CanReceiveCallback cb) {
    std::lock_guard<std::mutex> lk(impl_->cb_mutex_);
    impl_->rx_cb_ = std::move(cb);
}

void CanAdapter::flushRxQueue() {
    std::lock_guard<std::mutex> lk(impl_->rx_mutex_);
    impl_->rx_queue_.clear();
}

BaseAdapter::Stats CanAdapter::stats() const noexcept {
    return { impl_->tx_count_.load(), impl_->rx_count_.load(),
             impl_->error_count_.load(), impl_->timeout_count_.load() };
}

void CanAdapter::resetStats() noexcept {
    impl_->tx_count_.store(0); impl_->rx_count_.store(0);
    impl_->error_count_.store(0); impl_->timeout_count_.store(0);
}

CanAdapter::BusLoad CanAdapter::busLoad() const noexcept {
    // Real implementation would query the driver; stub returns zeroes.
    return {};
}

} // namespace hw_adapter
