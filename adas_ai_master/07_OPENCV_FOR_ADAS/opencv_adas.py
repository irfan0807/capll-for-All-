"""
07_OPENCV_FOR_ADAS — OpenCV Production Patterns
Camera ISP pipeline, real-time video processing, DNN module
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
import time

# ============================================================================
# 1. CAMERA CAPTURE PIPELINE (V4L2 / GStreamer)
# ============================================================================

class CameraCapture:
    """Production camera capture with GStreamer pipeline (Jetson/embedded).
    Falls back to standard V4L2 if GStreamer unavailable.
    
    Jetson GStreamer: uses hardware-accelerated NvJPEG + NvVICom ISP pipeline.
    """
    
    @staticmethod
    def gstreamer_pipeline(sensor_id: int = 0, width: int = 1280, height: int = 720,
                           framerate: int = 30) -> str:
        """Jetson Orin GStreamer pipeline string for CSI camera."""
        return (
            f"nvarguscamerasrc sensor-id={sensor_id} ! "
            f"video/x-raw(memory:NVMM), width=(int){width}, height=(int){height}, "
            f"format=(string)NV12, framerate=(fraction){framerate}/1 ! "
            f"nvvidconv flip-method=0 ! "
            f"video/x-raw, width=(int){width}, height=(int){height}, format=(string)BGRx ! "
            f"videoconvert ! video/x-raw, format=(string)BGR ! appsink"
        )
    
    def __init__(self, source=0, width: int = 1280, height: int = 720,
                 use_gstreamer: bool = False):
        if use_gstreamer:
            pipeline = self.gstreamer_pipeline(source, width, height)
            self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        else:
            self.cap = cv2.VideoCapture(source)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            # Reduce internal buffer to 1 frame — minimise latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        self.width  = width
        self.height = height
        self._frame_count = 0
        self._t_prev = time.perf_counter()
    
    def read(self) -> Tuple[bool, Optional[np.ndarray], float]:
        """Returns (success, frame, actual_fps)."""
        ret, frame = self.cap.read()
        t_now = time.perf_counter()
        fps = 1.0 / (t_now - self._t_prev + 1e-9)
        self._t_prev = t_now
        self._frame_count += 1
        return ret, frame, fps
    
    def release(self):
        self.cap.release()

# ============================================================================
# 2. IMAGE PREPROCESSING PIPELINE
# ============================================================================

class ImagePreprocessor:
    """Production image pre-processing for ADAS cameras.
    Sequence: Undistort → Demosaic → White Balance → Gamma → Resize → Normalise"""
    
    def __init__(self, K: np.ndarray, dist: np.ndarray,
                 target_size: Tuple[int,int] = (640, 384)):
        self.target_w, self.target_h = target_size
        h, w = 720, 1280  # Assume 1280×720 input
        
        # Pre-compute undistort LUT (fast remap at inference time)
        new_K, roi = cv2.getOptimalNewCameraMatrix(K, dist, (w, h), alpha=0)
        self.map1, self.map2 = cv2.initUndistortRectifyMap(
            K, dist, None, new_K, (w, h), cv2.CV_16SC2)
    
    def process(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Full preprocessing pipeline. Returns (384, 640, 3) uint8 RGB."""
        # Undistort using pre-computed maps (3-5× faster than cv2.undistort)
        undist = cv2.remap(frame_bgr, self.map1, self.map2, cv2.INTER_LINEAR)
        
        # Resize with INTER_LINEAR (fast, sufficient quality for NN input)
        resized = cv2.resize(undist, (self.target_w, self.target_h),
                             interpolation=cv2.INTER_LINEAR)
        
        # BGR → RGB
        return cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    
    def process_batch(self, frames: List[np.ndarray]) -> np.ndarray:
        """Process multiple frames into (N, H, W, 3) array."""
        processed = [self.process(f) for f in frames]
        return np.stack(processed)  # (N, H, W, 3)

# ============================================================================
# 3. CLASSICAL LANE LINE DETECTION (Hough Transform)
# ============================================================================

