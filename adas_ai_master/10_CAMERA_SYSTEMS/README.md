# 10 — Camera Systems for ADAS

## Overview
Camera types, lens selection, ISP pipeline, and camera-specific AI challenges for automotive applications. Covers mono, stereo, fisheye, and surround-view systems.

---

## 1. Camera Types in Automotive

| Camera Type | FOV | Range | Primary Use |
|------------|-----|-------|------------|
| Long-range mono (front) | 25-50° | 200-250m | ACC, AEB, TSR |
| Medium-range (front) | 60-80° | 80-100m | LKA, LDA, pedestrian |
| Wide/fisheye (surround) | 180-190° | 3-10m | Parking, BSD |
| Stereo front | 45-60° | 0-50m (stereo range) | AEB, close-range depth |
| Interior (DMS) | 60° | 0.5-1.5m | Driver monitoring |

---

## 2. Lens Selection Parameters

**Focal length for front ADAS camera:**
```
FOV = 2 × arctan(sensor_width / (2 × focal_length))
For 1/2.7" sensor (5.37mm wide), 50° HFOV:
  f = 5.37 / (2 × tan(25°)) = 5.75mm
For 25° HFOV (long-range):
  f = 5.37 / (2 × tan(12.5°)) = 12.1mm
```

**Resolution requirements:**
- At 250m, a car (1.8m wide) subtends: `1.8/250 = 7.2 mrad`
- For recognition (minimum 10px on target): `pixel_size = 7.2mrad / 10 = 0.72mrad/px`
- At 50° HFOV, 1920px: `50°/1920 = 1.45mrad/px` — marginal at 250m
- Conclusion: Long-range detection requires 2MP+ camera or tighter FOV

---

## 3. ISP (Image Signal Processor) Pipeline

```
RAW (Bayer) ──► Demosaic ──► Lens Shading ──► White Balance
     │          (bilinear,      Correction     (grey world,
     │           Malvar)        (polynomial)    AWB)
     │
     ▼
Noise Reduction ──► Tone Mapping ──► Gamma ──► BGR output
(temporal NR,        (HDR compress)   (γ=2.2)
 bilateral)
```

**Why ISP matters for ADAS AI:**
- RGB values from ISP affect training data statistics
- ISP settings (gamma, tone mapping) must be identical between training data collection and deployment
- Dynamic range: automotive HDR cameras (120dB) require tonemapping before NN — otherwise overexposed/underexposed regions wash out features
- Night driving: noise amplified by ISP gain → CNN must be trained with noisy samples

---

## 4. High Dynamic Range (HDR) Cameras

**Problem:** Typical 8-bit camera: DR ≈ 60dB. Road scene: tunnel exit (100,000 lux) + shadow (1 lux) = 100dB DR. Result: clipped highlights + crushed shadows.

**HDR solutions:**
1. **Multi-exposure fusion** — capture 2-3 frames at different exposures, merge ISP
2. **Wide-DR sensor** — logarithmic pixels (OmniVision OX05B, Sony IMX728)
3. **Tone mapping** — Reinhard/ACES for display; ADAS uses linear HDR internally

**For ADAS perception:**
```python
# Don't apply display gamma (sRGB) before NN input
# ADAS CNNs trained on linear-light or HDR images perform better
# in challenging lighting vs sRGB-gamma images

# Linear HDR → NN input normalisation:
hdr_linear = raw_pixels / 65535.0  # 16-bit linear
# NO gamma correction — CNN learns directly from linear light
```

---

## 5. Rolling Shutter vs Global Shutter

| Property | Rolling Shutter | Global Shutter |
|----------|----------------|----------------|
| Read mechanism | Row-by-row | All rows simultaneously |
| Cost | Low | High (2-3×) |
| Motion artifacts | Skew, wobble | None |
| ADAS suitability | OK for <100kph | Required for fast-moving targets |

**Rolling shutter correction:**
```python
# Correct rolling shutter using IMU data
# Each row k has timestamp offset: t_k = t_0 + k * row_time
# row_time = 1/(fps × frame_height) ≈ 0.04ms per row at 30fps, 720p
# Apply rotation/translation correction per row using gyroscope
```

---

## 6. Camera Mounting and Vibration

**ECU requirement:** Camera must stay calibrated across temperature range (-40°C to +85°C), vibration (JESD22-B103), and shock (100G, 6ms).

**Production calibration strategy:**
1. Factory calibration at end-of-line (EOL) tester — reprojection error < 0.5px
2. Online recalibration using vanishing point estimation (lane lines, building edges)
3. Delta calibration stored in NVM, applied to extrinsic transform

---

## 7. Camera in AI Training Pipeline

```python
# Dataset augmentation matching deployment ISP settings:
import albumentations as A

# Simulate ISP artifacts during training:
train_transform = A.Compose([
    A.ImageCompression(quality_lower=75, p=0.3),   # JPEG ISP artifacts
    A.GaussNoise(var_limit=(0, 50), p=0.3),          # Sensor noise
    A.ColorJitter(brightness=0.3, contrast=0.3,      # ISP variation
                  saturation=0.2, hue=0.1, p=0.5),
    A.Defocus(radius=(1,3), p=0.1),                  # Lens defocus
])
```

---

## 8. Interview Q&A

### L1
**Q: What is Bayer pattern and why does demosaic matter for ADAS?**  
A: Camera sensors have one photodiode per pixel, each covered with a colour filter (RGGB pattern). Demosaicing interpolates missing colour values. For ADAS: low-quality demosaicing creates colour artifacts (zipper effect) at sharp edges — this confuses lane edge detectors and creates false gradients in Canny edge detection.

### L2
**Q: How does rolling shutter cause problems in highway ADAS and how is it mitigated?**  
A: At 130kph, vehicle moves 36m/s. With 30fps camera and 720 rows: row read time = 0.04ms. Top-to-bottom time = 29ms. The front of the vehicle is captured 29ms before the rear — at 36m/s this causes ~1m skew in the detected bounding box. Mitigation: (1) Global shutter camera; (2) IMU-based rolling shutter correction per row; (3) In tracking: accept larger bounding box uncertainty at high speed.

### L3
**Q: Design a surround-view parking camera system (4 fisheye cameras) for a production vehicle.**  
A: (1) Four fisheye cameras (185° FOV) at front bumper, rear, and both mirrors — 2m mounting height. (2) Individual camera calibration: standard checkerboard for intrinsics + distortion (fisheye model in OpenCV: `cv2.fisheye.calibrate`). (3) Extrinsic calibration: ground-plane pattern visible in 2+ cameras simultaneously. (4) Stitch: `cv2.remap()` with precomputed LUT to project each fisheye to top-down cylinder coordinates; blend overlap regions with seam at ~1m from camera. (5) Top-down synthesis: project all 4 cameras to ground plane, fuse with weighted blend (closer camera has more weight). (6) Processing: runs on Renesas R-Car V3H ISP at <2ms per frame, displayed at 15fps for parking.
