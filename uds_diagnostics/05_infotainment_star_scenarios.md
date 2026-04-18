# UDS Diagnostics — Infotainment STAR Scenarios
## 100 Real Interview Cases | HU · Radio · Bluetooth · Apple CarPlay · Android Auto · Audio · OTA | April 2026

**STAR Format:** S=Situation T=Task A=Action R=Result
**ECU:** HU = Head Unit (0x7D0 → 0x7D8), AMP = Amplifier (0x7D2), CDC = CD/Media (0x7D4)
**Key Context:** Infotainment ECUs are often Linux/Android-based with UDS over DoIP (UDP) or K-Line/CAN

---

### Case 1 — Head Unit Black Screen After Battery Disconnection
**S:** After battery replacement, head unit shows a completely black screen on startup. All other vehicle systems function. Audio briefly plays then stops.
**T:** Diagnose why HU is not displaying after power cycle.
**A:**
```
10 01 on 0x7D0 → 50 01 (HU responds! Not dead — just display issue)
22 [HU_Display_Status DID] → Display_Powered=0x01, Backlight=0x00 (backlight off!)
22 [HU_Backlight_Config DID] → Backlight_Source=0x02 (ILL signal from BCM)
ILL (illumination) signal from BCM: should be HIGH when ignition on
22 [BCM_ILL_Output DID] on BCM → ILL=0x00 (BCM sending ILL=off)
BCM resets ILL timeout on battery disconnection — sets ILL=0 until next ignition cycle complete
11 01 on HU → Hard reset
2F [HU_Backlight DID] 03 FF → Force maximum backlight
Backlight ON → display immediately visible
BCM ILL re-syncs after full ignition cycle
```
**R:** BCM ILL output was 0 after battery disconnect reset (ILL timeout protection prevents HU backlight staying on with ignition off). Full ignition cycle reset BCM ILL state. Temporary IO control verified backlight hardware was functioning.

---

### Case 2 — Bluetooth Pairing Not Possible (NRC 0x22)
**S:** Vehicle Bluetooth cannot pair with phones. DTC U0186: Bluetooth Module Communication Fault. Customers cannot connect.
**T:** Diagnose Bluetooth module and restore pairing.
**A:**
```
19 02 09 on 0x7D0 → U0186 confirmed
22 [BT_Module_Status DID] → BT_State=0x00 (module offline)
22 [BT_FW_Version DID] → 0x00000000 (firmware blank — not flashed)
This BT module was replaced but BT firmware not re-flashed
31 01 [BT_Flash_RID] → Start Bluetooth firmware flash routine
7F 31 78 × n (flashing ~90 seconds)
71 01 [RID] 01 PASS
11 03 → Soft reset
22 [BT_Module_Status DID] → BT_State=0x03 (ready for pairing)
19 02 09 → No DTCs
Bluetooth pairing test with iPhone: connects in <8s
```
**R:** Replacement Bluetooth module was supplied without firmware. UDS firmware flash routine loaded BT stack. Paired and verified functional.

---

### Case 3 — Apple CarPlay Not Available After HU SW Update
**S:** After an over-the-air HU software update, Apple CarPlay is unavailable. Android Auto still works. No DTCs.
**T:** Diagnose CarPlay post-update.
**A:**
```
22 [HU_CarPlay_Status DID] → CarPlay_Enable=0x01 (enabled in config)
22 [HU_CarPlay_License DID] → License=0x00 (INVALID — CarPlay license key missing!)
OEM CarPlay license is stored in HU NVM. SW update cleared license partition
22 [HU_License_Partition DID] → Partition_Status=0xFF (erased)
Contact OEM licensing server: VIN-linked license key retrieved
2E [HU_CarPlay_License DID] [license_key_bytes] → Re-install license
11 01 → Hard reset
22 [HU_CarPlay_Status DID] → License=0x01 (VALID)
CarPlay connects via USB: confirmed working
```
**R:** SW update erased HU license partition. CarPlay uses a VIN-linked license key (Apple licensing requirement). License re-provision from OEM server required. Android Auto does not require a per-vehicle license (explains why it still worked).

---

### Case 4 — Radio Presets Lost After Every Ignition Off
**S:** Customer has set 6 radio presets. Every time ignition is turned off and on, all presets reset to factory defaults (87.5 MHz).
**T:** Diagnose preset persistence failure.
**A:**
```
22 [HU_NVM_Status DID] → NVM_Write_Status=0x02 (write error — same as IC NVM issue pattern)
22 [HU_NVM_ErrorCode DID] → 0x04 (EMMC partition 2 write fail)
HU uses eMMC flash storage (not EEPROM). Partition 2 = user preferences partition
eMMC partition 2 health check:
31 01 [eMMC_Health_RID] → Bad_Block_Count=847 (critical — >500 = replace storage)
HU eMMC failing — user data not persisting
Replace HU (eMMC not field-replaceable)
After replacement: re-code HU via 2E [HU_Variant DID]
Set presets: save and verify after ignition cycle
```
**R:** eMMC storage bad block count critical threshold exceeded. Preset writes failing silently. HU replacement required. eMMC bad block diagnostics available via UDS health routine.

---

### Case 5 — Audio Distortion from Amplifier (Specific Speaker)
**S:** Left-rear speaker produces distorted audio (crackling) at volumes above 50%. Other speakers are clear. DTC B2140: Amplifier Output Channel 4 Fault.
**T:** Diagnose amplifier channel fault via UDS.
**A:**
```
19 02 09 on AMP ECU (0x7D2) → B2140 confirmed (Ch4 = left rear)
22 [AMP_CH4_Status DID] → CH4_LoadImpedance=2.1Ω (spec: 4–6Ω — sub-spec means speaker short or failing)
22 [AMP_Temp DID] → AMP_TempC=88°C (normal = <75°C — overheated due to short)
2F [AMP_CH4_Mute DID] 03 01 → Mute CH4 (protect amplifier from further thermal stress)
Physical: left-rear speaker voice coil partially shorted → low impedance → AMP overloads
Replace speaker
2F [AMP_CH4_Mute DID] 03 00 → Restore CH4 (un-mute)
22 [AMP_CH4_Status DID] → CH4_LoadImpedance=4.8Ω (correct)
19 02 09 → B2140 still active (needs trip confirm) → 14 FF FF FF → Cleared
```
**R:** Left-rear speaker partial voice coil short caused low impedance load → amplifier overloaded → Ch4 DTC. IO control mute protected amplifier during testing. Speaker replacement restored correct impedance and cleared fault.

---

### Case 6 — HU Does Not Accept USB Devices
**S:** USB ports on HU do not recognise any devices. USB charging works (phone charges) but no audio playback or CarPlay/Android Auto.
**T:** Diagnose USB data functionality.
**A:**
```
22 [HU_USB_Status DID] → USB1_Power=0x01 (power on), USB1_Data=0x00 (data disabled!)
22 [HU_USB_Config DID] → USB_Data_Mode=0x00 (charge only — data disabled!)
HU USB configured for "charge only" mode (some markets disable data due to driver distraction regulations)
27 01 / 27 02 → Security access
2E [HU_USB_Config DID] [USB_Data_Mode=0x01] → Enable USB data
11 03 → Soft reset
22 [HU_USB_Status DID] → USB1_Data=0x01 (data active)
Test: USB stick connected → music library detected
CarPlay via USB: working
```
**R:** HU USB data was deliberately disabled in market-specific configuration (charge-only mode for certain markets with data-use regulations while driving). Re-enabling data mode required security access and UDS DID write.

---

### Case 7 — HU Software Update Fails: Insufficient Storage
**S:** OTA HU software update fails at download stage. HU reports insufficient storage. The new SW package is 3.2 GB. HU has 32 GB storage claimed.
**T:** Diagnose HU storage availability.
**A:**
```
22 [HU_Storage_Status DID] → Total=32GB, Used=31.2GB, Free=0.8GB (insufficient for 3.2GB!)
22 [HU_StorageBreakdown DID] → System=8GB, Maps=14GB, Media=3GB, Cache=6GB (cache bloated!)
HU cache partition grown to 6GB (should max 2GB) — cache management bug
31 01 [HU_CacheClear_RID] → Clear cache partition
71 01 [RID] 01 PASS → Cache cleared
22 [HU_Storage_Status DID] → Free=4.8GB (enough for 3.2GB update)
Retry OTA update: download proceeds and installs successfully
```
**R:** HU cache partition exceeded normal bounds (6GB vs 2GB expected) due to a cache management SW bug. Clearing cache via UDS routine freed sufficient space for the OTA update. SW update included a cache management fix to prevent recurrence.

---

