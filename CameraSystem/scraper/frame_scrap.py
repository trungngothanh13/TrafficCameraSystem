#!/usr/bin/env python3
"""
Frame Scraper - Scrape camera frames from Ho Chi Minh City Traffic Map
Extracts camera IDs from Map.aspx and downloads frames from all cameras
"""

import requests
import time
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Set
from urllib.parse import urljoin, urlparse

# URLs
MAP_URL = "https://giaothong.hochiminhcity.gov.vn/Map.aspx"
CAMERA_HANDLER_BASE = "https://giaothong.hochiminhcity.gov.vn:8007/Render/CameraHandler.ashx"

# Headers để giả lập browser
# Headers cho trang Map (HTML)
map_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.9,en;q=0.8,en-GB;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Headers cho camera image requests
image_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,en-GB;q=0.8",  # Giống với network inspector
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Referer": MAP_URL,
}

# Cấu hình
OUTPUT_DIR = Path("frames")
SCRAPE_INTERVAL = 1.0  # giây giữa mỗi lần scrape
CAMERA_TIMEOUT = 5  # timeout cho mỗi request
MAX_RETRIES = 3  # số lần retry khi lỗi


def extract_camera_ids_from_page(html_content: str) -> Set[str]:
    """
    Trích xuất camera IDs từ HTML của trang Map.aspx
    
    Tìm kiếm các pattern có thể chứa camera ID:
    - Trong JavaScript variables
    - Trong JSON data
    - Trong HTML attributes (data-id, id, etc.)
    - Trong URL patterns
    """
    camera_ids = set()
    
    # Pattern 1: Tìm trong JavaScript - biến chứa camera data
    # Ví dụ: var cameras = [{id: "5d8cd98d76cc88007118895a", ...}]
    js_patterns = [
        r'["\']id["\']\s*:\s*["\']([a-f0-9]{24})["\']',  # "id": "5d8cd98d76cc88007118895a"
        r'id["\']?\s*[:=]\s*["\']([a-f0-9]{24})["\']',   # id: "5d8cd98d76cc88007118895a"
        r'CameraHandler\.ashx\?id=([a-f0-9]{24})',       # URL pattern
    ]
    
    for pattern in js_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        camera_ids.update(matches)
    
    # Pattern 2: Tìm trong JSON data
    # Tìm các object JSON có thể chứa camera info
    json_pattern = r'\{[^{}]*["\']id["\'][^{}]*["\']([a-f0-9]{24})["\'][^{}]*\}'
    json_matches = re.findall(json_pattern, html_content, re.IGNORECASE)
    camera_ids.update(json_matches)
    
    # Pattern 3: Tìm trong HTML attributes
    # data-camera-id, data-id, etc.
    attr_patterns = [
        r'data-camera-id=["\']([a-f0-9]{24})["\']',
        r'data-id=["\']([a-f0-9]{24})["\']',
        r'camera-id=["\']([a-f0-9]{24})["\']',
    ]
    
    for pattern in attr_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        camera_ids.update(matches)
    
    # Validate: camera ID phải là 24 ký tự hex (MongoDB ObjectId format)
    validated_ids = {cid for cid in camera_ids if len(cid) == 24 and all(c in '0123456789abcdef' for c in cid.lower())}
    
    return validated_ids


def get_camera_ids_from_map(session: requests.Session) -> Set[str]:
    """
    Tải trang Map.aspx và trích xuất tất cả camera IDs
    Sử dụng session để giữ cookies
    
    Args:
        session: requests.Session để giữ cookies giữa các requests
    """
    print(f"Đang tải trang Map: {MAP_URL}")
    
    try:
        response = session.get(MAP_URL, headers=map_headers, timeout=10)
        response.raise_for_status()
        
        print(f"Đã tải trang thành công ({len(response.text)} bytes)")
        
        # Trích xuất camera IDs
        camera_ids = extract_camera_ids_from_page(response.text)
        
        print(f"Tìm thấy {len(camera_ids)} camera ID(s)")
        if camera_ids:
            print(f"Camera IDs: {', '.join(sorted(camera_ids)[:5])}{'...' if len(camera_ids) > 5 else ''}")
        
        return camera_ids
        
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi tải trang Map: {e}")
        return set()


