"""
02_PYTHON_FOR_ADAS_AI — Production Python Pipelines
Author: ADAS AI Engineer
Purpose: NumPy/PyTorch/OpenCV for real-time ADAS inference
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import cv2
import time
from typing import List, Tuple, Optional
from dataclasses import dataclass

# ============================================================================
# 1. REAL-TIME CAMERA FRAME PIPELINE (NumPy + OpenCV)
# ============================================================================

@dataclass
class FrameMetadata:
    timestamp_ms: float
    frame_id: int
    width: int
    height: int
    camera_id: str

class CameraFramePipeline:
    """Production-grade camera pre-processing pipeline.
    Matches what runs on TDA4VM / NVIDIA Orin camera ISP pipeline."""
    
    def __init__(self, target_w: int = 640, target_h: int = 384):
        self.target_w = target_w
        self.target_h = target_h
        # ImageNet mean/std — used for pretrained CNN backbones
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        self._proc_times = []

    def preprocess(self, frame_bgr: np.ndarray) -> Tuple[torch.Tensor, FrameMetadata]:
        t0 = time.perf_counter()
        
        # 1. Resize (bilinear — faster than bicubic, sufficient for NN input)
        resized = cv2.resize(frame_bgr, (self.target_w, self.target_h),
                             interpolation=cv2.INTER_LINEAR)
        
        # 2. BGR → RGB (OpenCV is BGR by default, PyTorch models expect RGB)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # 3. Normalise to float32 [0, 1], then ImageNet normalise
        img = rgb.astype(np.float32) / 255.0
        img = (img - self.mean) / self.std
        
        # 4. HWC → CHW (PyTorch tensor format)
        chw = np.transpose(img, (2, 0, 1))
        
        # 5. Add batch dimension: CHW → NCHW
        tensor = torch.from_numpy(chw).unsqueeze(0)  # (1, 3, H, W)
        
        self._proc_times.append((time.perf_counter() - t0) * 1000)
        meta = FrameMetadata(
            timestamp_ms=time.time() * 1000,
            frame_id=len(self._proc_times),
            width=self.target_w, height=self.target_h,
            camera_id="front_camera"
        )
        return tensor, meta

    def avg_latency_ms(self) -> float:
        return np.mean(self._proc_times[-100:]) if self._proc_times else 0.0

# ============================================================================
# 2. PYTORCH DATASET — KITTI-STYLE
# ============================================================================

class KittiObjectDataset(Dataset):
    """Simplified KITTI object detection dataset loader.
    Real KITTI has 7481 training images with velodyne + camera + calib."""
    
    def __init__(self, image_paths: List[str], label_paths: List[str],
                 transform=None, img_size=(640, 384)):
        self.image_paths = image_paths
        self.label_paths = label_paths
        self.transform   = transform
        self.img_size    = img_size
        self.pipeline    = CameraFramePipeline(*img_size)
        
    def __len__(self): return len(self.image_paths)
    
    def __getitem__(self, idx):
        # Load image
        img = cv2.imread(self.image_paths[idx])
        if img is None:
            img = np.zeros((375, 1242, 3), dtype=np.uint8)  # KITTI default size
        tensor, _ = self.pipeline.preprocess(img)
        
        # Load KITTI label: "Car 0.00 0 -1.57 614.24 181.78 727.31 284.77 1.57 1.73 4.15 2.28 1.55 46.73 -1.59"
        boxes = self._parse_kitti_label(self.label_paths[idx])
        return tensor.squeeze(0), boxes
    
    def _parse_kitti_label(self, path: str) -> torch.Tensor:
        """Parse KITTI label file into (N, 5) tensor: [class, x1, y1, x2, y2]."""
        boxes = []
        class_map = {'Car': 0, 'Pedestrian': 1, 'Cyclist': 2, 'Van': 3, 'Truck': 4}
        try:
            with open(path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts[0] in class_map and parts[0] != 'DontCare':
                        cls_id = class_map[parts[0]]
                        x1, y1, x2, y2 = float(parts[4]), float(parts[5]), \
                                          float(parts[6]), float(parts[7])
                        boxes.append([cls_id, x1, y1, x2, y2])
        except FileNotFoundError:
            pass
        return torch.tensor(boxes, dtype=torch.float32) if boxes else torch.zeros((0, 5))

    @staticmethod
    def collate_fn(batch):
        """Custom collate: images → stacked tensor, labels → list (variable len)."""
        images = torch.stack([item[0] for item in batch])
        labels = [item[1] for item in batch]  # list of tensors (different sizes)
        return images, labels

# ============================================================================
# 3. PYTORCH TRAINING LOOP — PRODUCTION PATTERN
# ============================================================================

class AdasTrainer:
    """Production PyTorch training loop with:
    - Gradient clipping (prevents exploding gradients)
    - Mixed precision (FP16 — 2× faster on NVIDIA GPU)
    - Learning rate scheduling (cosine annealing)
    - Checkpoint saving
    """
    
    def __init__(self, model: nn.Module, device: str = 'cuda'):
        self.model  = model.to(device)
        self.device = device
        self.scaler = torch.cuda.amp.GradScaler(enabled=(device == 'cuda'))
        
    def train_epoch(self, loader: DataLoader, optimizer: optim.Optimizer,
                    criterion: nn.Module, epoch: int) -> float:
        self.model.train()
        total_loss = 0.0
        
        for batch_idx, (images, targets) in enumerate(loader):
            images = images.to(self.device)
            
            optimizer.zero_grad()
            
            # Mixed precision forward pass (FP16 on GPU)
            with torch.cuda.amp.autocast(enabled=(self.device == 'cuda')):
                outputs = self.model(images)
                loss = criterion(outputs, targets)
            
            # Backward + gradient scaling (for FP16 stability)
            self.scaler.scale(loss).backward()
            
            # Gradient clipping — CRITICAL for ADAS models (prevents NaN weights)
            self.scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=10.0)
            
            self.scaler.step(optimizer)
            self.scaler.update()
            
            total_loss += loss.item()
            
            if batch_idx % 50 == 0:
                print(f"Epoch {epoch} [{batch_idx}/{len(loader)}] Loss: {loss.item():.4f}")
        
        return total_loss / len(loader)
    
    def save_checkpoint(self, path: str, epoch: int, loss: float, optimizer):
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'loss': loss,
        }, path)
        print(f"Checkpoint saved: {path}")

# ============================================================================
# 4. NUMPY SENSOR DATA PIPELINE
# ============================================================================

class RadarDataPipeline:
    """Process raw radar point cloud (range, azimuth, elevation, velocity, SNR).
    Mirrors what runs in AUTOSAR SWC before ML inference."""
    
    def __init__(self, max_range_m: float = 200.0, min_snr_db: float = 12.0):
        self.max_range = max_range_m
        self.min_snr   = min_snr_db
    
    def preprocess(self, detections: np.ndarray) -> np.ndarray:
        """
        detections: (N, 5) — [range_m, azimuth_deg, elev_deg, vel_mps, snr_db]
        returns: filtered + normalised (N', 6) with Cartesian XY added
        """
        if len(detections) == 0:
            return np.zeros((0, 6), dtype=np.float32)
        
        # Filter: range + SNR quality gate
        valid = (detections[:, 0] < self.max_range) & \
                (detections[:, 4] > self.min_snr)
        det = detections[valid]
        
        # Convert polar → Cartesian
        az_rad = np.deg2rad(det[:, 1])
        x = det[:, 0] * np.cos(az_rad)   # Longitudinal (forward)
        y = det[:, 0] * np.sin(az_rad)   # Lateral
        
        # Normalise for ML input
        x_norm = x / self.max_range
        y_norm = y / 50.0    # ±50m lateral range
        v_norm = det[:, 3] / 55.0  # ±55 m/s relative velocity
        snr_norm = det[:, 4] / 40.0  # 0–40 dB SNR
        
        return np.stack([x, y, x_norm, y_norm, v_norm, snr_norm], axis=1).astype(np.float32)
    
    def compute_ttc(self, x: float, relative_velocity_mps: float,
                    ego_decel_ms2: float = -3.5) -> float:
        """Time-to-collision with deceleration model.
        Returns seconds (99.0 = no collision risk)."""
        if relative_velocity_mps >= 0:  # Not approaching
            return 99.0
        closing_speed = abs(relative_velocity_mps)
        # Quadratic TTC: x + v*t + 0.5*a*t² = 0
        # t = (-v - sqrt(v² + 2*a*x)) / a  (take positive root)
        discriminant = closing_speed**2 + 2.0 * abs(ego_decel_ms2) * x
        if discriminant < 0:
            return 99.0
        t = (closing_speed - np.sqrt(discriminant)) / abs(ego_decel_ms2)
        return max(0.0, t)

# ============================================================================
# 5. QUICK DEMO
# ============================================================================

if __name__ == "__main__":
    print("=== ADAS Python Pipeline Demo ===\n")
    
    # Camera pipeline
    pipeline = CameraFramePipeline(640, 384)
    dummy_frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    tensor, meta = pipeline.preprocess(dummy_frame)
    print(f"Camera: input {dummy_frame.shape} → tensor {tensor.shape}")
    print(f"  Latency: {pipeline.avg_latency_ms():.2f}ms")
    
    # Radar pipeline
    radar_pipe = RadarDataPipeline()
    raw_detections = np.array([
        [45.0,  2.0, 0.0, -10.0, 25.0],  # 45m, 2deg az, -10m/s, 25dB
        [80.0, -1.0, 0.0, -8.0,  18.0],  # 80m, -1deg az, -8m/s, 18dB
        [12.0,  0.5, 0.0,  0.0,   8.0],  # 12m, low SNR (filtered out)
    ])
    processed = radar_pipe.preprocess(raw_detections)
    print(f"\nRadar: {len(raw_detections)} raw → {len(processed)} valid detections")
    
    # TTC
    ttc = radar_pipe.compute_ttc(x=45.0, relative_velocity_mps=-10.0)
    print(f"TTC at 45m, -10m/s: {ttc:.2f}s")
    
    # Kalman Filter (from 01_MATH_FOR_AI)
    print("\nKalman filter demo: see 01_MATH_FOR_AI/README.md")
