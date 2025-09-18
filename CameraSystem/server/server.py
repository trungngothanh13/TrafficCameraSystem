#!/usr/bin/env python3
"""
Traffic Camera System - WebSocket Server
Stream 4 cameras from Unity to web clients using WebSocket
"""

import asyncio
import websockets
import json
import base64
import logging
from datetime import datetime
from typing import Set, Dict, Any
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TrafficCameraServer:
    def __init__(self, host='0.0.0.0', port=8081):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.camera_streams: Dict[int, Dict[str, Any]] = {}
        self.server = None
        
    async def register_client(self, websocket, path):
        """Register new client connection"""
        self.clients.add(websocket)
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"New client connected: {client_info}")
        
        # Send welcome message
        welcome_msg = {
            "type": "connection",
            "message": "Connected to Traffic Camera Server",
            "timestamp": datetime.now().isoformat(),
            "server": "Python WebSocket Server"
        }
        await websocket.send(json.dumps(welcome_msg))
        
        # Send all existing camera streams to new client
        for camera_id, stream_data in self.camera_streams.items():
            stream_msg = {
                "type": "camera_stream",
                "cameraId": camera_id,
                "data": stream_data["data"],
                "timestamp": stream_data["timestamp"]
            }
            await websocket.send(json.dumps(stream_msg))
        
        logger.info(f"Sent {len(self.camera_streams)} existing streams to new client")
        
    async def unregister_client(self, websocket):
        """Unregister client connection"""
        self.clients.discard(websocket)
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client disconnected: {client_info}")
        
    async def handle_camera_stream(self, message: str, sender_websocket):
        """Handle camera stream message from Unity"""
        try:
            # Parse message: "CAMERA_STREAM:{cameraId}:{base64Data}"
            parts = message.split(':', 2)
            if len(parts) >= 3:
                camera_id = int(parts[1])
                base64_data = parts[2]
                
                # Store latest frame data
                self.camera_streams[camera_id] = {
                    "data": base64_data,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Create stream message for web clients
                stream_msg = {
                    "type": "camera_stream",
                    "cameraId": camera_id,
                    "data": base64_data,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Broadcast to all web clients (excluding sender)
                if self.clients:
                    disconnected_clients = set()
                    for client in self.clients:
                        try:
                            if client != sender_websocket and not client.closed:
                                await client.send(json.dumps(stream_msg))
                        except websockets.exceptions.ConnectionClosed:
                            disconnected_clients.add(client)
                    
                    # Remove disconnected clients
                    for client in disconnected_clients:
                        self.clients.discard(client)
                
                logger.info(f"Broadcasted camera {camera_id} stream to {len(self.clients)} clients")
                
        except Exception as e:
            logger.error(f"Error handling camera stream: {e}")
    
    async def handle_message(self, websocket, message):
        """Handle incoming message from client"""
        try:
            message_str = message.decode('utf-8') if isinstance(message, bytes) else message
            
            # Check if it's a camera stream from Unity
            if message_str.startswith('CAMERA_STREAM:'):
                await self.handle_camera_stream(message_str, websocket)
            else:
                # Handle other message types
                try:
                    data = json.loads(message_str)
                    logger.info(f"Received JSON message: {data.get('type', 'unknown')}")
                except json.JSONDecodeError:
                    logger.info(f"Received text message: {message_str}")
                    
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def handle_client(self, websocket, path):
        """Handle individual client connection"""
        await self.register_client(websocket, path)
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Error in client handler: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting Traffic Camera WebSocket Server on {self.host}:{self.port}")
        
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10,
            compression=None  # Disable permessage-deflate to avoid unsupported headers in some Unity/.NET clients
        )
        
        logger.info(f"Server started successfully!")
        logger.info(f"WebSocket URL: ws://{self.host}:{self.port}")
        logger.info(f"Waiting for connections...")
        
        # Keep server running
        await self.server.wait_closed()
    
    def get_status(self):
        """Get server status information"""
        return {
            "status": "running",
            "connected_clients": len(self.clients),
            "active_cameras": len(self.camera_streams),
            "timestamp": datetime.now().isoformat(),
            "server": "Python WebSocket Server"
        }
    
    def get_cameras(self):
        """Get camera information"""
        camera_list = []
        for camera_id, stream_data in self.camera_streams.items():
            camera_list.append({
                "id": camera_id,
                "lastUpdate": stream_data["timestamp"],
                "status": "active"
            })
        
        return {
            "cameras": camera_list,
            "count": len(camera_list)
        }

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
