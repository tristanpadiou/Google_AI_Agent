# Google_AI_Agent

# Google AI Integration for Various Tasks

This project integrates multiple Google AI-based tools to help you interact with Google services, including image search, contact management, task management, maps, mail, and calendar management.

## Features

- **Google Image Search**: Search for images using the Google Custom Search API.
- **Contacts Manager**: Manage contacts (list, create, modify, delete, retrieve details).
- **Tasks Manager**: Manage tasks (list, create, get task details, complete tasks).
- **Maps Manager**: Search and get details about locations (restaurants, museums, etc.).
- **Mail Manager**: Interact with your email inbox, send emails, create drafts, verify email content.
- **Calendar Manager**: Manage your calendar (create recurring events, view calendar, refresh calendar).

## Requirements

To use this project, you need to install the necessary dependencies and configure a few Google APIs. 

### Python Requirements

Ensure you have Python 3.7 or higher installed. Create a virtual environment and install the required dependencies:

```bash
pip install -r requirements.txt

```
## Project Requirements

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

## Google API Setup

To interact with various Google services (e.g., Google Custom Search, Gmail, Calendar, etc.), you'll need to set up Google APIs, obtain credentials, and configure them in your environment.

### 1. Google Cloud API Key

To access Google services via API (like Google Custom Search), you need to set up a Google Cloud project, enable the relevant APIs, and create an API key.

#### Steps:
1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/).
   - Click **Select a project** > **New Project**.
   - Provide a name for the project and create it.

2. **Enable APIs**:
   - From the **Google Cloud Console**, navigate to the **APIs & Services** dashboard.
   - Enable the APIs that you need (e.g., **Custom Search API**, **Gmail API**, **Google Calendar API**, etc.).
   
3. **Create an API Key**:
   - In the **APIs & Services** section, go to **Credentials**.
   - Click on **Create credentials** > **API key**.
   - Copy the generated API key.

4. **Set up the API Key in your environment**:
   - You can securely store your API key in environment variables to keep it private.

   **Example:**

   In your terminal or `.bashrc` (Linux/macOS) or `.env` file, add:

   ```bash
   export GOOGLE_API_KEY='your-api-key'
   export CUSTOM_SEARCH_ENGINE_ID='your-custom-search-id'
