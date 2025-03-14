"""
OpenRouter API Integration

This module handles interactions with the OpenRouter API for accessing various LLMs.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class OpenRouterAPI:
    """Client for interacting with OpenRouter API to access various LLMs"""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key: str):
        """
        Initialize the OpenRouter API client
        
        Args:
            api_key: OpenRouter API key
        """
        self.api_key = api_key
        self.default_model = os.getenv("DEFAULT_MODEL", "claude-3-sonnet-20240229")
        logger.info(f"OpenRouter API client initialized with default model: {self.default_model}")
    
    def get_headers(self) -> Dict[str, str]:
        """
        Generate headers for OpenRouter API requests
        
        Returns:
            Dictionary of headers
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://manus-ai-agent.example.com"  # Replace with your domain
        }
    
    def generate_completion(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop_sequences: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a completion response from the specified model
        
        Args:
            prompt: The input prompt to generate a completion for
            model: The model to use (defaults to self.default_model if None)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (higher = more creative, lower = more deterministic)
            top_p: Nucleus sampling parameter
            stop_sequences: Optional list of sequences that will stop generation if encountered
            
        Returns:
            The completion response
        """
        model_to_use = model or self.default_model
        logger.info(f"Generating completion with model: {model_to_use}")
        
        url = f"{self.BASE_URL}/chat/completions"
        headers = self.get_headers()
        
        payload = {
            "model": model_to_use,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if stop_sequences:
            payload["stop"] = stop_sequences
        
        try:
            logger.debug(f"Sending request to OpenRouter API: {json.dumps(payload)}")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            completion_data = response.json()
            
            # Extract the completion text
            completion = completion_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"Successfully received completion from OpenRouter API")
            
            return {
                "completion": completion,
                "model": model_to_use,
                "raw_response": completion_data
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to OpenRouter API: {str(e)}")
            return {
                "error": str(e),
                "completion": "",
                "model": model_to_use
            }
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Fetch the list of available models from OpenRouter
        
        Returns:
            List of available models with their details
        """
        url = f"{self.BASE_URL}/models"
        headers = self.get_headers()
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            models_data = response.json()
            
            logger.info(f"Successfully retrieved {len(models_data.get('data', []))} models from OpenRouter API")
            return models_data.get("data", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching available models from OpenRouter API: {str(e)}")
            return [] 