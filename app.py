# app.py — Main Entry Point for ECOLIFEBUDDY Surveillance Workstation
import subprocess
import sys
import time
import os
import webbrowser
import threading

def run_workstation():
    """Launch the ECOLIFEBUDDY Surveillance Workstation."""
    print("=" * 65)
    print("  ECOLIFEBUDDY Surveillance Workstation v4.2 Pro")
    print("  District 4 Clean Surveillance Control Room")
    print("=" * 65)
    print("Starting AI Surveillance Engine and Desktop Workstation Window...")
    
    # Import and start web server
    import web_server
    web_server.start_server(port=5000)

if __name__ == '__main__':
    run_workstation()