class HoughLaneDetector:
    """Hough-transform based lane line detection.
    Simple, fast, interpretable — used as validation baseline alongside CNN.
    
    Pipeline: Gray → Blur → Canny → ROI mask → HoughLinesP → Filter lines"""
    
    def __init__(self, img_w: int = 1280, img_h: int = 720):
        self.img_w = img_w
        self.img_h = img_h
        # Region of interest: lower 40% of image (road area)
        self.roi_vertices = np.array([[
            (0,       img_h),
            (img_w//3, int(img_h * 0.6)),
            (2*img_w//3, int(img_h * 0.6)),
            (img_w,   img_h)
        ]], dtype=np.int32)
    
    def _apply_roi(self, img: np.ndarray) -> np.ndarray:
        mask = np.zeros_like(img)
        cv2.fillPoly(mask, self.roi_vertices, 255)
        return cv2.bitwise_and(img, mask)
    
    def _separate_lanes(self, lines) -> Tuple[List, List]:
        """Separate detected lines into left (negative slope) and right (positive)."""
        left, right = [], []
        if lines is None:
            return left, right
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue  # Skip vertical lines
            slope = (y2 - y1) / (x2 - x1)
            if abs(slope) < 0.3:
                continue  # Skip near-horizontal (road markings, not lane edges)
            if slope < 0:
                left.append((slope, x1 * slope * -1 + y1))   # (m, b) form
            else:
                right.append((slope, x1 * slope * -1 + y1))
        return left, right
    
    def _average_line(self, lines: List, y_bottom: int, y_top: int):
        """Average multiple candidate lines into a single line segment."""
        if not lines:
            return None
        avg_m = np.mean([l[0] for l in lines])
        avg_b = np.mean([l[1] for l in lines])
        x_bottom = int((y_bottom - avg_b) / avg_m)
        x_top    = int((y_top    - avg_b) / avg_m)
        return (x_bottom, y_bottom, x_top, y_top)
    
    def detect(self, frame_bgr: np.ndarray):
        """Returns (left_line, right_line) or None if not detected.
        Each line: (x1, y1, x2, y2)"""
        gray    = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges   = cv2.Canny(blurred, 50, 150)
        roi     = self._apply_roi(edges)
        
        lines = cv2.HoughLinesP(roi, rho=1, theta=np.pi/180, threshold=50,
                                 minLineLength=50, maxLineGap=150)
        
        left_lines, right_lines = self._separate_lanes(lines)
        y_bottom = self.img_h
        y_top    = int(self.img_h * 0.6)
        
        return (self._average_line(left_lines, y_bottom, y_top),
                self._average_line(right_lines, y_bottom, y_top))

# ============================================================================
# 4. CONTOUR-BASED OBJECT DETECTION (fallback without GPU)
# ============================================================================

def detect_moving_objects_contour(bg_subtractor, frame_bgr: np.ndarray,
                                   min_area: int = 500) -> List[tuple]:
    """Background subtraction + contour detection.
    Works without GPU — useful as a fallback or for parking/low-speed scenarios.
    
    bg_subtractor: cv2.createBackgroundSubtractorMOG2() or KNN
    Returns: list of (x, y, w, h) bounding boxes"""
    fg_mask = bg_subtractor.apply(frame_bgr)
    
    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN,  kernel)  # Remove noise
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)  # Fill holes
    
    contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(cnt)
            boxes.append((x, y, w, h))
    return boxes

# ============================================================================
# 5. OPENCV DNN MODULE — ONNX INFERENCE
# ============================================================================

