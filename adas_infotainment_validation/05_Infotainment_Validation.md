# 05 — Infotainment (IVI) Validation

> **Topic**: In-Vehicle Infotainment system testing — HMI, media, connectivity, OTA, Android Automotive  
> **Tools**: ADB, Appium, Selenium, Android Studio, Wireshark, JIRA  
> **Outcome**: Validate head unit features, connectivity stacks, HMI responses, and OTA update flows

---

## 1. What Is the Infotainment System (IVI)?

IVI (In-Vehicle Infotainment) is the head unit — the large touchscreen computer in the center console:

```
IVI System Block Diagram:
─────────────────────────────────────────────────────────────────────────────
┌───────────────────────────────────────────────────────────────────────────┐
│                        IVI Head Unit                                      │
│                                                                           │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────────────────┐ │
│  │  Display │  │  Audio   │  │ Android   │  │  Connectivity Stack      │ │
│  │ 10–15"   │  │  Amp/DSP │  │ Automotive│  │  WiFi / BT / 4G/5G      │ │
│  │ OLED/LCD │  │  ANC     │  │ OS (AOSP) │  │  Apple CarPlay / AA     │ │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └───────────┬──────────────┘ │
│       │             │              │                     │                 │
│       └─────────────┴──────────────┴─────────────────────┘                 │
│                                   │                                        │
│                         SoC (Snapdragon / i.MX8)                          │
│                           RAM: 8–16 GB, ROM: 64–256 GB                    │
│                                   │                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                   Vehicle Integration Layer                           │ │
│  │   CAN gateway │ LIN │ MOST │ A2B audio │ USB │ LVDS video            │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

### IVI Feature Domains
| Domain | Features | Test Priority |
|--------|---------|---------------|
| Navigation | Map display, routing, POI, traffic | High |
| Audio/Media | FM/DAB radio, BT audio, USB, streaming | High |
| Phone | Bluetooth HFP, SMS, contacts | High |
| Connectivity | WiFi, 4G/5G data, hotspot | High |
| Vehicle integration | Speed, fuel, DTC display, ADAS HMI | Critical |
| Apple CarPlay / Android Auto | Mirror, Siri, Google Assistant | High |
| OTA updates | SW update download and install | Critical |
| HMI | Touch, voice, buttons, response time | High |

---

## 2. Android Automotive OS (AAOS) Testing

Most modern IVI systems run Android Automotive OS (Google's automotive variant):

```
Android Automotive OS (AAOS) architecture:
─────────────────────────────────────────────────────────────────────────────
┌────────────────────────────────────────────────────────────────────────┐
│                         Application Layer                              │
│   Google Maps │ Spotify │ YouTube │ OEM Apps │ System Apps             │
├────────────────────────────────────────────────────────────────────────┤
│                    Android Automotive SDK                              │
│   CarMediaSession │ CarUiLib │ CarPropertyManager │ VehicleHAL        │
├────────────────────────────────────────────────────────────────────────┤
│                    AAOS Framework                                      │
│   CarService │ CarAudioService │ CarNavigationService                  │
├────────────────────────────────────────────────────────────────────────┤
│                    Vendor HAL / BSP                                    │
│   VehicleHAL (VHAL) │ Audio HAL │ Display HAL │ Camera HAL            │
├────────────────────────────────────────────────────────────────────────┤
│                    Linux Kernel (BSP)                                  │
└────────────────────────────────────────────────────────────────────────┘

Key difference vs phone Android:
  - No touch is required (supports rotary knob + voice only)
  - VHAL bridges Android CarProperty ↔ CAN bus signals
  - Distraction optimization rules (NHTSA/JAMA guidelines)
  - Always-on display, no power saving sleep mode while driving
```

### ADB — Android Debug Bridge
```bash
# ADB is your primary tool for testing AAOS head units

# Connect to head unit (USB or WiFi)
adb connect 192.168.100.50:5555   # WiFi ADB
adb devices                        # List connected devices

# View logcat (all logs)
adb logcat -v time | grep -E "AEB|ADAS|CarService"

# Filter by tag
adb logcat -s CarService:D NavigationApp:I

# Capture screenshot
adb shell screencap /sdcard/screen.png
adb pull /sdcard/screen.png ./screenshots/

# Dump system services
adb shell dumpsys car_service
adb shell dumpsys media_session
adb shell dumpsys bluetooth_manager