### Case 8 — Navigation Maps Not Updating via OTA
**S:** Map update via OTA repeatedly fails. Progress reaches 100% then rolls back to original maps. No error shown on HMI.
**T:** Diagnose OTA map update failure.
**A:**
```
19 02 09 on HU → U3B44 (OTA Update Fail) stored
22 [OTA_MapUpdate_Status DID] → Status=0x05 (verification failed — signature invalid)
22 [OTA_ReceivedSize DID] → 2.1GB received (correct for EU map package)
22 [OTA_Server_Cert DID] → Certificate valid
22 [Map_Package_Hash DID] → Local hash ≠ server hash (data corrupted in download)
Partial cellular dropout during transfer corrupted map data in one segment
OTA protocol does not support resume for map updates (different from SW updates)
Retry full download on strong Wi-Fi tether
Map update completes and verifies successfully
```
**R:** Map package hash mismatch caused rollback — OTA correctly protecting against corrupted map data being applied. Cellular signal issue during download was the root cause. Recommend: map updates over Wi-Fi when possible (hotspot from phone). Cellular OTA implementation improved with resume capability.

---

### Case 9 — Phone Audio Not Working with New iPhone Model
**S:** After customer upgrades to latest iPhone, audio calls through vehicle are silent (no audio either direction). Previous iPhone worked. Bluetooth connection shows as connected.
**T:** Diagnose Bluetooth audio profile compatibility.
**A:**
```
22 [BT_Profile_Status DID] → HFP=0x01 (connected), A2DP=0x01 (connected), AVRCP=0x01
22 [BT_HFP_CodecStatus DID] → Codec=0x03 (mSBC wideband) — new iPhone default
22 [HU_BT_CodecSupport DID] → mSBC=0x00 (not supported! Only CVSD=0x01 supported)
New iPhone defaults to mSBC (wideband hands-free). Old HU only supports CVSD (narrowband)
Profile negotiation fallback not working: new iPhone refusing fallback to CVSD
31 01 [BT_Codec_Negotiation_RID] → Force renegotiate to CVSD
71 01 [RID] 01 PASS → Negotiated to CVSD
Audio call confirmed working (narrowband quality)
Permanent fix: HU SW update to add mSBC support (wideband audio)
```
**R:** iPhone firmware update changed BT HFP default codec to mSBC (wideband). HU only supported CVSD. Codec negotiation fallback had a SW bug. Temporary: forced CVSD via UDS routine. Permanent: HU SW update adds mSBC support.

---

### Case 10 — Android Auto Disconnects Every 5 Minutes
**S:** Android Auto connects successfully but disconnects exactly every 5 minutes. Immediately reconnects but the 5-second reconnect break disrupts navigation.
**T:** Diagnose periodic Android Auto disconnection.
**A:**
```
22 [HU_AA_Status DID] → Connection_Uptime=300s at each disconnect (exactly 5 minutes)
22 [HU_AA_Config DID] → AA_Session_Max_Duration=300s (5-minute session limit!)
This is an OEM configuration limiting AA session duration (originally a thermal protection measure)
Check: is thermal issue present?
22 [HU_Temp DID] → HU_CPU_Temp=42°C (normal — no thermal issue)
Session limit is unnecessary for this hardware revision
27 01 / 27 02
2E [HU_AA_Config DID] [AA_Session_Max_Duration=0 (unlimited)]
11 03 → Verify: AA session now unlimited
```
**R:** Android Auto session duration was hard-coded to 5 minutes in HU config — originally added as a thermal protection for an older HU hardware revision. Current hardware has better thermal management. Duration limit removed via UDS write.

---

### Case 11 — HU Speaker Channel Balance Shifted to One Side
**S:** Audio balance has shifted fully left. Balance control on HMI can be moved to right but reverts to full-left after restart.
**T:** Diagnose audio balance persistence.
**A:**
```
22 [HU_Audio_Balance DID] → Balance=0xF0 (full left = -15 steps)
Spec: factory default Centre = 0x00
2F [HU_Audio_Balance DID] 03 00 → IO control: set to centre
Balance=centre during session, but reverts after restart
→ Persistent value is still F0 in NVM
22 [HU_NVM_AudioPrefs DID] → Balance_NVM=0xF0 (stored full-left)
27 01 / 27 02
2E [HU_NVM_AudioPrefs DID] [Balance=0x00] → Write centre to NVM
11 03
22 [HU_Audio_Balance DID] → Balance=0x00 after restart — persistent
```
**R:** Audio balance NVM had persistent full-left value. HMI changes are temporary if NVM write is not performed. Direct NVM write via UDS DID corrected the stored balance. Root cause: factory end-of-line test procedure left balance at test position.

---

### Case 12 — DAB Radio Not Receiving Stations
**S:** DAB radio shows "No Signal" in an area with confirmed DAB coverage. FM works normally. No DTCs.
**T:** Diagnose DAB tuner.
**A:**
```
22 [HU_DAB_Status DID] → DAB_RF_Level=−120 dBm (extremely low — antenna fault suspected)
22 [HU_Antenna_Config DID] → DAB_Antenna=0x01 (configured — external antenna)
Physical: DAB antenna connector at HU not fully seated (antenna amp connector partially out)
Re-seat DAB antenna connector
22 [HU_DAB_Status DID] → DAB_RF_Level=−65 dBm (good)
31 01 [DAB_Scan_RID] → Scan for stations
71 01 [RID] 01 PASS → 28 stations found
DAB working normally
```
**R:** DAB antenna connector not fully seated causing near-zero signal level. FM uses a different connector path (via windscreen antenna) — hence FM worked. Physical re-seat resolved. RF signal level DID is a valuable diagnostic for antenna connectivity issues.

---

### Case 13 — Navigation Voice Guidance Volume Incorrect
**S:** Navigation voice guidance is always at maximum volume regardless of volume knob settings. In quiet tunnels it is very loud.
**T:** Diagnose nav guidance volume control.
**A:**
```
22 [HU_NavVolume_Config DID] → NavVol_Source=0x02 (fixed level), NavVol_Fixed=0xFF (max)
Spec: NavVol_Source=0x01 (follow master volume knob)
2E [HU_NavVolume_Config DID] [Source=0x01] → Set to follow master volume
11 03 → Verify: navigation guidance now follows volume knob level
Additional: 22 [HU_NavVolumeAdjust_Config DID] → AutoVolumeWithSpeed=0x01 (enabled — correct for tunnel adjustment)
```
**R:** Navigation volume was configured to use a fixed maximum level rather than following the master volume knob. Configuration corrected via UDS DID write. Auto-volume-with-speed feature was already enabled for speed-dependent volume.

---

### Case 14 — HU Cannot Enter Programming Session (NRC 0x25)
**S:** Attempting HU firmware update. 10 02 returns NRC 0x25 (requestSequenceError).
**T:** Identify correct session entry sequence for HU programming.
**A:**
```
10 02 → 7F 10 25 (requestSequenceError — must pass through extended session first)
Many HUs require: 10 01 → 10 03 → 10 02 (default → extended → programming)
10 01 → 50 01 (default session)
10 03 → 50 03 (extended session)
27 01 / 27 02 → Security access level 1 (extended)
10 02 → 50 02 (programming session now accepted)
27 11 / 27 12 → Security access level programming
Proceed with firmware download
```
**R:** HU requires a pre-defined session transition sequence (default → extended → programming) unlike some ECUs that allow direct programming session access. This is an OEM-specific sequence requirement documented in the diagnostic specification.

---

### Case 15 — Radio Mono Output (No Stereo)
**S:** All audio mono. Stereo music plays in mono via HU. Both left and right speakers work (balance manual test passes).
**T:** Diagnose stereo mode configuration.
**A:**
```
22 [HU_Audio_Mode DID] → StereoMode=0x00 (mono enabled!)
Factory config: some accessibility builds have mono default for hearing-impaired compatibility
27 01 / 27 02
2E [HU_Audio_Mode DID] [StereoMode=0x01] → Enable stereo
11 03
Test: stereo audio confirmed — left/right channel separation present
```
**R:** Mono mode was enabled in a configuration intended for accessibility markets. Stereo enabled via UDS DID write. Demonstrates that accessibility features are UDS-configurable.

---

