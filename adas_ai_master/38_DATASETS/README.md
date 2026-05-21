# 38 — ADAS/AD Datasets

## Overview
Comprehensive guide to public and proprietary datasets used for training and validating ADAS AI models: object detection, lane detection, depth estimation, segmentation, and full AD stacks.

---

## 1. Major Public Datasets

| Dataset | Size | Sensors | Labels | Primary Use |
|---------|------|---------|--------|------------|
| KITTI | 15K frames | Camera, LiDAR, GPS | 3D BB, lanes, depth | Detection, SLAM, depth |
| NuScenes (Motional) | 1,000 scenes | 6 cameras, 1 LiDAR, 5 radar | 3D BB, tracking, maps | Full perception |
| Waymo Open | 2,030 scenes | 5 cameras, 5 LiDAR | 3D BB, tracking | Detection, tracking |
| ONCE (autonomous) | 1M frames | 1 LiDAR, 7 cameras | 3D BB | Large-scale detection |
| nuPlan | 1500h driving | Multi-camera | Planning scenarios | Planning validation |
| Argoverse 2 | 1000 scenes | 7 cameras, 2 LiDAR | 3D BB, HD map | Motion forecasting |
| BDD100K (Berkeley) | 100K videos | Camera | 2D BB, lanes, segs | 2D detection, diversity |
| CityScapes | 5K images | Camera (stereo) | Semantic segmentation | Seg research |
| LISA | 6K frames | Camera | Traffic signs | TSR training |
| TuSimple | 128K frames | Camera | Lane polynomials | Lane detection |

---

## 2. Dataset Format Comparison

### KITTI Format
```
# Image: /image_2/000001.png
# Label: /label_2/000001.txt

# Each line: type truncated occluded alpha x1 y1 x2 y2 h w l x y z ry score
Car 0.00 0 -1.57 587.01 173.33 614.12 200.12 1.65 1.67 3.64 -0.65 1.71 46.70 -1.59

# Columns: class | trunc | occ | alpha | 2D bbox (x1y1x2y2) | 3D size (hwl) | 3D loc (xyz) | yaw | score
```

### NuScenes JSON Format
```python
# NuScenes sample annotation
{
    "token": "abc123",
    "sample_token": "sample_token_xyz",
    "category_name": "vehicle.car",
    "translation": [373.214, 1130.48, 0.8],   # [x, y, z] in m (map frame)
    "size":        [1.975, 4.77, 1.67],         # [width, length, height]
    "rotation":    [0.911, 0, 0, 0.41],         # Quaternion [w, x, y, z]
    "num_lidar_pts": 95,
    "num_radar_pts": 6,
    "visibility_token": "4",                    # 1-4 (4 = fully visible)
    "attribute_tokens": ["vehicle.stopped"]
}
```

---

## 3. Loading Datasets in Python

```python
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import json


class KITTIDetectionDataset:
    """PyTorch-compatible KITTI 3D Object Detection dataset loader."""
    
    CLASSES = ['Car', 'Pedestrian', 'Cyclist', 'Van', 'Truck', 'Misc']
    
    def __init__(self, root: str, split: str = 'train'):
        self.root       = Path(root)
        self.split      = split
        self.image_dir  = self.root / 'image_2'
        self.label_dir  = self.root / 'label_2'
        self.calib_dir  = self.root / 'calib'
        
        split_file = self.root / 'ImageSets' / f'{split}.txt'
        self.samples = split_file.read_text().splitlines() \
                       if split_file.exists() else []
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Dict:
        sample_id = self.samples[idx]
        
        # Load labels
        label_path = self.label_dir / f'{sample_id}.txt'
        annotations = self._load_labels(label_path)
        
        return {
            'sample_id':   sample_id,
            'annotations': annotations,
        }
    
    def _load_labels(self, path: Path) -> List[Dict]:
        if not path.exists():
            return []
        
        annotations = []
        for line in path.read_text().splitlines():
            parts = line.split()
            if len(parts) < 15:
                continue
            
            cls = parts[0]
            if cls not in self.CLASSES:
                continue
            
            annotations.append({
                'class':     cls,
                'truncated': float(parts[1]),
                'occluded':  int(parts[2]),
                'alpha':     float(parts[3]),
                'bbox_2d':   [float(x) for x in parts[4:8]],  # x1,y1,x2,y2
                'dim_3d':    [float(x) for x in parts[8:11]], # h,w,l
                'loc_3d':    [float(x) for x in parts[11:14]],# x,y,z
                'rot_y':     float(parts[14]),
            })
        
        return annotations


class NuScenesLoader:
    """NuScenes dataset loader (requires nuscenes-devkit installed)."""
    
    def __init__(self, dataroot: str, version: str = 'v1.0-mini'):
        try:
            from nuscenes.nuscenes import NuScenes
            self.nusc = NuScenes(version=version, dataroot=dataroot)
        except ImportError:
            print("nuscenes-devkit not installed. Demo mode.")
            self.nusc = None
    
    def get_sample_data(self, sample_token: str) -> Dict:
        """Get sensor data and annotations for one sample."""
        if self.nusc is None:
            return {}
        
        sample = self.nusc.get('sample', sample_token)
        
        # Get front camera
        cam_token = sample['data']['CAM_FRONT']
        cam_data  = self.nusc.get('sample_data', cam_token)
        
        # Get annotations
        anns = [self.nusc.get('sample_annotation', a)
                for a in sample['anns']]
        
        return {
            'image_path': cam_data['filename'],
            'annotations': anns,
            'timestamp':  sample['timestamp'],
        }
```

