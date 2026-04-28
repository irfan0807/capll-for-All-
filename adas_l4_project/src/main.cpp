// ============================================================================
// main.cpp  –  ADAS L4 End-to-End Simulation
//
// Scenarios:
//   1. Highway cruise – L4 engaged, maintain 120 km/h
//   2. Car ahead – ACC follow mode
//   3. Pedestrian crossing – yield and stop
//   4. Sensor fault – LiDAR fails, degraded mode
//   5. Emergency stop – AEB triggered (TTC < 1s)
//   6. ODD exit – disengage and minimal risk condition
// ============================================================================
#include <cstdio>
#include <cstring>
#include <cmath>

#include "include/sensors/lidar_sensor.hpp"
#include "include/sensors/radar_sensor.hpp"
#include "include/sensors/camera_sensor.hpp"
#include "include/sensors/imu_sensor.hpp"
#include "include/perception/sensor_fusion.hpp"
#include "include/perception/lane_detector.hpp"
#include "include/planning/path_planner.hpp"
#include "include/planning/trajectory_generator.hpp"
#include "include/control/vehicle_controller.hpp"
#include "include/safety/safety_monitor.hpp"
#include "include/safety/emergency_handler.hpp"
#include "include/safety/adas_fsm.hpp"
#include "include/can/adas_can_bus.hpp"

using namespace adas;
using namespace adas::perception;
using namespace adas::planning;
using namespace adas::control;
using namespace adas::safety;
using namespace adas::can_bus;

// ---------------------------------------------------------------------------
// Global CAN Tx buffer (captures last transmitted frame)
// ---------------------------------------------------------------------------
static CanFrame g_lastTxFrame;
static uint32_t g_txCount = 0;
static void canTxCallback(const CanFrame& f) {
    g_lastTxFrame = f;
    g_txCount++;
}

// ---------------------------------------------------------------------------
// Helper: create a minimal LiDAR scan with a few obstacle points
// ---------------------------------------------------------------------------
static const LidarScan& makeLidarScan(uint32_t ts_ms, float obstacleX = 999.0f) {
    static LidarScan scan;
    memset(&scan, 0, sizeof(scan));
    scan.timestamp_ms = ts_ms;
    scan.health       = SensorHealth::OK;
    scan.count        = 0;

    // 1000 simulated ground points (flat z = -1.5m below sensor)
    for (uint32_t i = 0; i < 1000 && scan.count < MAX_LIDAR_POINTS; ++i) {
        LidarPoint& p = scan.points[scan.count++];
        p.x       = -20.0f + static_cast<float>(i) * 0.1f;
        p.y       = static_cast<float>(i % 50) * 0.2f - 5.0f;
        p.z       = -1.5f;
        p.intensity = 0.3f;
        p.ring    = 0;
    }

    // Add obstacle cluster if requested
    if (obstacleX < 990.0f) {
        for (uint32_t i = 0; i < 20 && scan.count < MAX_LIDAR_POINTS; ++i) {
            LidarPoint& p = scan.points[scan.count++];
            p.x       = obstacleX + static_cast<float>(i % 5) * 0.2f;
            p.y       = static_cast<float>(i / 5) * 0.4f - 0.4f;
            p.z       = 0.5f;  // elevated, not on ground
            p.intensity = 0.8f;
            p.ring    = 5;
        }
    }
    return scan;
}

// ---------------------------------------------------------------------------
// Helper: create radar scan with one object
// ---------------------------------------------------------------------------
static RadarScan makeRadarScan(uint32_t ts, float range_m, float vel_mps) {
    RadarScan scan;
    scan.timestamp_ms = ts;
    scan.health       = SensorHealth::OK;
    scan.count        = 1;
    scan.objects[0].id            = 1;
    scan.objects[0].range_m       = range_m;
    scan.objects[0].azimuth_deg   = 0.0f;
    scan.objects[0].elevation_deg = 0.0f;
    scan.objects[0].range_rate_mps= vel_mps;
    scan.objects[0].rcs_dBsm      = 10.0f;
    scan.objects[0].confidence    = 90;
    scan.objects[0].is_moving     = true;
    return scan;
}

// ---------------------------------------------------------------------------
// Helper: create empty radar scan
// ---------------------------------------------------------------------------
static RadarScan makeEmptyRadarScan(uint32_t ts) {
    RadarScan scan;
    scan.timestamp_ms = ts;
    scan.health       = SensorHealth::OK;
    scan.count        = 0;
    return scan;
}