### Case 16 — HU Crashes When Playing Phone Call and Navigation Simultaneously
**S:** HU software crashes (shows OEM boot screen) every time a phone call is received while navigation is active. Happens 100% reproducibly.
**T:** Capture crash log and diagnose root cause.
**A:**
```
After crash: power-on
22 [HU_CrashLog_DID] → LastCrash_Reason=0x0A (null pointer dereference), Task=AudioMixer
22 [HU_CrashCount DID] → Count=23 (23 crashes of this type in last 30 days)
22 [HU_SW_Version DID] → v4.2.1
OEM release notes: v4.2.1 has known audio mixer null pointer bug when switching audio sources
Fix: HU SW update to v4.2.3 which patches the audio source switch logic
Perform HU SW update
22 [HU_SW_Version DID] → v4.2.3
Test: phone call during navigation → no crash
```
**R:** Known SW bug in v4.2.1 audio mixer caused null pointer dereference when switching between navigation audio and phone call audio simultaneously. Crash log DID captured sufficient detail to identify the exact fault. SW update to v4.2.3 resolved.

---

### Case 17 — HU Stuck in Reverse Camera Mode
**S:** Reverse camera image displayed permanently on HU even with vehicle in Drive at 60 km/h. Reversing camera image stuck on screen.
**T:** Diagnose reverse trigger signal to HU.
**A:**
```
22 [HU_ReverseCam_Status DID] → Reverse_Trigger=0x01 (HU receiving reverse signal = active)
22 [HU_ReverseTrigger_Source DID] → Source=0x02 (CAN from TCM reverse gear)
22 [TCM_GearStatus DID] on TCM → Gear=D (Drive) — not in reverse
22 [HU_CAN_RxMsg DID] → HU receiving gear messages, latest: Gear=0x07 (0x07 = Reverse in this encoding)
Trace: did encoding change after TCM SW update?
TCM SW update changed D=0x05 and R=0x07 to D=0x07 and R=0x05 (reversed)
HU DBC not updated → reading old encoding → sees "Reverse" when in Drive
HU SW update to correct DBC encoding resolves issue
```
**R:** TCM SW update reversed the gear position byte encoding. HU was reading old encoding and interpreting Drive gear byte as Reverse. SW update to HU corrected gear decoding. DBC version synchronisation between TCM and HU is critical.

---

### Case 18 — Subwoofer Not Producing Bass
**S:** Vehicle has factory subwoofer. Bass frequencies are absent. Midrange and treble normal. Subwoofer tested physically: OK.
**T:** Diagnose subwoofer signal chain via UDS.
**A:**
```
22 [HU_Subwoofer_Config DID] → Sub_Enable=0x01, Sub_Volume=0x80 (50%), Sub_Crossover=80Hz
2F [HU_Sub_Channel DID] 03 [test_tone_50Hz] → Force 50Hz test tone to subwoofer channel
Physical: no audio from subwoofer during forced test tone
22 [AMP_SubChannel_Status DID] on 0x7D2 → Sub_Channel_Impedance=999Ω (open circuit — no speaker connected!)
Subwoofer connector at amplifier end disconnected
Re-connect subwoofer to AMP connector
22 [AMP_SubChannel_Status DID] → Impedance=6.2Ω (correct)
Subwoofer producing bass confirmed
```
**R:** Subwoofer connector at amplifier disconnected (loose after vibration). Amplifier impedance sense DID confirmed open circuit. IO control test tone confirmed signal path was intact up to amplifier. Physical reconnection resolved.

---

### Case 19 — HU VIN-Locked After Theft Recovery
**S:** Vehicle recovered after theft. HU shows "Locked — Contact Dealer". VIN lock activated. Vehicle needs HU reactivated.
**T:** Unlock HU via UDS with OEM authorisation.
**A:**
```
10 01 on 0x7D0 → 50 01 (HU responds in locked state)
22 [HU_SecurityState DID] → State=0x05 (VIN-locked)
22 [HU_Lock_Reason DID] → Reason=0x02 (theft reported — VIN locked by OEM server)
Process:
1. Police report reference obtained
2. OEM server verifies ownership + police clearance
3. OEM generates VIN-specific unlock code
4. 27 01 → Seed from HU
5. OEM computes unlock key from seed + VIN + police reference
6. 27 02 [unlock key] → Security access granted
7. 31 01 [HU_Unlock_RID] → Execute unlock routine
8. 71 01 [RID] 01 PASS
9. 11 01 → HU functional — no "Locked" message
```
**R:** VIN-lock triggered by OEM server after theft report. Unlock requires OEM-generated time-limited key tied to police clearance reference and VIN. Demonstrates layered security: knowledge of seed-key algorithm alone is insufficient for unlocking VIN-locked units — OEM server involvement required.

---

### Case 20 — HU Audio Output Missing on Specific Zone (Rear Zone)
**S:** Vehicle has multi-zone audio (front/rear cabin different source). Rear cabin zone has no audio. Front zone normal.
**T:** Diagnose rear zone audio output.
**A:**
```
22 [HU_Zone_Config DID] → Zone1=0x01 (front, active), Zone2=0x00 (rear, disabled!)
Rear zone disabled in variant configuration (base trim without rear zone audio option)
But vehicle physically has rear speaker cables and speakers installed
The option was not enabled at order (cost saving on infotainment spec)
27 01 / 27 02
2E [HU_Zone_Config DID] [Zone2=0x01] → Enable rear zone
2F [HU_Zone2_Channel DID] 03 [test_tone] → Verify rear speakers producing audio
Audio confirmed in rear zone
Note: rear zone activation may require additional license/option unlock in some OEM implementations
```
**R:** Rear audio zone was disabled in base configuration despite hardware being fitted. Feature enabled via UDS configuration. Common cost-saving practice: fit hardware for all trims but software-gate features by trim level.

---

### Case 21 → Case 100 (Summary Format)

> The following 80 cases cover the remaining UDS Infotainment diagnostic topics including voice recognition, wireless charging, HDMI/screen mirroring, HU hardware faults, OTA failures, security attacks, regulatory compliance, and end-of-line testing.

---

**Case 21 — Wireless Charging Not Working**
S: Wireless charging pad not charging phone. Wired charging works.
A: `22 [HU_WPC_Status DID] → WPC_Enable=0x00. 2E → 0x01. 11 03. Wireless charging enabled.`
R: Wireless charging (Qi WPC) was disabled in base trim coding. Enabled via UDS.

---

**Case 22 — HU Does Not Display Reverse Camera Grid Lines**
S: Reverse camera works but parking grid lines missing.
A: `22 [HU_CameraGridLines DID] → GridLines_Enable=0x00. 2E → 0x01 (enable). Verified.`
R: Grid line overlay was disabled in configuration. Enabled via UDS write.

---

**Case 23 — Audio Equaliser Settings Not Saving**
S: Customer sets bass/treble EQ but it resets after restart.
A: `22 [HU_NVM_AudioEQ DID] → Write fails: 0x03 (NVM full). 14 FF FF FF – but wait for NVM cleanup. 31 01 [NVM_Defrag_RID] → defragment NVM. Settings now save.`
R: NVM fragmentation prevented EQ settings from being written. NVM defrag routine resolved.

---

**Case 24 — HDMI Screen Mirroring Protocol Mismatch**
S: Third-party HDMI dongle not working for screen mirroring.
A: `22 [HU_HDMI_Config DID] → HDMI_Protocol=MHL (older standard). Device needs SlimPort. 2E → SlimPort mode. Retest: device mirrors successfully.`
R: HDMI/alternate-mode protocol configured wrong for device type. UDS DID write corrected protocol.

---

**Case 25 — HU Fan Running at Maximum Speed (Noisy)**
S: HU cooling fan runs at full speed constantly, very audible.
A: `22 [HU_Temp DID] → CPU=35°C (cold!). 22 [HU_FanControl DID] → Fan_Mode=0x02 (full speed always — debug mode). 2E → 0x01 (auto). Fan now proportional to temperature.`
R: Fan left in fixed-full-speed debug mode. Auto mode restored via UDS.

---

**Case 26 — HU Shows Wrong Time Zone**
S: HU clock shows UTC even though vehicle is in Germany (UTC+2 in summer).
A: `22 [HU_TimeZone DID] → TZ=UTC (no offset). 2E → Europe/Berlin (UTC+2). 11 03. Clock shows local time.`
R: Time zone not configured. UDS write of IANA time zone code resolved.

---

**Case 27 — HU PIN Not Accepted After Too Many Tries**
S: HU security PIN locked after 10 failed attempts (children guessing PIN).
A: `22 [HU_PIN_Lock DID] → Locked=0x01, UnlockTime=3600s. Wait 60 minutes. OR: 27 01/02 → security access → 31 01 [PIN_Reset_RID] → reset PIN to factory default. PUK code required from OEM.`
R: HU has brute-force protection (10 attempts then 60-min lockout). Factory reset via UDS requires OEM PUK code.

---

