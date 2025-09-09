import socket
import struct
import cv2
import numpy as np
import time


def recv_exact(sock, num_bytes):
    """Receive exactly num_bytes from socket"""
    data = bytearray()
    while len(data) < num_bytes:
        chunk = sock.recv(num_bytes - len(data))
        if not chunk:
            raise ConnectionError("Socket closed")
        data.extend(chunk)
    return bytes(data)


def connect_to_unity(host="127.0.0.1", port=5001):
    """Connect to Unity camera stream"""
    try:
        print(f"Connecting to Unity at {host}:{port}...")
        sock = socket.create_connection((host, port), timeout=5.0)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(30.0)  # Set longer timeout for receiving data
        print("Connected! Starting video stream...")
        return sock
    except Exception as e:
        print(f"Connection failed: {e}")
        return None


def main():
    """Main streaming loop"""
    sock = connect_to_unity()
    if not sock:
        return
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Read frame length (4 bytes, big-endian)
            length_data = recv_exact(sock, 4)
            frame_len = struct.unpack("!i", length_data)[0]
            
            if frame_len <= 0:
                print("Invalid frame length")
                break
            
            # Read JPEG data
            jpeg_data = recv_exact(sock, frame_len)
            
            # Decode image
            img_array = np.frombuffer(jpeg_data, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None:
                print("Failed to decode frame")
                continue
            
            frame_count += 1
            
            # Calculate FPS
            current_time = time.time()
            elapsed = current_time - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            
            # Add FPS text to image
            cv2.putText(img, f"FPS: {fps:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(img, f"Frame: {frame_count}", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Display image
            cv2.imshow("Unity Camera Stream", img)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                print("ESC pressed - closing")
                break
            elif key == ord('s'):  # Save frame
                filename = f"frame_{frame_count}.jpg"
                cv2.imwrite(filename, img)
                print(f"Saved: {filename}")
            
            # Print progress every 100 frames
            if frame_count % 100 == 0:
                print(f"Frames: {frame_count}, FPS: {fps:.1f}")
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()
        cv2.destroyAllWindows()
        
        # Print final stats
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        print(f"Session: {frame_count} frames, {avg_fps:.1f} avg FPS, {total_time:.1f}s")


if __name__ == "__main__":
    main()
