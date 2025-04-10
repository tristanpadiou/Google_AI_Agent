from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os.path

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://mail.google.com/","https://www.googleapis.com/auth/calendar",'https://www.googleapis.com/auth/cloud-platform','https://www.googleapis.com/auth/contacts','https://www.googleapis.com/auth/tasks','https://www.googleapis.com/auth/generative-language.retriever']


def get_creds():
  """Shows basic usage of the Gmail API.
  Lists the user's Gmail labels.
  """
  try:
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
      creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
        try:
          creds.refresh(Request())
          # Save the refreshed credentials
          with open("token.json", "w") as token:
            token.write(creds.to_json())
        except Exception as e:
          print(f"Error refreshing token: {e}")
          # If refresh fails, we need to get new credentials
          flow = InstalledAppFlow.from_client_secrets_file(
              "credentials.json", SCOPES
          )
          creds = flow.run_local_server(port=0)
      else:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
      
      # Save the credentials for the next run
      with open("token.json", "w") as token:
        token.write(creds.to_json())
    
    return ' token available '
      
  except Exception as e:
    print(f"Error in get_creds: {e}")
    return 'something is wrong (no token)'