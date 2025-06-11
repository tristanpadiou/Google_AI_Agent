from google_agent import Google_agent
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Optional, List, Union
from dotenv import load_dotenv
import os
import hashlib
load_dotenv()

import uvicorn
import time


import logfire

app = FastAPI(
    title="Google Agent API", 
    description="""
    ## Google AI Agent API
    
    A comprehensive API for interacting with Google AI Agent with multi-modal capabilities and Google Workspace integration.
    
    ### Available Endpoints:
    
    **GET Requests:**
    - `/health` - Check API health status and uptime
    - `/api-docs` - Get comprehensive API documentation
    
    **POST Requests:**
    - `/chat` - Main chat endpoint for text-based interactions
    - `/reset` - Reset Google Agent's memory and conversation history
    
    ### Features:
    - Text-based chat interactions
    - Google Workspace integration (Gmail, Calendar, Tasks)
    - Google Custom Search integration
    - OpenAI GPT integration
    - Composio tools integration
    - Memory management and conversation reset
    - Health monitoring and uptime tracking
    """,
    version="0.1.0",
    docs_url=None,  # Disable built-in docs
    redoc_url=None  # Disable redoc as well
)

# Configure logfire if token is available
logfire_token = os.getenv('logfire_token')
if logfire_token:
    logfire.configure(token=logfire_token)
    logfire.instrument_pydantic_ai()

startup_time = time.time()



class EndpointInfo(BaseModel):
    path: str
    method: str
    description: str
    parameters: List[Dict[str, str]]
    example_request: Dict[str, str]
    example_response: Dict[str, str]

class APIDocumentation(BaseModel):
    name: str
    version: str
    description: str
    endpoints: List[EndpointInfo]

class KeyCache:
    def __init__(self):
        self._last_keys_hash = None
        self._google_agent = None
    
    def _compute_keys_hash(self, api_keys: Dict[str, str]) -> str:
        # Sort keys to ensure consistent hashing regardless of order
        sorted_keys = dict(sorted(api_keys.items()))
        # Create a string representation of the keys
        keys_str = "|".join(f"{k}:{v}" for k, v in sorted_keys.items() if v is not None)
        # Compute hash
        return hashlib.sha256(keys_str.encode()).hexdigest()
    
    def get_google_agent(self, api_keys: Dict[str, str]) -> Google_agent:
        current_hash = self._compute_keys_hash(api_keys)
        
        # Initialize or reinitialize if keys have changed
        if self._last_keys_hash != current_hash:
            # Filter out None values for initialization
            init_keys = {k: v for k, v in api_keys.items() if v is not None}
            # Pass the entire dictionary as a single parameter
            self._google_agent = Google_agent(api_keys=init_keys)
            self._last_keys_hash = current_hash
        
        return self._google_agent
    
    def reset(self):
        if self._google_agent:
            self._google_agent.reset()
        self._last_keys_hash = None

# Initialize key cache
key_cache = KeyCache()



@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "uptime": time.time() - startup_time,
        "version": "0.1.0",
        "service": "Google Agent API"
    }

