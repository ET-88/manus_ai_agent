#!/usr/bin/env python3
"""
Manus AI Agent - VPS Deployment Script

This script helps set up and deploy the Manus AI Agent on a VPS.
"""

import os
import sys
import argparse
import subprocess
import shutil
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("deploy.log")
    ]
)
logger = logging.getLogger("deploy")

def run_command(command, shell=False):
    """
    Run a shell command and log the output
    
    Args:
        command: Command to run (list or string)
        shell: Whether to use shell execution
        
    Returns:
        Command output
    """
    logger.info(f"Running command: {command if isinstance(command, str) else ' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=True,
            text=True,
            capture_output=True
        )
        
        if result.stdout:
            logger.info(f"Command output: {result.stdout.strip()}")
        
        return result.stdout.strip()
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        if e.stdout:
            logger.error(f"Command output: {e.stdout.strip()}")
        if e.stderr:
            logger.error(f"Command error: {e.stderr.strip()}")
        raise

def check_dependencies():
    """
    Check if all required dependencies are installed
    """
    logger.info("Checking dependencies...")
    
    # Check Python version
    python_version = sys.version_info
    logger.info(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 9):
        logger.error("Python 3.9 or higher is required")
        sys.exit(1)
    
    # Check if pip is installed
    try:
        run_command(["pip", "--version"])
    except Exception:
        logger.error("pip is not installed or not in PATH")
        sys.exit(1)
    
    # Check if Docker is installed (optional)
    try:
        run_command(["docker", "--version"])
        logger.info("Docker is installed, sandbox mode will be available")
    except Exception:
        logger.warning("Docker is not installed or not in PATH, sandbox mode will not be available")
    
    logger.info("All required dependencies are installed")

def install_packages():
    """
    Install required Python packages
    """
    logger.info("Installing required Python packages...")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        logger.error(f"Requirements file not found: {requirements_file}")
        sys.exit(1)
    
    try:
        run_command(["pip", "install", "-r", str(requirements_file)])
        logger.info("All packages installed successfully")
    except Exception as e:
        logger.error(f"Failed to install packages: {str(e)}")
        sys.exit(1)

def setup_systemd_service(username):
    """
    Set up systemd service for running the agent on boot
    
    Args:
        username: System username
    """
    logger.info("Setting up systemd service...")
    
    # Define the service file path
    service_path = Path("/etc/systemd/system/manus-agent.service")
    
    # Get the absolute path to the project
    project_path = Path(__file__).parent.absolute()
    
    # Define the service file content
    service_content = f"""[Unit]
Description=Manus AI Agent
After=network.target

[Service]
User={username}
WorkingDirectory={project_path}
ExecStart=/usr/bin/python3 {project_path}/main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
    
    # Write the service file
    try:
        with open(service_path, "w") as f:
            f.write(service_content)
        
        # Set proper permissions
        os.chmod(service_path, 0o644)
        
        # Reload systemd and enable the service
        run_command(["systemctl", "daemon-reload"])
        run_command(["systemctl", "enable", "manus-agent.service"])
        
        logger.info("Systemd service set up successfully")
        logger.info("You can start the service with: sudo systemctl start manus-agent.service")
        
    except Exception as e:
        logger.error(f"Failed to set up systemd service: {str(e)}")
        sys.exit(1)

def configure_env_file(api_key=None):
    """
    Configure the .env file
    
    Args:
        api_key: Optional OpenRouter API key
    """
    logger.info("Configuring .env file...")
    
    env_file = Path(__file__).parent / ".env"
    env_example_file = Path(__file__).parent / ".env.example"
    
    # Check if .env.example exists
    if not env_example_file.exists():
        logger.error(f".env.example file not found: {env_example_file}")
        sys.exit(1)
    
    # Copy .env.example to .env if .env doesn't exist
    if not env_file.exists():
        shutil.copy(env_example_file, env_file)
        logger.info(f"Created .env file from .env.example")
    
    # Update API key if provided
    if api_key:
        logger.info("Updating API key in .env file...")
        
        # Read the current .env file
        with open(env_file, "r") as f:
            env_lines = f.readlines()
        
        # Update the API key line
        with open(env_file, "w") as f:
            for line in env_lines:
                if line.startswith("OPENROUTER_API_KEY="):
                    f.write(f"OPENROUTER_API_KEY={api_key}\n")
                else:
                    f.write(line)
        
        logger.info("API key updated successfully")

def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description="Deploy Manus AI Agent to a VPS")
    
    parser.add_argument("--api-key", help="OpenRouter API key")
    parser.add_argument("--username", default="root", help="System username for systemd service")
    parser.add_argument("--setup-service", action="store_true", help="Set up systemd service")
    parser.add_argument("--install-deps", action="store_true", help="Install dependencies")
    
    args = parser.parse_args()
    
    logger.info("Starting deployment of Manus AI Agent...")
    
    # Check dependencies
    check_dependencies()
    
    # Install packages if requested
    if args.install_deps:
        install_packages()
    
    # Configure .env file
    configure_env_file(args.api_key)
    
    # Set up systemd service if requested
    if args.setup_service:
        setup_systemd_service(args.username)
    
    logger.info("Deployment completed successfully")
    logger.info("Run 'python main.py' to start the agent interactively, or use the systemd service if configured")

if __name__ == "__main__":
    main() 