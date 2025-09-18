
```
CameraSystem/
├── server/                # WebSocket server (Python)
│   ├── server.py
│   ├── start_server.py
│   └── requirements.txt
├── web/                   # (đã bỏ)
├── setup_python.md        # Hướng dẫn setup Python
├── start_python.bat       # Script chạy server (Windows)
├── start_python.sh        # Script chạy server (Linux/Mac)
└── README.md
```
## Cài đặt nhanh

### Chạy Python Server
cd CameraSystem/server
python start_server.py

### Mở OpenCV Viewer
Mở term mới chạy 
cd CameraSystem/server
opencv_viewer.py

## Cấu hình

- **WebSocket Port**: 8081 (Python server)
- **HTTP Port**: 8080 (Web interface)
- **Camera Resolution**: 1920x1080
- **Frame Rate**: 30 FPS
- **JPEG Quality**: 80%

## Exception 
- Kiểm tra lại thư viện, phiên bản xem có cài đúng chưa ?