**Case 28 — HU Doesn't Remember Favourite Contacts**
S: Favourite contacts in phonebook reset every ignition cycle.
A: `22 [HU_Phonebook_NVM DID] → LastWrite=0x00 (never written). 22 [HU_BT_PhoneSync DID] → SyncMode=0x00 (sync disabled). 2E → 0x01 (auto-sync). Contacts now saved per ignition cycle.`
R: Phone contact sync to NVM was disabled. Enabled via UDS config. Contacts now persistent.

---

**Case 29 — HU Microphone Very Quiet for Calls**
S: Passengers say driver sounds very quiet and far away during calls.
A: `22 [HU_Mic_Gain DID] → Mic_Gain=0x10 (16 = 25% gain). Spec: 0x40 (64 = 100%). 27 01/02. 2E → 0x40 (nominal gain). Verified: call audio quality improved.`
R: Microphone gain was set to 25% — likely a factory assembly test value not reset. Gain corrected to 100% nominal.

---

**Case 30 — HU Satellite Radio Not Receiving Channels**
S: SiriusXM satellite radio inactive. "Acquiring Signal" displayed permanently.
A: `22 [HU_SAT_Status DID] → Subscription_Status=0x00 (not activated). 31 01 [SAT_Activate_RID] [VehicleID, SubscriptionCode] → Activate. 71 01 PASS. Channels appear.`
R: Satellite radio subscription not activated. UDS activation routine with OEM-provided subscription code required.

---

**Case 31 — HU Speed-Compensated Volume Not Active**
S: Music gets drowned out at highway speeds. Speed-compensated volume was advertised as a feature.
A: `22 [HU_SCV_Config DID] → SCV_Enable=0x00 (disabled). 2E → 0x01. 11 03. Volume increases proportionally with speed above 80 km/h — confirmed.`
R: Speed-compensated volume (SCV/GALA) was disabled in variant coding. One line UDS write enabled it.

---

**Case 32 — HU Does Not Recognise Second USB Port**
S: USB-A port 1 works. USB-A port 2 (second cable) does not.
A: `22 [HU_USB2_Status DID] → USB2_Hardware=0x00 (USB2 hub chip not detected). 19 02 09 → U1042 (USB Hub 2 Communication Fault). USB hub IC failed on PCB. HU replacement required.`
R: USB hub IC failure on HU PCB. Hardware fault identified via UDS USB port status DID.

---

**Case 33 — HU Display Touchscreen Unresponsive in Top-Left Corner**
S: Top-left 3cm × 3cm area of touchscreen does not register touch.
A: `31 01 [Touchscreen_Test_RID] → Run capacitive touch map test. Result: Top_Left_Region=0x00 (dead zone detected). 22 [Touch_Defect DID] → Defect_Count=1, Location=Top_Left. HU display assembly replacement required (touch panel bonded to LCD).`
R: Capacitive touch panel dead zone detected via UDS self-test routine. Hardware replacement required. Cannot be repaired in field.

---

**Case 34 — Hands-Free Audio Echo on Passenger End**
S: Passengers say they hear an echo of their own voice during hands-free calls.
A: `22 [HU_AEC_Config DID] → AEC_Enable=0x00 (Acoustic Echo Cancellation disabled!). 2E → 0x01. 11 03. AEC active: echo eliminated in call test.`
R: Acoustic Echo Cancellation was disabled. AEC processing removes the speaker-to-microphone feedback loop that causes echo. Enabled via UDS.

---

**Case 35 — HU Maps Showing Wrong Country**
S: Navigation maps show incorrect country (shows NA maps in EU vehicle).
A: `22 [HU_MapRegion DID] → Region=0x01 (North America). Vehicle is EU. 27 01/02. 2E → 0x02 (Europe). 31 01 [Map_Reload_RID] → reload EU maps from onboard storage. EU maps activated.`
R: Map region configuration set to NA in an EU vehicle during a fleet swap. Corrected map region and reloaded correct regional maps.

---

**Case 36 — HU Popup Notifications in Wrong Language**
S: System popup messages appear in German despite UI language set to English.
A: `22 [HU_UI_Language DID] → UI=English. 22 [HU_System_Language DID] → System_Lang=German (separate system layer). 2E [HU_System_Language DID] English. All popups now in English.`
R: HU has separate UI language and system (OS) language settings. Only UI language was changed; system language (used for OS-level popups) was still German. Both must be set.

---

**Case 37 — HU OTA Update Server Certificate Expired**
S: OTA update check fails. HU reports "Cannot connect to update server".
A: `22 [HU_OTA_CertStatus DID] → Server_Cert_Expiry=2024-01-01 (expired!). OEM update server certificate expired. OEM renews server certificate. 2E [HU_OTA_RootCert DID] [new_cert_bytes] → Push new root certificate to HU. OTA update check succeeds.`
R: OEM OTA server root certificate expired causing TLS handshake failure. Certificate renewed and pushed to fleet vehicles via dealer UDS write. UN R156 requires secure OTA certificate management.

---

**Case 38 — HU MOST Bus Communication Lost**
S: HU on a MOST (Media Oriented Systems Transport) network loses communication with amplifier and CDC. All audio stops.
A: `22 [HU_MOST_Status DID] → MOST_Ring_State=0x02 (broken ring). 19 02 09 → U0177 (MOST Network Open). MOST ring topology: one open connection = entire ring fails. Physical: MOST optical cable connector at amplifier loose. Re-seat → ring state=0x01 (closed). Audio restored.`
R: MOST optical ring broken by loose connector. Single physical fault in MOST breaks the entire ring. Confirmed via HU MOST ring state DID.

---

**Case 39 — HU Screen Saver Activates Too Quickly**
S: HU screen saver activates after 30 seconds of no touch input, requiring a touch to wake it. Customer finds it interrupts frequent interactions.
A: `22 [HU_ScreenSaver_Config DID] → Timeout_s=30. 2E → Timeout_s=120 (2 minutes). Or disable: 0x00 = no screensaver.`
R: Screen saver timeout configurable via UDS DID. Extended from 30s to 2 minutes per customer preference.

---

**Case 40 — HU Not Connecting to Home Wi-Fi for OTA**
S: OTA updates require Wi-Fi. Vehicle Wi-Fi cannot connect to customer's home network (WPA3 security protocol).
A: `22 [HU_WiFi_Protocol DID] → WiFi_Security_Support=0x03 (WPA2). WPA3 not supported. SW update required to add WPA3/SAE support. After update: 22 [HU_WiFi_Protocol DID] → WPA3=0x01 supported. Home network connection successful.`
R: HU Wi-Fi only supported WPA2, not WPA3 (modern routers default to WPA3-only). SW update added WPA3 support.

---

**Case 41 — Voice Recognition Does Not Understand Accented Speech**
S: Voice recognition works for standard English but consistently fails for customer with South African accent.
A: `22 [HU_Voice_Language DID] → Voice_Model=0x01 (US English). 2E → 0x07 (en-ZA / South African English model). Accuracy improves significantly.`
R: Wrong regional language model selected for voice recognition. Switching to ZA English model improved accuracy.

---

**Case 42 — HU Does Not Boot Past Logo Screen**
S: HU shows OEM logo and freezes. No further boot progress. Happens after a failed SW flash.
A: `Physical: HU in bootloader lockdown mode after failed flash. Connect via JTAG/bootloader serial interface (not UDS). Flash emergency recovery image. HU boots to recovery mode. UDS available: 10 03 → 10 02 → re-flash full SW image. 11 01 → Full boot.`
R: Failed SW flash left HU in bootloader stuck state. UDS not available in this state — emergency recovery via JTAG/serial required. After recovery image, UDS flash of full SW image completes successfully.

---

**Case 43 — Climate Control Display Area Frozen on HU**
S: HU main display works but the climate control zone (persistent display strip at bottom of screen) is frozen with old temperature values.
A: `22 [HU_Zone_Status DID] → Climate_Zone=0x02 (sub-process hung). 31 01 [Climate_Zone_Restart_RID] → Restart climate display process. 71 01 PASS. Climate zone updates correctly without full reboot.`
R: Climate display is a separate process on the Linux HU OS. Process hung without crashing full OS. UDS routine to restart specific process resolved without full reboot.

---

**Case 44 — HU Shows Incorrect Range-on-Charge for BEV**
S: BEV HU shows 250 km range even when battery is at 10%. BMS reports 25 km correctly.
A: `22 [HU_Range_Source DID] → Source=0x03 (HU local estimate). BMS source not used! 2E [HU_Range_Source DID] 01 → Use BMS provided range. 11 03. HU now shows BMS-provided range: 25 km.`
R: HU was using its own internal range estimate (based on a fixed energy model) instead of the BMS-provided precision estimate. Switched to BMS source.

---