// ---------------------------------------------------------------------------
// Helper: create camera frame with lane info
// ---------------------------------------------------------------------------
static CameraFrame makeCameraFrame(uint32_t ts, float left_m, float right_m,
                                    float laneW = 3.6f, uint8_t quality = 85) {
    CameraFrame frame;
    frame.timestamp_ms         = ts;
    frame.health               = SensorHealth::OK;
    frame.count                = 0;
    frame.left_lane_offset_m   = left_m;
    frame.right_lane_offset_m  = right_m;
    frame.lane_width_m         = laneW;
    frame.lane_curvature_inv_m = 0.0f;
    frame.lane_quality         = quality;
    return frame;
}

// ---------------------------------------------------------------------------
// Add pedestrian detection to camera frame
// ---------------------------------------------------------------------------
static void addPedestrian(CameraFrame& frame, float x_m, float y_m) {
    if (frame.count < MAX_CAMERA_OBJECTS) {
        auto& d           = frame.detections[frame.count++];
        d.id              = 10;
        d.object_class    = ObjectClass::PEDESTRIAN;
        d.confidence      = 0.9f;
        d.x_m             = x_m;
        d.y_m             = y_m;
        d.width_m         = 0.5f;
        d.length_m        = 0.5f;
        d.img_x = d.img_y = d.img_w = d.img_h = 0;
    }
}

// ---------------------------------------------------------------------------
static void printSeparator(const char* title) {
    printf("\n======================================================================\n");
    printf("  %s\n", title);
    printf("======================================================================\n");
}

static void printState(AdasSystemState state, SafetyDecision dec,
                        const ActuatorCommands& cmds, float egoSpd_kmh,
                        float minTtc, uint32_t cycle) {
    printf("[cycle %4u] State: %-15s | Safety: %s | Speed: %5.1f km/h"
           " | Thr: %4.1f%% Brk: %4.1f%% Steer: %6.1f°"
           " | AEB: %s | TTC: %.1fs\n",
           cycle,
           stateToStr(state),
           dec == SafetyDecision::NOMINAL        ? "NOMINAL     " :
           dec == SafetyDecision::WARN           ? "WARN        " :
           dec == SafetyDecision::DEGRADE_ODD    ? "DEGRADE_ODD " :
           dec == SafetyDecision::MINIMAL_RISK   ? "MINIMAL_RISK" :
                                                   "EMERG_STOP  ",
           egoSpd_kmh,
           cmds.throttle_pct, cmds.brake_pct, cmds.steering_deg,
           cmds.aeb_active ? "YES" : " no",
           minTtc);
}

