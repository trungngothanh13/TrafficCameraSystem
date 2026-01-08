# Traffic Camera Server

WebSocket server để stream **4 cameras** từ Unity đến Python clients.

## Cấu trúc

```
server/
├── server.py          # Main WebSocket server
├── config.py          # Configuration settings
├── protocol.py        # Protocol definitions (binary/text)
├── camera_manager.py  # Camera management (4 cameras)
├── opencv_viewer.py   # OpenCV viewer client
├── start_server.py    # Server starter script
├── requirements.txt   # Dependencies
└── README.md         # This file
```

## Cài đặt

```bash
cd CameraSystem/server
pip install -r requirements.txt
```

## Chạy Server

### Cách 1: Dùng start script (khuyến nghị)

```bash
python start_server.py
```

### Cách 2: Chạy trực tiếp

```bash
python server.py
```

Server sẽ chạy trên **ws://0.0.0.0:8081**

## Chạy OpenCV Viewer

Mở terminal mới:

```bash
python opencv_viewer.py
```

Viewer sẽ hiển thị **4 camera** trong grid 2x2.

## Cấu hình

Chỉnh sửa `config.py`:

- **DEFAULT_PORT**: 8081 (WebSocket port)
- **MAX_CAMERAS**: 4 (số camera tối đa)
- **PING_INTERVAL**: 20s (keep-alive)
- **LOG_LEVEL**: INFO (logging level)

## Protocol

Server hỗ trợ 2 protocols:

1. **Binary** (khuyến nghị - hiện tại): 
   - Format: `[1 byte: camera_id][8 bytes: timestamp][4 bytes: length][N bytes: jpeg_data]`
   - Hiệu quả hơn, không có base64 overhead

2. **Text** (legacy - backward compatibility): 
   - Format: `CAMERA_STREAM:{cameraId}:{base64Data}`
   - Vẫn được hỗ trợ cho clients cũ

Unity clients nên dùng **binary protocol** để tối ưu hiệu năng.

## Camera IDs

- **Camera 0**: ID = 0
- **Camera 1**: ID = 1
- **Camera 2**: ID = 2
- **Camera 3**: ID = 3

## Features

- ✅ Hỗ trợ **4 camera streams** đồng thời
- ✅ Binary và text protocols
- ✅ Auto-reconnect cho clients
- ✅ Camera status monitoring (FPS, frame count)
- ✅ Inactive camera cleanup (tự động xóa camera không hoạt động)
- ✅ Parallel broadcast (gửi song song đến nhiều clients)
- ✅ Frame rate tracking per camera

## Workflow

1. **Unity**: 4 cameras gửi frames qua WebSocket (binary protocol)
2. **Server**: Nhận frames, lưu cache, broadcast đến tất cả clients
3. **OpenCV Viewer**: Nhận frames và hiển thị trong grid 2x2

## Troubleshooting

- **Camera không hiển thị**: Kiểm tra camera ID (0-3) và Unity connection
- **Chậm/lag**: Giảm resolution hoặc FPS trong Unity
- **Connection lost**: Server tự động cleanup, Unity sẽ reconnect
