#!/usr/bin/env python3
"""
Traffic Camera System - OpenCV Viewer
Connects to the Python WebSocket server and displays up to 4 camera feeds in a 2x2 grid.
"""

import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
from datetime import datetime

WS_URL = 'ws://127.0.0.1:8081'
WINDOW_NAME = 'Traffic Camera - OpenCV Viewer'

class OpenCVViewer:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.frames = {}
        self.last_update = {}
        self.max_cameras = 4
        self.running = True

    def decode_frame(self, base64_data: str):
        try:
            jpg_data = base64.b64decode(base64_data)
            np_arr = np.frombuffer(jpg_data, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return frame
        except Exception:
            return None

    def build_grid(self):
        # Determine grid size based on available frames
        canvas_h, canvas_w = 1080, 1920
        grid = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

        # Sort by camera id for deterministic placement
        items = sorted(self.frames.items(), key=lambda kv: kv[0])[:self.max_cameras]
        num = len(items)
        if num == 0:
            cv2.putText(grid, 'Waiting for streams...', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255), 2)
            return grid

        # 2x2 grid layout
        cell_w = canvas_w // 2
        cell_h = canvas_h // 2
        positions = [(0,0), (0,cell_w), (cell_h,0), (cell_h,cell_w)]

        for idx, (cam_id, frame) in enumerate(items):
            if frame is None:
                continue
            h, w = frame.shape[:2]
            scale = min(cell_w / w, cell_h / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            resized = cv2.resize(frame, (new_w, new_h))

            y, x = positions[idx]
            y_off = y + (cell_h - new_h) // 2
            x_off = x + (cell_w - new_w) // 2
            grid[y_off:y_off+new_h, x_off:x_off+new_w] = resized

            # Overlay labels
            label = f'Camera {cam_id}  {self.last_update.get(cam_id, "").split("T")[-1][:8]}'
            cv2.rectangle(grid, (x+10, y+10), (x+250, y+45), (0,0,0), -1)
            cv2.putText(grid, label, (x+15, y+38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)

        return grid

    async def run(self):
        print(f'Connecting to {self.ws_url} ...')
        async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10, compression=None) as ws:
            print('Connected.')
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WINDOW_NAME, 1280, 720)

            async for message in ws:
                try:
                    data = json.loads(message)
                except Exception:
                    continue

                if data.get('type') == 'camera_stream':
                    cam_id = int(data.get('cameraId', -1))
                    img_b64 = data.get('data')
                    ts = data.get('timestamp', datetime.now().isoformat())
                    frame = self.decode_frame(img_b64)
                    if frame is not None:
                        self.frames[cam_id] = frame
                        self.last_update[cam_id] = ts

                    grid = self.build_grid()
                    cv2.imshow(WINDOW_NAME, grid)

                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:  # ESC
                        print('Exiting...')
                        break

        cv2.destroyAllWindows()


def main():
    viewer = OpenCVViewer(WS_URL)
    asyncio.run(viewer.run())

if __name__ == '__main__':
    main()
