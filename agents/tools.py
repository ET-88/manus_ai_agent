"""
Agent Tools Module

Provides tool implementations for agents to use during task execution.
"""

import os
import logging
import subprocess
import tempfile
import json
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

# Optional imports
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

logger = logging.getLogger(__name__)

class WebScraper:
    """Tool for scraping content from web pages"""
    
    def __init__(self):
        """Initialize the web scraper tool"""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        logger.info("Web scraper tool initialized")
    
    def scrape(self, url: str, selector: Optional[str] = None, credentials: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Scrape content from a URL
        
        Args:
            url: The URL to scrape
            selector: Optional CSS selector to extract specific content
            credentials: Optional dictionary with username/password for basic auth
            
        Returns:
            Dictionary with scraped content
        """
        try:
            logger.info(f"Scraping URL: {url}")
            
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return {"success": False, "error": f"Invalid URL: {url}"}
            
            # Handle authentication if provided
            auth = None
            if credentials and "username" in credentials and "password" in credentials:
                auth = (credentials["username"], credentials["password"])
            
            # Make the request
            response = self.session.get(url, auth=auth, timeout=30)
            response.raise_for_status()
            
            # Process the content
            content_type = response.headers.get("Content-Type", "")
            
            if "text/html" in content_type and BS4_AVAILABLE:
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Extract title
                title = soup.title.string if soup.title else "No title"
                
                # Extract main content
                if selector:
                    # Use selector if provided
                    selected_elements = soup.select(selector)
                    if selected_elements:
                        content = "\n".join(el.get_text(strip=True) for el in selected_elements)
                    else:
                        content = "No content found with the provided selector"
                else:
                    # Simple extraction of main content
                    for tag in soup(["script", "style", "meta", "link"]):
                        tag.extract()
                    content = soup.get_text(separator="\n", strip=True)
                
                return {
                    "success": True,
                    "url": url,
                    "title": title,
                    "content": content[:5000] + "..." if len(content) > 5000 else content,
                    "content_type": "html"
                }
                
            elif "application/json" in content_type:
                # Process JSON
                json_data = response.json()
                return {
                    "success": True,
                    "url": url,
                    "content": json.dumps(json_data, indent=2)[:5000] + "..." if len(json.dumps(json_data)) > 5000 else json.dumps(json_data, indent=2),
                    "content_type": "json"
                }
                
            else:
                # Return raw content for other types
                return {
                    "success": True,
                    "url": url,
                    "content": response.text[:5000] + "..." if len(response.text) > 5000 else response.text,
                    "content_type": content_type
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping URL {url}: {str(e)}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error scraping URL {url}: {str(e)}")
            return {
                "success": False,
                "url": url,
                "error": f"Unexpected error: {str(e)}"
            }


class ShellExecutor:
    """Tool for executing shell commands"""
    
    def __init__(self, allowed_commands: List[str] = None, blocked_commands: List[str] = None, enable_sandbox: bool = True):
        """
        Initialize the shell executor
        
        Args:
            allowed_commands: List of allowed shell commands
            blocked_commands: List of blocked shell commands
            enable_sandbox: Whether to use Docker sandboxing for command execution
        """
        self.allowed_commands = allowed_commands or ["ls", "cat", "pwd", "echo", "grep", "find"]
        self.blocked_commands = blocked_commands or ["rm", "mkfs", "dd", ">", "format"]
        self.enable_sandbox = enable_sandbox and DOCKER_AVAILABLE
        
        if self.enable_sandbox:
            try:
                self.docker_client = docker.from_env()
                logger.info("Docker sandbox enabled for shell command execution")
            except Exception as e:
                logger.warning(f"Failed to initialize Docker client: {str(e)}")
                self.enable_sandbox = False
        
        logger.info(f"Shell executor initialized with sandbox={self.enable_sandbox}")
    
    def is_command_allowed(self, command: str) -> bool:
        """
        Check if a command is allowed to be executed
        
        Args:
            command: The command to check
            
        Returns:
            True if allowed, False otherwise
        """
        # Split the command to get the base command
        command_parts = command.strip().split()
        if not command_parts:
            return False
            
        base_command = command_parts[0]
        
        # Check if the command is in the block list
        for blocked in self.blocked_commands:
            if blocked in command:
                logger.warning(f"Command contains blocked pattern: {blocked}")
                return False
        
        # Check if the command is in the allow list
        if self.allowed_commands:
            if base_command not in self.allowed_commands:
                logger.warning(f"Command not in allowed list: {base_command}")
                return False
        
        return True
    
    def run_command(self, command: str) -> Dict[str, Any]:
        """
        Execute a shell command
        
        Args:
            command: The command to execute
            
        Returns:
            Dictionary with command output
        """
        try:
            logger.info(f"Executing shell command: {command}")
            
            # First, check if the command is allowed
            if not self.is_command_allowed(command):
                return {
                    "success": False,
                    "command": command,
                    "error": "This command is not allowed for security reasons."
                }
            
            # Execute the command
            if self.enable_sandbox:
                return self._run_sandboxed(command)
            else:
                return self._run_local(command)
                
        except Exception as e:
            logger.error(f"Error executing command {command}: {str(e)}")
            return {
                "success": False,
                "command": command,
                "error": str(e)
            }
    
    def _run_local(self, command: str) -> Dict[str, Any]:
        """
        Run a command locally
        
        Args:
            command: Command to execute
            
        Returns:
            Command execution results
        """
        try:
            # Execute the command with a timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            stdout = result.stdout
            stderr = result.stderr
            
            return {
                "success": result.returncode == 0,
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "command": command,
                "error": "Command execution timed out after 60 seconds"
            }
    
    def _run_sandboxed(self, command: str) -> Dict[str, Any]:
        """
        Run a command in a Docker sandbox
        
        Args:
            command: Command to execute
            
        Returns:
            Command execution results
        """
        try:
            # Create a temporary script file
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.sh', delete=False) as script_file:
                script_file.write(f"#!/bin/sh\n{command}")
                script_path = script_file.name
            
            # Make the script executable
            os.chmod(script_path, 0o755)
            
            # Run the command in a Docker container
            container = self.docker_client.containers.run(
                "alpine:latest",
                ["/bin/sh", "-c", command],
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
                timeout=60,
                volumes={
                    os.path.dirname(script_path): {
                        'bind': '/mnt',
                        'mode': 'ro'
                    }
                }
            )
            
            # Parse the output
            try:
                output = container.decode('utf-8')
                return {
                    "success": True,
                    "command": command,
                    "stdout": output,
                    "stderr": "",
                    "returncode": 0
                }
            except Exception:
                return {
                    "success": False,
                    "command": command,
                    "error": "Failed to decode container output"
                }
                
        except Exception as e:
            return {
                "success": False,
                "command": command,
                "error": f"Error in Docker execution: {str(e)}"
            }
        finally:
            # Clean up temporary script
            if 'script_path' in locals():
                try:
                    os.unlink(script_path)
                except Exception:
                    pass


class FileManager:
    """Tool for managing files in the working directory"""
    
    def __init__(self, working_dir: Optional[str] = None):
        """
        Initialize the file manager
        
        Args:
            working_dir: Optional working directory (defaults to current directory)
        """
        self.working_dir = working_dir or os.getcwd()
        logger.info(f"File manager initialized with working directory: {self.working_dir}")
    
    def manage_file(self, action: str, path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform a file operation
        
        Args:
            action: The action to perform (read, write, append, delete, list)
            path: The file or directory path
            content: Optional content for write/append operations
            
        Returns:
            Dictionary with operation results
        """
        try:
            logger.info(f"File operation: {action} on {path}")
            
            # Resolve the full path
            full_path = os.path.join(self.working_dir, path)
            
            # Make sure the path is within the working directory
            if not os.path.normpath(full_path).startswith(os.path.normpath(self.working_dir)):
                return {
                    "success": False,
                    "path": path,
                    "error": "Path is outside the working directory"
                }
            
            # Perform the requested action
            if action == "read":
                if not os.path.exists(full_path):
                    return {
                        "success": False,
                        "path": path,
                        "error": "File does not exist"
                    }
                    
                if os.path.isdir(full_path):
                    # List directory contents
                    contents = os.listdir(full_path)
                    return {
                        "success": True,
                        "path": path,
                        "is_directory": True,
                        "contents": contents
                    }
                else:
                    # Read file contents
                    with open(full_path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                    return {
                        "success": True,
                        "path": path,
                        "is_directory": False,
                        "content": file_content
                    }
                    
            elif action == "write":
                # Ensure the directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Write the content
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content or "")
                return {
                    "success": True,
                    "path": path,
                    "action": "write"
                }
                
            elif action == "append":
                # Ensure the directory exists
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Append the content
                with open(full_path, "a", encoding="utf-8") as f:
                    f.write(content or "")
                return {
                    "success": True,
                    "path": path,
                    "action": "append"
                }
                
            elif action == "delete":
                if not os.path.exists(full_path):
                    return {
                        "success": False,
                        "path": path,
                        "error": "File does not exist"
                    }
                    
                if os.path.isdir(full_path):
                    return {
                        "success": False,
                        "path": path,
                        "error": "Cannot delete directories"
                    }
                else:
                    # Delete the file
                    os.unlink(full_path)
                    return {
                        "success": True,
                        "path": path,
                        "action": "delete"
                    }
                    
            elif action == "list":
                if not os.path.exists(full_path):
                    return {
                        "success": False,
                        "path": path,
                        "error": "Path does not exist"
                    }
                    
                if not os.path.isdir(full_path):
                    return {
                        "success": False,
                        "path": path,
                        "error": "Path is not a directory"
                    }
                    
                # List directory contents with details
                contents = []
                for item in os.listdir(full_path):
                    item_path = os.path.join(full_path, item)
                    stat = os.stat(item_path)
                    contents.append({
                        "name": item,
                        "is_directory": os.path.isdir(item_path),
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    })
                    
                return {
                    "success": True,
                    "path": path,
                    "contents": contents
                }
                
            else:
                return {
                    "success": False,
                    "path": path,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            logger.error(f"Error in file operation {action} on {path}: {str(e)}")
            return {
                "success": False,
                "path": path,
                "action": action,
                "error": str(e)
            }


class WebSearchTool:
    """Tool for performing web searches"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the web search tool
        
        Args:
            api_key: Optional API key for search service
        """
        self.api_key = api_key
        logger.info("Web search tool initialized")
    
    def search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Perform a web search
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            Dictionary with search results
        """
        try:
            logger.info(f"Web search for: {query}")
            
            # In a real implementation, we would use a search API
            # For this simulation, we'll just return dummy results
            
            return {
                "success": True,
                "query": query,
                "results": [
                    {
                        "title": f"Example search result 1 for {query}",
                        "snippet": "This is an example search result snippet that would be returned by a real search API.",
                        "url": "https://example.com/result1"
                    },
                    {
                        "title": f"Example search result 2 for {query}",
                        "snippet": "Another example search result snippet that would be returned by a real search API.",
                        "url": "https://example.com/result2"
                    },
                    {
                        "title": f"Example search result 3 for {query}",
                        "snippet": "A third example search result snippet with relevant information about the query.",
                        "url": "https://example.com/result3"
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in web search for {query}: {str(e)}")
            return {
                "success": False,
                "query": query,
                "error": str(e)
            } 