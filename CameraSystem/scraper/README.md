# Frame Scraper

Script để scrape frames từ camera giao thông của thành phố Hồ Chí Minh.

## Tính năng

- ✅ Tự động tìm tất cả camera IDs từ trang Map.aspx
- ✅ Scrape frames từ nhiều camera đồng thời
- ✅ Lưu frames với timestamp và camera ID
- ✅ Tự động retry khi có lỗi
- ✅ Thống kê số frames đã scrape

## Cài đặt

```bash
cd CameraSystem/scraper
pip install -r requirements.txt
```

## Sử dụng

```bash
python frame_scrap.py
```

Script sẽ:
1. Tải trang `https://giaothong.hochiminhcity.gov.vn/Map.aspx`
2. Trích xuất tất cả camera IDs từ trang
3. Bắt đầu scrape frames từ tất cả cameras
4. Lưu frames vào thư mục `frames/`

## Cấu hình

Có thể chỉnh sửa các tham số trong script:

- `SCRAPE_INTERVAL`: Khoảng thời gian giữa mỗi lần scrape (mặc định: 1 giây)
- `CAMERA_TIMEOUT`: Timeout cho mỗi request (mặc định: 5 giây)
- `OUTPUT_DIR`: Thư mục lưu frames (mặc định: `frames/`)

## Output

Frames được lưu với format:
```
frames/cam_{camera_id_8_chars}_{timestamp}.jpg
```

Ví dụ: `frames/cam_5d8cd98d_20241201_143025_123456.jpg`

## Dừng script

Nhấn `Ctrl+C` để dừng. Script sẽ hiển thị thống kê số frames đã scrape.
