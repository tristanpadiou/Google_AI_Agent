from token_creator import get_creds
get_creds()

from gmail_agent import Gmail_agent
from calendar_agent import Calendar_agent
from maps_agent import Maps_agent
from contacts_agent import Contacts_agent
from tasks_agent import Tasks_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool,Tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import (
    HumanMessage,

)
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore


from typing_extensions import TypedDict
from typing import Annotated
from dotenv import load_dotenv 

#get graph visuals
from IPython.display import Image, display
from langchain_core.runnables.graph import MermaidDrawMethod
import os
import requests


load_dotenv()
GOOGLE_API_KEY=os.getenv('google_api_key')
pse=os.getenv('pse')


GEMINI_MODEL='gemini-2.0-flash'
llm = ChatGoogleGenerativeAI(google_api_key=GOOGLE_API_KEY, model=GEMINI_MODEL, temperature=0.3)


mail_agent=Gmail_agent(llm)
calendar_agent=Calendar_agent(llm)
maps_agent=Maps_agent(llm)
tasks_agent=Tasks_agent(llm)
contacts_agent=Contacts_agent(llm)

class State(TypedDict):
    messages: Annotated[list, add_messages]

store=InMemoryStore()

def google_image_search(query: str) -> str:
  """Search for images using Google Custom Search API
  args: query
  return: image url
  """
  # Define the API endpoint for Google Custom Search
  url = "https://www.googleapis.com/customsearch/v1"

  params = {
      "q": query,
      "cx": pse,
      "key": GOOGLE_API_KEY,
      "searchType": "image",  # Search for images
      "num": 1  # Number of results to fetch
  }

  # Make the request to the Google Custom Search API
  response = requests.get(url, params=params)
  data = response.json()

  # Check if the response contains image results
  if 'items' in data:
      # Extract the first image result
      image_url = data['items'][0]['link']
      return image_url
  else:
      return "Sorry, no images were found for your query."

google_image_tool=Tool(name='google_image_tool', func=google_image_search, description='Use this tool to search for images using Google Custom Search API')

@tool 
def contacts_manager(query: str):
    """use this tool to answer queries about a contact or a person
    this tool can do multiple tasks at once as long as the query mentions them:
    this tool can:
    list my contacts
    get a contact's details
    delete a contact
    create a contact
    modify a contact
    args: query - pass the email related queries directly here
    """
    response=contacts_agent.chat(str(query))
    return response

@tool
def tasks_manager(query:str):
    """use this tool to answer task related queries
    this tool can do multiple tasks at once as long as the query mentions them:
    this tool can:
    list tasks
    create tasks
    get task details
    complete a task (which also deletes it :) )

    args: query - pass the email related queries directly here
    
    """


    response=tasks_agent.chat(str(query))
    return response

@tool
def maps_manager(query:str):
    """tool to use to answer maps and location queries
    this tool can do multiple tasks at once as long as the query mentions them:
    this tool can:
    find locations such as restorants, bowling alleys, museums and others
    display those locations's infos (eg. adress, name, url, price range)
    args: query - pass the email related queries directly here
    """
    response=maps_agent.chat(str(query))
    return response


@tool
def mail_manager(query:str):
    """Tool to use to answer any email related queries
    this tool can do multiple tasks at once as long as the query mentions them:
    this tool can:
    get new mail
    show the inbox
    get a specific mail's content to display
    create a draft of a new mail
    create an email
    verify the email content
    send the email
    list all the drafts
    args: query - pass the email related queries directly here
    """
    response=mail_agent.chat(str(query))
    return response

@tool
def calendar_manager(query:str):
    """tool to use to answere any calendar or schedule related queries
    this tool can do multiple tasks at once as long as the query mentions them:
    this tool can:
    create recuring events
    create quick events
    refresh the calendar
    show the calendar
    args: query - pass the calendar related queries directly here
    """
    response=calendar_agent.chat(str(query))
    return response

class Google_agent:
    def __init__(self,llm: any):
        self.agent=self._setup(llm)
    def _setup(self,llm):
   
        langgraph_tools=[mail_manager,calendar_manager,maps_manager, tasks_manager, contacts_manager, google_image_tool]



        graph_builder = StateGraph(State)

        # Modification: tell the LLM which tools it can call
        llm_with_tools = llm.bind_tools(langgraph_tools)
        tool_node = ToolNode(tools=langgraph_tools)
        def chatbot(state: State):
            """ google ai agent, that can interact with contacts, emails, maps, tasks and calendar.
            Depending on the request, leverage which tools to use if necessary."""
            return {"messages": [llm_with_tools.invoke(state['messages'])]}

        graph_builder.add_node("chatbot", chatbot)

        
        graph_builder.add_node("tools", tool_node)
        # Any time a tool is called, we return to the chatbot to decide the next step
        graph_builder.add_edge(START,'chatbot')
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_conditional_edges(
            "chatbot",
            tools_condition,
        )
        memory=MemorySaver()
        graph=graph_builder.compile(checkpointer=memory,store=store)
        return graph
        

    def display_graph(self):
        return display(
                        Image(
                                self.agent.get_graph().draw_mermaid_png(
                                    draw_method=MermaidDrawMethod.API,
                                )
                            )
                        )
    def stream(self,input:str):
        config = {"configurable": {"thread_id": "1"}}
        input_message = HumanMessage(content=input)
        for event in self.agent.stream({"messages": [input_message]}, config, stream_mode="values"):
            event["messages"][-1].pretty_print()

    def chat(self,input:str):
        config = {"configurable": {"thread_id": "1"}}
        response=self.agent.invoke({'messages':HumanMessage(content=str(input))},config)
        return response['messages'][-1].content
    
    def get_state(self, state_val:str):
        config = {"configurable": {"thread_id": "1"}}
        return self.agent.get_state(config).values[state_val]