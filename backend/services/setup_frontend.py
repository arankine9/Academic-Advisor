import os
import subprocess
import sys
from pathlib import Path

"""
This script automates the setup of the React frontend.
It's a simplified version that only handles production builds.
"""

# Get the current directory
FRONTEND_DIR = Path(__file__).parent.absolute()

def check_npm_installed():
    """Check if npm is installed."""
    try:
        subprocess.run(['npm', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_dependencies():
    """Install npm dependencies."""
    print("Installing React dependencies...")
    try:
        subprocess.run(['npm', 'install'], cwd=FRONTEND_DIR, check=True)
        print("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False

def build_frontend():
    """Build the React frontend for production."""
    print("Building React frontend...")
    try:
        subprocess.run(['npm', 'run', 'build'], cwd=FRONTEND_DIR, check=True)
        print("Frontend built successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building frontend: {e}")
        return False

def setup_frontend():
    """Set up the React frontend for production."""
    # Check if package.json exists
    package_json_path = FRONTEND_DIR / 'package.json'
    if not package_json_path.exists():
        print("Error: package.json not found in frontend directory.")
        return False

    # Check if npm is installed
    if not check_npm_installed():
        print("Error: npm is not installed. Please install Node.js and npm.")
        return False

    # Install dependencies if node_modules doesn't exist
    node_modules_path = FRONTEND_DIR / 'node_modules'
    if not node_modules_path.exists():
        if not install_dependencies():
            return False

    # Always build for production
    if not build_frontend():
        return False

    return True

if __name__ == "__main__":
    success = setup_frontend()
    sys.exit(0 if success else 1)