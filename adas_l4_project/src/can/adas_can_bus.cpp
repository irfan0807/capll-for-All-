// ============================================================================
// adas_can_bus.cpp  –  CAN Tx/Rx for ADAS ECU
// ============================================================================
#include "../../include/can/adas_can_bus.hpp"
#include <cstring>
#include <cmath>

using namespace adas::can_signals;

namespace adas {
namespace can_bus {

AdasCanBus::AdasCanBus()
    : m_txFn(nullptr), m_txCount(0), m_rxCount(0)
{
    memset(&m_lastRx, 0, sizeof(m_lastRx));
}

void AdasCanBus::injectRx(const CanFrame& frame) {
    m_lastRx = frame;
    m_rxCount++;
}

void AdasCanBus::sendFrame(const CanFrame& frame) {
    if (m_txFn) m_txFn(frame);
    m_txCount++;
}

// ---------------------------------------------------------------------------
void AdasCanBus::txObjectList(const perception::TrackedObject& obj) {
    CanFrame f;
    f.id  = MSG_ID_OBJECT_LIST_1;
    f.dlc = 8;

    f.data[0] = encodeObjId(obj.id);
    uint8_t conf16 = static_cast<uint8_t>(obj.confidence * 15.0f);
    f.data[1] = encodeObjClass(static_cast<uint8_t>(obj.object_class), conf16);

    uint16_t range = encodeRange(sqrtf(obj.x_m * obj.x_m + obj.y_m * obj.y_m));
    f.data[2] = static_cast<uint8_t>(range >> 8);
    f.data[3] = static_cast<uint8_t>(range & 0xFF);

    float azimuth_deg = atan2f(obj.y_m, obj.x_m) * 180.0f / 3.14159265f;
    int16_t az = encodeAzimuth(azimuth_deg);
    f.data[4] = static_cast<uint8_t>(static_cast<uint16_t>(az) >> 8);
    f.data[5] = static_cast<uint8_t>(static_cast<uint16_t>(az) & 0xFF);

    int16_t rv = encodeRelVel(obj.vx_mps);
    f.data[6] = static_cast<uint8_t>(static_cast<uint16_t>(rv) >> 8);
    f.data[7] = static_cast<uint8_t>(static_cast<uint16_t>(rv) & 0xFF);

    sendFrame(f);
}

void AdasCanBus::txLaneInfo(const perception::LaneEstimate& lane) {
    CanFrame f;
    f.id  = MSG_ID_LANE_INFO;
    f.dlc = 8;
    f.data[0] = encodeLaneWidth(lane.lane_width_m);
    f.data[1] = static_cast<uint8_t>(encodeLaneLateral(lane.lateral_offset_m));
    f.data[2] = lane.quality;
    uint8_t flags = 0;
    if (lane.left_marking_valid)  flags |= 0x02U;
    if (lane.right_marking_valid) flags |= 0x04U;
    f.data[3] = flags;
    for (uint8_t i = 4; i < 8; i++) f.data[i] = 0;
    sendFrame(f);
}

void AdasCanBus::txVehicleCmd(const control::ActuatorCommands& cmds) {
    CanFrame f;
    f.id  = MSG_ID_VEHICLE_CMD;
    f.dlc = 8;
    uint16_t spd = encodeTargetSpeed(0.0f);   // placeholder
    f.data[0] = static_cast<uint8_t>(spd >> 8);
    f.data[1] = static_cast<uint8_t>(spd & 0xFF);
    int16_t steer = encodeSteeringAngle(cmds.steering_deg);
    f.data[2] = static_cast<uint8_t>(static_cast<uint16_t>(steer) >> 8);
    f.data[3] = static_cast<uint8_t>(static_cast<uint16_t>(steer) & 0xFF);
    f.data[4] = static_cast<uint8_t>(cmds.throttle_pct);
    f.data[5] = static_cast<uint8_t>(cmds.brake_pct);
    f.data[6] = cmds.gear;
    f.data[7] = 2U;  // L4 control mode
    sendFrame(f);
}

void AdasCanBus::txSafetyStatus(const safety::FaultFlags& faults,
                                  safety::AdasSystemState state,
                                  float min_ttc_s, bool aeb_active,
                                  bool odd_valid) {
    CanFrame f;
    f.id  = MSG_ID_SAFETY_STATUS;
    f.dlc = 8;
    f.data[0] = static_cast<uint8_t>(state);
    // Fault bitmask
    uint8_t faultByte = 0;
    if (faults.lidar_failed)    faultByte |= 0x01U;
    if (faults.camera_failed)   faultByte |= 0x02U;
    if (faults.radar_failed)    faultByte |= 0x04U;
    if (faults.fusion_timeout)  faultByte |= 0x08U;
    if (faults.planning_timeout)faultByte |= 0x10U;
    f.data[1] = faultByte;
    uint8_t flags2 = 0;
    if (aeb_active) flags2 |= 0x01U;
    if (odd_valid)  flags2 |= 0x04U;
    f.data[2] = flags2;
    f.data[3] = encodeMinTTC(min_ttc_s);
    for (uint8_t i = 4; i < 8; i++) f.data[i] = 0;
    sendFrame(f);
}

void AdasCanBus::txEgoState(float speed_mps, float yaw_rad) {
    CanFrame f;
    f.id  = MSG_ID_EGO_STATE;
    f.dlc = 8;
    uint16_t spd_raw = static_cast<uint16_t>(speed_mps * 10.0f);
    f.data[0] = static_cast<uint8_t>(spd_raw >> 8);
    f.data[1] = static_cast<uint8_t>(spd_raw & 0xFF);
    int16_t yaw_raw = static_cast<int16_t>(yaw_rad * 1000.0f);
    f.data[2] = static_cast<uint8_t>(static_cast<uint16_t>(yaw_raw) >> 8);
    f.data[3] = static_cast<uint8_t>(static_cast<uint16_t>(yaw_raw) & 0xFF);
    for (uint8_t i = 4; i < 8; i++) f.data[i] = 0;
    sendFrame(f);
}

void AdasCanBus::transmitAll(
        const perception::ObjectList&    objects,
        const perception::LaneEstimate&  lane,
        const control::ActuatorCommands& cmds,
        const safety::FaultFlags&        faults,
        safety::AdasSystemState          state,
        float ego_speed_mps, float ego_yaw_rad,
        float min_ttc_s, bool aeb_active, bool odd_valid) {

    // Transmit top priority object
    if (objects.count > 0) {
        txObjectList(objects.objects[0]);
    }
    txLaneInfo(lane);
    txVehicleCmd(cmds);
    txSafetyStatus(faults, state, min_ttc_s, aeb_active, odd_valid);
    txEgoState(ego_speed_mps, ego_yaw_rad);
}

} // namespace can_bus
} // namespace adas
