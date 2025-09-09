# Simple Unity to OpenCV TCP Streaming

A simple TCP streaming system that sends camera feed from Unity to Python OpenCV.

## Setup

### Unity Side
1. Open Unity project
2. Add `CameraStreamer` script to a Camera
3. Press Play

### Python Side
1. Install dependencies:
   ```bash
   pip install opencv-python numpy
   ```

2. Run the client:
   ```bash
   python traffic_camera.py
   ```

## Controls
- **ESC** - Quit
- **S** - Save current frame

## Settings
- **Port**: 5001 (default)
- **Resolution**: 1920x1080
- **JPEG Quality**: 75%
- **Frame Rate**: 30 FPS

## Files
- `CameraStreamer.cs` - Unity streaming script
- `traffic_camera.py` - Python OpenCV client