# Read vehicle property (via VHAL)
adb shell cmd car_service get-property \
    android.car.VehiclePropertyIds.SPEED    # Vehicle speed

# Simulate vehicle property (for bench testing)
adb shell cmd car_service set-int-property \
    android.car.VehiclePropertyIds.GEAR_SELECTION 8   # DRIVE

# Install/uninstall app
adb install -r MyApp.apk
adb uninstall com.company.myapp

# Check memory / CPU
adb shell top -n 1 | head -20
adb shell dumpsys meminfo com.google.android.apps.maps
```

---

## 3. HMI Testing

HMI (Human-Machine Interface) testing validates the visual, audio, and haptic responses:

### HMI Test Dimensions
```
What to validate in HMI testing:
──────────────────────────────────────────────────────────────────────────
Dimension         Test                        Pass Criterion
──────────────────────────────────────────────────────────────────────────
Responsiveness    Tap → response time         < 100 ms (NHTSA guideline)
                  Menu → sub-menu open         < 300 ms
                  Map render on open           < 3 s

Text accuracy     All strings correct          Zero typos / wrong language
                  Language switch works         All strings translate

Icon accuracy     All icons correct            No missing icons (blank)
                  Night mode icons visible     Correct contrast

Color scheme      Day mode colors              Pass colorimetry spec
                  Night mode dimming           < 10% brightness
                  Warning colors               Red = critical (no other use)

Layout            Screen density              No overlap at 1920×1080
                  Landscape / portrait         (if rotation supported)
                  Font sizes                   ≥ 12pt for driver-visible

Audio feedback    Button click sound           Present and correct
                  Navigation voice prompt      Audible at 70 dB road noise
                  Warning chime               ≥ 85 dBSPL in cabin

Distraction rules Interaction time            NHTSA: ≤ 12 s per task
                  Glance count                ≤ 6 glances per task
──────────────────────────────────────────────────────────────────────────
```

### Automated HMI Testing with Appium
```python
"""
Automated HMI testing using Appium + UIAutomator2 (Android)
"""
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class IVITester:
    """Appium-based IVI HMI test automation."""

    def __init__(self, device_id: str):
        caps = {
            "platformName":        "Android",
            "deviceName":          device_id,
            "automationName":      "UiAutomator2",
            "appPackage":          "com.oemname.launcher",
            "appActivity":         ".MainActivity",
            "noReset":             True,
            "newCommandTimeout":   120,
        }
        self.driver = webdriver.Remote("http://localhost:4723/wd/hub", caps)
        self.wait = WebDriverWait(self.driver, timeout=10)

    def test_navigation_open_time(self):
        """Navigation app must open in < 3 seconds."""
        t_start = time.time()

        # Tap Navigation icon on home screen
        nav_icon = self.wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.ACCESSIBILITY_ID, "Navigation")
            )
        )
        nav_icon.click()

        # Wait for map to render (wait for a map element to appear)
        self.wait.until(
            EC.presence_of_element_located(
                (AppiumBy.ID, "com.google.android.apps.maps:id/map_view")
            )
        )

        elapsed = time.time() - t_start
        assert elapsed < 3.0, f"Navigation opened in {elapsed:.2f}s (limit 3.0s)"
        print(f"[PASS] Navigation opened in {elapsed:.2f}s")

    def test_volume_control_response(self):
        """Volume change must update display in < 100 ms."""
        # Find volume slider
        slider = self.wait.until(
            EC.presence_of_element_located(
                (AppiumBy.ID, "com.oemname.mediaplayer:id/volume_slider")
            )
        )
        current_level = int(slider.get_attribute("progress"))

        t_start = time.time()
        # Set volume to 50%
        self.driver.execute_script("mobile: setProgress", {
            "element": slider,
            "value": 50
        })

        # Verify volume indicator updated
        volume_label = self.wait.until(
            EC.presence_of_element_located(
                (AppiumBy.ID, "com.oemname.mediaplayer:id/volume_text")
            )
        )
        elapsed = time.time() - t_start
        assert "50" in volume_label.text, f"Volume label shows: {volume_label.text}"
        assert elapsed < 0.1, f"Volume response {elapsed*1000:.0f}ms (limit 100ms)"

    def test_night_mode_switch(self):
        """Night mode must change display brightness and colors."""
        # Simulate vehicle ambient light change via adb
        import subprocess
        subprocess.run([
            "adb", "shell", "cmd", "car_service",
            "set-int-property",
            "android.car.VehiclePropertyIds.NIGHT_MODE", "1"
        ])
        time.sleep(0.5)

        # Verify background color is dark
        screenshot = self.driver.get_screenshot_as_png()
        # Image processing would check dominant color is dark
        # (simplified check here)
        bg = self.driver.find_element(
            AppiumBy.ID, "com.oemname.launcher:id/background"
        )
        bg_color = bg.get_attribute("backgroundColor")
        # Expect dark background in night mode
        assert bg_color in ["#1A1A1A", "#000000", "#0D0D0D"], \
            f"Night mode background {bg_color} not dark enough"

    def teardown(self):
        self.driver.quit()
