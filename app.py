from langchain_google_genai import ChatGoogleGenerativeAI
import os
from google_agent import Google_agent
from dotenv import load_dotenv 
import gradio as gr
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
load_dotenv()
#get the api keys from the environment variables
google_api_key=os.getenv('google_api_key')
pse=os.getenv('pse')
openai_api_key=os.getenv('openai_api_key')
composio_api_key=os.getenv('composio_api_key')

api_keys={
    'google_api_key':google_api_key,
    'pse':pse,
    'openai_api_key':openai_api_key,
    'composio_key':composio_api_key
}

llms={'pydantic_llm':GoogleModel('gemini-2.5-flash-preview-05-20', provider=GoogleProvider(api_key=api_keys['google_api_key'])),
              'langchain_llm':ChatGoogleGenerativeAI(google_api_key=api_keys['google_api_key'], model='gemini-2.0-flash', temperature=0.3)}

agent=Google_agent(llms=llms, api_keys=api_keys)


def chatbot(input,history):
    response=agent.chat(input)
    return response

demo = gr.ChatInterface(chatbot, type="messages", autofocus=False)

if __name__ == "__main__":
    demo.launch()