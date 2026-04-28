// ============================================================================
// test_sensors.cpp  –  Unit tests for sensor layer (17 tests)
// ============================================================================
#include <cassert>
#include <cstdio>
#include <cmath>
#include <cstring>

#include "../include/sensors/lidar_sensor.hpp"
#include "../include/sensors/radar_sensor.hpp"
#include "../include/sensors/camera_sensor.hpp"
#include "../include/sensors/imu_sensor.hpp"

using namespace adas;

static int g_pass = 0;
static int g_fail = 0;

#define ASSERT_TRUE(cond) do { \
    if (cond) { printf("  [PASS] %s\n", #cond); g_pass++; } \
    else       { printf("  [FAIL] %s  (line %d)\n", #cond, __LINE__); g_fail++; } \
} while(0)

#define ASSERT_EQ(a,b) do { \
    if ((a)==(b)) { printf("  [PASS] " #a " == " #b "\n"); g_pass++; } \
    else          { printf("  [FAIL] " #a " == " #b " (line %d)\n", __LINE__); g_fail++; } \
} while(0)

#define ASSERT_NEAR(a,b,tol) do { \
    if (fabsf((a)-(b)) <= (tol)) { printf("  [PASS] " #a " ~= " #b "\n"); g_pass++; } \
    else { printf("  [FAIL] " #a "=%.4f vs " #b "=%.4f (line %d)\n", \
                  static_cast<double>(a), static_cast<double>(b), __LINE__); g_fail++; } \
} while(0)

// ---------------------------------------------------------------------------
// LiDAR tests
// ---------------------------------------------------------------------------
static void test_lidar_initial_health() {
    LidarSensor sensor;
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::INIT);
}

static void test_lidar_inject_scan_updates_health() {
    LidarSensor sensor;
    LidarScan scan;
    scan.timestamp_ms = 1000;
    scan.health       = SensorHealth::OK;
    scan.count        = 0;
    sensor.injectScan(scan);
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::OK);
}

static void test_lidar_ground_removal_reduces_points() {
    LidarSensor sensor;
    LidarScan scan;
    scan.timestamp_ms = 1000;
    scan.health       = SensorHealth::OK;
    scan.count        = 0;

    // 900 ground points (z = -1.5) with varying x and y for non-collinear RANSAC sampling
    for (uint32_t i = 0; i < 900 && scan.count < MAX_LIDAR_POINTS; ++i) {
        LidarPoint& p = scan.points[scan.count++];
        p.x = -20.0f + static_cast<float>(i % 30) * 1.5f;
        p.y = -20.0f + static_cast<float>(i / 30) * 1.5f;
        p.z = -1.5f;
        p.intensity = 0.2f;
        p.ring = 0;
    }
    // 100 obstacle points (z = +0.5)
    for (uint32_t i = 0; i < 100 && scan.count < MAX_LIDAR_POINTS; ++i) {
        LidarPoint& p = scan.points[scan.count++];
        p.x = 10.0f + static_cast<float>(i % 10) * 0.5f;
        p.y = -2.5f + static_cast<float>(i / 10) * 0.5f;
        p.z = 0.5f;
        p.intensity = 0.8f;
        p.ring = 5;
    }

    sensor.injectScan(scan);
    const LidarScan& obs = sensor.getObstacleScan();
    // Obstacle scan should have fewer points than raw (ground removed)
    ASSERT_TRUE(obs.count < scan.count);
    ASSERT_TRUE(obs.count > 0);
}

static void test_lidar_timeout_sets_failed() {
    LidarSensor sensor;
    LidarScan scan;
    scan.timestamp_ms = 100;
    scan.health       = SensorHealth::OK;
    scan.count        = 0;
    sensor.injectScan(scan);

    // Advance time by 3 cycles of 100ms without new scan
    sensor.cyclic100ms();
    sensor.cyclic100ms();
    sensor.cyclic100ms();

    ASSERT_TRUE(sensor.getHealth() == SensorHealth::FAILED);
}

static void test_lidar_empty_scan_obstacle_count_zero() {
    LidarSensor sensor;
    LidarScan scan;
    scan.timestamp_ms = 500;
    scan.health       = SensorHealth::OK;
    scan.count        = 0;
    sensor.injectScan(scan);
    ASSERT_TRUE(sensor.getObstacleScan().count == 0);
}

// ---------------------------------------------------------------------------
// Radar tests
// ---------------------------------------------------------------------------
static void test_radar_initial_state() {
    RadarSensor sensor(0);
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::INIT);
    ASSERT_EQ(sensor.getSensorId(), static_cast<uint8_t>(0));
}

static void test_radar_inject_scan() {
    RadarSensor sensor(1);
    RadarScan scan;
    scan.timestamp_ms = 200;
    scan.health       = SensorHealth::OK;
    scan.count        = 2;
    scan.objects[0].range_m = 30.0f;
    scan.objects[1].range_m = 60.0f;
    sensor.injectObjectList(scan);
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::OK);
    ASSERT_NEAR(sensor.getScan().objects[0].range_m, 30.0f, 0.001f);
    ASSERT_EQ(sensor.getScan().count, static_cast<uint8_t>(2));
}

static void test_radar_timeout() {
    RadarSensor sensor(0);
    RadarScan scan;
    scan.timestamp_ms = 100;
    scan.health       = SensorHealth::OK;
    scan.count        = 1;
    sensor.injectObjectList(scan);
    sensor.cyclic100ms();
    sensor.cyclic100ms();
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::FAILED);
}

// ---------------------------------------------------------------------------
// Camera tests
// ---------------------------------------------------------------------------
static void test_camera_initial_state() {
    CameraSensor sensor(0);
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::INIT);
}

static void test_camera_inject_frame() {
    CameraSensor sensor(0);
    CameraFrame frame;
    frame.timestamp_ms        = 100;
    frame.health              = SensorHealth::OK;
    frame.count               = 1;
    frame.lane_quality        = 80;
    frame.lane_width_m        = 3.5f;
    frame.left_lane_offset_m  = -1.75f;
    frame.right_lane_offset_m = 1.75f;
    frame.lane_curvature_inv_m= 0.0f;
    sensor.injectFrame(frame);
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::OK);
    ASSERT_EQ(sensor.getFrame().lane_quality, static_cast<uint8_t>(80));
    ASSERT_NEAR(sensor.getFrame().lane_width_m, 3.5f, 0.001f);
}