**Case 45 — Rear Seat Entertainment Screen Not Syncing with HU**
S: Rear seat screens (RSE) show different content than what's selected on front HU. They appear to be running independently.
A: `22 [RSE_Sync_Status DID] on RSE module → HU_Link=0x00 (not connected to HU). 19 02 09 → U0215 (Lost Comm with HU). Physical: LVDS cable between HU and RSE partially disconnected. Re-seat. RSE syncs with HU.`
R: LVDS cable signal degradation disconnected RSE from HU network. RSE fell back to independent operation. LVDS re-connection restored sync.

---

**Case 46 — HU Power Consumption Too High in Parked State**
S: Fleet manager reports excessive 12V drain from infotainment. HU uses 2.2W when parked (spec: <0.5W in sleep).
A: `22 [HU_Sleep_Status DID] → State=0x03 (partial sleep — GPS keep-alive active). 22 [HU_GPS_Keepalive DID] → Enabled=0x01 (GPS hot-start maintained). 2E → 0x00 (disable GPS keep-alive except during eCall readiness). Power drops to 0.3W.`
R: GPS keep-alive was maintaining GPS receiver active during parking. Disabled to reduce parasitic drain. Cold GPS start accepted (10-15s longer for first fix) in exchange for 2W less drain.

---

**Case 47 — HU Factory Reset Does Not Clear User Data**
S: Security audit: performing factory reset from HU menu does not clear stored phone numbers, home address, or garage door codes.
A: `31 01 [HU_FactoryReset_RID] [Level=0x02 (full secure erase)] → Level 1 (soft reset) was used in factory reset menu — only clears settings, not user data. Level 2 required for user data. 27 01/02 → security access required for Level 2. After Level 2: 22 [HU_UserData DID] → all entries 0xFF (secure erased). GDPR compliant.`
R: Factory reset menu used Level 1 (settings only). Secure user data erasure requires Level 2 (cryptographic erase) with security access. GDPR compliance requires Level 2 for personal data. OEM updated factory reset menu to default to Level 2 when selling vehicle.

---

**Case 48 — HU Clock Drifts 5 Minutes Per Day**
S: Vehicle HU clock drifts 5 minutes per day. Customer re-sets clock frequently.
A: `22 [HU_TimeSync_Status DID] → GPS_Sync=0x01 (enabled), GPS_LastSync=T-48h (2 days ago!). GPS sync should update every startup. Check: Why no recent sync? 22 [HU_GPS_Status DID] → GPS_Fix=0x00 (no fix — vehicle parked indoor garage). GPS time sync needs outdoor GPS fix. Enable: NTP over Wi-Fi as fallback time source. 2E [HU_TimeSource DID] [GPS+NTP fallback]. HU syncs via Wi-Fi when parked.`
R: HU clock drift as expected without time sync. GPS unavailable in residential garage. Added NTP-over-Wi-Fi as fallback. Clock now syncs when connected to home Wi-Fi.

---

**Case 49 — HU MQTT/Telemetry Data Sending to Wrong Server**
S: Vehicle telemetry (fleet vehicle) sending data to a test server URL instead of production server.
A: `22 [HU_Telemetry_Config DID] → Server_URL=https://test.oemserver.com (test). Production: https://api.oemserver.com. 2E → correct production URL. 11 03. Telemetry data now reaching production server.`
R: Test server URL left in production vehicle configuration. Corrected via UDS DID write. Fleet configuration management must ensure production server URL is applied at final provisioning.

---

**Case 50 — HU Does Not Accept DTC-Clear for Certain PIDs**
S: `14 FF FF FF` on HU returns NRC 0x31 — only some DTCs are cleared, others remain.
A: `19 02 FF → 12 DTCs. 14 FF FF FF → 7F 14 31. 22 [HU_DTC_Retention DID] → B3041 is retention=OEM_PERMANENT (cannot be cleared by technician). B3041 = Airbag deployment history embedded by design. 14 must be run on specific DTC groups: 14 00 00 FF clears standard group. Permanent group requires OEM dealer override.`
R: Certain DTCs are marked as permanent (not re-settable by technician). This is intentional for safety events (collision, airbag deployment). Standard 14 FF FF FF cannot clear them. OEM dealer procedure with special override access required.

---

**Case 51 — HU Ambient Light Strip Wrong Colour (Blue Instead of White)**
S: Interior ambient lighting strip controlled by HU shows blue regardless of customer colour selection.
A: `22 [HU_Ambient_Config DID] → AmbientColour=0x0000FF (blue hardcoded). 27 01/02. 2E → 0xFFFFFF (white) or customer-set RGB value. 11 03. Ambient light now follows HMI colour picker.`
R: Ambient light colour hardcoded to blue in configuration. NVM DID write with security access restored HMI control of colour.

---

**Case 52 — HU Video Interface Not Sending Image to Rear Camera**
S: New OEM rear camera installed but no image appears on HU. Old camera showed image correctly.
A: `22 [HU_Camera_Config DID] → Camera_Protocol=0x01 (CVBS analogue). New camera: LVDS digital. 2E → 0x02 (LVDS). HU now decodes LVDS camera stream. Image displayed.`
R: New camera uses LVDS digital interface vs old analogue CVBS. Interface protocol must match camera type. UDS DID write updated HU camera interface selection.

---

**Case 53 — HU Apple CarPlay Wireless Not Available**
S: CarPlay wireless (without USB) not available. Wired CarPlay works. Phone supports wireless CarPlay.
A: `22 [HU_CarPlay_Config DID] → Wireless_Mode=0x00 (disabled). 2E → 0x01. 11 03. Wireless CarPlay available and pairing successfully.`
R: Wireless CarPlay disabled in variant coding (enabled later as a paid software update option by OEM). Activated via UDS DID write once purchase confirmed.

---

**Case 54 — HU Audio Delay (Lip Sync Issue on Video)**
S: Video plays on HU but audio is 200ms ahead of video. Noticeable lip-sync error.
A: `22 [HU_AV_Sync DID] → Audio_Offset_ms=200 (audio playing 200ms early). 2E → Audio_Offset_ms=0 (synchronise to video). 11 03. Lip sync corrected.`
R: Audio-Video synchronisation offset incorrectly set at factory. Set to 0ms offset for correct lip sync. Demonstrates UDS configurability of audio-visual timing parameters.

---

**Case 55 — HU Showing OTA Update Available But Vehicle Ineligible**
S: HU prompts for SW update but the update is for a different hardware revision (HW revision mismatch). Installing would brick the unit.
A: `22 [HU_HW_Revision DID] → HW_Rev=0x02. Update Package Header: Requires HW_Rev=0x03. HU correctly refusing: 7F 34 31 (requestOutOfRange — HW incompatible). Safety correctly working. Report: OEM server pushed wrong update to this VIN. OEM server excludes this VIN from update campaign.`
R: Hardware revision check in OTA correctly prevented incompatible update installation. OEM server targeting error pushed wrong package. Demonstrated HU self-protection against wrong-HW updates.

---

**Case 56 — Rear Camera Grid Lines Skewed After Bumper Replacement**
S: After rear bumper replacement, camera grid lines no longer align with road correctly.
A: `22 [HU_Camera_Calibration DID] → GridLine_Offset_mm=0 (no offset). Physical: new bumper moved camera 15mm down compared to OEM spec. 31 01 [Camera_Calibrate_RID] → Run calibration grid target procedure. Enter new vertical offset = −15mm. 71 01 PASS. Grid lines realigned.`
R: Bumper replacement changed camera mounting height. Camera calibration routine via UDS re-calculated grid line offset for new physical position.

---

**Case 57 — HU Does Not Show Instrument Cluster Notifications**
S: Low fuel notification from IC does not appear on HU display. Navigation and media visible on HU.
A: `22 [HU_IC_Notify_Config DID] → IC_Notification_Enable=0x00. 2E → 0x01. 11 03. Low fuel, door open, seat belt notifications now appear on HU.`
R: IC-to-HU notification forwarding was disabled in configuration. Enabled via UDS write.

---

**Case 58 — HU Rear Camera Recording Not Functioning**
S: Dashcam recording (integrated in HU via rear camera) not saving files.
A: `22 [HU_Dashcam_Status DID] → SD_Card_Status=0x00 (no SD card detected). 22 [HU_Dashcam_Config DID] → Storage=SD only (internal eMMC dashcam storage not enabled). SD card missing. 2E [Storage=Internal_eMMC]. Dashcam now records to internal eMMC. Alternatively: insert SD card and use SD storage.`
R: HU configured to use SD card for dashcam storage. SD card not installed. Re-configured to use internal eMMC for dashcam.

---

