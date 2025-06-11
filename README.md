# Google AI Agent API

A comprehensive API for interacting with Google AI Agent with Google Workspace integration and multi-modal capabilities.

## Features

### 🚀 Core Capabilities
- **Text-based chat interactions** with natural language processing
- **Google Workspace integration** (Gmail, Calendar, Tasks)
- **Google Custom Search** integration
- **Memory management** and conversation reset
- **Health monitoring** and uptime tracking

### 🔧 Google Workspace Integration
- **Gmail Management:** Read, send, create draft emails
- **Google Tasks:** Create, list, complete, and manage tasks
- **Google Calendar:** View events, create events, manage calendar
- **Google Custom Search:** Search for images and web content

### 🤖 AI Integration
- **Google Gemini AI** for advanced language processing
- **OpenAI GPT** integration for enhanced capabilities
- **Composio tools** for seamless Google Workspace connectivity

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Google_AI_Agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   # Optional: Logfire token for monitoring
   google_agent_api_logfire_token=your_logfire_token_here
   ```

## API Keys Required

To use the Google Agent API, you'll need the following API keys:

### Required Keys:
- **Google API Key** - For Gemini AI and Google services
- **OpenAI API Key** - For GPT language model
- **Composio Key** - For Google Workspace integration

### Optional Keys:
- **PSE (Personal Search Engine)** - For image search functionality

## Quick Start

1. **Start the server**
   ```bash
   python google_agent_api.py
   ```
   The API will be available at `http://localhost:8001`

2. **Test the health endpoint**
   ```bash
   curl http://localhost:8001/health
   ```

3. **Make a chat request**
   ```bash
   curl -X POST "http://localhost:8001/chat" \
        -F "query=Check my emails" \
        -F "google_api_key=your_google_api_key" \
        -F "openai_api_key=your_openai_api_key" \
        -F "composio_key=your_composio_key"
   ```

## API Endpoints

### POST `/chat`
Main chat endpoint with Google Workspace integration.

**Parameters:**
- `query` (required): The text query to process
- `google_api_key` (required): Google API key
- `openai_api_key` (required): OpenAI API key
- `composio_key` (required): Composio API key
- `pse` (optional): Personal Search Engine identifier

### POST `/reset`
Reset Google Agent's memory and conversation history.

### GET `/health`
Check API health status and uptime.

### GET `/docs`
Get comprehensive API documentation in JSON format.

### GET `/api-docs`
Get comprehensive API documentation in markdown format.

## Usage Examples

### Basic Chat
```python
import requests

response = requests.post(
    "http://localhost:8001/chat",
    data={
        "query": "What's in my inbox?",
        "google_api_key": "your_google_api_key",
        "openai_api_key": "your_openai_api_key",
        "composio_key": "your_composio_key"
    }
)
print(response.json())
```

### Create Google Tasks
```python
import requests

response = requests.post(
    "http://localhost:8001/chat",
    data={
        "query": "Create a task to review quarterly reports by Friday",
        "google_api_key": "your_google_api_key",
        "openai_api_key": "your_openai_api_key",
        "composio_key": "your_composio_key"
    }
)
print(response.json())
```

### Manage Google Calendar
```python
import requests

response = requests.post(
    "http://localhost:8001/chat",
    data={
        "query": "Schedule a meeting for tomorrow at 2 PM with the team",
        "google_api_key": "your_google_api_key",
        "openai_api_key": "your_openai_api_key",
        "composio_key": "your_composio_key"
    }
)
result = response.json()
print("Response:", result["response"])
```

## Google Workspace Setup

To use Google Workspace integration, you'll need to:

1. **Set up Composio** with your Google Workspace account
2. **Obtain necessary API keys** from Google Cloud Console
3. **Configure authentication** for Gmail, Calendar, and Tasks APIs

Refer to the [Composio documentation](https://docs.composio.dev/) for detailed setup instructions.

## Error Handling

The API provides detailed error messages for common issues:

- **401 Unauthorized**: Invalid API keys
- **500 Internal Server Error**: Server-side errors with detailed messages
- **422 Validation Error**: Invalid request parameters

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the API documentation at `/api-docs`
2. Review the health status at `/health`
3. Check server logs for detailed error information