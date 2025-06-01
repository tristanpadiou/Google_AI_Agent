# Google_AI_Agent

# Google AI Integration for Various Tasks

This project integrates multiple Google AI-based tools to help you interact with Google services, including image search, contact management, task management, maps, mail, and calendar management. The project uses **Composio** to seamlessly integrate with Google services and **LangGraph** for intelligent workflow orchestration.

## Features

- **Google Image Search**: Search for images using the Google Custom Search API.
- **Contacts Manager**: Manage contacts (list, create, modify, delete, retrieve details).
- **Tasks Manager**: Manage tasks (list, create, get task details, complete tasks).
- **Maps Manager**: Search and get details about locations (restaurants, museums, etc.).
- **Mail Manager**: Interact with your email inbox, send emails, create drafts, verify email content.
- **Calendar Manager**: Manage your calendar (create recurring events, view calendar, refresh calendar).

## Requirements

To use this project, you need to install the necessary dependencies and configure Google APIs and Composio authentication.

### Python Requirements

Ensure you have Python 3.7 or higher installed. Create a virtual environment and install the required dependencies:

```bash
pip install -r requirements.txt
```

### Project Requirements

Below is the list of required packages for this project:

- `geocoder==1.38.1`
- `google-api-python-client==2.161.0`
- `google-auth-oauthlib==1.2.1`
- `gradio==5.19.0`
- `ipython==8.32.0`
- `langchain==0.3.19`
- `langchain-core==0.3.40`
- `langchain-google-genai==2.0.11`
- `langgraph==0.3.1`
- `protobuf==5.29.3`
- `python-dotenv==1.0.1`
- `Requests==2.32.3`
- `typing_extensions==4.12.2`
- `composio-langgraph>=0.3.0`  # Composio LangGraph integration
- `pydantic-ai>=0.0.1`        # Pydantic AI framework
- `openai>=1.0.0`             # OpenAI API client

## Composio Setup and Authentication

This project uses **Composio** to integrate with Google services. Composio provides a unified platform to connect with 100+ tools and APIs.

### 1. Create a Composio Account

1. Visit [Composio.dev](https://app.composio.dev)
2. Sign up for a free account
3. Complete the email verification process

### 2. Get Your Composio API Key

1. Log in to your Composio dashboard
2. Navigate to **Settings** > **API Keys**
3. Click **Generate New API Key**
4. Copy the generated API key (keep it secure)

### 3. Install Composio CLI (Optional but Recommended)

```bash
pip install composio-core
```

### 4. Authenticate with Google Services via Composio

You need to connect your Google account to Composio to access Gmail, Google Calendar, Google Tasks, and Google Maps:

#### Via Composio Dashboard (Recommended):
1. Log in to [app.composio.dev](https://app.composio.dev)
2. Go to **Integrations** or **Connected Apps**
3. Search for and select **Gmail**
4. Click **Connect** and follow the OAuth flow to authorize access
5. Repeat for **Google Calendar**, **Google Tasks**, and **Google Maps**

#### Via CLI (Alternative):
```bash
# Login to Composio
composio login

# Add Google integrations
composio add gmail
composio add googlecalendar
composio add googletasks
composio add googlemaps
```

### 5. Environment Variables Setup

Create a `.env` file in your project root with the following variables:

```bash
# Composio API Key
COMPOSIO_API_KEY=your_composio_api_key_here

# Google API Keys (for Custom Search)
GOOGLE_API_KEY=your_google_api_key_here
CUSTOM_SEARCH_ENGINE_ID=your_custom_search_engine_id_here

# OpenAI API Key (for LLM)
OPENAI_API_KEY=your_openai_api_key_here

# Additional Google credentials (if needed)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### 6. Verify Composio Connections

You can verify your connections are working by running:

```python
from composio_langgraph import ComposioToolSet, App

toolset = ComposioToolSet(api_key="your_composio_api_key")

# Check available apps
apps = toolset.get_connected_apps()
print("Connected apps:", apps)

# Get tools for specific apps
gmail_tools = toolset.get_tools(apps=[App.GMAIL])
print(f"Gmail tools available: {len(gmail_tools)}")
```

## Google API Setup

In addition to Composio, you'll need some direct Google API access for certain features like Custom Search.

### 1. Google Cloud API Key

To access Google Custom Search API, you need to set up a Google Cloud project:

#### Steps:
1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/).
   - Click **Select a project** > **New Project**.
   - Provide a name for the project and create it.

2. **Enable APIs**:
   - From the **Google Cloud Console**, navigate to the **APIs & Services** dashboard.
   - Enable the **Custom Search API**.
   
3. **Create an API Key**:
   - In the **APIs & Services** section, go to **Credentials**.
   - Click on **Create credentials** > **API key**.
   - Copy the generated API key.

4. **Set up Custom Search Engine**:
   - Go to [Google Custom Search Engine](https://cse.google.com/cse/)
   - Create a new search engine
   - Configure it to search the entire web
   - Copy the Search Engine ID

## Docker Deployment

The application can be deployed using Docker for easy setup and consistent environments.

### Prerequisites
- Docker installed on your system
- `.env` file with your API credentials (Google, Composio, OpenAI)

### Building the Docker Image

To build the Docker image, run the following command in the project root directory:

```bash
docker build -t google-ai-agent .
```

### Running the Container

To run the application in a Docker container:

```bash
docker run -p 7860:7860 --env-file .env google-ai-agent
```

The application will be available at `http://localhost:7860`

### Notes
- The container uses Python 3.13.2
- Port 7860 is exposed for the Gradio interface
- Environment variables are loaded from your `.env` file
- Make sure your `.env` file contains all necessary credentials (Composio, Google, OpenAI)

## Troubleshooting

### Common Issues:

1. **Composio Authentication Errors**:
   - Ensure your Composio API key is correct
   - Verify that Google services are properly connected in Composio dashboard
   - Check that you have the necessary permissions for each Google service

2. **Google API Quota Errors**:
   - Check your Google Cloud Console for API quotas
   - Ensure billing is enabled if using paid APIs

3. **Missing Dependencies**:
   - Make sure all packages are installed: `pip install -r requirements.txt`
   - Verify Python version compatibility (3.7+)

### Getting Help:

- **Composio Documentation**: [docs.composio.dev](https://docs.composio.dev)
- **Composio Discord**: Join the community for support
- **Google API Documentation**: [developers.google.com](https://developers.google.com)

## Usage Example

```python
from google_agent import Google_agent

# Initialize with your LLMs and API keys
api_keys = {
    'composio_key': 'your_composio_api_key',
    'google_api_key': 'your_google_api_key',
    'pse': 'your_custom_search_engine_id'
}

llms = {
    'openai_llm': your_openai_llm_instance,
    'pydantic_llm': your_pydantic_llm_instance
}

# Create the agent
agent = Google_agent(llms=llms, api_keys=api_keys)

# Chat with the agent
response = agent.chat("Schedule a meeting for tomorrow at 2 PM")
print(response)
```