**Case 59 — HU Jukebox Not Reading USB Drive Above 64GB**
S: 256GB USB drive not recognised by HU media player. 32GB drive works.
A: `22 [HU_USB_Storage_Config DID] → Max_Supported_Storage=0x40 (64GB limit!). 2E → 0x00 (unlimited). 11 03. 256GB drive now recognised and plays correctly.`
R: HU had an artificial 64GB USB storage limit in configuration (older OS limitation). Removed via UDS DID write after validating HU OS supports exFAT drives beyond 64GB.

---

**Case 60 — HU Cannot Connect to 5GHz Hotspot**
S: Phone hotspot on 5GHz band not connecting to HU. 2.4GHz hotspot works.
A: `22 [HU_WiFi_Bands DID] → 5GHz_Enable=0x00 (5GHz radio disabled). 2E → 0x01. 11 03. HU connects to 5GHz hotspot. Higher bandwidth OTA download now possible.`
R: 5GHz Wi-Fi band was disabled in configuration. Enable via UDS DID write. 5GHz provides higher bandwidth for faster OTA downloads.

---

**Case 61 — HU Stores Personal Data After Factory Reset**
S: Privacy audit: personal data (home address, calendar, contacts) persists after factory reset.
A: `31 01 [HU_SecureErase_RID] [Level=0x03 full crypto-erase] → Requires security access level 3 (dealer only). 71 01 PASS. 22 [HU_PersonalData DID] → 0xFF (all zero). 22 [HU_NVM_Hash DID] → Data erased confirmed. GDPR compliant.`
R: Full cryptographic erase (Level 3) needed for GDPR-compliant data removal. Regular factory reset insufficient. Dealer required for Level 3 access. Policy: Level 3 erase mandatory before vehicle resale.

---

**Case 62 — HU Navigation Recalculation Very Slow**
S: Navigation takes 30+ seconds to reroute after a wrong turn. Customers complain about poor navigation performance.
A: `22 [HU_Nav_Config DID] → MapProcessing_Mode=0x01 (offline only). Online assisted routing disabled. 2E → 0x02 (hybrid: local + cloud). Rerouting now uses cellular for faster cloud-assisted calculation. Rerouting time: < 3 seconds.`
R: Navigation was configured for offline-only processing. Cloud-assisted hybrid mode enabled via UDS, using cellular connectivity for faster route calculations.

---

**Case 63 — HU Does Not Display Real-Time Traffic**
S: Navigation has no traffic data. All routes ignore congestion.
A: `22 [HU_Traffic_Config DID] → RealTime_Traffic=0x00 (disabled). 22 [HU_Connectivity_Status DID] → Cellular=0x01 (connected). 2E [Traffic=0x01] → Enable. 11 03. Traffic data now displayed on map.`
R: Real-time traffic feed disabled in configuration. Cellular connection available. Single UDS write enabled traffic data display.

---

**Case 64 — HU Overheating Shutdown During Long Video**
S: HU shuts down after 45 minutes of video playback. Thermal shutdown.
A: `22 [HU_Temp DID] → CPU_Max=95°C (critical). 22 [HU_Fan_Status DID] → Fan_RPM=0 (fan failed!). 22 [HU_FanFault DID] → Fan_Open_Circuit=0x01. HU cooling fan motor failed. Replace fan. 22 [HU_Temp DID] post-fix → CPU stable at 55°C during video playback.`
R: HU cooling fan motor failed causing CPU thermal runaway. UDS temperature and fan status DIDs identified the fan as the root cause. Fan replacement resolved overheating.

---

**Case 65 — HU Touch Sensitivity Too Low in Cold Weather**
S: HU touchscreen barely responds in winter. Works normally in warm weather.
A: `22 [HU_Touch_Config DID] → Touch_Sensitivity=0x20 (low). 2E → 0x40 (medium-high). 11 03. Touch response improved in cold conditions. 22 [HU_Touch_TempComp DID] → TempComp=0x00 (disabled). 2E → 0x01 (enable temperature compensation). Touch controller adjusts sensitivity with temperature.`
R: Capacitive touch sensitivity was too low for gloved/cold finger use. Temperature compensation also disabled. Both corrected via UDS. Cold-weather touch response significantly improved.

---

**Case 66 — HU Second User Not Getting Navigation Voice**
S: Navigation voice announcements stop when second user (passenger) profile is active. Work in driver profile.
A: `22 [HU_Profile_NavVoice DID] Profile=0x02 → NavVoice=0x00 (disabled for profile 2). 2E → 0x01. NavVoice now active for all profiles.`
R: Navigation voice announcements were disabled in second user profile configuration. Enabled via UDS per-profile DID.

---

**Case 67 — HU Date Format Shows MM/DD/YYYY in EU Vehicle**
S: HU displays dates in US format (MM/DD/YYYY) instead of EU (DD/MM/YYYY).
A: `22 [HU_DateFormat DID] → Format=0x02 (US). Correct for EU: 0x01 (DD/MM/YYYY). 2E → 0x01. 11 03. Date format corrected.`
R: Wrong regional date format in configuration. Corrected via UDS write.

---

**Case 68 — Audio Popping Sound at Ignition Off**
S: Loud pop from speakers at ignition off. DTC B2180: AMP Channel output fault.
A: `22 [AMP_Mute_Config DID] → Mute_Delay_ms=0 (mute applied immediately = no ramp-down). Correct: Mute_Delay_ms=50ms (50ms audio ramp-down before mute). 2E → 50ms. Pop eliminated at ignition off.`
R: Amplifier muting was immediate with no audio ramp-down, causing a DC transient pop. 50ms ramp-down before muting eliminates the pop. Classic audio engineering requirement.

---

**Case 69 — HU Not Available for Remote Software Diagnostics**
S: OEM remotely connects for field monitoring. HU returns "no response" for remote UDS session.
A: `22 [HU_RemoteDiag_Config DID] → Remote_Diag_Enable=0x00. 2E → 0x01. 11 03. Remote UDS (over DoIP via TCU) confirmed working. OEM can now run remote 22/19 queries.`
R: Remote diagnostics was disabled in HU configuration. Enabled via local diagnostics. OEM field monitoring now possible.

---

**Case 70 — HU Showing Demo Mode Content**
S: New vehicle is showing looping demo videos and a "DEMO MODE" watermark. Customer confused.
A: `22 [HU_Demo_Mode DID] → Demo=0x01 (demo mode on — set at dealership showroom). 2E → 0x00. 11 01. Normal operational mode. Dealership forgot to exit demo mode before vehicle delivery.`
R: HU demo mode left active from dealership showroom display. Single UDS write exits demo mode. EOL/PDI checklist must include demo mode check.

---

**Case 71 — HU Location Services Not Available**
S: Infotainment location-based services (ETA sharing, Find My Car) not working. GPS navigation works separately.
A: `22 [HU_LocationServices DID] → Consent=0x00 (user data consent not given). Legal: GDPR requires explicit user consent for location data sharing. Prompt customer consent screen → 2E [Consent=0x01] after customer agrees. Location services now active.`
R: GDPR consent not recorded for location services. Legal requirement: must obtain and store consent before enabling location data sharing. UDS DID stores consent status.

---

**Case 72 — HU Audio Not Fading on Phone Proximity**
S: Audio should reduce when driver's phone rings (audio ducking). It doesn't. Audio continues at full volume.
A: `22 [HU_AudioDucking DID] → PhoneCall_Ducking=0x00. 2E → 0x01. 11 03. Audio now reduces by 8dB when BT call indicates ringing.`
R: Audio ducking for incoming calls disabled. Enabled via UDS DID write.

---

**Case 73 — HU Media Index Not Updating for New Songs on USB**
S: Customer adds new songs to USB drive. HU still shows old song list and doesn't detect new files.
A: `22 [HU_Media_Index DID] → AutoRescan=0x00 (manual rescan only). 31 01 [Media_Rescan_RID] → Force rescan. New songs appear. 2E [AutoRescan=0x01] → Enable auto rescan on USB connect event.`
R: Media indexer auto-rescan was disabled. Forced rescan via UDS routine detected new files. Auto-rescan enabled for future USB connections.

---

**Case 74 — HU Cannot Store More Than 5 Paired Devices**
S: Customer has 6 Bluetooth devices but HU only allows 5. Asks if limit can be increased.
A: `22 [HU_BT_MaxDevices DID] → Max=5. 2E → Max=10 (if HW supports — check BT controller capability). Verify: 22 [HU_BT_Controller_Cap DID] → Max_Paired=10 (HW supports 10). 2E → 10. Now allows up to 10 paired devices.`
R: BT maximum paired device count was set lower than hardware capability. Increased via UDS DID write.

