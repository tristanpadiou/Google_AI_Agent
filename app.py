from langchain_google_genai import ChatGoogleGenerativeAI
import os
from google_agent import Google_agent
from dotenv import load_dotenv 
import gradio as gr
load_dotenv()
GOOGLE_API_KEY=os.getenv('google_api_key')


GEMINI_MODEL='gemini-2.0-flash'
llm = ChatGoogleGenerativeAI(google_api_key=GOOGLE_API_KEY, model=GEMINI_MODEL, temperature=0.3)
agent=Google_agent()


def chatbot(input,history):
    response=agent.chat(input)
    return response

demo = gr.ChatInterface(chatbot, type="messages", autofocus=False)

if __name__ == "__main__":
    demo.launch()