```

---

## 4. Connectivity Testing

### Bluetooth Testing
```
Bluetooth test matrix:
──────────────────────────────────────────────────────────────────────────
Feature           Test Case                      Pass Criterion
──────────────────────────────────────────────────────────────────────────
Pairing           Pair new phone                 Completes in < 30 s
Auto-connect      Ignition on → auto-connect     Connected in < 5 s
HFP call          Make/receive call              Clear audio, < 1 s delay
A2DP audio        Stream music                   No drops for 10 min
PBAP contacts     Import contacts                All contacts synced < 60 s
Multiple devices  2 phones paired simultaneously Both visible, priority correct
Disconnect        KL15 off → disconnect          Disconnects within 3 s
Re-pair           Delete + re-pair same phone    Completes correctly
Range test        Walk to 10 m distance          Connected; 15 m drops

Test tools:
  - Real Android/iPhone phones
  - Bluetooth analyzer (Frontline, Ellisys)
  - adb for log capture during testing
  - Automated: btmgmt CLI + Python scripting
──────────────────────────────────────────────────────────────────────────
```

```python
import subprocess
import time
import re

class BluetoothTester:

    def __init__(self, phone_mac="AA:BB:CC:DD:EE:FF"):
        self.phone_mac = phone_mac

    def _adb(self, cmd: str) -> str:
        """Run adb shell command and return output."""
        result = subprocess.run(
            f"adb shell {cmd}",
            shell=True, capture_output=True, text=True
        )
        return result.stdout.strip()

    def test_auto_connect_time(self) -> float:
        """Measure BT auto-connect time after ignition on."""
        # Simulate ignition ON
        subprocess.run([
            "adb", "shell", "cmd", "car_service",
            "set-int-property",
            "android.car.VehiclePropertyIds.IGNITION_STATE", "3"
        ])
        t_start = time.time()

        # Poll for BT connection
        for _ in range(50):  # up to 5 s
            status = self._adb(f"dumpsys bluetooth_manager | grep {self.phone_mac}")
            if "CONNECTED" in status.upper():
                elapsed = time.time() - t_start
                print(f"[PASS] BT auto-connected in {elapsed:.2f}s")
                return elapsed
            time.sleep(0.1)

        raise AssertionError("Bluetooth did not auto-connect within 5 s")
```

### WiFi Testing
```python
def test_wifi_internet_connectivity():
    """Verify WiFi connects and provides internet access."""
    # Enable WiFi
    subprocess.run(["adb", "shell", "svc", "wifi", "enable"])
    time.sleep(2.0)

    # Connect to SSID
    subprocess.run([
        "adb", "shell",
        f'cmd wifi connect-network "CarTest_5G" wpa2 "password123"'
    ])
    time.sleep(5.0)

    # Verify connected and has internet
    output = subprocess.check_output(
        ["adb", "shell", "ping", "-c", "3", "8.8.8.8"],
        text=True
    )
    # Check for packet loss
    match = re.search(r"(\d+)% packet loss", output)
    loss = int(match.group(1)) if match else 100
    assert loss == 0, f"WiFi packet loss: {loss}%"

    # Measure latency
    latency_match = re.search(r"avg.*?(\d+\.\d+)/", output)
    avg_latency = float(latency_match.group(1)) if latency_match else 9999
    assert avg_latency < 100, f"WiFi latency {avg_latency}ms > 100ms"
    print(f"[PASS] WiFi connected. Latency: {avg_latency:.1f}ms, loss: {loss}%")
