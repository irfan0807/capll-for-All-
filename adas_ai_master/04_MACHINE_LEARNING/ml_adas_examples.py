"""
04_MACHINE_LEARNING — Classical ML for ADAS
Scikit-learn: regression, classification, anomaly detection for automotive
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.svm import SVC, OneClassSVM
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, mean_absolute_error
import joblib
from typing import Tuple, List
from dataclasses import dataclass

# ============================================================================
# 1. LANE OFFSET REGRESSION (Ridge Regression)
# ============================================================================

class LaneOffsetRegressor:
    """Predict lateral offset from lane centre using classical ML features.
    
    Input features (11): derived from image processing, NOT raw pixels.
    This is the approach used before CNN-era ADAS (pre-2015 Mobileye).
    
    Features: left/right lane polynomial coefficients + vehicle state
    """
    
    FEATURE_NAMES = [
        'left_a', 'left_b', 'left_c',      # Left lane polynomial
        'right_a', 'right_b', 'right_c',   # Right lane polynomial  
        'yaw_rate_dps',                     # Gyroscope
        'steering_angle_deg',               # Steering wheel angle
        'vehicle_speed_kph',                # Vehicle speed
        'lane_width_m',                     # Estimated lane width
        'curvature_inv_m'                   # 1/radius_of_curvature
    ]
    
    def __init__(self):
        self.model = Pipeline([
            ('scaler', StandardScaler()),
            ('regressor', Ridge(alpha=1.0))  # L2 regularisation avoids overfitting
        ])
        self._trained = False
    
    def generate_synthetic_data(self, n: int = 5000) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data for demo."""
        rng = np.random.default_rng(42)
        X = rng.standard_normal((n, len(self.FEATURE_NAMES))).astype(np.float32)
        # Ground truth: offset is mainly driven by left/right c-coefficients
        y = 0.3 * X[:, 2] - 0.3 * X[:, 5] + 0.05 * X[:, 7] + \
            rng.normal(0, 0.05, n)  # add noise
        return X, y.astype(np.float32)
    
    def train(self, X: np.ndarray, y: np.ndarray):
        X_tr, X_val, y_tr, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        self.model.fit(X_tr, y_tr)
        self._trained = True
        
        y_pred = self.model.predict(X_val)
        mae = mean_absolute_error(y_val, y_pred)
        print(f"Lane Offset Regressor — MAE: {mae*100:.1f}cm")
        return mae
    
    def predict(self, features: np.ndarray) -> float:
        """Returns lateral offset in metres (+ = vehicle is right of centre)."""
        return float(self.model.predict(features.reshape(1, -1))[0])
    
    def save(self, path: str):
        joblib.dump(self.model, path)

# ============================================================================
# 2. ROAD SURFACE CLASSIFICATION (Random Forest)
# ============================================================================

