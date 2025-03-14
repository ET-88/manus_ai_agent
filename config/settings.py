"""
Settings Module

Handles loading and managing application configuration.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class Settings(BaseModel):
    """Settings model for the application"""
    
    # API settings
    openrouter_api_key: Optional[str] = None
    default_model: str = "claude-3-sonnet-20240229"
    
    # Security settings
    enable_sandbox: bool = True
    max_execution_time: int = 300  # seconds
    
    # GUI settings
    gui_width: int = 800
    gui_height: int = 600
    default_yolo_mode: bool = False
    
    # Agent settings
    planning_temperature: float = 0.2
    execution_temperature: float = 0.7
    max_planning_tokens: int = 2048
    max_execution_tokens: int = 4096
    
    # Advanced settings
    allowed_commands: list = ["ls", "cat", "pwd", "echo", "grep", "find"]
    blocked_commands: list = ["rm", "mkfs", "dd", ">", "format"]

def load_settings() -> Settings:
    """
    Load settings from environment variables and config files
    
    Returns:
        Settings object with loaded configuration
    """
    # First, load from environment variables
    settings_dict = {
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
        "default_model": os.getenv("DEFAULT_MODEL", "claude-3-sonnet-20240229"),
        "enable_sandbox": os.getenv("ENABLE_SANDBOX", "true").lower() == "true",
        "max_execution_time": int(os.getenv("MAX_EXECUTION_TIME", "300")),
        "gui_width": int(os.getenv("GUI_WIDTH", "800")),
        "gui_height": int(os.getenv("GUI_HEIGHT", "600")),
        "default_yolo_mode": os.getenv("DEFAULT_YOLO_MODE", "false").lower() == "true"
    }
    
    # Try to load from config.json if it exists
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
                # Update settings with config file values
                settings_dict.update(config_data)
                logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config file {config_path}: {str(e)}")
    
    # Create and return settings object
    settings = Settings(**settings_dict)
    return settings

def save_settings(settings: Settings) -> bool:
    """
    Save settings to config file
    
    Args:
        settings: Settings object to save
        
    Returns:
        True if successful, False otherwise
    """
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        # Convert to dictionary and remove None values
        settings_dict = settings.dict(exclude_none=True)
        
        # Write to config file
        with open(config_path, "w") as f:
            json.dump(settings_dict, f, indent=2)
        
        logger.info(f"Saved configuration to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving config file {config_path}: {str(e)}")
        return False 