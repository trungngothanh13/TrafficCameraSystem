#!/usr/bin/env python3
"""
Camera Manager - Manages 4 camera streams
Tracks camera status, statistics, and health
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import deque
import time

class CameraManager:
    """
    Manages multiple camera streams (up to 4)
    
    Features:
    - Track camera status and health
    - Monitor frame rates and statistics
    - Detect inactive cameras
    - Provide camera information for status endpoints
    """
    
    def __init__(self, max_cameras: int = 4):
        """
        Initialize camera manager
        
        Args:
            max_cameras: Maximum number of cameras to support
        """
        self.max_cameras = max_cameras
        # Camera data: {camera_id: {data: base64, timestamp: ISO, ...}}
        self.cameras: Dict[int, Dict] = {}
        # Frame rate tracking: {camera_id: deque of timestamps}
        self.frame_timestamps: Dict[int, deque] = {}
        # Statistics: {camera_id: {frames_received, last_update, avg_fps}}
        self.stats: Dict[int, Dict] = {}
        # Timeout for inactive camera (seconds)
        self.inactive_timeout = 10.0
    
    def update_camera(self, camera_id: int, base64_data: str) -> None:
        """
        Update camera frame data
        
        Args:
            camera_id: Camera ID (0-3 for 4 cameras)
            base64_data: Base64-encoded JPEG frame
        """
        now = datetime.now()
        now_iso = now.isoformat()
        
        # Update camera data
        self.cameras[camera_id] = {
            "data": base64_data,
            "timestamp": now_iso,
            "last_update": now
        }
        
        # Track frame timestamps for FPS calculation
        if camera_id not in self.frame_timestamps:
            self.frame_timestamps[camera_id] = deque(maxlen=30)  # Keep last 30 frames
        
        self.frame_timestamps[camera_id].append(time.time())
        
        # Update statistics
        if camera_id not in self.stats:
            self.stats[camera_id] = {
                "frames_received": 0,
                "first_seen": now,
                "last_update": now
            }
        
        self.stats[camera_id]["frames_received"] += 1
        self.stats[camera_id]["last_update"] = now
        
        # Calculate average FPS (over last 30 frames)
        timestamps = self.frame_timestamps[camera_id]
        if len(timestamps) >= 2:
            time_span = timestamps[-1] - timestamps[0]
            if time_span > 0:
                fps = (len(timestamps) - 1) / time_span
                self.stats[camera_id]["avg_fps"] = round(fps, 2)
    
    def get_camera_status(self, camera_id: int) -> Dict:
        """
        Get status information for a specific camera
        
        Args:
            camera_id: Camera ID
        
        Returns:
            Dict with camera status information
        """
        if camera_id not in self.cameras:
            return {
                "id": camera_id,
                "status": "inactive",
                "lastUpdate": None,
                "fps": 0,
                "frames_received": 0
            }
        
        camera_data = self.cameras[camera_id]
        stats = self.stats.get(camera_id, {})
        
        # Check if camera is active (received frame recently)
        last_update = camera_data.get("last_update", datetime.now())
        time_since_update = (datetime.now() - last_update).total_seconds()
        is_active = time_since_update < self.inactive_timeout
        
        return {
            "id": camera_id,
            "status": "active" if is_active else "inactive",
            "lastUpdate": camera_data["timestamp"],
            "fps": stats.get("avg_fps", 0),
            "frames_received": stats.get("frames_received", 0),
            "time_since_update": round(time_since_update, 2)
        }
    
    def get_all_cameras_status(self) -> Dict:
        """
        Get status for all cameras
        
        Returns:
            Dict with list of camera statuses and summary
        """
        camera_list = []
        active_count = 0
        
        # Check all possible camera IDs (0-3 for 4 cameras)
        for cam_id in range(self.max_cameras):
            status = self.get_camera_status(cam_id)
            camera_list.append(status)
            if status["status"] == "active":
                active_count += 1
        
        return {
            "cameras": camera_list,
            "total": len(camera_list),
            "active": active_count,
            "inactive": len(camera_list) - active_count
        }
    
    def get_active_camera_ids(self) -> list:
        """Get list of active camera IDs"""
        active = []
        for cam_id in range(self.max_cameras):
            status = self.get_camera_status(cam_id)
            if status["status"] == "active":
                active.append(cam_id)
        return active
    
    def get_camera_data(self, camera_id: int) -> Optional[Dict]:
        """
        Get latest frame data for a camera
        
        Args:
            camera_id: Camera ID
        
        Returns:
            Camera data dict or None if not found
        """
        return self.cameras.get(camera_id)
    
    def get_all_camera_data(self) -> Dict[int, Dict]:
        """Get all camera data"""
        return self.cameras.copy()
    
    def clear_inactive_cameras(self) -> int:
        """
        Remove cameras that haven't sent frames recently
        
        Returns:
            Number of cameras removed
        """
        removed = 0
        now = datetime.now()
        
        for cam_id in list(self.cameras.keys()):
            camera_data = self.cameras[cam_id]
            last_update = camera_data.get("last_update", now)
            time_since_update = (now - last_update).total_seconds()
            
            if time_since_update > self.inactive_timeout * 2:  # Double timeout before removal
                del self.cameras[cam_id]
                if cam_id in self.frame_timestamps:
                    del self.frame_timestamps[cam_id]
                if cam_id in self.stats:
                    del self.stats[cam_id]
                removed += 1
        
        return removed
