#!/usr/bin/env python3
"""
Protocol definitions for Traffic Camera System
Defines message formats and packet structures
"""

from typing import Dict, Any
from datetime import datetime
import base64
import struct

# ============================================================================
# MESSAGE TYPES
# ============================================================================

class MessageType:
    """Message type constants"""
    CONNECTION = "connection"
    CAMERA_STREAM = "camera_stream"
    ERROR = "error"
    STATUS = "status"

# ============================================================================
# TEXT PROTOCOL (Legacy - for backward compatibility)
# ============================================================================

def parse_text_stream_message(message: str) -> Dict[str, Any]:
    """
    Parse text format camera stream message from Unity (legacy)
    
    Format: "CAMERA_STREAM:{cameraId}:{base64Data}"
    
    Args:
        message: Text message string
    
    Returns:
        Dict with 'camera_id' and 'base64_data', or None if invalid
    """
    try:
        parts = message.split(':', 2)
        if len(parts) >= 3:
            return {
                'camera_id': int(parts[1]),
                'base64_data': parts[2]
            }
    except (ValueError, IndexError):
        pass
    return None

def create_text_stream_message(camera_id: int, base64_data: str) -> str:
    """
    Create text format camera stream message (legacy)
    
    Format: "CAMERA_STREAM:{cameraId}:{base64Data}"
    """
    return f"CAMERA_STREAM:{camera_id}:{base64_data}"

# ============================================================================
# BINARY PROTOCOL (Current - more efficient)
# ============================================================================

# Binary packet structure:
# [1 byte: camera_id][8 bytes: timestamp_ticks][4 bytes: jpeg_length][N bytes: jpeg_data]
BINARY_HEADER_SIZE = 1 + 8 + 4  # 13 bytes

def parse_binary_stream_packet(data: bytes) -> Dict[str, Any]:
    """
    Parse binary camera stream packet from Unity
    
    Packet format:
    - Byte 0: camera_id (uint8)
    - Bytes 1-8: timestamp_ticks (int64, little-endian) - currently unused
    - Bytes 9-12: jpeg_length (uint32, little-endian)
    - Bytes 13+: jpeg_data (raw bytes)
    
    Args:
        data: Binary packet data
    
    Returns:
        Dict with 'camera_id', 'jpeg_bytes', and optionally 'timestamp_ticks'
        Returns None if packet is invalid
    """
    if len(data) < BINARY_HEADER_SIZE:
        return None
    
    try:
        # Extract camera ID (first byte)
        camera_id = data[0]
        
        # Extract timestamp ticks (bytes 1-8) - little-endian signed int64
        # Currently not used, but kept for future use
        timestamp_ticks = struct.unpack('<q', data[1:9])[0]
        
        # Extract JPEG length (bytes 9-12) - little-endian unsigned int32
        jpeg_length = struct.unpack('<I', data[9:13])[0]
        
        # Validate packet length
        expected_length = BINARY_HEADER_SIZE + jpeg_length
        if len(data) < expected_length:
            return None
        
        # Extract JPEG data
        jpeg_bytes = data[13:13 + jpeg_length]
        
        return {
            'camera_id': camera_id,
            'timestamp_ticks': timestamp_ticks,
            'jpeg_bytes': jpeg_bytes,
            'jpeg_length': jpeg_length
        }
    except (struct.error, IndexError):
        return None

def create_binary_stream_packet(camera_id: int, jpeg_bytes: bytes, 
                                timestamp_ticks: int = 0) -> bytes:
    """
    Create binary camera stream packet
    
    Args:
        camera_id: Camera ID (0-255)
        jpeg_bytes: JPEG image data
        timestamp_ticks: Timestamp in ticks (optional, defaults to 0)
    
    Returns:
        Binary packet bytes
    """
    # Pack header: camera_id (1 byte) + timestamp (8 bytes) + length (4 bytes)
    header = struct.pack('<BqI', camera_id, timestamp_ticks, len(jpeg_bytes))
    
    # Combine header + JPEG data
    return header + jpeg_bytes

# ============================================================================
# JSON MESSAGE FORMATS (For WebSocket clients)
# ============================================================================

def create_connection_message() -> Dict[str, Any]:
    """Create welcome connection message"""
    return {
        "type": MessageType.CONNECTION,
        "message": "Connected to Traffic Camera Server",
        "timestamp": datetime.now().isoformat(),
        "server": "Python WebSocket Server"
    }

def create_stream_message(camera_id: int, base64_data: str) -> Dict[str, Any]:
    """
    Create camera stream message for web clients
    
    Args:
        camera_id: Camera ID
        base64_data: Base64-encoded JPEG data
    
    Returns:
        JSON-serializable dict
    """
    return {
        "type": MessageType.CAMERA_STREAM,
        "cameraId": camera_id,
        "data": base64_data,
        "timestamp": datetime.now().isoformat()
    }

def jpeg_to_base64(jpeg_bytes: bytes) -> str:
    """Convert JPEG bytes to base64 string"""
    return base64.b64encode(jpeg_bytes).decode('ascii')

def base64_to_jpeg(base64_data: str) -> bytes:
    """Convert base64 string to JPEG bytes"""
    return base64.b64decode(base64_data)
