#!/usr/bin/env python3
"""
Manus AI Agent - Main Application Entry Point
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import project modules
from gui.app import start_gui
from config.settings import load_settings
from agents.orchestrator import AgentOrchestrator
from api.openrouter import OpenRouterAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("manus_agent.log")
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the Manus AI Agent application"""
    try:
        # Load environment variables
        load_dotenv()
        logger.info("Environment variables loaded")
        
        # Load application settings
        settings = load_settings()
        logger.info("Application settings loaded")
        
        # Initialize OpenRouter API client
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.error("OPENROUTER_API_KEY not found in environment variables")
            print("Error: OPENROUTER_API_KEY not found. Please set it in your .env file.")
            sys.exit(1)
            
        openrouter_client = OpenRouterAPI(api_key)
        logger.info("OpenRouter API client initialized")
        
        # Initialize agent orchestrator
        orchestrator = AgentOrchestrator(openrouter_client, settings)
        logger.info("Agent orchestrator initialized")
        
        # Start the GUI application
        start_gui(orchestrator)
        
    except Exception as e:
        logger.error(f"Error in main application: {str(e)}", exc_info=True)
        print(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 