---

**Case 75 — HU Screen Auto-Rotation Not Working in Portrait Mode**
S: Mounted phone-like HU has auto-rotate feature. Rotating vehicle (for parking camera display in landscape/portrait) doesn't change orientation.
A: `22 [HU_Rotation_Config DID] → AutoRotate=0x00. 2E → 0x01. 11 03. Auto-rotation now responds to gyroscope and switches portrait/landscape.`
R: Auto-rotation disabled. Enabled via UDS DID. HU uses internal IMU (inertial measurement unit) for orientation detection.

---

**Case 76 — HU Reverse Trigger Active While Driving Forward (False Reverse)**
S: Reported in a fleet of 20 vehicles: one vehicle occasionally activates reverse camera while driving forward at 5–10 km/h.
A: `22 [HU_ReverseTrigger_Config DID] → Reverse_Vehicle_Speed_Max=20 km/h (trigger allowed up to 20 km/h). Any reverse signal (even electrical noise) below 20 km/h activates camera. 2E → Reverse_Vehicle_Speed_Max=5 km/h. False activations eliminated.`
R: Reverse camera trigger permitted up to 20 km/h. Low-speed electrical noise on reverse signal line triggered camera while driving slowly. Reduced trigger speed limit to 5 km/h (only valid in actual parking scenarios).

---

**Case 77 — HU Does Not Announce Speed Camera Alerts**
S: Navigation has speed camera alerts enabled in HU menu but no voice announcements occur.
A: `22 [HU_SpeedCam_Config DID] → SpeedCam_Alert=0x01 (enabled), SpeedCam_Voice=0x00 (visual only). 2E [SpeedCam_Voice=0x01] → Enable voice announcements. 11 03.`
R: Speed camera alert was visual-only. Voice announcement setting was separate and disabled. Enabled via UDS DID.

---

**Case 78 — HU Internal Mic Picks Up Road Noise**
S: Hands-free call quality poor due to excessive road/wind noise in microphone input.
A: `22 [HU_NoiseCancel_Config DID] → ANC_Level=0x01 (low). 2E → ANC_Level=0x03 (high). 11 03. Noise cancellation aggressiveness increased. Call quality test: road noise reduced by 12dB by objective measurement.`
R: Noise cancellation level was set too low. Increased to high level via UDS DID write. Significant improvement in hands-free call quality.

---

**Case 79 — HU Programmable Button Without Function**
S: Vehicle has a programmable button on steering wheel. Customer assigns a function via HMI but it doesn't work when pressed.
A: `22 [HU_Prog_Button_Config DID] → Button1_Function=0x07 (Home screen), ButtonInput_Source=0x01 (CAN). 22 [HU_Button_CAN_Status DID] → Button1_RxCount=0 (HU not receiving button press). Trace: steering wheel button sends on ID 0x2A1; HU listens on 0x2A2. Wrong ID in HU config. 2E [Button_RxMsgID = 0x02A1]. Button now functional.`
R: Programmable button CAN message ID mismatch. HU listening on wrong ID. Corrected via UDS DID write.

---

**Case 80 — HU eMMC SMART Health Critical Warning**
S: HU shows intermittent freezes and slowness. No obvious cause from user perspective.
A: `22 [HU_eMMC_Health DID] → Health=0x05 (CRITICAL — 95% worn), BadBlock=2847, ReserveUsed=99%. eMMC approaching end of life. Critical threshold: BadBlock > 500. 2E cannot fix hardware wear. HU replacement required. Before replacement → backup user data to USB via: 31 01 [HU_DataBackup_RID] → export contacts, presets, saved POIs.`
R: eMMC storage wearing out. HU replacement necessary. UDS eMMC health DID provides proactive warning before catastrophic failure. Data backup via UDS routine preserved customer settings for transfer to new unit.

---

**Case 81 — HU Night Mode Colour Temperature Wrong**
S: HU night mode uses warm amber but customer prefers cool blue-white night mode.
A: `22 [HU_NightMode_Config DID] → NightColourTemp=3000K (warm). 2E → 6500K (cool white). 11 03. Display shows cool blue-white in night mode.`
R: Night mode colour temperature is configurable. Updated to cooler tone per customer preference.

---

**Case 82 — HU Frozen After Playing Specific Video File**
S: Playing a specific video from USB always freezes HU. Other videos play normally.
A: `22 [HU_CrashLog DID] → LastCrash_Reason=0x12 (video decoder exception — codec unsupported). 22 [HU_VideoCodecs DID] → Supported: H.264, H.265, MPEG4. Not: AV1. Video file encoded in AV1. HU SW update adds AV1 decoder. After update: AV1 video plays normally.`
R: Video file uses AV1 codec unsupported by HU decoder. Crash log identified codec exception. SW update added AV1 codec support.

---

**Case 83 — HU Does Not Show Nearby EV Chargers**
S: BEV HU navigation does not show nearby charging stations. EV range map empty.
A: `22 [HU_EV_POI_Config DID] → EV_Charger_POI=0x00 (disabled). 22 [HU_POI_Database DID] → EV_DB_Version=0x00 (not installed). 31 01 [EV_POI_Install_RID] → Install EV charger POI database. OTA download of EV POI data. 2E [EV_Charger_POI=0x01]. EV charger map layer now visible.`
R: EV charger POI database not installed and feature disabled. OTA database install and feature enable via UDS resolved.

---

**Case 84 — HU 360-Degree Camera System Has Mirror Image on Front Camera**
S: 360-degree surround system: front camera shows mirrored image (left-right reversed). Other cameras correct.
A: `22 [HU_Camera_Mirror_Config DID] → Front_Camera_Mirror=0x01 (mirrored). Correct: 0x00 (normal). 2E → 0x00. 11 03. Front camera correct orientation.`
R: Front camera mirror flip was enabled (typically used for reversing cameras, not front). Single DID write corrected orientation.

---

**Case 85 — HU Language Pack Missing After Market Change**
S: Vehicle originally sold in Germany. Imported to UK. German language works but English not available in language menu.
A: `22 [HU_Language_Pack DID] → Installed: DE, FR, IT, ES. EN not installed. 31 01 [Language_Pack_Install_RID] [EN_Pack] → Install EN language pack from OTA. 71 01 PASS. English now available in language list.`
R: UK English language pack not installed in the original German market firmware. Language pack install via UDS OTA routine added English support.

---

**Case 86 — HU Parental Control Not Working**
S: Child lock / parental controls on HU allow all content access despite being enabled.
A: `22 [HU_Parental_Config DID] → Parental_Enable=0x01 but Pin_Set=0x00 (no PIN set). Without PIN, parental controls are UI cosmetic only — not enforced. 31 01 [Parental_PIN_Set_RID] [PIN=1234] → Set PIN. Controls now enforced. Specify content rating limit: 2E [Content_Rating=PG].`
R: Parental controls were enabled but no PIN was set, making them non-functional. PIN setup via UDS routine activated enforcement.

---

**Case 87 — HU In-App Purchase Feature Not Available**
S: HU app store features (add-on navigation features, premium streaming service) not available in app store.
A: `22 [HU_AppStore_Config DID] → InApp_Purchase=0x00 (disabled — this market). Region check: some markets restrict in-app purchases. 22 [HU_Market DID] → Market=0x12 (China — restricted). Market-specific regulation prevents in-app purchases via vehicle. Per regulation: app purchases must go through external platform. No UDS override — regulatory non-bypassable.`
R: In-app purchases disabled by market-specific regulatory requirement (China). Not a UDS accessible fix — market regulation. Customer directed to equivalent web-based purchase path.

---

**Case 88 — HU Audio Stuttering During Active Phone Navigation (AA/CarPlay)**
S: Audio stutters/drops for ~100ms every 3 seconds during Android Auto navigation.
A: `22 [HU_AA_BufferConfig DID] → Audio_Buffer_ms=50 (50ms audio buffer). At 100ms latency from phone, buffer underruns every cycle. 2E → Audio_Buffer_ms=300 (300ms buffer). AA audio stuttering eliminated.`
R: Audio buffer too small for Android Auto USB audio latency. Increased buffer from 50ms to 300ms eliminated periodic underruns.

---

**Case 89 — HU Fails Regulatory Radio Frequency Compliance Test**
S: Vehicle fails RF emission test. HU Wi-Fi and Bluetooth radiating above EU CE limits.
A: `22 [HU_RF_Config DID] → WiFi_TxPower=30dBm (too high for indoor EU: max 20dBm EIRP). BT_TxPower=20dBm (too high: max 10dBm for EU). 2E [WiFi=20dBm, BT=10dBm]. RE-test: passes EU ETSI EN 300 328 and EN 301 489. 11 03.`
R: RF transmit power exceeded regulatory limits. Reduced to EU-compliant levels via UDS DID write. All market-variant vehicles must have region-appropriate RF power limits configured at production.

