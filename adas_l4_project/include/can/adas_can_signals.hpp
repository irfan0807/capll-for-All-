#pragma once
// ============================================================================
// adas_can_signals.hpp  –  CAN message IDs and signal encoding for ADAS ECU
// ============================================================================
#include <cstdint>

namespace adas {
namespace can_signals {

// ---------------------------------------------------------------------------
// CAN Message IDs
// ---------------------------------------------------------------------------
static constexpr uint32_t MSG_ID_OBJECT_LIST_1   = 0x300U;  ///< 8 bytes, 10Hz
static constexpr uint32_t MSG_ID_OBJECT_LIST_2   = 0x301U;  ///< 8 bytes, 10Hz
static constexpr uint32_t MSG_ID_LANE_INFO        = 0x310U;  ///< 8 bytes, 10Hz
static constexpr uint32_t MSG_ID_EGO_STATE        = 0x320U;  ///< 8 bytes, 10Hz
static constexpr uint32_t MSG_ID_PATH_INFO        = 0x330U;  ///< 8 bytes, 10Hz
static constexpr uint32_t MSG_ID_VEHICLE_CMD      = 0x340U;  ///< 8 bytes, 10Hz
static constexpr uint32_t MSG_ID_SAFETY_STATUS    = 0x350U;  ///< 8 bytes, 10Hz
static constexpr uint32_t MSG_ID_SENSOR_STATUS    = 0x360U;  ///< 4 bytes, 1Hz
static constexpr uint32_t MSG_ID_UDS_REQ          = 0x7E2U;  ///< diagnostic request
static constexpr uint32_t MSG_ID_UDS_RESP         = 0x7EAU;  ///< diagnostic response

// ---------------------------------------------------------------------------
// Object List (0x300) – one object per message (priority: closest TTC)
// Byte  0:   Object ID
// Byte  1:   Class (4 LSB) | Confidence/16 (4 MSB)
// Bytes 2-3: Range      (uint16, 0.1m, 0-6553.5m)
// Bytes 4-5: Azimuth    (int16,  0.01 deg, -327.68 to +327.67 deg)
// Bytes 6-7: RelVelocity(int16,  0.01 m/s, -327.68 to +327.67 m/s)
// ---------------------------------------------------------------------------

inline uint8_t encodeObjId(uint8_t id)        { return id; }
inline uint8_t encodeObjClass(uint8_t cls, uint8_t conf16)
    { return static_cast<uint8_t>((cls & 0x0FU) | ((conf16 & 0x0FU) << 4)); }
inline uint16_t encodeRange   (float r_m)   { return static_cast<uint16_t>(r_m / 0.1f); }
inline int16_t  encodeAzimuth (float a_deg) { return static_cast<int16_t> (a_deg / 0.01f); }
inline int16_t  encodeRelVel  (float v_mps) { return static_cast<int16_t> (v_mps / 0.01f); }

// ---------------------------------------------------------------------------
// Lane Info (0x310)
// Byte 0:   Lane width   (uint8, 0.04m offset, 0-10.16m)
// Byte 1:   Lateral offset (int8, 0.02m, -2.54 to +2.54m)
// Byte 2:   Lane quality (0-100)
// Byte 3:   Flags: bit0=LKA_active, bit1=left_valid, bit2=right_valid, bit3=LDW_warning
// ---------------------------------------------------------------------------
inline uint8_t encodeLaneWidth  (float w_m)   { return static_cast<uint8_t>(w_m / 0.04f); }
inline int8_t  encodeLaneLateral(float lat_m) { return static_cast<int8_t> (lat_m / 0.02f); }

// ---------------------------------------------------------------------------
// Vehicle Cmd (0x340)
// Bytes 0-1: Target speed (uint16, 0.1 km/h)
// Bytes 2-3: Steering angle (int16, 0.1 deg)
// Byte  4:   Throttle % (0-100)
// Byte  5:   Brake % (0-100)
// Byte  6:   Gear (1=D, 2=N, 3=R, 4=P)
// Byte  7:   Ctrl mode (0=manual, 1=ACC, 2=L4)
// ---------------------------------------------------------------------------
inline uint16_t encodeTargetSpeed   (float kmh)      { return static_cast<uint16_t>(kmh / 0.1f); }
inline int16_t  encodeSteeringAngle (float deg)      { return static_cast<int16_t> (deg / 0.1f); }

// ---------------------------------------------------------------------------
// Safety Status (0x350)
// Byte 0: SystemState (AdasSystemState)
// Byte 1: Fault bitmask (byte 0)
// Byte 2: AEB active (1 bit) | EmergencyStop (1 bit) | ODD valid (1 bit)
// Byte 3: MinTTC (uint8, 0.1s, max 25.5s = 0xFF)
// ---------------------------------------------------------------------------
inline uint8_t encodeMinTTC(float ttc_s)
    { return (ttc_s > 25.4f) ? 0xFFU : static_cast<uint8_t>(ttc_s / 0.1f); }

} // namespace can_signals
} // namespace adas
