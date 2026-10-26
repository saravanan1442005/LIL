import os
import sys
import subprocess

# Auto-switch to project virtual environment if global python is used
venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts", "python.exe")
if os.path.exists(venv_python) and os.path.abspath(sys.executable).lower() != os.path.abspath(venv_python).lower():
    try:
        import sqlalchemy
    except ImportError:
        result = subprocess.call([venv_python] + sys.argv)
        sys.exit(result)

import time
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
