#!/usr/bin/env python3
"""
Configuration settings for Traffic Camera Server
"""

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

# Network settings
DEFAULT_HOST = '0.0.0.0'  # Listen on all interfaces
DEFAULT_PORT = 8081

# WebSocket connection settings
PING_INTERVAL = 20  # Send ping every 20 seconds to keep connection alive
PING_TIMEOUT = 10   # Wait 10 seconds for pong response
CLOSE_TIMEOUT = 5   # Wait 5 seconds for graceful close
MAX_QUEUE = 32      # Maximum queued messages per connection (prevent memory bloat)

# Compression
ENABLE_COMPRESSION = False  # Disabled for Unity/.NET compatibility

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# ============================================================================
# CAMERA STREAM SETTINGS
# ============================================================================

MAX_CAMERAS = 4  # Maximum number of camera streams supported
