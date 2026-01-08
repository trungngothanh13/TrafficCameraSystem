#!/usr/bin/env python3
"""
Traffic Camera System - Server Starter
Simple script to start the WebSocket server with proper error handling
"""

import sys
import subprocess
import os
from pathlib import Path
import argparse

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("ERROR: Python 3.7 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True

def install_requirements(skip_install: bool):
    """Install required packages (can be skipped with flag)"""
    if skip_install:
        print("⏩ Skip installing requirements (requested)")
        return True

    try:
        print("Installing required packages...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        print("✅ Packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing packages: {e}")
        return False
    except FileNotFoundError:
        print("❌ pip not found. Please install pip first.")
        return False

def start_server():
    """Start the WebSocket server"""
    try:
        print("Starting Traffic Camera WebSocket Server...")
        print("=" * 50)
        subprocess.run([sys.executable, "server.py"])
    except KeyboardInterrupt:
        print("\n✅ Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Traffic Camera System - Python Server")
    parser.add_argument("--skip-install", action="store_true", help="Skip pip install -r requirements.txt")
    args = parser.parse_args()

    print("🚦 Traffic Camera System - Python Server")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Install requirements
    if not install_requirements(args.skip_install):
        sys.exit(1)
    
    print()
    print("✅ All requirements satisfied!")
    print("🚀 Starting server...")
    print()
    
    # Start server
    start_server()

if __name__ == "__main__":
    main()