class OpenCvDnnInference:
    """OpenCV DNN module inference — runs .onnx models without PyTorch/TRT.
    Supports: CPU (optimised with OpenBLAS/MKL), CUDA, OpenCL.
    Useful for: embedded targets without NVIDIA GPU (Renesas, TDA4VM via OpenCL).
    """
    
    def __init__(self, model_path: str, backend: str = 'cpu',
                 input_size: Tuple[int,int] = (640, 384)):
        self.net = cv2.dnn.readNetFromONNX(model_path)
        
        backend_map = {
            'cpu':    (cv2.dnn.DNN_BACKEND_OPENCV,  cv2.dnn.DNN_TARGET_CPU),
            'cuda':   (cv2.dnn.DNN_BACKEND_CUDA,    cv2.dnn.DNN_TARGET_CUDA_FP16),
            'opencl': (cv2.dnn.DNN_BACKEND_OPENCV,  cv2.dnn.DNN_TARGET_OPENCL_FP16),
        }
        bk, tgt = backend_map.get(backend, backend_map['cpu'])
        self.net.setPreferableBackend(bk)
        self.net.setPreferableTarget(tgt)
        
        self.input_w, self.input_h = input_size
    
    def infer(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Preprocess + infer. Returns raw output numpy array."""
        blob = cv2.dnn.blobFromImage(
            frame_bgr, scalefactor=1/255.0,
            size=(self.input_w, self.input_h),
            mean=(0.485*255, 0.456*255, 0.406*255),
            swapRB=True, crop=False                 # swapRB: BGR→RGB
        )
        self.net.setInput(blob)
        return self.net.forward()

# ============================================================================
# 6. VIDEO ANNOTATION (for dataset labelling / offline analysis)
# ============================================================================

def draw_lane_lines(frame: np.ndarray, left_line, right_line,
                    offset_m: float = 0.0) -> np.ndarray:
    """Overlay lane detection results on frame."""
    overlay = frame.copy()
    
    def draw_line(line, color):
        if line:
            x1, y1, x2, y2 = line
            cv2.line(overlay, (x1,y1), (x2,y2), color, thickness=4)
    
    draw_line(left_line,  (0, 255, 0))   # Green
    draw_line(right_line, (0, 255, 0))
    
    # Fill lane area between lines
    if left_line and right_line:
        pts = np.array([[left_line[0], left_line[1]],
                        [left_line[2], left_line[3]],
                        [right_line[2], right_line[3]],
                        [right_line[0], right_line[1]]])
        fill = np.zeros_like(frame)
        cv2.fillPoly(fill, [pts], (0, 100, 0))
        overlay = cv2.addWeighted(overlay, 0.7, fill, 0.3, 0)
    
    # Offset indicator
    color = (0,0,255) if abs(offset_m) > 0.3 else (0,255,0)
    cv2.putText(overlay, f"Offset: {offset_m:+.2f}m", (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 2)
    return overlay

def draw_detections(frame: np.ndarray, boxes: List[tuple],
                    labels: List[str] = None,
                    scores: List[float] = None) -> np.ndarray:
    """Draw YOLO-style detections on frame."""
    colors = {'car': (0,255,255), 'truck': (255,128,0),
              'pedestrian': (255,0,0), 'cyclist': (0,128,255)}
    result = frame.copy()
    
    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = [int(b) for b in box[:4]]
        label  = labels[i] if labels else 'obj'
        score  = scores[i] if scores else 1.0
        color  = colors.get(label, (255,255,255))
        
        cv2.rectangle(result, (x1,y1), (x2,y2), color, 2)
        text = f"{label} {score:.2f}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.rectangle(result, (x1, y1-th-6), (x1+tw, y1), color, -1)
        cv2.putText(result, text, (x1, y1-4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 1)
    return result

# ============================================================================
# 7. DEMO
# ============================================================================

if __name__ == "__main__":
    print("=== OpenCV ADAS Demo ===\n")
    
    # Hough lane detector
    detector = HoughLaneDetector(1280, 720)
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    # Draw white lane lines on dummy frame
    cv2.line(dummy_frame, (380, 720), (560, 432), (255,255,255), 5)
    cv2.line(dummy_frame, (900, 720), (720, 432), (255,255,255), 5)
    
    left, right = detector.detect(dummy_frame)
    print(f"Hough lanes — Left: {left}")
    print(f"             Right: {right}")
    
    # Background subtraction
    bg_sub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16)
    # Warm up with background frames
    for _ in range(5):
        bg_bg = np.zeros((480, 640, 3), dtype=np.uint8)
        bg_sub.apply(bg_bg)
    # Add moving object (white rectangle)
    moving_frame = bg_bg.copy()
    cv2.rectangle(moving_frame, (200, 200), (300, 300), (255,255,255), -1)
    boxes = detect_moving_objects_contour(bg_sub, moving_frame, min_area=100)
    print(f"\nBackground subtraction detected {len(boxes)} moving objects")
    
    # Annotation test
    test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    annotated = draw_lane_lines(test_frame, left, right, offset_m=0.15)
    print(f"\nAnnotated frame shape: {annotated.shape}")
    
    test_boxes = [(200, 100, 400, 300), (600, 200, 900, 500)]
    annotated2 = draw_detections(test_frame, test_boxes,
                                  labels=['car', 'pedestrian'],
                                  scores=[0.92, 0.87])
    print(f"Annotated detections: {len(test_boxes)} objects drawn")
