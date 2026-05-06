/**
 * bindings.cpp
 * pybind11 bindings — exposes hw_adapter C++ classes to Python.
 *
 * Build:
 *   cmake .. -DBUILD_PYTHON_BINDINGS=ON
 *   make -j$(nproc)
 *
 * Python usage:
 *   import hw_adapter_cpp as hw
 *   can = hw.CanAdapter()
 *   can.open("vcan0")
 *   can.transmit(hw.CanFrame.make(0x300, [0xAA, 0xBB, 0xCC]))
 */

#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl.h>
#include <pybind11/chrono.h>

#include "hw_adapter/can_adapter.hpp"
#include "hw_adapter/uds_adapter.hpp"
#include "utils/signal_filter.hpp"

namespace py = pybind11;
using namespace hw_adapter;

// ─── Helpers ──────────────────────────────────────────────────────────────────

static Buffer pyBytesToBuffer(const py::bytes& b) {
    std::string s = b;
    return Buffer(s.begin(), s.end());
}

static py::bytes bufferToPyBytes(const Buffer& buf) {
    return py::bytes(reinterpret_cast<const char*>(buf.data()), buf.size());
}

// ─── Module definition ────────────────────────────────────────────────────────

PYBIND11_MODULE(hw_adapter_cpp, m) {
    m.doc() = "Hardware adapter C++ extension — CAN, UDS, and signal processing.";

    // ─── AdapterStatus enum ───────────────────────────────────────────────────
    py::enum_<AdapterStatus>(m, "AdapterStatus")
        .value("OK",               AdapterStatus::OK)
        .value("ERR_NOT_INIT",     AdapterStatus::ERR_NOT_INIT)
        .value("ERR_TIMEOUT",      AdapterStatus::ERR_TIMEOUT)
        .value("ERR_BUS_ERROR",    AdapterStatus::ERR_BUS_ERROR)
        .value("ERR_INVALID_ARG",  AdapterStatus::ERR_INVALID_ARG)
        .value("ERR_OVERFLOW",     AdapterStatus::ERR_OVERFLOW)
        .value("ERR_NACK",         AdapterStatus::ERR_NACK)
        .value("ERR_DISCONNECTED", AdapterStatus::ERR_DISCONNECTED)
        .export_values();

    // ─── AdapterException ─────────────────────────────────────────────────────
    py::register_exception<AdapterException>(m, "AdapterException");

    // ─── CanBitrate ───────────────────────────────────────────────────────────
    py::enum_<CanBitrate>(m, "CanBitrate")
        .value("kbps_125", CanBitrate::kbps_125)
        .value("kbps_250", CanBitrate::kbps_250)
        .value("kbps_500", CanBitrate::kbps_500)
        .value("Mbps_1",   CanBitrate::Mbps_1)
        .export_values();

    // ─── CanFilter ────────────────────────────────────────────────────────────
    py::class_<CanFilter>(m, "CanFilter")
        .def(py::init<>())
        .def_readwrite("id",       &CanFilter::id)
        .def_readwrite("mask",     &CanFilter::mask)
        .def_readwrite("extended", &CanFilter::extended)
        .def_static("accept_all", &CanFilter::acceptAll)
        .def_static("exact_id",   &CanFilter::exactId,
                    py::arg("id"), py::arg("extended") = false)
        .def("__repr__", [](const CanFilter& f){
            return "<CanFilter id=0x" + std::to_string(f.id) + ">";
        });

    // ─── CanFrame ─────────────────────────────────────────────────────────────
    py::class_<CanFrame>(m, "CanFrame")
        .def(py::init<>())
        .def_readwrite("id",           &CanFrame::id)
        .def_readwrite("is_extended",  &CanFrame::is_extended)
        .def_readwrite("is_remote",    &CanFrame::is_remote)
        .def_readwrite("is_error",     &CanFrame::is_error)
        .def_readwrite("dlc",          &CanFrame::dlc)
        .def_readwrite("timestamp_us", &CanFrame::timestamp_us)
        .def_static("make", [](uint32_t id, py::list data, bool extended){
            std::initializer_list<Byte> init;
            std::vector<Byte> vec;
            for (auto& item : data) vec.push_back(item.cast<Byte>());
            CanFrame f;
            f.id          = id;
            f.is_extended = extended;
            f.dlc         = static_cast<uint8_t>(std::min(vec.size(), size_t(8)));
            std::copy_n(vec.begin(), f.dlc, f.data);
            return f;
        }, py::arg("id"), py::arg("data"), py::arg("extended") = false)
        .def("to_bytes", [](const CanFrame& f){
            return py::bytes(reinterpret_cast<const char*>(f.data), f.dlc);
        })
        .def("__repr__", [](const CanFrame& f){
            std::ostringstream oss;
            oss << "<CanFrame id=0x" << std::hex << f.id << " dlc=" << (int)f.dlc << " data=[";
            for (int i = 0; i < f.dlc; ++i) {
                if (i) oss << ", ";
                oss << "0x" << std::hex << (int)f.data[i];
            }
            oss << "]>";
            return oss.str();
        });

    // ─── BaseAdapter::Stats ───────────────────────────────────────────────────
    py::class_<BaseAdapter::Stats>(m, "AdapterStats")
        .def_readwrite("tx_count",      &BaseAdapter::Stats::tx_count)
        .def_readwrite("rx_count",      &BaseAdapter::Stats::rx_count)
        .def_readwrite("error_count",   &BaseAdapter::Stats::error_count)
        .def_readwrite("timeout_count", &BaseAdapter::Stats::timeout_count);

    // ─── CanAdapter::BusLoad ──────────────────────────────────────────────────
    py::class_<CanAdapter::BusLoad>(m, "BusLoad")
        .def_readwrite("percent",      &CanAdapter::BusLoad::percent)
        .def_readwrite("error_count",  &CanAdapter::BusLoad::error_count)
        .def_readwrite("tec",          &CanAdapter::BusLoad::tec)
        .def_readwrite("rec",          &CanAdapter::BusLoad::rec);

    // ─── CanAdapter ───────────────────────────────────────────────────────────
    py::class_<CanAdapter, std::shared_ptr<CanAdapter>>(m, "CanAdapter")
        .def(py::init<>())
        .def("open",     &CanAdapter::open,    py::arg("device_uri"),
             "Open the CAN adapter (e.g., 'vcan0' for SocketCAN).")
        .def("close",    &CanAdapter::close,   "Close and release the adapter.")
        .def("is_open",  &CanAdapter::isOpen,  "Returns True if the adapter is open.")
        .def("name",     &CanAdapter::name)
        .def("version",  &CanAdapter::version)
        .def("set_bitrate", &CanAdapter::setBitrate, py::arg("bitrate"))
        .def("set_filter",  &CanAdapter::setFilter,  py::arg("filter"))
        .def("transmit", [](CanAdapter& self, const CanFrame& f, int timeout_ms){
                return self.transmit(f, timeout_ms);
             }, py::arg("frame"), py::arg("timeout_ms") = 100,
             "Transmit a single CAN frame.")
        .def("transmit_burst", [](CanAdapter& self, const std::vector<CanFrame>& frames, int t){
                return self.transmitBurst(frames, t);
             }, py::arg("frames"), py::arg("timeout_ms") = 500)
        .def("receive", [](CanAdapter& self, int timeout_ms) -> py::object {
                auto f = self.receive(timeout_ms);
                if (!f) return py::none();
                return py::cast(*f);
             }, py::arg("timeout_ms") = 1000,
             "Blocking receive — returns CanFrame or None on timeout.")
        .def("on_receive", [](CanAdapter& self, py::function cb){
                self.onReceive([cb](const CanFrame& f){
                    py::gil_scoped_acquire acquire;
                    cb(f);
                });
             }, py::arg("callback"),
             "Register a Python callback for incoming frames (called from RX thread).")
        .def("flush_rx_queue", &CanAdapter::flushRxQueue)
        .def("bus_load",       &CanAdapter::busLoad)
        .def("stats",          &CanAdapter::stats)
        .def("reset_stats",    &CanAdapter::resetStats)
        // Context manager
        .def("__enter__", [](CanAdapter& self) -> CanAdapter& { return self; })
        .def("__exit__",  [](CanAdapter& self, py::object, py::object, py::object){
                self.close();
             });

    // ─── UDS types ────────────────────────────────────────────────────────────
    py::enum_<UdsSession>(m, "UdsSession")
        .value("Default",     UdsSession::Default)
        .value("Programming", UdsSession::Programming)
        .value("Extended",    UdsSession::Extended)
        .export_values();

    py::enum_<UdsNrc>(m, "UdsNrc")
        .value("ServiceNotSupported",         UdsNrc::ServiceNotSupported)
        .value("ConditionsNotCorrect",        UdsNrc::ConditionsNotCorrect)
        .value("SecurityAccessDenied",        UdsNrc::SecurityAccessDenied)
        .value("InvalidKey",                  UdsNrc::InvalidKey)
        .value("ResponsePending",             UdsNrc::ResponsePending)
        .value("ServiceNotSupportedInSession",UdsNrc::ServiceNotSupportedInSession)
        .export_values();

    py::class_<DtcRecord>(m, "DtcRecord")
        .def_readwrite("dtc_number",  &DtcRecord::dtc_number)
        .def_readwrite("status_byte", &DtcRecord::status_byte)
        .def("confirmed",  &DtcRecord::confirmed)
        .def("pending",    &DtcRecord::pending)
        .def("test_failed",&DtcRecord::testFailed)
        .def("hex",        &DtcRecord::hex)
        .def("__repr__", [](const DtcRecord& r){
            return "<DtcRecord " + r.hex() + " status=0x"
                 + std::to_string(r.status_byte) + ">";
        });

    py::class_<UdsResponse>(m, "UdsResponse")
        .def_readwrite("positive",    &UdsResponse::positive)
        .def_readwrite("service_id",  &UdsResponse::service_id)
        .def_readwrite("elapsed_us",  &UdsResponse::elapsed_us)
        .def("payload", [](const UdsResponse& r){ return bufferToPyBytes(r.payload); })
        .def("ok",      &UdsResponse::ok)
        .def("u8_at",   &UdsResponse::u8At,  py::arg("offset"))
        .def("u16_at",  &UdsResponse::u16At, py::arg("offset"))
        .def("__repr__", [](const UdsResponse& r){
            return std::string("<UdsResponse ") + (r.positive ? "POSITIVE" : "NEGATIVE") + ">";
        });

    py::class_<IsoTpConfig>(m, "IsoTpConfig")
        .def(py::init<>())
        .def_readwrite("tx_id",          &IsoTpConfig::tx_id)
        .def_readwrite("rx_id",          &IsoTpConfig::rx_id)
        .def_readwrite("extended_ids",   &IsoTpConfig::extended_ids)
        .def_readwrite("block_size",     &IsoTpConfig::block_size)
        .def_readwrite("st_min_ms",      &IsoTpConfig::st_min_ms)
        .def_readwrite("timeout_ms",     &IsoTpConfig::timeout_ms)
        .def_readwrite("timeout_ext_ms", &IsoTpConfig::timeout_ext_ms);

    // ─── UdsAdapter ───────────────────────────────────────────────────────────
    py::class_<UdsAdapter>(m, "UdsAdapter")
        .def(py::init<std::shared_ptr<CanAdapter>>(), py::arg("can_adapter"))
        .def("open",      &UdsAdapter::open,    py::arg("device_uri") = "")
        .def("close",     &UdsAdapter::close)
        .def("is_open",   &UdsAdapter::isOpen)
        .def("configure", &UdsAdapter::configure, py::arg("config"))
        .def("open_session",    &UdsAdapter::openSession,
             py::arg("session") = UdsSession::Extended)
        .def("tester_present",  &UdsAdapter::testerPresent,
             py::arg("suppress") = true)
        .def("ecu_reset",       &UdsAdapter::ecuReset,
             py::arg("reset_type") = 0x01)
        .def("read_did",        &UdsAdapter::readDataByIdentifier, py::arg("did"))
        .def("write_did", [](UdsAdapter& self, uint16_t did, py::bytes data){
                return self.writeDataByIdentifier(did, pyBytesToBuffer(data));
             }, py::arg("did"), py::arg("data"))
        .def("read_dtcs",       &UdsAdapter::readDTCs,
             py::arg("status_mask") = 0x0F)
        .def("clear_dtcs",      &UdsAdapter::clearDTCs,
             py::arg("group") = 0xFFFFFF)
        .def("security_access", [](UdsAdapter& self, uint8_t level, py::function fn){
                return self.securityAccess(level, [fn](const Buffer& seed) -> Buffer {
                    py::gil_scoped_acquire acquire;
                    py::bytes py_seed(reinterpret_cast<const char*>(seed.data()), seed.size());
                    py::bytes key = fn(py_seed);
                    return pyBytesToBuffer(key);
                });
             }, py::arg("level"), py::arg("seed_to_key_fn"))
        .def("io_control", [](UdsAdapter& self, uint16_t did, uint8_t ctrl, py::bytes data){
                return self.inputOutputControl(did, ctrl, pyBytesToBuffer(data));
             }, py::arg("did"), py::arg("control_param"), py::arg("data") = py::bytes())
        .def("start_routine",   [](UdsAdapter& self, uint16_t rid, py::bytes p){
                return self.startRoutine(rid, pyBytesToBuffer(p));
             }, py::arg("routine_id"), py::arg("params") = py::bytes())
        .def("stop_routine",    &UdsAdapter::stopRoutine, py::arg("routine_id"))
        .def("send_raw", [](UdsAdapter& self, py::bytes req){
                return self.send(pyBytesToBuffer(req));
             }, py::arg("request"))
        .def("stats",        &UdsAdapter::stats)
        .def("reset_stats",  &UdsAdapter::resetStats)
        .def("__enter__", [](UdsAdapter& s) -> UdsAdapter& { return s; })
        .def("__exit__",  [](UdsAdapter& s, py::object, py::object, py::object){ s.close(); });

    // ─── Signal filters ───────────────────────────────────────────────────────
    py::class_<ExponentialMovingAverage<double>>(m, "EMA")
        .def(py::init<double>(), py::arg("alpha") = 0.1,
             "Exponential Moving Average filter. alpha=1.0 = pass-through.")
        .def("update",    &ExponentialMovingAverage<double>::update, py::arg("sample"))
        .def("value",     &ExponentialMovingAverage<double>::value)
        .def("reset",     &ExponentialMovingAverage<double>::reset)
        .def("set_alpha", &ExponentialMovingAverage<double>::setAlpha, py::arg("alpha"));

    py::class_<MedianFilter<double, 5>>(m, "MedianFilter5")
        .def(py::init<>(), "5-sample sliding median filter.")
        .def("update", &MedianFilter<double, 5>::update, py::arg("sample"))
        .def("median", &MedianFilter<double, 5>::median)
        .def("reset",  &MedianFilter<double, 5>::reset);

    py::class_<RateOfChangeGuard<double>>(m, "RateOfChangeGuard")
        .def(py::init<double>(), py::arg("max_delta_per_step"))
        .def("update",      &RateOfChangeGuard<double>::update, py::arg("sample"))
        .def("was_limited", &RateOfChangeGuard<double>::wasLimited)
        .def("value",       &RateOfChangeGuard<double>::value)
        .def("reset",       &RateOfChangeGuard<double>::reset);
}
