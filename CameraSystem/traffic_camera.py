import argparse
import socket
import struct
import sys
import time
import cv2
import numpy as np


def recv_exact(sock: socket.socket, num_bytes: int) -> bytes:
    """
    Receive exactly num_bytes from socket.
    Critical for TCP streaming - ensures complete frames.
    """
    data = bytearray()
    while len(data) < num_bytes:
        chunk = sock.recv(num_bytes - len(data))
        if not chunk:
            raise ConnectionError("Socket closed while receiving data")
        data.extend(chunk)
    return bytes(data)


def connect_once(host: str, port: int, window_title: str, debug: bool = False) -> None:
    """Enhanced connection with debugging and monitoring"""
    
    print(f"🔄 Attempting to connect to Unity at {host}:{port}...")
    print("📝 Make sure Unity is running and the CameraStreamer script is active!")
    
    try:
        with socket.create_connection((host, port), timeout=10.0) as sock:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            print(f"✅ Connected to {host}:{port}")
            print("📺 Starting video stream... Press ESC to quit, 'S' to save frame")
            
            # Frame monitoring
            frame_count = 0
            start_time = time.time()
            last_fps_update = start_time
            fps = 0
            
            while True:
                try:
                    # Read 4-byte big-endian length
                    length_be = recv_exact(sock, 4)
                    (frame_len,) = struct.unpack("!i", length_be)
                    
                    if debug and frame_count % 30 == 0:  # Debug every 30 frames
                        print(f"📦 Frame {frame_count}: {frame_len} bytes")
                    
                    if frame_len <= 0 or frame_len > 50_000_000:
                        raise ValueError(f"Invalid frame length: {frame_len}")

                    # Read JPEG payload
                    jpg_bytes = recv_exact(sock, frame_len)
                    np_buf = np.frombuffer(jpg_bytes, dtype=np.uint8)
                    img = cv2.imdecode(np_buf, cv2.IMREAD_COLOR)
                    
                    if img is None:
                        print("⚠️  Warning: failed to decode frame", file=sys.stderr)
                        continue

                    frame_count += 1
                    
                    # Calculate FPS
                    current_time = time.time()
                    if current_time - last_fps_update >= 1.0:  # Update FPS every second
                        elapsed = current_time - start_time
                        fps = frame_count / elapsed if elapsed > 0 else 0
                        last_fps_update = current_time
                    
                    # Add info overlay to image
                    img_display = img.copy()
                    info_text = [
                        f"Frame: {frame_count}",
                        f"FPS: {fps:.1f}",
                        f"Size: {img.shape[1]}x{img.shape[0]}",
                        f"Data: {frame_len} bytes"
                    ]
                    
                    y_pos = 25
                    for text in info_text:
                        cv2.putText(img_display, text, (10, y_pos), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                        y_pos += 25
                    
                    # Display image
                    cv2.imshow(window_title, img_display)
                    
                    # Handle key presses
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:  # ESC to quit
                        print("👋 ESC pressed - closing connection")
                        break
                    elif key == ord('s') or key == ord('S'):  # Save frame
                        timestamp = int(time.time())
                        filename = f"unity_frame_{timestamp}.jpg"
                        cv2.imwrite(filename, img)
                        print(f"💾 Saved frame: {filename}")
                    elif key == ord('d') or key == ord('D'):  # Toggle debug
                        debug = not debug
                        print(f"🐛 Debug mode: {'ON' if debug else 'OFF'}")
                    
                    # Show progress periodically
                    if frame_count % 100 == 0:
                        print(f"📊 Received {frame_count} frames, FPS: {fps:.1f}")
                        
                except struct.error as e:
                    print(f"❌ Protocol error: {e}")
                    print("🔧 Check if Unity CameraStreamer is sending correct format")
                    break
                except Exception as e:
                    print(f"❌ Frame processing error: {e}")
                    continue

    except ConnectionRefusedError:
        print("❌ Connection refused!")
        print("🔧 Make sure:")
        print("   1. Unity is running")
        print("   2. CameraStreamer script is attached to a camera")
        print("   3. Unity scene is playing")
        print(f"   4. Port {port} is not blocked by firewall")
    except socket.timeout:
        print("⏱️  Connection timeout!")
        print("🔧 Unity might be slow to start or not responding")
    except Exception as e:
        print(f"❌ Connection error: {e}")
    finally:
        cv2.destroyAllWindows()
        total_time = time.time() - start_time
        if frame_count > 0:
            avg_fps = frame_count / total_time if total_time > 0 else 0
            print(f"📈 Session stats: {frame_count} frames, {avg_fps:.1f} avg FPS, {total_time:.1f}s")


def test_connection(host: str, port: int) -> bool:
    """Test if Unity server is reachable"""
    try:
        print(f"🔍 Testing connection to {host}:{port}...")
        sock = socket.create_connection((host, port), timeout=3.0)
        sock.close()
        print("✅ Connection test successful!")
        return True
    except:
        print("❌ Connection test failed - Unity server not reachable")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Receive and display Unity camera stream over TCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Controls:
  ESC     - Quit application
  S       - Save current frame
  D       - Toggle debug mode

Make sure Unity is running with CameraStreamer script attached to a camera!
        """
    )
    parser.add_argument("--host", default="127.0.0.1", 
                       help="Unity server host/IP (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5001, 
                       help="Unity server port (default: 5001)")
    parser.add_argument("--retry", type=int, default=3, 
                       help="Reconnect attempts (-1 for infinite, default: 3)")
    parser.add_argument("--delay", type=float, default=2.0, 
                       help="Delay between retries in seconds (default: 2.0)")
    parser.add_argument("--debug", action="store_true", 
                       help="Enable debug output")
    parser.add_argument("--test", action="store_true", 
                       help="Test connection and exit")
    
    args = parser.parse_args()
    
    # Test connection if requested
    if args.test:
        success = test_connection(args.host, args.port)
        sys.exit(0 if success else 1)
    
    print("🎮 Unity Camera Stream Client")
    print("=" * 40)
    print(f"Target: {args.host}:{args.port}")
    print(f"Retries: {'infinite' if args.retry < 0 else args.retry}")
    print(f"Debug: {'enabled' if args.debug else 'disabled'}")
    print()

    retries_remaining = args.retry
    attempt = 1
    
    while True:
        try:
            print(f"🔄 Connection attempt {attempt}")
            connect_once(args.host, args.port, 
                        window_title=f"Unity Stream {args.host}:{args.port}",
                        debug=args.debug)
            print("✅ Session ended normally")
            break
            
        except (ConnectionError, OSError, ValueError) as exc:
            print(f"❌ Connection failed: {exc}")
            
            if retries_remaining == 0:
                print("💔 No more retries. Exiting.")
                break
                
            if retries_remaining > 0:
                retries_remaining -= 1
                
            remaining_str = 'infinite' if args.retry < 0 else str(retries_remaining)
            print(f"⏳ Retrying in {args.delay:.1f}s... ({remaining_str} attempts left)")
            time.sleep(args.delay)
            attempt += 1
            
        except KeyboardInterrupt:
            print("\n👋 Interrupted by user")
            break


if __name__ == "__main__":
    main()