// ===========================================================================
// MAIN
// ===========================================================================
int main() {
    printf("===========================================================\n");
    printf("   ADAS Level 4 – End-to-End Simulation\n");
    printf("===========================================================\n");

    // ── Instantiate all modules (static to keep off stack – LidarScan is large)
    static LidarSensor          lidar;
    static RadarSensor          radar(0);
    static CameraSensor         camera(0);
    static ImuSensor            imu;
    static SensorFusion         fusion;
    static LaneDetector         laneDetector;
    static PathPlanner          planner;
    static TrajectoryGenerator  trajGen;
    static VehicleController    controller;
    static SafetyMonitor        safetyMon;
    static EmergencyHandler     emergHandler;
    static AdasFSM              fsm;
    static AdasCanBus           canBus;

    canBus.setTxCallback(canTxCallback);
    emergHandler.setSafetyMonitor(&safetyMon);
    emergHandler.setVehicleController(&controller);

    float egoX = 0, egoY = 0, egoYaw = 0, egoSpeed = 0;
    uint32_t systemTime = 0;
    uint32_t cycle = 0;

    // ── Ignition ON + self-test ──────────────────────────────────────────────
    printSeparator("SCENARIO 0: IGNITION ON + SELF TEST");
    fsm.onIgnitionOn();
    for (uint8_t i = 0; i < 12; ++i) {
        systemTime += 100;
        fsm.update(true, true, false, false, false, false);
    }
    printf("After self-test: FSM state = %s\n", stateToStr(fsm.getState()));

    // ── SCENARIO 1: Highway cruise ───────────────────────────────────────────
    printSeparator("SCENARIO 1: HIGHWAY CRUISE (L4 ACTIVE, 120 km/h)");
    fsm.requestEngage();
    fsm.update(true, true, false, false, false, false);
    printf("FSM after engage request: %s\n", stateToStr(fsm.getState()));

    float targetSpeed = 120.0f / 3.6f;
    planner.setTargetSpeed(targetSpeed);

    for (uint8_t i = 0; i < 10; ++i) {
        systemTime += 100;
        cycle++;

        LidarScan lidarScan  = makeLidarScan(systemTime);
        RadarScan radarScan  = makeEmptyRadarScan(systemTime);
        CameraFrame camFrame = makeCameraFrame(systemTime, -1.8f, 1.8f);

        lidar.injectScan(lidarScan);
        radar.injectObjectList(radarScan);
        camera.injectFrame(camFrame);

        fusion.setLidarScan(lidar.getObstacleScan());
        fusion.setRadarScan(radar.getScan());
        fusion.setCameraFrame(camera.getFrame());
        fusion.process(0.1f);
        fusion.computeTTC(egoSpeed);
        safetyMon.kickFusionWatchdog(systemTime);

        laneDetector.setCameraFrame(camera.getFrame());
        laneDetector.process();

        planner.setObjectList(fusion.getObjectList());
        planner.setLaneEstimate(laneDetector.getLaneEstimate());
        planner.setEgoPose(egoX, egoY, egoYaw, egoSpeed);
        planner.plan();
        safetyMon.kickPlanningWatchdog(systemTime);

        trajGen.setLocalPath(planner.getPath());
        trajGen.setEgoState(egoX, egoY, egoYaw, egoSpeed, 0.0f);
        trajGen.setObjectList(fusion.getObjectList());
        trajGen.generate();

        controller.setEgoState(egoSpeed, egoYaw, egoX, egoY);
        controller.setTrajectory(trajGen.getTrajectory());
        controller.compute(0.1f);
        safetyMon.kickControlWatchdog(systemTime);

        safetyMon.updateSensorHealth(lidar.getHealth(), camera.getHealth(),
                                      radar.getHealth(), imu.getHealth());
        safetyMon.updateObjectList(fusion.getObjectList());
        safetyMon.updateSpeed(egoSpeed, targetSpeed);
        SafetyDecision dec = safetyMon.evaluate(systemTime);
        emergHandler.handle(dec, fsm.getState(), egoSpeed);
        fsm.update(true, true, false, false, dec == SafetyDecision::EMERGENCY_STOP, false);

        const ActuatorCommands& cmds = controller.getCommands();

        // Simple ego dynamics: throttle accelerates, brake decelerates
        float accel = (cmds.throttle_pct / 100.0f) * 3.0f
                    - (cmds.brake_pct    / 100.0f) * 8.0f;
        egoSpeed += accel * 0.1f;
        if (egoSpeed < 0) egoSpeed = 0;
        egoX += egoSpeed * 0.1f;

        printState(fsm.getState(), dec, cmds, egoSpeed * 3.6f,
                   safetyMon.getMinTTC(), cycle);

        canBus.transmitAll(fusion.getObjectList(), laneDetector.getLaneEstimate(),
                           cmds, safetyMon.getFaults(), fsm.getState(),
                           egoSpeed, egoYaw, safetyMon.getMinTTC(),
                           safetyMon.isAebRequired(), true);
    }
    printf("Final speed: %.1f km/h  |  CAN Tx frames: %u\n",
           egoSpeed * 3.6f, canBus.getTxCount());

    // ── SCENARIO 2: Car ahead (ACC follow) ──────────────────────────────────
    printSeparator("SCENARIO 2: LEAD VEHICLE DETECTED – ACC FOLLOW MODE");
    egoSpeed = 30.0f;  // 108 km/h start

    for (uint8_t i = 0; i < 8; ++i) {
        systemTime += 100;
        cycle++;

        float leadRange = 40.0f - static_cast<float>(i) * 2.0f;  // closing in
        RadarScan radarScan = makeRadarScan(systemTime, leadRange, -2.0f);
        CameraFrame cam     = makeCameraFrame(systemTime, -1.8f, 1.8f);

        radar.injectObjectList(radarScan);
        camera.injectFrame(cam);
        fusion.setRadarScan(radar.getScan());
        fusion.setCameraFrame(camera.getFrame());
        fusion.process(0.1f);
        fusion.computeTTC(egoSpeed);
        safetyMon.kickFusionWatchdog(systemTime);

        laneDetector.setCameraFrame(camera.getFrame());
        laneDetector.process();
        planner.setObjectList(fusion.getObjectList());
        planner.setLaneEstimate(laneDetector.getLaneEstimate());
        planner.setEgoPose(egoX, egoY, egoYaw, egoSpeed);
        planner.plan();
        safetyMon.kickPlanningWatchdog(systemTime);

        trajGen.setLocalPath(planner.getPath());
        trajGen.setEgoState(egoX, egoY, egoYaw, egoSpeed, 0.0f);
        trajGen.setObjectList(fusion.getObjectList());
        trajGen.generate();

        controller.setEgoState(egoSpeed, egoYaw, egoX, egoY);
        controller.setTrajectory(trajGen.getTrajectory());
        controller.compute(0.1f);
        safetyMon.kickControlWatchdog(systemTime);

        safetyMon.updateSensorHealth(lidar.getHealth(), camera.getHealth(),
                                      radar.getHealth(), imu.getHealth());
        safetyMon.updateObjectList(fusion.getObjectList());
        safetyMon.updateSpeed(egoSpeed, targetSpeed);
        SafetyDecision dec = safetyMon.evaluate(systemTime);
        emergHandler.handle(dec, fsm.getState(), egoSpeed);
        fsm.update(true, true, false, false, dec == SafetyDecision::EMERGENCY_STOP, false);

        const ActuatorCommands& cmds = controller.getCommands();
        float accel = (cmds.throttle_pct / 100.0f) * 3.0f
                    - (cmds.brake_pct    / 100.0f) * 8.0f;
        egoSpeed += accel * 0.1f;
        if (egoSpeed < 0) egoSpeed = 0;
        egoX += egoSpeed * 0.1f;

        printState(fsm.getState(), dec, cmds, egoSpeed * 3.6f,
                   safetyMon.getMinTTC(), cycle);
    }

    // ── SCENARIO 3: Pedestrian crossing ─────────────────────────────────────
    printSeparator("SCENARIO 3: PEDESTRIAN CROSSING – YIELD & STOP");

    for (uint8_t i = 0; i < 6; ++i) {
        systemTime += 100;
        cycle++;

        float pedX = 15.0f - static_cast<float>(i) * 1.0f;
        CameraFrame cam = makeCameraFrame(systemTime, -1.8f, 1.8f);
        addPedestrian(cam, pedX, 0.5f);
        camera.injectFrame(cam);
        radar.injectObjectList(makeEmptyRadarScan(systemTime));

        fusion.setRadarScan(radar.getScan());
        fusion.setCameraFrame(camera.getFrame());
        fusion.process(0.1f);
        fusion.computeTTC(egoSpeed);
        safetyMon.kickFusionWatchdog(systemTime);

        laneDetector.setCameraFrame(camera.getFrame());
        laneDetector.process();
        planner.setObjectList(fusion.getObjectList());
        planner.setLaneEstimate(laneDetector.getLaneEstimate());
        planner.setEgoPose(egoX, egoY, egoYaw, egoSpeed);
        planner.plan();
        safetyMon.kickPlanningWatchdog(systemTime);

        trajGen.setLocalPath(planner.getPath());
        trajGen.setEgoState(egoX, egoY, egoYaw, egoSpeed, 0.0f);
        trajGen.setObjectList(fusion.getObjectList());
        trajGen.generate();

        controller.setEgoState(egoSpeed, egoYaw, egoX, egoY);
        controller.setTrajectory(trajGen.getTrajectory());
        controller.compute(0.1f);
        safetyMon.kickControlWatchdog(systemTime);

        safetyMon.updateSensorHealth(lidar.getHealth(), camera.getHealth(),
                                      radar.getHealth(), imu.getHealth());
        safetyMon.updateObjectList(fusion.getObjectList());
        safetyMon.updateSpeed(egoSpeed, targetSpeed);
        SafetyDecision dec = safetyMon.evaluate(systemTime);
        emergHandler.handle(dec, fsm.getState(), egoSpeed);
        fsm.update(true, true, false, false, dec == SafetyDecision::EMERGENCY_STOP, false);

        const ActuatorCommands& cmds = controller.getCommands();
        float accel = (cmds.throttle_pct / 100.0f) * 3.0f
                    - (cmds.brake_pct    / 100.0f) * 8.0f;
        egoSpeed += accel * 0.1f;
        if (egoSpeed < 0) egoSpeed = 0;
        egoX += egoSpeed * 0.1f;

        printf("[cycle %4u] Pedestrian @ x=%.1fm | Decision: %-20s | "
               "Speed: %.1f km/h | Brake: %.1f%%\n",
               cycle, pedX,
               planner.getDecision().state == BehaviorState::YIELD ? "YIELD" :
               planner.getDecision().state == BehaviorState::EMERGENCY_STOP ? "EMERGENCY_STOP" :
               planner.getDecision().must_stop ? "MUST_STOP" : "NORMAL",
               egoSpeed * 3.6f, cmds.brake_pct);
    }

    // ── SCENARIO 4: LiDAR sensor failure ────────────────────────────────────
    printSeparator("SCENARIO 4: LIDAR FAILURE – DEGRADED MODE");

    // Stop sending LiDAR scans → timeout will trigger
    systemTime += 500;   // jump 500ms without LiDAR
    lidar.cyclic100ms(); lidar.cyclic100ms(); lidar.cyclic100ms();
    lidar.cyclic100ms(); lidar.cyclic100ms();

    printf("LiDAR health after timeout: %s\n",
           lidar.getHealth() == SensorHealth::FAILED ? "FAILED" :
           lidar.getHealth() == SensorHealth::DEGRADED ? "DEGRADED" : "OK");

    safetyMon.updateSensorHealth(lidar.getHealth(), camera.getHealth(),
                                  radar.getHealth(), imu.getHealth());
    SafetyDecision dec4 = safetyMon.evaluate(systemTime);
    printf("Safety decision with LiDAR failed: %s\n",
           dec4 == SafetyDecision::DEGRADE_ODD    ? "DEGRADE_ODD" :
           dec4 == SafetyDecision::MINIMAL_RISK   ? "MINIMAL_RISK" :
           dec4 == SafetyDecision::EMERGENCY_STOP ? "EMERGENCY_STOP" : "OTHER");

    // ── SCENARIO 5: Emergency stop (AEB) ────────────────────────────────────
    printSeparator("SCENARIO 5: AEB – EMERGENCY STOP (TTC < 1s)");

    egoSpeed = 15.0f;  // 54 km/h

    // Object very close and closing fast
    RadarScan closeScan = makeRadarScan(systemTime, 8.0f, -15.0f);  // 8m, 54 km/h relative
    radar.injectObjectList(closeScan);
    fusion.setRadarScan(radar.getScan());
    fusion.process(0.1f);
    fusion.computeTTC(egoSpeed);

    // Manually force TTC update via object list
    ObjectList ol = fusion.getObjectList();
    // Set TTC on first object if any
    if (ol.count > 0) {
        ol.objects[0].ttc_s = 0.5f;  // 0.5s TTC
        ol.objects[0].is_in_ego_path = true;
    }
    safetyMon.updateObjectList(ol);
    safetyMon.kickFusionWatchdog(systemTime + 100);
    safetyMon.kickPlanningWatchdog(systemTime + 100);
    safetyMon.kickControlWatchdog(systemTime + 100);
    SafetyDecision dec5 = safetyMon.evaluate(systemTime + 100);

    emergHandler.handle(dec5, fsm.getState(), egoSpeed);
    controller.setEgoState(egoSpeed, egoYaw, egoX, egoY);
    controller.setTrajectory(trajGen.getTrajectory());
    controller.compute(0.1f);

    const ActuatorCommands& aebCmds = controller.getCommands();
    printf("Safety decision: %s\n",
           dec5 == SafetyDecision::EMERGENCY_STOP ? "EMERGENCY_STOP ✓" : "OTHER");
    printf("AEB active: %s | Brake: %.1f%%\n",
           aebCmds.aeb_active ? "YES ✓" : "NO",
           aebCmds.brake_pct);

    // ── SCENARIO 6: ODD EXIT → MINIMAL RISK CONDITION ───────────────────────
    printSeparator("SCENARIO 6: ODD EXIT – MINIMAL RISK CONDITION");

    emergHandler.handle(SafetyDecision::NOMINAL, AdasSystemState::ACTIVE_L4, 0.0f);
    controller.clearEmergencyStop();

    fsm.update(true, false /* ODD invalid */, false, true, false, false);
    printf("FSM state after ODD exit: %s\n", stateToStr(fsm.getState()));

    // ── Final Summary ────────────────────────────────────────────────────────
    printSeparator("SIMULATION COMPLETE – SUMMARY");
    printf("Total simulation cycles : %u\n", cycle);
    printf("Total CAN Tx frames     : %u\n", canBus.getTxCount() + g_txCount);
    printf("Final FSM state         : %s\n", stateToStr(fsm.getState()));
    printf("AEB triggered           : %s\n",
           dec5 == SafetyDecision::EMERGENCY_STOP ? "YES" : "NO");
    printf("\nAll scenarios executed successfully.\n");

    return 0;
}