class RoadSurfaceClassifier:
    """Classify road surface: dry / wet / snow / gravel.
    Features from accelerometers (IMU vibration signature) + radar reflectivity.
    
    Why Random Forest for this?
    - Robust to outliers (vibration spikes from potholes)
    - Feature importance explains which sensors matter most
    - Fast inference: ~0.1ms for 100 trees on ARM A53
    """
    
    CLASSES = ['dry', 'wet', 'snow', 'gravel']
    
    def __init__(self):
        self.model = Pipeline([
            ('scaler', StandardScaler()),
            ('clf', RandomForestClassifier(
                n_estimators=100,
                max_depth=8,          # Limit depth → prevent overfitting
                min_samples_leaf=5,   # ADAS models must not be too specialised
                class_weight='balanced',  # Handle imbalanced dataset (rare snow)
                random_state=42,
                n_jobs=2              # Parallelism (limited on ECU)
            ))
        ])
        self._le = LabelEncoder()
    
    def generate_synthetic_data(self, n_per_class: int = 1000):
        """Simulate IMU + radar features for 4 road types."""
        rng = np.random.default_rng(0)
        all_X, all_y = [], []
        
        # Feature layout: [accel_x_rms, accel_y_rms, accel_z_rms, 
        #                   gyro_x, gyro_y, gyro_z,
        #                   radar_reflectivity_dB, radar_noise_floor]
        surface_params = {
            'dry':    {'accel_rms': 0.1, 'radar_ref': -5.0},
            'wet':    {'accel_rms': 0.15, 'radar_ref': -15.0},  # Lower reflectivity
            'snow':   {'accel_rms': 0.08, 'radar_ref': -25.0},  # Very low
            'gravel': {'accel_rms': 0.5, 'radar_ref': -8.0},    # High vibration
        }
        
        for cls, params in surface_params.items():
            a_rms = params['accel_rms']
            r_ref = params['radar_ref']
            X = np.column_stack([
                rng.normal(a_rms, 0.02, n_per_class),   # accel_x_rms
                rng.normal(a_rms, 0.02, n_per_class),   # accel_y_rms
                rng.normal(a_rms*1.5, 0.03, n_per_class),  # accel_z_rms
                rng.normal(0, 0.1, n_per_class),         # gyro_x
                rng.normal(0, 0.1, n_per_class),         # gyro_y
                rng.normal(0, 0.05, n_per_class),        # gyro_z
                rng.normal(r_ref, 3.0, n_per_class),     # radar reflectivity
                rng.normal(-40, 2.0, n_per_class),       # noise floor
            ])
            all_X.append(X)
            all_y.extend([cls] * n_per_class)
        
        return (np.vstack(all_X).astype(np.float32),
                np.array(all_y))
    
    def train(self, X: np.ndarray, y_labels: np.ndarray):
        y = self._le.fit_transform(y_labels)
        X_tr, X_val, y_tr, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model.fit(X_tr, y_tr)
        y_pred = self.model.predict(X_val)
        print("\nRoad Surface Classifier Report:")
        print(classification_report(y_val, y_pred,
                                    target_names=self._le.classes_))
        
        # Feature importance (which sensor matters most?)
        rf = self.model.named_steps['clf']
        feat_names = ['ax_rms','ay_rms','az_rms','gx','gy','gz','radar_ref','noise']
        importances = rf.feature_importances_
        for name, imp in sorted(zip(feat_names, importances), key=lambda x: -x[1]):
            print(f"  {name}: {imp:.3f}")
    
    def predict(self, features: np.ndarray) -> str:
        y = self.model.predict(features.reshape(1, -1))[0]
        return self._le.inverse_transform([y])[0]
    
    def predict_proba(self, features: np.ndarray) -> dict:
        proba = self.model.predict_proba(features.reshape(1, -1))[0]
        return dict(zip(self._le.classes_, proba))

# ============================================================================
# 3. SENSOR FAULT DETECTION (Isolation Forest)
# ============================================================================

class SensorFaultDetector:
    """Detect abnormal sensor readings using Isolation Forest.
    
    Application: detect stuck-at, intermittent, or biased sensor faults.
    ISO 26262: safety monitors must detect sensor failure before it affects 
    the safety function (DTC: Diagnostic Trouble Code).
    
    Isolation Forest: anomalies are 'easy to isolate' (shorter average path length
    in random forest partitions). Does not require labelled fault data.
    """
    
    def __init__(self, contamination: float = 0.01):
        """contamination: expected fraction of anomalies in training data (1%)."""
        self.model = Pipeline([
            ('scaler', StandardScaler()),
            ('detector', IsolationForest(
                n_estimators=100,
                contamination=contamination,
                random_state=42,
                n_jobs=2
            ))
        ])
    
    def train_on_nominal(self, normal_data: np.ndarray):
        """Train on NORMAL sensor data only (unsupervised).
        Model learns what 'healthy' looks like."""
        self.model.fit(normal_data)
        print(f"Isolation Forest trained on {len(normal_data)} nominal samples")
    
    def is_fault(self, sample: np.ndarray) -> Tuple[bool, float]:
        """
        Returns: (is_fault: bool, anomaly_score: float)
        anomaly_score < 0 = anomaly, closer to -1 = more anomalous
        """
        score = self.model.decision_function(sample.reshape(1, -1))[0]
        pred  = self.model.predict(sample.reshape(1, -1))[0]  # -1=anomaly, 1=normal
        return pred == -1, score

# ============================================================================
# 4. RADAR OBJECT CLASSIFICATION (SVM)
# ============================================================================