---

## 4. Data Augmentation for ADAS

```python
import albumentations as A
import numpy as np

# ADAS-specific augmentation pipeline
adas_aug = A.Compose([
    # Geometric: simulate camera mounting variation
    A.RandomCrop(width=1280, height=720, p=0.5),
    A.HorizontalFlip(p=0.0),         # Never flip — left/right has meaning (traffic rules)
    A.ShiftScaleRotate(shift_limit=0.02, scale_limit=0.1,
                        rotate_limit=3, p=0.5),
    
    # Colour/photometric: simulate lighting changes
    A.RandomBrightnessContrast(brightness_limit=0.4,
                                 contrast_limit=0.4, p=0.7),
    A.HueSaturationValue(hue_shift_limit=10, p=0.3),
    A.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, p=0.5),
    
    # Noise: simulate camera sensor noise
    A.GaussNoise(var_limit=(10, 50), p=0.3),
    A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=0.2),
    
    # Weather simulation
    A.RandomRain(blur_value=3, brightness_coefficient=0.8, p=0.2),
    A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.4, p=0.15),
    A.RandomSunFlare(flare_roi=(0,0,1,0.5), p=0.1),
    
    # Blur: simulate motion blur or lens defocus
    A.MotionBlur(blur_limit=5, p=0.2),
    A.Blur(blur_limit=3, p=0.1),
    
], bbox_params=A.BboxParams(format='pascal_voc',
                              label_fields=['class_labels'],
                              min_visibility=0.3))
```

---

## 5. Dataset Statistics for Training

| Dataset | Vehicles | Pedestrians | Cyclists | Night % | Rain % |
|---------|---------|------------|---------|--------|--------|
| KITTI | 28,742 | 4,487 | 1,627 | 0% | 0% |
| NuScenes train | 318,760 | 120,195 | 14,028 | 25% | 10% |
| Waymo Open | 8.1M | 2.5M | 210K | 30% | 8% |
| BDD100K | 1.1M | 97K | 9K | 47% | 13% |

**Class imbalance:** Pedestrians ~10× fewer than vehicles → use focal loss or oversampling.

---

## 6. Proprietary OEM Datasets

OEM datasets (not public) typically contain:
- 100M+ frames from test fleet (100+ vehicles, multiple countries)
- Corner cases specifically collected: edge weather, construction, unusual scenarios
- Anonymised (pedestrian faces/plates blurred — GDPR)
- Multi-sensor (camera + radar + LiDAR time-synchronised)

Tesla releases: no public dataset, but publishes FSD improvement statistics.  
Waymo releases: Waymo Open Dataset (public portion of production data).  
Bosch/Continental: no public datasets — internal only.

---

## 7. Interview Q&A

### L1
**Q: What is the difference between KITTI and NuScenes and which would you use for training a 3D object detector?**  
A: KITTI: 15,000 frames, single drive session in Karlsruhe Germany, only daytime clear weather, 1 camera + 1 LiDAR, smaller scale — good for benchmarking and research. NuScenes: 1,000 scenes, 6 cameras (360°), 1 LiDAR, 5 radars, 40% night/rain scenes, diverse locations — more representative of production conditions. For training a production 3D detector: NuScenes preferred (diversity, multi-sensor, weather coverage). For research/benchmarking: KITTI (well-established baselines). In production: neither alone — fine-tune on OEM fleet data after pre-training on public datasets.

### L2
**Q: How do you handle class imbalance in ADAS object detection datasets?**  
A: Pedestrians are 10× rarer than vehicles. Strategies: (1) Focal loss: α-balanced focal loss reduces contribution of easy examples (cars, common), focuses on hard examples (pedestrians, cyclists) — standard in ADAS; (2) Oversampling: repeat frames containing pedestrians 3× in training batches; (3) Copy-paste augmentation: cut pedestrian patches from rare images, paste onto other scenes at realistic scales; (4) Per-class weighting in mAP: define minimum pedestrian AP threshold (e.g., 80%) as acceptance gate — forces model to not sacrifice pedestrian performance for overall mAP; (5) Hard negative mining: identify frames where model repeatedly misses pedestrians → oversample those frames in next training run.

### L3
**Q: Design a data pipeline for collecting and processing 10M camera frames for ADAS model training.**  
A: (1) Collection: 100 test vehicles globally, 4 cameras each, 30fps, 1 hour/day drive → 100×4×30×3600 = 43.2M frames/day; store raw H.264 video to NAS (400GB/vehicle/day). (2) Ingestion: GPU cluster decodes video → JPEG frames (90% quality); metadata: GPS, CAN signals (speed, wipers = weather proxy), timestamp stored in database. (3) Auto-labelling: run pre-trained detector ensemble (YOLOv8x + DINO + PointPillars) on all frames; store initial labels; human review on 2% random sample + all low-confidence cases. (4) Quality filter: remove blur score < 100 (Laplacian variance), night frames without illumination > 50 lux (if night dataset not needed), duplicate frames (perceptual hash dedup). (5) Diversity sampling: cluster embeddings (ResNet50 features, K-means 1000 clusters); sample proportionally to cluster size → ensures diversity. (6) GDPR: face blur (RetinaFace), plate blur (YOLO plate model), applied before storage. (7) Storage: 10M frames × 500KB = 5TB; distributed across S3 with metadata in PostgreSQL; versioned by collection date, OEM region, weather tag. (8) Training readiness: final 10M balanced set (equal day/night, weather distribution); TFDS or WebDataset format for fast streaming.