def build_camera_url(camera_id: str, width: int = 300, height: int = 230, use_timestamp: bool = False) -> str:
    """
    Tạo URL để lấy frame từ camera handler
    
    Args:
        camera_id: Camera ID
        width: Chiều rộng ảnh (mặc định: 300 như trong network inspector)
        height: Chiều cao ảnh (mặc định: 230 như trong network inspector)
        use_timestamp: Có thêm parameter 't' để cache-busting không (mặc định: False)
    """
    url = f"{CAMERA_HANDLER_BASE}?id={camera_id}&bg=black&w={width}&h={height}"
    
    # Thêm timestamp nếu cần (một số request có, một số không)
    if use_timestamp:
        timestamp = int(time.time() * 1000)  # milliseconds
        url += f"&t={timestamp}"
    
    return url


def scrape_camera_frame(camera_id: str, output_dir: Path, session: requests.Session) -> bool:
    """
    Scrape một frame từ camera và lưu vào file
    Sử dụng session để giữ cookies và headers
    
    Args:
        camera_id: Camera ID
        output_dir: Thư mục lưu file
        session: requests.Session để giữ cookies
        
    Returns:
        True nếu thành công, False nếu thất bại
    """
    url = build_camera_url(camera_id)
    
    try:
        response = session.get(url, headers=image_headers, timeout=CAMERA_TIMEOUT)
        
        if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image/"):
            # Tạo tên file với timestamp và camera ID
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"cam_{camera_id[:8]}_{ts}.jpg"
            filepath = output_dir / filename
            
            # Lưu file
            with open(filepath, "wb") as f:
                f.write(response.content)
            
            return True
        else:
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"  Lỗi khi scrape camera {camera_id[:8]}: {e}")
        return False


def main():
    """Hàm chính"""
    print("=" * 60)
    print("  Traffic Camera Frame Scraper")
    print("=" * 60)
    print()
    
    # Tạo thư mục output
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Thư mục output: {OUTPUT_DIR.absolute()}")
    print()
    
    # Tạo session để giữ cookies giữa các requests
    session = requests.Session()
    
    # Lấy danh sách camera IDs từ trang Map
    camera_ids = get_camera_ids_from_map(session)
    
    if not camera_ids:
        print("⚠️  Không tìm thấy camera nào. Sử dụng camera ID mặc định...")
        # Fallback: sử dụng camera ID từ network inspector mới nhất
        camera_ids = {"6623f3436f998a001b252863"}
    
    print(f"\nBắt đầu scrape {len(camera_ids)} camera(s)...")
    print(f"Interval: {SCRAPE_INTERVAL} giây")
    print("Nhấn Ctrl+C để dừng")
    print()
    
    frame_count = {cid: 0 for cid in camera_ids}
    
    try:
        while True:
            start_time = time.time()
            
            for camera_id in camera_ids:
                success = scrape_camera_frame(camera_id, OUTPUT_DIR, session)
                if success:
                    frame_count[camera_id] += 1
                    print(f"✓ Camera {camera_id[:8]}: Frame #{frame_count[camera_id]}", end="\r")
            
            # Đợi đến interval tiếp theo
            elapsed = time.time() - start_time
            sleep_time = max(0, SCRAPE_INTERVAL - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
                
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Đã dừng scraper")
        print("=" * 60)
        print("\nThống kê:")
        for camera_id, count in frame_count.items():
            print(f"  Camera {camera_id[:8]}: {count} frames")
        print(f"\nTổng: {sum(frame_count.values())} frames")
        print(f"Lưu tại: {OUTPUT_DIR.absolute()}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