class RadarObjectClassifier:
    """Classify radar detections: car / truck / motorcycle / stationary.
    
    Features extracted from radar point clusters (RCS pattern, velocity spread).
    SVM with RBF kernel excels at small dataset classification tasks.
    Inference: ~0.5ms for 1000 detection clusters on ARM A53.
    """
    
    CLASSES = ['car', 'truck', 'motorcycle', 'stationary']
    
    def __init__(self):
        self.model = Pipeline([
            ('scaler', StandardScaler()),
            ('svm', SVC(
                kernel='rbf',
                C=10.0,             # Regularisation (higher = tighter fit)
                gamma='scale',      # Automatic kernel bandwidth
                probability=True,   # Enable predict_proba (slower but needed for fusion)
                class_weight='balanced'
            ))
        ])
        self._le = LabelEncoder()
    
    def generate_synthetic_data(self, n_per_class: int = 500):
        """Simulate radar cluster features for 4 object types.
        Features: [range_m, rcs_dBsm, range_spread_m, vel_mps, 
                   vel_spread_mps, azimuth_span_deg, n_points]
        """
        rng = np.random.default_rng(7)
        data = {
            'car':        {'rcs': 10, 'range_sp': 0.8, 'vel_sp': 0.3, 'az_sp': 3.0},
            'truck':      {'rcs': 20, 'range_sp': 2.0, 'vel_sp': 0.5, 'az_sp': 6.0},
            'motorcycle': {'rcs': 3,  'range_sp': 0.3, 'vel_sp': 0.5, 'az_sp': 1.5},
            'stationary': {'rcs': 8,  'range_sp': 0.2, 'vel_sp': 0.05, 'az_sp': 2.0},
        }
        all_X, all_y = [], []
        for cls, p in data.items():
            n = n_per_class
            X = np.column_stack([
                rng.uniform(10, 150, n),                     # range_m
                rng.normal(p['rcs'], p['rcs']*0.2, n),       # rcs_dBsm
                rng.normal(p['range_sp'], 0.1, n).clip(0.1), # range_spread
                rng.normal(-10, 5, n),                        # velocity
                rng.normal(p['vel_sp'], 0.05, n).clip(0.01), # vel_spread
                rng.normal(p['az_sp'], 0.5, n).clip(0.5),    # azimuth_span
                rng.integers(3, 30, n).astype(float),        # n_points
            ])
            all_X.append(X)
            all_y.extend([cls]*n)
        return np.vstack(all_X).astype(np.float32), np.array(all_y)
    
    def train(self, X, y_labels):
        y = self._le.fit_transform(y_labels)
        cv_scores = cross_val_score(self.model, X, y, cv=5, scoring='accuracy')
        print(f"\nRadar Classifier CV Accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
        self.model.fit(X, y)
    
    def predict(self, features: np.ndarray) -> str:
        y = self.model.predict(features.reshape(1, -1))[0]
        return str(self._le.inverse_transform([y])[0])
    
    def predict_proba(self, features: np.ndarray) -> dict:
        proba = self.model.predict_proba(features.reshape(1, -1))[0]
        return dict(zip(self._le.classes_, proba))

# ============================================================================
# 5. DEMO
# ============================================================================

if __name__ == "__main__":
    print("=== ADAS Machine Learning Demo ===\n")
    
    # 1. Lane offset regression
    regressor = LaneOffsetRegressor()
    X, y = regressor.generate_synthetic_data(5000)
    regressor.train(X, y)
    test_sample = X[0]
    pred_offset = regressor.predict(test_sample)
    print(f"Predicted lane offset: {pred_offset*100:.1f}cm")
    
    # 2. Road surface classification
    surf_clf = RoadSurfaceClassifier()
    Xs, ys = surf_clf.generate_synthetic_data(1000)
    surf_clf.train(Xs, ys)
    test_imu = Xs[0]
    pred_surface = surf_clf.predict(test_imu)
    proba = surf_clf.predict_proba(test_imu)
    print(f"\nPredicted surface: {pred_surface}")
    for cls, p in sorted(proba.items(), key=lambda x: -x[1]):
        print(f"  {cls}: {p:.3f}")
    
    # 3. Sensor fault detection
    fault_det = SensorFaultDetector(contamination=0.01)
    normal_sensor_data = np.random.normal(0, 1, (2000, 6)).astype(np.float32)
    fault_det.train_on_nominal(normal_sensor_data)
    
    normal_sample = np.array([0.1, -0.2, 0.3, 0.0, 0.1, -0.1], dtype=np.float32)
    stuck_at_fault = np.array([5.0, 5.0, 5.0, 5.0, 5.0, 5.0], dtype=np.float32)
    
    is_fault_n, score_n = fault_det.is_fault(normal_sample)
    is_fault_f, score_f = fault_det.is_fault(stuck_at_fault)
    print(f"\nNormal sample: fault={is_fault_n}, score={score_n:.3f}")
    print(f"Stuck-at fault: fault={is_fault_f}, score={score_f:.3f}")
    
    # 4. Radar classifier
    radar_clf = RadarObjectClassifier()
    Xr, yr = radar_clf.generate_synthetic_data(500)
    radar_clf.train(Xr, yr)
    test_radar = Xr[10]
    pred_obj = radar_clf.predict(test_radar)
    print(f"\nRadar object: {pred_obj}")
