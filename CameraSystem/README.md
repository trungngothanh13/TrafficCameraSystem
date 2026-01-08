# Camera System

Hệ thống xử lý và phân tích video từ traffic camera, bao gồm streaming, scraping YouTube, và object detection.

## Cấu trúc thư mục

```
CameraSystem/
├── server/                    # WebSocket server cho streaming camera
│   ├── server.py             # WebSocket server chính
│   ├── opencv_viewer.py      # OpenCV viewer để xem streams
│   ├── start_server.py       # Script khởi động server
│   ├── requirements.txt       # Python dependencies
│   └── README.md             # Hướng dẫn server
│
├── yt_live_camera_scraper/   # Scraper video từ YouTube live stream
│   ├── scrape_youtube_live.py  # Script tải và cắt video
│   ├── requirements.txt         # Python dependencies
│   ├── README.md               # Hướng dẫn scraper
│   ├── temp/                   # Thư mục tạm cho video tải về
│   └── output/                 # Thư mục output video đã cắt
│
└── object_detection/         # Object detection trên video
    ├── object_detection.py    # Script detect objects (YOLOv8)
    ├── requirements.txt       # Python dependencies
    └── README.md              # Hướng dẫn detection
```

## Modules

### 1. Server (`server/`)

WebSocket server để stream camera từ Unity đến Python clients.

**Cài đặt:**
```bash
cd server
pip install -r requirements.txt
python start_server.py
```

**Sử dụng:**
- Server chạy trên port 8081
- Unity clients kết nối và gửi camera streams
- OpenCV viewer có thể xem streams real-time

Xem chi tiết: [server/README.md](server/README.md)

### 2. YouTube Live Scraper (`yt_live_camera_scraper/`)

Tải và cắt video từ YouTube live stream.

**Cài đặt:**
```bash
cd yt_live_camera_scraper
pip install -r requirements.txt
```

**Yêu cầu:**
- Python 3.7+
- yt-dlp
- ffmpeg

**Sử dụng:**
```bash
python scrape_youtube_live.py
```

Xem chi tiết: [yt_live_camera_scraper/README.md](yt_live_camera_scraper/README.md)

### 3. Object Detection (`object_detection/`)

Detect objects (xe, người, v.v.) trong video traffic camera bằng YOLOv8.

**Cài đặt:**
```bash
cd object_detection
pip install -r requirements.txt
```

**Sử dụng:**
```bash
python object_detection.py
```

Xem chi tiết: [object_detection/README.md](object_detection/README.md)

## Workflow đề xuất

1. **Stream từ Unity** → Server → OpenCV Viewer (real-time)
2. **Scrape từ YouTube** → Tải video → Cắt đoạn cần thiết
3. **Object Detection** → Phân tích video → Detect vehicles/people

## Yêu cầu chung

- Python 3.7+
- pip
- ffmpeg (cho YouTube scraper)

## Cài đặt tất cả dependencies

```bash
# Server
cd server && pip install -r requirements.txt && cd ..

# YouTube Scraper
cd yt_live_camera_scraper && pip install -r requirements.txt && cd ..

# Object Detection
cd object_detection && pip install -r requirements.txt && cd ..
```

## Notes

- Mỗi module có thể hoạt động độc lập
- Output files được lưu trong thư mục `output/` của từng module
- Temp files được lưu trong thư mục `temp/` (có thể xóa sau khi xử lý)