```

---

## 5. Vehicle Data Integration Testing

The IVI reads vehicle data via VHAL (Vehicle Hardware Abstraction Layer):

```
VHAL property test matrix:
──────────────────────────────────────────────────────────────────────────
Property ID                         Signal Name        Test
──────────────────────────────────────────────────────────────────────────
PERF_VEHICLE_SPEED                  Car.vx             Speed displayed ±1 km/h
ENGINE_RPM                          Engine.RPM         RPM gauge moves correctly
FUEL_LEVEL                          Fuel.Level_pct     Fuel gauge displays pct
RANGE_REMAINING                     Range.km           Shows remaining km
OUTSIDE_TEMPERATURE                 Amb.Temp_C         Shows correct temperature
HVAC_FAN_SPEED                      HVAC.Fan           Fan control responds
DOOR_OPEN                           Door.FL.Open       Warning icon shows
SEATBELT_UNLATCHED                  Belt.Driver.Open   Warning chime plays
NIGHT_MODE                          Ambient.Night      Display dims
TURN_SIGNAL_STATE                   Indicator.Left/Rt  Turn indicator icon
ADAS_ACTIVE                         ADAS.State         ADAS icon in cluster area
──────────────────────────────────────────────────────────────────────────
```

```python
def test_speedometer_display_accuracy():
    """Verify speed displayed on IVI matches CAN vehicle speed."""
    test_speeds = [0, 30, 50, 80, 100, 130, 160]

    for speed_kmh in test_speeds:
        # Set vehicle speed via VHAL injection (bench only)
        subprocess.run([
            "adb", "shell", "cmd", "car_service",
            "set-float-property",
            "android.car.VehiclePropertyIds.PERF_VEHICLE_SPEED",
            str(speed_kmh / 3.6)   # VHAL uses m/s
        ])
        time.sleep(0.5)  # Allow UI to update

        # Read displayed speed via UI automation
        speed_text = driver.find_element(
            AppiumBy.ID, "com.oemname.cluster:id/speed_value"
        ).text
        displayed_speed = int(speed_text)

        error = abs(displayed_speed - speed_kmh)
        assert error <= 2, \
            f"Speed {speed_kmh} km/h displayed as {displayed_speed} (error {error})"
        print(f"  v={speed_kmh}: displayed={displayed_speed} ✓")
```

---

## 6. OTA (Over-The-Air) Update Testing

OTA updates are safety-critical: a failed update can brick the IVI or create security vulnerabilities:

```
OTA Update Test Flow:
────────────────────────────────────────────────────────────────────────────
Backend Server
  │
  │ 1. Update available notification (push)
  │
  ▼
IVI Download Manager
  │ 2. Check package signature (RSA-2048 / ECDSA)
  │ 3. Verify SHA-256 hash of package
  │ 4. Download to update partition
  │
  ▼
Update Engine (OTA service)
  │ 5. Verify package metadata
  │ 6. Check compatibility (HW version, current SW version)
  │ 7. Apply delta patch (A/B update partition)
  │
  ▼
Recovery / Bootloader
  │ 8. Boot to new partition
  │ 9. CRC check of new system
  │
  ▼
New OS version running
  │ 10. Report update success to backend
  │ 11. Commit new partition as active
────────────────────────────────────────────────────────────────────────────
```

### OTA Test Cases
```
OTA Test Matrix:
──────────────────────────────────────────────────────────────────────────
Test ID    Scenario                           Expected Result
──────────────────────────────────────────────────────────────────────────
OTA-001    Normal update (good package)       Update succeeds, new version
OTA-002    Power cut during download          Rollback, old version intact
OTA-003    Power cut during flash             A/B: rollback; non-A/B: FAIL
OTA-004    Wrong signature (tampered pkg)     Update rejected, error shown
OTA-005    Wrong HW version                   Update rejected, clear message
OTA-006    Insufficient storage              Update rejected, user informed
OTA-007    Network interruption mid-download  Resume download correctly
OTA-008    Update during driving (inhibit?)   Rejected or deferred
OTA-009    Full update (OS + apps)            All components updated
OTA-010    Delta update only                  Only changed blocks applied
OTA-011    Rollback after bad update          Previous version restored
OTA-012    Security patch only               Boot image signed correctly
──────────────────────────────────────────────────────────────────────────
```

```python
def test_ota_power_cut_recovery(device, update_server):
    """
    Simulate power cut during OTA download.
    Expected: system rolls back to previous version, no brick.
    """
    original_version = get_sw_version(device)  # e.g., "4.1.2"

    # Trigger OTA download
    update_server.push_update("4.2.0")
    time.sleep(5)  # Let download start

    # Simulate power cut (HIL: cut 12V supply)
    power_supply.set_voltage(0)
    time.sleep(2)

    # Restore power
    power_supply.set_voltage(13.5)
    time.sleep(10)  # Wait for boot

    # Verify system is still running old version (not bricked)
    current_version = get_sw_version(device)
    assert current_version == original_version, \
        f"Expected rollback to {original_version}, got {current_version}"
    assert device_is_bootable(device), "Device bricked after power cut!"
    print(f"[PASS] Power cut recovery: device running v{current_version}")
