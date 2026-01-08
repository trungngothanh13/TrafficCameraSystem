#!/usr/bin/env python3
"""
Traffic Camera System - WebSocket Server
Stream 4 cameras from Unity to web clients using WebSocket

Architecture:
- Unity clients send camera frames (binary or text format)
- Server broadcasts frames to all connected web/OpenCV clients
- Supports both binary (efficient) and text (legacy) protocols
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Set, Dict, Any, Optional
import signal
import sys

# Import configuration and protocol
from config import (
    DEFAULT_HOST, DEFAULT_PORT,
    PING_INTERVAL, PING_TIMEOUT, CLOSE_TIMEOUT, MAX_QUEUE,
    ENABLE_COMPRESSION, LOG_FORMAT, LOG_LEVEL, MAX_CAMERAS
)
from protocol import (
    parse_text_stream_message, parse_binary_stream_packet,
    create_connection_message, create_stream_message,
    jpeg_to_base64
)
from camera_manager import CameraManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

class TrafficCameraServer:
    """
    WebSocket server for traffic camera streaming
    
    Responsibilities:
    1. Accept connections from Unity (senders) and web clients (receivers)
    2. Receive camera frames from Unity (binary or text format)
    3. Broadcast frames to all connected web/OpenCV clients
    4. Maintain latest frame cache for each camera
    """
    
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        """
        Initialize server
        
        Args:
            host: Server host address (default: '0.0.0.0' = all interfaces)
            port: Server port (default: 8081)
        """
        self.host = host
        self.port = port
        # Active WebSocket connections (both Unity senders and web receivers)
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        # Camera manager for 4 cameras
        self.camera_manager = CameraManager(max_cameras=MAX_CAMERAS)
        # Legacy camera_streams dict (for backward compatibility)
        self.camera_streams: Dict[int, Dict[str, Any]] = {}
        self.server: Optional[websockets.Server] = None
        
    async def register_client(self, websocket: websockets.WebSocketServerProtocol, 
                             path: str) -> None:
        """
        Register new client connection and send initial data
        
        Flow:
        1. Add client to active connections set
        2. Send welcome message
        3. Send all existing camera frames (catch-up for new clients)
        
        Args:
            websocket: WebSocket connection object
            path: Connection path (unused, kept for compatibility)
        """
        self.clients.add(websocket)
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"New client connected: {client_info}")
        
        # Send welcome message
        welcome_msg = create_connection_message()
        await websocket.send(json.dumps(welcome_msg))
        
        # Send all existing camera streams to new client (catch-up)
        # This ensures new clients see current state immediately
        all_cameras = self.camera_manager.get_all_camera_data()
        for camera_id, camera_data in all_cameras.items():
            stream_msg = create_stream_message(
                camera_id,
                camera_data["data"]
            )
            await websocket.send(json.dumps(stream_msg))
        
        logger.info(f"Sent {len(all_cameras)} existing streams to new client")
        
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """
        Unregister client connection (cleanup)
        
        Args:
            websocket: WebSocket connection to remove
        """
        self.clients.discard(websocket)
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client disconnected: {client_info}")
        
    async def handle_camera_stream_text(self, message: str, 
                                       sender_websocket: websockets.WebSocketServerProtocol) -> None:
        """
        Handle text-format camera stream message (legacy protocol)
        
        Message format: "CAMERA_STREAM:{cameraId}:{base64Data}"
        
        Args:
            message: Text message string
            sender_websocket: WebSocket connection that sent the message
        """
        try:
            parsed = parse_text_stream_message(message)
            if not parsed:
                logger.warning("Invalid text stream message format")
                return
            
            camera_id = parsed['camera_id']
            base64_data = parsed['base64_data']
            
            # Validate camera ID (0-3 for 4 cameras)
            if camera_id < 0 or camera_id >= MAX_CAMERAS:
                logger.warning(f"Invalid camera ID: {camera_id} (expected 0-{MAX_CAMERAS-1})")
                return
            
            # Update camera manager
            self.camera_manager.update_camera(camera_id, base64_data)
            
            # Legacy compatibility
            self.camera_streams[camera_id] = {
                "data": base64_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Broadcast to all clients (excluding sender)
            await self._broadcast_stream(camera_id, base64_data, sender_websocket)
            
            # Log camera activity (every 30 frames to reduce spam)
            stats = self.camera_manager.stats.get(camera_id, {})
            frames = stats.get("frames_received", 0)
            if frames % 30 == 0:
                fps = stats.get("avg_fps", 0)
                logger.info(f"Camera {camera_id}: {frames} frames, {fps} FPS")
            
        except Exception as e:
            logger.error(f"Error handling text camera stream: {e}", exc_info=True)

    async def handle_binary_stream(self, data: bytes, 
                                  sender_websocket: websockets.WebSocketServerProtocol) -> None:
        """
        Handle binary-format camera stream packet (current protocol)
        
        Packet format: [1 byte: camera_id][8 bytes: timestamp][4 bytes: length][N bytes: jpeg]
        
        Advantages over text format:
        - No base64 encoding overhead (33% size reduction)
        - Faster parsing (binary vs string split)
        - More efficient network usage
        
        Args:
            data: Binary packet data
            sender_websocket: WebSocket connection that sent the packet
        """
        try:
            parsed = parse_binary_stream_packet(data)
            if not parsed:
                logger.warning("Invalid binary packet format or too short")
                return
            
            camera_id = parsed['camera_id']
            jpeg_bytes = parsed['jpeg_bytes']
            
            # Validate camera ID (0-3 for 4 cameras)
            if camera_id < 0 or camera_id >= MAX_CAMERAS:
                logger.warning(f"Invalid camera ID: {camera_id} (expected 0-{MAX_CAMERAS-1})")
                return
            
            # Convert JPEG to base64 for JSON message (web clients expect base64)
            base64_data = jpeg_to_base64(jpeg_bytes)
            
            # Update camera manager
            self.camera_manager.update_camera(camera_id, base64_data)
            
            # Legacy compatibility
            self.camera_streams[camera_id] = {
                "data": base64_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Broadcast to all clients (excluding sender)
            await self._broadcast_stream(camera_id, base64_data, sender_websocket)
            
            # Log camera activity (every 30 frames to reduce spam)
            stats = self.camera_manager.stats.get(camera_id, {})
            frames = stats.get("frames_received", 0)
            if frames % 30 == 0:
                fps = stats.get("avg_fps", 0)
                logger.info(f"Camera {camera_id}: {frames} frames, {fps} FPS")
            
        except Exception as e:
            logger.error(f"Error handling binary camera stream: {e}", exc_info=True)
    
    async def _broadcast_stream(self, camera_id: int, base64_data: str,
                               sender_websocket: websockets.WebSocketServerProtocol) -> None:
        """
        Broadcast camera stream to all connected clients (except sender)
        
        Uses asyncio.gather for parallel sending to improve performance.
        Exceptions from individual sends are caught to prevent one failed
        client from blocking others.
        
        Args:
            camera_id: Camera ID
            base64_data: Base64-encoded JPEG data
            sender_websocket: WebSocket that sent the frame (excluded from broadcast)
        """
        if not self.clients:
            return
        
        # Create JSON message for web/OpenCV clients
        stream_msg = create_stream_message(camera_id, base64_data)
        payload = json.dumps(stream_msg)
        
        # Collect send tasks for all clients except sender
        tasks = []
        for client in self.clients:
            if client != sender_websocket and not client.closed:
                tasks.append(client.send(payload))
        
        # Send to all clients in parallel
        if tasks:
            # return_exceptions=True: don't fail if one client errors
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful sends
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            if success_count > 0:
                logger.debug(f"Broadcasted camera {camera_id} to {success_count}/{len(tasks)} clients")

    async def handle_message(self, websocket: websockets.WebSocketServerProtocol, 
                           message: Any) -> None:
        """
        Route incoming message to appropriate handler
        
        Message types:
        - bytes: Binary camera stream packet (current protocol)
        - str starting with "CAMERA_STREAM:": Text camera stream (legacy)
        - Other str: JSON or plain text message
        
        Args:
            websocket: WebSocket connection
            message: Message data (bytes or str)
        """
        try:
            # Binary protocol (current - more efficient)
            if isinstance(message, bytes):
                await self.handle_binary_stream(message, websocket)
                return
            
            # Text protocol (legacy - for backward compatibility)
            if isinstance(message, str):
                # Legacy text format: "CAMERA_STREAM:{id}:{base64}"
                if message.startswith('CAMERA_STREAM:'):
                    await self.handle_camera_stream_text(message, websocket)
                    return
                
                # Try parsing as JSON
                try:
                    data = json.loads(message)
                    logger.info(f"Received JSON message: {data.get('type', 'unknown')}")
                except json.JSONDecodeError:
                    logger.debug(f"Received plain text message: {message[:100]}")
                    
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, 
                           path: str) -> None:
        """
        Handle individual client connection lifecycle
        
        Flow:
        1. Register client (send welcome + catch-up frames)
        2. Process incoming messages in loop
        3. Unregister client on disconnect/error
        
        Args:
            websocket: WebSocket connection
            path: Connection path (unused)
        """
        await self.register_client(websocket, path)
        try:
            # Message processing loop
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            # Normal disconnect (client closed connection)
            # No need to log as error
            pass
        except Exception as e:
            logger.error(f"Error in client handler: {e}", exc_info=True)
        finally:
            # Always cleanup, even on error
            await self.unregister_client(websocket)
    
    async def start_server(self) -> None:
        """
        Start the WebSocket server and begin accepting connections
        
        Server configuration:
        - ping_interval: Send ping every N seconds to detect dead connections
        - ping_timeout: Wait N seconds for pong response
        - close_timeout: Graceful shutdown timeout
        - max_queue: Limit queued messages to prevent memory issues
        - compression: Disabled for Unity/.NET compatibility
        """
        logger.info(f"Starting Traffic Camera WebSocket Server on {self.host}:{self.port}")
        
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=PING_INTERVAL,
            ping_timeout=PING_TIMEOUT,
            close_timeout=CLOSE_TIMEOUT,
            max_queue=MAX_QUEUE,
            compression=None if not ENABLE_COMPRESSION else 'deflate'
        )
        
        logger.info(f"Server started successfully!")
        logger.info(f"WebSocket URL: ws://{self.host}:{self.port}")
        logger.info(f"Maximum cameras supported: {MAX_CAMERAS}")
        logger.info(f"Waiting for connections...")
        
        # Start background task for periodic cleanup
        asyncio.create_task(self._periodic_cleanup())
        
        # Keep server running until closed
        await self.server.wait_closed()
    
    async def _periodic_cleanup(self):
        """
        Periodic background task to clean up inactive cameras
        
        Runs every 30 seconds to remove cameras that haven't sent frames
        """
        while True:
            try:
                await asyncio.sleep(30)  # Run every 30 seconds
                removed = self.camera_manager.clear_inactive_cameras()
                if removed > 0:
                    logger.info(f"Cleaned up {removed} inactive camera(s)")
                
                # Log camera status periodically
                status = self.camera_manager.get_all_cameras_status()
                active_cameras = [cam["id"] for cam in status["cameras"] if cam["status"] == "active"]
                if active_cameras:
                    logger.info(f"Active cameras: {active_cameras} ({status['active']}/{status['total']})")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive server status information
        
        Returns:
            Dict with server status, clients, and camera statistics
        """
        camera_status = self.camera_manager.get_all_cameras_status()
        
        return {
            "status": "running",
            "connected_clients": len(self.clients),
            "cameras": camera_status,
            "timestamp": datetime.now().isoformat(),
            "server": "Python WebSocket Server",
            "max_cameras": MAX_CAMERAS
        }
    
    def get_cameras(self) -> Dict[str, Any]:
        """
        Get detailed camera information
        
        Returns:
            Dict with list of camera statuses and statistics
        """
        return self.camera_manager.get_all_cameras_status()
    
    def get_camera_info(self, camera_id: int) -> Dict[str, Any]:
        """
        Get information for a specific camera
        
        Args:
            camera_id: Camera ID (0-3)
        
        Returns:
            Camera status dict
        """
        return self.camera_manager.get_camera_status(camera_id)

# Global server instance
server_instance = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal, closing server...")
    if server_instance and server_instance.server:
        asyncio.create_task(server_instance.server.close())
    sys.exit(0)

async def main():
    """Main function"""
    global server_instance
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start server
    server_instance = TrafficCameraServer()
    
    try:
        await server_instance.start_server()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    print("=" * 50)
    print("   Traffic Camera System - Python Server")
    print("=" * 50)
    print()
    print("Starting WebSocket server...")
    print("WebSocket URL: ws://localhost:8081")
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)
