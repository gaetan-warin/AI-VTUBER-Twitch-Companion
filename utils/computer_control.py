"""Computer Control Module for AI Assistant

This module provides safe and controlled computer interaction capabilities for the AI assistant.
It implements a set of actions that allow the AI to interact with the computer to accomplish tasks.
"""

import os
import subprocess
import logging
import json
import webbrowser
import requests
from pathlib import Path
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ComputerController:
    """Handles computer control actions with safety checks and logging."""
    
    def __init__(self, require_confirmation=True):
        """
        Initialize the computer controller.
        
        Args:
            require_confirmation: Whether to require user confirmation for actions
        """
        self.require_confirmation = require_confirmation
        self.allowed_actions = {
            'open_application': self.open_application,
            'open_website': self.open_website,
            'create_file': self.create_file,
            'read_file': self.read_file,
            'list_directory': self.list_directory,
            'run_command': self.run_command,
            'search_web': self.search_web,
            'scrape_webpage': self.scrape_webpage,
            'extract_links': self.extract_links,
        }
    
    def execute_action(self, action_name, parameters):
        """
        Execute a computer control action.
        
        Args:
            action_name: Name of the action to execute
            parameters: Dictionary of parameters for the action
            
        Returns:
            dict: Result of the action with status and message
        """
        if action_name not in self.allowed_actions:
            return {
                'status': 'error',
                'message': f'Unknown action: {action_name}'
            }
        
        try:
            logger.info(f"Executing action: {action_name} with params: {parameters}")
            action_func = self.allowed_actions[action_name]
            result = action_func(**parameters)
            return {
                'status': 'success',
                'message': result
            }
        except Exception as e:
            logger.error(f"Error executing action {action_name}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def open_application(self, application_name):
        """
        Open an application on Windows.
        
        Args:
            application_name: Name or path of the application
            
        Returns:
            str: Success message
        """
        common_apps = {
            'notepad': 'notepad.exe',
            'calculator': 'calc.exe',
            'paint': 'mspaint.exe',
            'explorer': 'explorer.exe',
            'chrome': 'chrome.exe',
            'firefox': 'firefox.exe',
            'edge': 'msedge.exe',
            'vscode': 'code',
            'word': 'winword.exe',
            'excel': 'excel.exe',
            'powerpoint': 'powerpnt.exe',
        }
        
        app_to_open = common_apps.get(application_name.lower(), application_name)
        
        try:
            subprocess.Popen(app_to_open, shell=True)
            return f"Opened {application_name}"
        except Exception as e:
            raise Exception(f"Failed to open {application_name}: {e}")
    
    def open_website(self, url):
        """
        Open a website in the default browser.
        
        Args:
            url: URL to open
            
        Returns:
            str: Success message
        """
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        webbrowser.open(url)
        return f"Opened website: {url}"
    
    def create_file(self, file_path, content=""):
        """
        Create a new file with optional content.
        
        Args:
            file_path: Path where to create the file (can be relative or absolute)
            content: Content to write to the file
            
        Returns:
            str: Success message
        """
        # Get the project root directory (where app.py is located)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(project_root, 'output')
        
        # If path is relative or just a filename, put it in the output directory
        if not os.path.isabs(file_path):
            file_path = os.path.join(output_dir, file_path)
        else:
            # For absolute paths, check if they're in safe directories
            safe_paths = [
                os.path.expanduser('~\\Documents'), 
                os.path.expanduser('~\\Desktop'),
                output_dir
            ]
            file_path = os.path.abspath(file_path)
            
            if not any(file_path.startswith(safe_path) for safe_path in safe_paths):
                # If not in safe paths, save to output directory instead
                file_name = os.path.basename(file_path)
                file_path = os.path.join(output_dir, file_name)
                logger.warning(f"Path not in safe directories, saving to output folder: {file_path}")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Created file: {file_path}"
    
    def read_file(self, file_path):
        """
        Read the content of a file.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            str: File content
        """
        file_path = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")
        
        # Safety check: limit file size to 1MB
        if os.path.getsize(file_path) > 1024 * 1024:
            raise Exception("File too large to read (max 1MB)")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
    
    def list_directory(self, directory_path=None):
        """
        List the contents of a directory.
        
        Args:
            directory_path: Path to the directory (defaults to current directory)
            
        Returns:
            str: List of files and folders
        """
        if directory_path is None:
            directory_path = os.getcwd()
        else:
            directory_path = os.path.abspath(directory_path)
        
        if not os.path.exists(directory_path):
            raise Exception(f"Directory not found: {directory_path}")
        
        items = os.listdir(directory_path)
        
        # Separate folders and files
        folders = [item for item in items if os.path.isdir(os.path.join(directory_path, item))]
        files = [item for item in items if os.path.isfile(os.path.join(directory_path, item))]
        
        result = f"Directory: {directory_path}\n\n"
        result += "Folders:\n" + "\n".join(f"  📁 {folder}" for folder in folders) + "\n\n"
        result += "Files:\n" + "\n".join(f"  📄 {file}" for file in files)
        
        return result
    
    def run_command(self, command):
        """
        Run a safe shell command.
        
        Args:
            command: Command to run
            
        Returns:
            str: Command output
        """
        # Whitelist of safe commands
        safe_commands = ['dir', 'ls', 'echo', 'date', 'time', 'whoami', 'hostname', 'ipconfig /all']
        
        # Check if command starts with a safe command
        is_safe = any(command.lower().startswith(safe_cmd) for safe_cmd in safe_commands)
        
        if not is_safe:
            raise Exception(f"Command not allowed for security reasons: {command}")
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return result.stdout if result.stdout else result.stderr
    
    def search_web(self, query):
        """
        Search the web using the default browser.
        
        Args:
            query: Search query
            
        Returns:
            str: Success message
        """
        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(search_url)
        return f"Searching for: {query}"
    
    def scrape_webpage(self, url, selector=None):
        """
        Scrape content from a webpage.
        
        Args:
            url: URL of the webpage to scrape
            selector: Optional CSS selector to extract specific elements
            
        Returns:
            str: Extracted content from the webpage
        """
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            # Set a user agent to avoid being blocked
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Fetch the webpage
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            if selector:
                # Extract specific elements based on CSS selector
                elements = soup.select(selector)
                if elements:
                    content = '\n\n'.join([elem.get_text(strip=True) for elem in elements[:10]])  # Limit to 10 elements
                else:
                    content = "No elements found matching the selector"
            else:
                # Get all text content
                content = soup.get_text(separator='\n', strip=True)
                # Limit content length
                if len(content) > 5000:
                    content = content[:5000] + "\n\n... (content truncated)"
            
            return f"Content from {url}:\n\n{content}"
            
        except requests.Timeout:
            raise Exception(f"Request timed out while accessing {url}")
        except requests.RequestException as e:
            raise Exception(f"Failed to scrape webpage: {e}")
        except Exception as e:
            raise Exception(f"Error parsing webpage: {e}")
    
    def extract_links(self, url, filter_text=None):
        """
        Extract links from a webpage.
        
        Args:
            url: URL of the webpage
            filter_text: Optional text to filter links (only return links containing this text)
            
        Returns:
            str: List of links found on the page
        """
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract all links
            links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                text = link.get_text(strip=True)
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                
                # Filter if needed
                if filter_text:
                    if filter_text.lower() in text.lower() or filter_text.lower() in href.lower():
                        links.append({'text': text, 'url': href})
                else:
                    links.append({'text': text, 'url': href})
                
                # Limit to 20 links
                if len(links) >= 20:
                    break
            
            if not links:
                return "No links found on the page"
            
            # Format the result
            result = f"Found {len(links)} links on {url}:\n\n"
            for i, link in enumerate(links, 1):
                result += f"{i}. {link['text']}\n   URL: {link['url']}\n\n"
            
            return result
            
        except Exception as e:
            raise Exception(f"Failed to extract links: {e}")


# Available functions for Gemini function calling
COMPUTER_CONTROL_FUNCTIONS = [
    {
        "name": "open_application",
        "description": "Open an application on the computer. Common apps: notepad, calculator, paint, explorer, chrome, firefox, edge, vscode",
        "parameters": {
            "type": "object",
            "properties": {
                "application_name": {
                    "type": "string",
                    "description": "Name of the application to open (e.g., 'notepad', 'calculator', 'chrome')"
                }
            },
            "required": ["application_name"]
        }
    },
    {
        "name": "open_website",
        "description": "Open a website in the default browser",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the website to open (e.g., 'google.com', 'https://github.com')"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "create_file",
        "description": "Create a new text file in Documents or Desktop folder",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Full path where to create the file (must be in Documents or Desktop)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and folders in a directory",
        "parameters": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "Path to the directory to list (optional, defaults to current directory)"
                }
            }
        }
    },
    {
        "name": "search_web",
        "description": "Search for information on the web using Google",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "scrape_webpage",
        "description": "Scrape and extract text content from a webpage. Can extract all text or use a CSS selector for specific elements.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the webpage to scrape (e.g., 'example.com' or 'https://example.com')"
                },
                "selector": {
                    "type": "string",
                    "description": "Optional CSS selector to extract specific elements (e.g., '.job-title', '#main-content', 'h1')"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "extract_links",
        "description": "Extract all links from a webpage. Can filter links by text content.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the webpage to extract links from"
                },
                "filter_text": {
                    "type": "string",
                    "description": "Optional text to filter links (only return links containing this text)"
                }
            },
            "required": ["url"]
        }
    }
]