```

---

## 7. Apple CarPlay / Android Auto Testing

```
CarPlay test matrix:
──────────────────────────────────────────────────────────────────────────
Feature              Test                          Pass Criterion
──────────────────────────────────────────────────────────────────────────
Connection           Plug iPhone via USB           CarPlay starts < 5 s
Wireless CarPlay     iPhone WiFi + BT pair         Starts < 10 s
Map display          Apple Maps navigation          Map renders, voice works
Phone call           Make/receive via CarPlay       Audio routed correctly
Siri                 "Hey Siri, navigate to..."    Command recognized
Music playback       Apple Music / Spotify          Plays without drops
Distraction check    Tap complexity                All interactions < 3 taps
Screen switch        CarPlay ↔ native IVI          Switch < 1 s
Disconnect           Unplug cable                  Graceful exit, no freeze
Background audio     Native radio + CarPlay         Transitions correctly
──────────────────────────────────────────────────────────────────────────
```

---

## 8. Audio System Testing

```
Audio test categories:
──────────────────────────────────────────────────────────────────────────
Category         Test                            Tool
──────────────────────────────────────────────────────────────────────────
Frequency resp.  Sine sweep 20 Hz – 20 kHz       Audio analyzer
SNR              Signal-to-noise ratio            Audio Precision AP2700
THD+N            Harmonic distortion              Audio analyzer
Channel balance  L/R 1 kHz sine tone              dBSPL meters
ANC              Active noise cancellation on/off  Microphone + spectrum
Speed-dependent  Volume increases with speed       CAN speed + SPL meter
Warning chime    FCW, seatbelt, door ajar          SPL meter, timing
Voice guidance   Navigation prompt at 70 dB noise  STI (Speech Transl. Index)
Bluetooth audio  A2DP quality at 10 m             Codec analysis
──────────────────────────────────────────────────────────────────────────
```

---

## 9. Interview Q&A

**Q1: What is VHAL and why does it matter for IVI testing?**  
VHAL (Vehicle Hardware Abstraction Layer) is Android Automotive's interface between the OS (CarService) and the vehicle's physical CAN/LIN signals. It maps raw CAN data to Android CarProperty APIs. For testing, VHAL injection allows you to set any vehicle property (speed, gear, fuel level) from ADB or a test script, so you can test IVI responses without needing a real car or running engine.

**Q2: What tools do you use to automate IVI HMI testing?**  
I use Appium with UIAutomator2 driver for Android Automotive — it allows element-level interaction (tap, swipe, scroll) and UI state verification. For image-based checks, I use screenshot comparison with OpenCV. ADB is used for system-level commands, log capture, and VHAL property injection. For timing measurements, I instrument the test scripts with precise timestamps around UI interactions.

**Q3: What is A/B partition update in OTA and why is it safer?**  
A/B partition keeps two complete system images on the device. Updates write to the inactive partition while the device runs normally. After successful verification, the bootloader switches to the new partition. If the new partition is corrupt or fails to boot, the bootloader automatically rolls back to the previous partition. This eliminates the "bricked device" risk of traditional single-partition OTA.

**Q4: What distraction rules apply to IVI HMI design?**  
NHTSA (US) and JAMA (Japan) guidelines specify: total interaction time per task ≤ 12 seconds, number of glances ≤ 6, individual glance duration ≤ 2 seconds. These are measured using eye-tracking in a test vehicle. EU regulations (ECE R10 level) add requirements for: text input while moving must be blocked, manual typing of phone numbers while driving must be disabled.

**Q5: How do you test OTA update security?**  
OTA security testing includes: (1) Tampered package test — modify one byte in the update package and verify the device rejects it (signature check); (2) Wrong certificate test — sign with an unofficial certificate, verify rejection; (3) Replay attack — try installing an older version after a newer one, verify rejection; (4) Man-in-the-middle — intercept OTA traffic and substitute a different package; (5) Package integrity — verify SHA-256 hash mismatch is detected and handled. All these must result in rejection with no harm to the running system.
