"""
Post-processor for Object Detection results
Handles filtering, tracking, and context-aware processing
"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from .yolo_detector import Detection, DetectionResult
from ..utils.logger import get_logger


logger = get_logger("adas.post_processor")


@dataclass
class TrackedDetection:
    """Detection with tracking information"""
    detection: Detection
    track_id: int
    track_history: List[Tuple[float, float, float, float]]  # History of bbox coordinates
    velocity: Optional[Tuple[float, float]] = None  # Estimated velocity (x, y) in pixels/frame
    distance: Optional[float] = None  # Estimated distance from camera
    last_seen: float = 0.0  # Timestamp of last detection


@dataclass
class ContextAwareResult:
    """Detection result with context awareness"""
    original_result: DetectionResult
    tracked_detections: List[TrackedDetection] = field(default_factory=list)
    priority_alerts: List[Detection] = field(default_factory=list)
    collision_warnings: List[Dict[str, Any]] = field(default_factory=list)
    lane_violation_warnings: List[Dict[str, Any]] = field(default_factory=list)
    speed_violation_warnings: List[Dict[str, Any]] = field(default_factory=list)


class DetectionPostProcessor:
    """
    Post-processor for Object Detection results
    Adds tracking, context awareness, and priority handling
    """
    
    def __init__(
        self,
        max_track_age: float = 2.0,  # Maximum age of a track in seconds
        iou_threshold: float = 0.5,  # IoU threshold for track association
        min_detection_confidence: float = 0.3,  # Minimum confidence for tracking
        priority_classes: Optional[List[str]] = None,
        collision_threshold: float = 0.5,  # Threshold for collision warning
        speed_limit: float = 60.0  # Speed limit in km/h for warnings
    ):
        """
        Initialize Detection PostProcessor
        
        Args:
            max_track_age: Maximum age of a track in seconds
            iou_threshold: IoU threshold for track association
            min_detection_confidence: Minimum confidence for tracking
            priority_classes: List of priority classes
            collision_threshold: Threshold for collision warning
            speed_limit: Speed limit for warnings
        """
        self.max_track_age = max_track_age
        self.iou_threshold = iou_threshold
        self.min_detection_confidence = min_detection_confidence
        self.priority_classes = priority_classes or [
            "person", "car", "motorcycle", "bus", "truck", "bicycle"
        ]
        self.collision_threshold = collision_threshold
        self.speed_limit = speed_limit
        
        # Track management
        self.tracks = {}  # track_id -> TrackedDetection
        self.next_track_id = 1
        self.last_frame_time = 0.0
        
        # For TTC (Time-to-Collision) calculation
        self.previous_positions = defaultdict(deque)
        self.ttc_window_size = 5  # Number of frames to use for TTC calculation
        
        # For lane violation detection
        self.lane_boundaries = None  # Will be set by external lane detection
        
        logger.info("Detection PostProcessor initialized")
    
    def process(self, detection_result: DetectionResult) -> ContextAwareResult:
        """
        Process detection results to add tracking and context
        
        Args:
            detection_result: Raw detection result from detector
        
        Returns:
            ContextAwareResult with tracking and context information
        """
        # Update frame time
        current_time = detection_result.timestamp
        if self.last_frame_time > 0:
            time_delta = current_time - self.last_frame_time
        else:
            time_delta = 0.0
        self.last_frame_time = current_time
        
        # Filter detections by confidence
        filtered_detections = [
            d for d in detection_result.detections 
            if d.confidence >= self.min_detection_confidence
        ]
        
        # Associate detections with existing tracks
        self._associate_detections(filtered_detections, time_delta)
        
        # Remove old tracks
        self._cleanup_old_tracks(current_time)
        
        # Calculate velocities and distances
        self._update_track_metrics(time_delta)
        
        # Generate context-aware warnings
        collision_warnings = self._detect_collisions()
        lane_violation_warnings = self._detect_lane_violations()
        speed_violation_warnings = self._detect_speed_violations()
        
        # Get priority alerts
        priority_alerts = [
            d for d in filtered_detections 
            if d.class_name in self.priority_classes and d.confidence >= 0.7
        ]
        
        # Create result
        result = ContextAwareResult(
            original_result=detection_result,
            tracked_detections=list(self.tracks.values()),
            priority_alerts=priority_alerts,
            collision_warnings=collision_warnings,
            lane_violation_warnings=lane_violation_warnings,
            speed_violation_warnings=speed_violation_warnings
        )
        
        return result
    
    def _associate_detections(self, detections: List[Detection], time_delta: float):
        """
        Associate detections with existing tracks using IoU
        
        Args:
            detections: List of current detections
            time_delta: Time since last frame
        """
        # Create list of unassigned detections
        unassigned_detections = list(detections)
        
        # For each existing track, find the best matching detection
        for track_id, track in list(self.tracks.items()):
            best_iou = 0.0
            best_detection = None
            best_index = -1
            
            for i, detection in enumerate(unassigned_detections):
                iou = self._calculate_iou(
                    track.detection.bbox,
                    detection.bbox
                )
                
                if iou > best_iou and iou > self.iou_threshold:
                    best_iou = iou
                    best_detection = detection
                    best_index = i
            
            if best_detection is not None:
                # Update track with new detection
                self._update_track(track_id, best_detection, time_delta)
                unassigned_detections.pop(best_index)
        
        # Create new tracks for unassigned detections
        for detection in unassigned_detections:
            self._create_new_track(detection)
    
    def _update_track(self, track_id: int, detection: Detection, time_delta: float):
        """
        Update an existing track with new detection
        
        Args:
            track_id: Track ID
            detection: New detection
            time_delta: Time since last frame
        """
        track = self.tracks[track_id]
        
        # Update detection
        track.detection = detection
        track.last_seen = detection.timestamp if hasattr(detection, 'timestamp') else 0.0
        
        # Update track history
        track.track_history.append(detection.bbox)
        if len(track.track_history) > 10:  # Keep last 10 positions
            track.track_history.pop(0)
        
        # Update previous positions for TTC calculation
        class_name = detection.class_name
        self.previous_positions[class_name].append(detection.bbox)
        if len(self.previous_positions[class_name]) > self.ttc_window_size:
            self.previous_positions[class_name].popleft()
    
    def _create_new_track(self, detection: Detection):
        """
        Create a new track for a detection
        
        Args:
            detection: Detection to track
        """
        track_id = self.next_track_id
        self.next_track_id += 1
        
        track = TrackedDetection(
            detection=detection,
            track_id=track_id,
            track_history=[detection.bbox],
            last_seen=detection.timestamp if hasattr(detection, 'timestamp') else 0.0
        )
        
        self.tracks[track_id] = track
        
        # Initialize previous positions for TTC
        class_name = detection.class_name
        if class_name not in self.previous_positions:
            self.previous_positions[class_name] = deque()
        self.previous_positions[class_name].append(detection.bbox)
    
    def _cleanup_old_tracks(self, current_time: float):
        """
        Remove tracks that haven't been updated recently
        
        Args:
            current_time: Current timestamp
        """
        tracks_to_remove = []
        
        for track_id, track in self.tracks.items():
            if current_time - track.last_seen > self.max_track_age:
                tracks_to_remove.append(track_id)
        
        for track_id in tracks_to_remove:
            del self.tracks[track_id]
            logger.debug(f"Removed old track: {track_id}")
    
    def _update_track_metrics(self, time_delta: float):
        """
        Update track metrics (velocity, distance, etc.)
        
        Args:
            time_delta: Time since last frame
        """
        if time_delta <= 0:
            return
        
        for track in self.tracks.values():
            if len(track.track_history) < 2:
                continue
            
            # Calculate velocity (pixels per second)
            prev_bbox = track.track_history[-2]
            curr_bbox = track.track_history[-1]
            
            # Use center point for velocity calculation
            prev_center = self._get_bbox_center(prev_bbox)
            curr_center = self._get_bbox_center(curr_bbox)
            
            dx = (curr_center[0] - prev_center[0]) / time_delta
            dy = (curr_center[1] - prev_center[1]) / time_delta
            
            track.velocity = (dx, dy)
            
            # Estimate distance (simplified - assumes camera calibration is known)
            # This is a placeholder - actual distance calculation would require camera parameters
            bbox_area = (curr_bbox[2] - curr_bbox[0]) * (curr_bbox[3] - curr_bbox[1])
            track.distance = 1000.0 / max(1, bbox_area)  # Inverse relationship with area
    
    def _get_bbox_center(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        """Get center point of bounding box"""
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    
    def _calculate_iou(
        self,
        bbox1: Tuple[float, float, float, float],
        bbox2: Tuple[float, float, float, float]
    ) -> float:
        """
        Calculate Intersection over Union (IoU) between two bounding boxes
        
        Args:
            bbox1: First bounding box (x1, y1, x2, y2)
            bbox2: Second bounding box (x1, y1, x2, y2)
        
        Returns:
            IoU value (0-1)
        """
        # Calculate intersection coordinates
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        # Calculate intersection area
        intersection_area = max(0, x2 - x1) * max(0, y2 - y1)
        
        # Calculate areas of each box
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        
        # Calculate union area
        union_area = area1 + area2 - intersection_area
        
        # Calculate IoU
        if union_area <= 0:
            return 0.0
        
        return intersection_area / union_area
    
    def _detect_collisions(self) -> List[Dict[str, Any]]:
        """
        Detect potential collisions based on TTC (Time-to-Collision)
        
        Returns:
            List of collision warnings
        """
        warnings = []
        
        for track in self.tracks.values():
            if track.velocity is None or len(track.track_history) < 2:
                continue
            
            # Calculate TTC (simplified)
            # This is a placeholder - actual TTC would require depth information
            # For now, we'll use a simple heuristic based on velocity and distance
            
            # Get current bbox
            curr_bbox = track.track_history[-1]
            bbox_width = curr_bbox[2] - curr_bbox[0]
            bbox_height = curr_bbox[3] - curr_bbox[1]
            
            # Estimate time to collision (simplified)
            # If object is getting larger (velocity towards camera), TTC is low
            if track.distance is not None and track.distance < 50:  # Close distance
                # Calculate growth rate (change in area)
                if len(track.track_history) >= 2:
                    prev_bbox = track.track_history[-2]
                    prev_area = (prev_bbox[2] - prev_bbox[0]) * (prev_bbox[3] - prev_bbox[1])
                    curr_area = bbox_width * bbox_height
                    
                    if prev_area > 0:
                        growth_rate = (curr_area - prev_area) / prev_area
                        if growth_rate > 0.1:  # Growing by more than 10%
                            ttc = track.distance / (abs(track.velocity[0]) + abs(track.velocity[1]) + 1)
                            
                            if ttc < self.collision_threshold:
                                warnings.append({
                                    "track_id": track.track_id,
                                    "class": track.detection.class_name,
                                    "confidence": track.detection.confidence,
                                    "ttc": ttc,
                                    "distance": track.distance,
                                    "severity": "high" if ttc < 0.3 else "medium"
                                })
        
        return warnings
    
    def _detect_lane_violations(self) -> List[Dict[str, Any]]:
        """
        Detect lane violations (requires lane boundaries to be set)
        
        Returns:
            List of lane violation warnings
        """
        warnings = []
        
        if self.lane_boundaries is None:
            return warnings
        
        for track in self.tracks.values():
            curr_bbox = track.track_history[-1]
            bbox_center = self._get_bbox_center(curr_bbox)
            
            # Check if center is outside lane boundaries
            # This is a placeholder - actual implementation would depend on lane detection
            for boundary in self.lane_boundaries:
                if not self._is_point_in_lane(bbox_center, boundary):
                    warnings.append({
                        "track_id": track.track_id,
                        "class": track.detection.class_name,
                        "confidence": track.detection.confidence,
                        "violation_type": "lane_departure",
                        "severity": "high"
                    })
                    break
        
        return warnings
    
    def _is_point_in_lane(self, point: Tuple[float, float], lane_boundary: Any) -> bool:
        """
        Check if a point is within lane boundaries
        
        Args:
            point: (x, y) coordinates
            lane_boundary: Lane boundary definition
        
        Returns:
            True if point is within lane
        """
        # Placeholder implementation
        # Actual implementation would depend on lane detection output
        return True
    
    def _detect_speed_violations(self) -> List[Dict[str, Any]]:
        """
        Detect speed violations (requires speed estimation)
        
        Returns:
            List of speed violation warnings
        """
        warnings = []
        
        for track in self.tracks.values():
            if track.velocity is None:
                continue
            
            # Estimate speed in km/h (simplified)
            # This is a placeholder - actual speed estimation would require camera calibration
            pixel_speed = np.sqrt(track.velocity[0]**2 + track.velocity[1]**2)
            
            # Convert pixels/second to km/h (approximate)
            # Assumes 100 pixels = 1 meter at 10m distance (very rough estimate)
            speed_kmh = pixel_speed * 0.01 * 3.6  # pixels/s * (m/pixel) * (km/m) * (h/s)
            
            if speed_kmh > self.speed_limit:
                warnings.append({
                    "track_id": track.track_id,
                    "class": track.detection.class_name,
                    "confidence": track.detection.confidence,
                    "estimated_speed": speed_kmh,
                    "speed_limit": self.speed_limit,
                    "severity": "high" if speed_kmh > self.speed_limit * 1.2 else "medium"
                })
        
        return warnings
    
    def set_lane_boundaries(self, boundaries: Any):
        """
        Set lane boundaries for lane violation detection
        
        Args:
            boundaries: Lane boundary definitions
        """
        self.lane_boundaries = boundaries
        logger.info("Lane boundaries updated")
    
    def reset(self):
        """Reset all tracks and state"""
        self.tracks.clear()
        self.previous_positions.clear()
        self.next_track_id = 1
        self.last_frame_time = 0.0
        logger.info("Detection PostProcessor reset")