---

**Case 90 — HU Does Not Clear Temporary Files (Performance Degradation)**
S: HU performance noticeably degrades after 2 years. Navigation slow, media playback stutters.
A: `22 [HU_Storage_Status DID] → Free=120MB (free space critically low — was 4GB when new). 22 [HU_StorageBreakdown DID] → Temp_Files=3.8GB (!). Temp file accumulation over 2 years — no automatic cleanup. 31 01 [Temp_Cleanup_RID] → Run cleanup. Freed 3.7GB. 22 [HU_Storage_Status DID] → Free=3.82GB. Performance restored.`
R: Temporary file accumulation over 2 years consumed nearly all free storage. Cleanup routine freed 3.7GB. Automatic periodic cleanup should be added to HU maintenance SW.

---

**Case 91 — HU Steering Wheel Media Controls Unresponsive**
S: Steering wheel media controls (skip, play/pause, volume) not working. HU touchscreen controls work.
A: `22 [HU_SWC_Status DID] → SWC_RxCount=0 (no steering wheel control messages). 22 [HU_SWC_Config DID] → SWC_Source=0x02 (LIN steering wheel). 19 02 09 on Steering Column ECU → B1202 (SWC Module Fault). LIN bus steering column module fault. Replace SWC module.`
R: Steering wheel control module fault on LIN bus. Confirmed via HU SWC receive counter (0 messages) and SA column ECU DTC. Module replacement required.

---

**Case 92 — HU Showing Third-Party Apps Not Installed**
S: HU app launcher shows icons for apps that are not installed (Amazon Music, Spotify). Pressing them shows error.
A: `22 [HU_AppLauncher_Config DID] → ShowUninstalled=0x01 (show all possible apps including uninstalled as prompts for download). 2E → ShowUninstalled=0x00. 11 03. Only installed apps appear in launcher.`
R: HU app launcher configured to show all supported apps regardless of installation status (OEM pre-marketing strategy). Customer preferred only installed apps visible. Configured via UDS.

---

**Case 93 — HU Crash Report to OEM Server Disabled**
S: OEM cannot receive field quality data from HU crash reports. Affects ability to identify fleet-wide SW issues.
A: `22 [HU_CrashReport_Config DID] → CrashReport_Enable=0x00. 22 [HU_Privacy_Consent DID] → Diagnostic_Data_Consent=0x01 (customer consented). 2E [CrashReport_Enable=0x01]. 11 03. Crash reports now sent to OEM server when crash occurs.`
R: Crash reporting was disabled despite customer having consented to diagnostic data sharing. Enabled via UDS. Important: GDPR requires explicit consent before enabling data transmission to OEM servers.

---

**Case 94 — HU First-Time Setup Wizard Does Not Appear**
S: New vehicle delivered without going through first-time setup wizard (language, region, consent screens). Settings defaulted to factory values.
A: `22 [HU_FirstRun_Config DID] → FirstRun_Complete=0x01 (already marked as completed!). EOL test runner marked first-run complete during a functional test and did not reset it. 2E → 0x00 (reset to not-complete). 11 01. Wizard appears on next boot. Customer completes setup.`
R: End-of-line functional test set first-run flag to complete and repair procedure failed to reset it. UDS DID write reset the flag, causing first-run wizard to appear correctly on next customer startup.

---

**Case 95 — HU Not Receiving Vehicle Speed for Speed-Dependent Features**
S: Speed-compensated volume, highway mode, and car-motion features on HU not working. All features require vehicle speed input.
A: `22 [HU_VehicleSpeed_Source DID] → Source=0x02 (CAN from ABS). 22 [HU_VehicleSpeed DID] → Speed=0 always (even while moving). 22 [HU_VehicleSpeed_RxCount DID] → Count=0 (zero messages received). CAN routing: ABS speed message not reaching HU CAN bus. Gateway routing fault (same as IC case 13). Add 0x180 (ABS speed) to gateway routing table. HU now receives vehicle speed.`
R: Gateway not routing ABS speed message to infotainment CAN. All speed-dependent HU features restored once gateway routing corrected.

---

**Case 96 — HU 4G/LTE Connection Dropping Every 30 Minutes**
S: TCU/HU cellular connection drops every 30 minutes then reconnects. OTA downloads frequently interrupted.
A: `22 [HU_Cellular_Config DID] → Session_Timeout=1800s (30 minutes — matches drop). Cellular bearer session timeout forcing reconnect. 2E → Session_Timeout=0 (persistent session). 19 02 09 → U2106 (Cellular Re-Registration Event) count reduced from 48 to 2 per day after change.`
R: Cellular bearer session was configured with a 30-minute timeout causing periodic reconnection (originally a power-saving measure from an older cellular modem specification). Setting persistent session aligned with modern LTE always-on bearer requirements.

---

**Case 97 — HU Screen Off During Reverse (No Camera)**
S: Screen turns off completely when reverse is engaged. No camera image. Audio continues.
A: `22 [HU_ReverseDisplay_Config DID] → ReverseDisplay_Enable=0x00 (disabled — display off in reverse). 2E → 0x01 (enable camera display in reverse). 11 03. Reverse camera now shows when reverse engaged.`
R: Reverse display mode was disabled. This was an end-of-line test remnant not reset. Enabled via UDS — camera display now activates in reverse.

---

**Case 98 — HU Screen Brightness Not Following Ambient in Garage (Too Bright)**
S: In a dark garage, HU display is very bright and not dimming.
A: `22 [HU_Ambient_Sensor DID] → AmbientLux_HU=4 (correctly reading dark). 22 [HU_Brightness_Min DID] → Min_Brightness=0xA0 (63% minimum — too high for dark). 2E [Min_Brightness=0x20 (12.5%)]. Garage brightness now comfortable.` 
R: Minimum brightness floor was set too high, preventing dimming below 63%. Minimum lowered via UDS to allow 12.5% brightness in very dark environments.

---

**Case 99 — HU Does Not Offer Parking Space Memory Feature**
S: High-spec trim vehicle should include Parking Space Memory (remember cabin settings per parking location). Feature not available.
A: `22 [HU_ParkMem_Config DID] → ParkingMemory_Enable=0x00. Verify: does this HW support the feature? 22 [HU_HW_Features DID] → ParkingMemory_Available=0x01 (HW supports). Feature was not activated in SW configuration. 27 01/02. 2E → 0x01. 11 03. Parking Space Memory feature now available in HU settings.`
R: HW supports Parking Space Memory but SW feature was disabled in configuration. Activated via UDS. Demonstrates OEM practice of fitting full feature HW but gating features by trim level in SW.

---

**Case 100 — HU Complete Pre-Delivery Acceptance Test**
**S:** New vehicle PDI. HU must pass all infotainment functional checks before delivery.
**T:** Execute complete HU UDS acceptance test as part of PDI.
**A:**
```
HU PDI Acceptance Test Sequence:
1.  10 01 on 0x7D0 → confirm HU responds
2.  19 02 09 → 0 active DTCs
3.  22 [HU_SW_Version DID] → correct version for this variant/market
4.  22 [HU_Variant DID] → matches VIN specification (market, trim, language)
5.  22 [HU_CarPlay_License DID] → valid (0x01)
6.  22 [BT_Module_Status DID] → 0x03 (ready)
7.  22 [HU_USB_Status DID] → USB1_Data=0x01 and USB2_Data=0x01
8.  22 [HU_DAB_Status DID] → RF level > −80 dBm (antenna connected)
9.  22 [HU_Display_Status DID] → Display_Powered=0x01, Backlight > 0x80
10. 22 [HU_eMMC_Health DID] → Health < 0x03 (good, not critical)
11. 22 [HU_Demo_Mode DID] → 0x00 (demo mode OFF)
12. 22 [HU_FirstRun_Config DID] → 0x00 (wizard will appear for customer)
13. 2F [AMP_CH1..CH8 DID] 03 [1kHz tone] → all channels produce audio (IO control)
14. 22 [HU_GPS_Status DID] → GPS fix within 120 seconds in open sky
15. All results PASS → vehicle released for delivery
```
**R:** Comprehensive 15-point HU/Infotainment PDI test completed. HU confirmed with correct SW, valid licenses, functional hardware, zero DTCs, and correct market configuration. Vehicle ready for customer delivery with fully functional infotainment system.

---
*File: 05_infotainment_star_scenarios.md | 100 UDS Cases | Infotainment / Head Unit | April 2026*