static void test_camera_timeout() {
    CameraSensor sensor(0);
    CameraFrame frame;
    frame.timestamp_ms = 50;
    frame.health       = SensorHealth::OK;
    frame.count        = 0;
    frame.lane_quality = 70;
    frame.lane_width_m = 3.5f;
    frame.left_lane_offset_m = frame.right_lane_offset_m = 0;
    frame.lane_curvature_inv_m = 0;
    sensor.injectFrame(frame);
    sensor.cyclic100ms();
    sensor.cyclic100ms();
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::FAILED);
}

// ---------------------------------------------------------------------------
// IMU tests
// ---------------------------------------------------------------------------
static void test_imu_initial_state() {
    ImuSensor sensor;
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::INIT);
}

static void test_imu_valid_data() {
    ImuSensor sensor;
    ImuData data;
    data.ax = 0.5f; data.ay = -0.2f; data.az = 9.81f;
    data.gx = 0.01f; data.gy = 0.0f; data.gz = 0.1f;
    data.timestamp_ms = 100;
    data.health = SensorHealth::OK;
    sensor.injectData(data);
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::OK);
    ASSERT_NEAR(sensor.getData().ax, 0.5f, 0.001f);
}

static void test_imu_out_of_range_acceleration() {
    ImuSensor sensor;
    ImuData data;
    data.ax = 25.0f;  // exceeds 20 m/s² limit
    data.ay = 0.0f; data.az = 9.81f;
    data.gx = data.gy = data.gz = 0.0f;
    data.timestamp_ms = 100;
    data.health = SensorHealth::OK;
    sensor.injectData(data);
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::DEGRADED);
}

static void test_imu_out_of_range_gyro() {
    ImuSensor sensor;
    ImuData data;
    data.ax = 0.0f; data.ay = 0.0f; data.az = 9.81f;
    data.gx = 10.0f;  // exceeds 5.24 rad/s limit
    data.gy = data.gz = 0.0f;
    data.timestamp_ms = 100;
    data.health = SensorHealth::OK;
    sensor.injectData(data);
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::DEGRADED);
}

static void test_imu_timeout() {
    ImuSensor sensor;
    ImuData data;
    data.ax = 0.0f; data.ay = 0.0f; data.az = 9.81f;
    data.gx = data.gy = data.gz = 0.0f;
    data.timestamp_ms = 10;
    data.health = SensorHealth::OK;
    sensor.injectData(data);
    sensor.cyclic100ms();
    sensor.cyclic100ms();
    ASSERT_TRUE(sensor.getHealth() == SensorHealth::FAILED);
}

// ---------------------------------------------------------------------------
int main() {
    printf("===========================================================\n");
    printf("  test_sensors – ADAS L4 Sensor Layer Unit Tests\n");
    printf("===========================================================\n");

    // LiDAR
    printf("\n-- LiDAR --\n");
    test_lidar_initial_health();
    test_lidar_inject_scan_updates_health();
    test_lidar_ground_removal_reduces_points();
    test_lidar_timeout_sets_failed();
    test_lidar_empty_scan_obstacle_count_zero();

    // Radar
    printf("\n-- Radar --\n");
    test_radar_initial_state();
    test_radar_inject_scan();
    test_radar_timeout();

    // Camera
    printf("\n-- Camera --\n");
    test_camera_initial_state();
    test_camera_inject_frame();
    test_camera_timeout();

    // IMU
    printf("\n-- IMU --\n");
    test_imu_initial_state();
    test_imu_valid_data();
    test_imu_out_of_range_acceleration();
    test_imu_out_of_range_gyro();
    test_imu_timeout();

    printf("\n===========================================================\n");
    printf("  Results: %d passed, %d failed\n", g_pass, g_fail);
    printf("===========================================================\n");
    return (g_fail == 0) ? 0 : 1;
}