@app.post("/chat")
async def chat(
    query: str = Form(...),
    google_api_key: str = Form(...),
    openai_api_key: str = Form(...),
    composio_key: str = Form(...),
    pse: str = Form(None),
):
    try:
        api_keys = {
            "google_api_key": google_api_key,
            "openai_api_key": openai_api_key,
            "composio_key": composio_key,
            "pse": pse
        }
        
        # Get or initialize Google Agent instance based on keys
        try:
            google_agent = key_cache.get_google_agent(api_keys)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting Google Agent instance: {str(e)}")
        
        # Use the chat method from Google_agent
        response = google_agent.chat(query)
        
        # Format the response for better readability
        formatted_response = ""
        if isinstance(response, dict):
            if 'node_messages_list' in response and response['node_messages_list']:
                # Extract the most recent meaningful response
                for message in reversed(response['node_messages_list']):
                    if isinstance(message, dict):
                        for tool, action_data in message.items():
                            if isinstance(action_data, dict):
                                for action, result in action_data.items():
                                    if result and result != "no image found":
                                        formatted_response += f"**{tool} - {action}:**\n{result}\n\n"
            
            # If no meaningful response found, use the raw response
            if not formatted_response:
                formatted_response = str(response)
        else:
            formatted_response = str(response)
        
        return {
            "response": formatted_response,
            "raw_response": response  # Include raw response for debugging
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")

@app.post("/reset")
async def reset_google_agent():
    try:
        key_cache.reset()
        return {"status": "success", "message": "Google Agent memory reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api-docs")
async def get_markdown_documentation():
    """
    Returns comprehensive documentation for all API endpoints in markdown format
    """
  
    return """# Google Agent API Documentation

**Version:** 0.1.0

## Description
API for interacting with Google AI Agent, including Google Workspace integration, chat, text-to-speech, and file processing capabilities.

---

## Endpoints

### POST `/chat`
**Description:** Main chat endpoint that processes text queries and integrates with Google Workspace (Gmail, Calendar, Tasks).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | The text query to process |
| google_api_key | string | Yes | Google API key for Gemini and search functionality |
| openai_api_key | string | Yes | OpenAI API key for language model |
| composio_key | string | Yes | Composio API key for Google Workspace integration |
| pse | string | No | Personal search engine identifier for image search |

**Example Request:**
```json
{
    "query": "Check my emails and create a task for tomorrow",
    "google_api_key": "your_google_api_key",
    "openai_api_key": "your_openai_api_key",
    "composio_key": "your_composio_key",
    "include_audio": "true",
    "hf_token": "your_hf_token"
}
```

**Example Response:**
```json
{
    "response": "I've checked your emails and found 5 new messages. Created a task for tomorrow as requested.",
    "raw_response": {...}
}
```

---

### POST `/reset`
**Description:** Reset Google Agent's memory and conversation history

**Parameters:** None

**Example Request:**
```json

```

**Example Response:**
```json
{
    "status": "success",
    "message": "Google Agent memory reset successfully"
}
```

---

### GET `/health`
**Description:** Check API health status and uptime

**Parameters:** None

**Example Request:** No body required

**Example Response:**
```json
{
    "status": "healthy",
    "uptime": 3600.5,
    "version": "0.1.0",
    "service": "Google Agent API"
}
```

---

### GET `/docs`
**Description:** Get comprehensive API documentation in JSON format

**Parameters:** None

**Example Request:** No body required

**Example Response:** Returns structured JSON documentation

---

### GET `/api-docs`
**Description:** Get comprehensive API documentation in markdown format

**Parameters:** None

**Example Request:** No body required

**Example Response:** Returns this markdown documentation

---

## Google Workspace Integration Features
- **Gmail Management:** Read emails, send emails, create drafts
- **Google Tasks:** Create, list, complete, and manage tasks
- **Google Calendar:** View events, create events, manage calendar
- **Google Custom Search:** Search for images and web content

## Additional Features
- Text-based chat interactions
- Google Workspace full integration
- OpenAI GPT integration
- Composio tools integration
- Memory management and conversation reset
- Health monitoring and uptime tracking

## Usage Notes
- All requests should use multipart/form-data encoding
- Google API key, OpenAI API key, and Composio key are required for full functionality
- The chat endpoint processes text queries only
- PSE (Personal Search Engine) is optional but needed for image search functionality
"""

@app.get("/docs")
async def get_docs():
    """
    Returns comprehensive documentation for all API endpoints in JSON format
    """
    return {
        "name": "Google Agent API",
        "version": "0.1.0", 
        "description": "API for interacting with Google AI Agent with Google Workspace integration and multi-modal capabilities",
        "endpoints": [
            {
                "path": "/chat",
                "method": "POST",
                "description": "Main chat endpoint with Google Workspace integration",
                "content_type": "multipart/form-data",
                "parameters": [
                    {
                        "name": "query",
                        "type": "string",
                        "required": True,
                        "description": "The text query to process"
                    },
                    {
                        "name": "google_api_key", 
                        "type": "string",
                        "required": True,
                        "description": "Google API key for Gemini and search functionality"
                    },
                    {
                        "name": "openai_api_key",
                        "type": "string", 
                        "required": True,
                        "description": "OpenAI API key for language model"
                    },
                    {
                        "name": "composio_key",
                        "type": "string",
                        "required": True,
                        "description": "Composio API key for Google Workspace integration"
                    },
                    {
                        "name": "pse",
                        "type": "string",
                        "required": False,
                        "description": "Personal search engine identifier for image search (optional)"
                    }
                ],
                "response": {
                    "response": "string - The AI assistant's formatted response",
                    "raw_response": "object - The raw response from Google Agent"
                }
            },
            {
                "path": "/reset",
                "method": "POST", 
                "description": "Reset Google Agent's memory and conversation history",
                "parameters": [],
                "response": {
                    "status": "string - success/error status",
                    "message": "string - confirmation message"
                }
            },
            {
                "path": "/health",
                "method": "GET",
                "description": "Check API health status and uptime", 
                "parameters": [],
                "response": {
                    "status": "string - health status",
                    "uptime": "number - seconds since startup",
                    "version": "string - API version",
                    "service": "string - service name"
                }
            },
            {
                "path": "/docs",
                "method": "GET",
                "description": "Get comprehensive API documentation in JSON format",
                "parameters": [],
                "response": "object - This documentation structure"
            },
            {
                "path": "/api-docs", 
                "method": "GET",
                "description": "Get comprehensive API documentation in markdown format",
                "parameters": [],
                "response": {
                    "markdown": "string - Full API documentation in markdown format"
                }
            }
        ],
        "google_workspace_features": [
            "Gmail Management - Read, send, create draft emails",
            "Google Tasks - Create, list, complete, and manage tasks",
            "Google Calendar - View events, create events, manage calendar",
            "Google Custom Search - Search for images and web content"
        ],
        "usage_notes": [
            "All requests must use multipart/form-data encoding",
            "Google API key, OpenAI API key, and Composio key are required for full functionality", 
            "The chat endpoint processes text queries only",
            "PSE (Personal Search Engine) is optional but needed for image search functionality"
        ]
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google AI Agent API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h2 { color: #2c3e50; }
            h3 { color: #34495e; }
            code { background-color: #f4f4f4; padding: 2px 4px; border-radius: 3px; }
            ul { line-height: 1.6; }
            .feature-list { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h2>Google AI Agent API</h2>
        
        <p>A comprehensive API for interacting with Google AI Agent with Google Workspace integration and multi-modal capabilities.</p>
        
        <h3>Available Endpoints:</h3>
        
        <p><strong>GET Requests:</strong></p>
        <ul>
            <li><code>/health</code> - Check API health status and uptime</li>
            <li><code>/api-docs</code> - Get comprehensive API documentation</li>
            <li><code>/docs</code> - Get comprehensive API documentation in JSON format</li>
        </ul>
        
        <p><strong>POST Requests:</strong></p>
        <ul>
            <li><code>/chat</code> - Main chat endpoint with Google Workspace integration</li>
            <li><code>/reset</code> - Reset Google Agent's memory and conversation history</li>
        </ul>
        
        <div class="feature-list">
            <h3>Google Workspace Integration:</h3>
            <ul>
                <li><strong>Gmail Management:</strong> Read emails, send emails, create drafts</li>
                <li><strong>Google Tasks:</strong> Create, list, complete, and manage tasks</li>
                <li><strong>Google Calendar:</strong> View events, create events, manage calendar</li>
                <li><strong>Google Custom Search:</strong> Search for images and web content</li>
            </ul>
        </div>
        
        <h3>Additional Features:</h3>
        <ul>
            <li>Text-based chat interactions</li>
            <li>Google Gemini AI integration</li>
            <li>OpenAI GPT integration</li>
            <li>Composio tools integration</li>
            <li>Memory management and conversation reset</li>
            <li>Health monitoring and uptime tracking</li>
        </ul>
        
        <h3>Required API Keys:</h3>
        <ul>
            <li><strong>Google API Key:</strong> For Gemini AI and Google services</li>
            <li><strong>OpenAI API Key:</strong> For GPT language model</li>
            <li><strong>Composio Key:</strong> For Google Workspace integration</li>
            <li><strong>PSE (Optional):</strong> Personal Search Engine for image search</li>
        </ul>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
