from token_creator import get_creds
get_creds()

from gmail_agent import Gmail_agent
from calendar_agent import Calendar_agent
from maps_agent import Maps_agent
from contacts_agent import Contacts_agent
from tasks_agent import Tasks_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    
)
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import RetryOutputParser


from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

from pydantic import BaseModel,Field

from typing_extensions import TypedDict
from typing import Annotated, List

import os
from dotenv import load_dotenv 

#get graph visuals
from IPython.display import Image, display
from langchain_core.runnables.graph import MermaidDrawMethod
import os
import requests
import gradio as gr

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

store=InMemoryStore()

class State(TypedDict):
    node_messages: Annotated[List, add_messages]
    query: str
    plan: List
    node_query:str

class ManagerCapability(BaseModel):
    """Represents a specific capability that a manager tool provides"""
    action: str = Field(..., description="The specific action that can be performed")
    description: str = Field(None, description="Optional description of what this capability does")

class ManagerTool(BaseModel):
    """Represents a manager tool and its capabilities"""
    name: str = Field(..., description="The name of the manager tool")
    tool_function: str = Field(..., description="The function name used to call this tool")
    description: str = Field(..., description="General description of what this tool does")
    capabilities: List[ManagerCapability] = Field(..., description="List of capabilities this tool provides")



class ManagerTools(BaseModel):
    """Collection of all available manager tools and their capabilities"""
    managers: List[ManagerTool] = Field(
        default=[
            ManagerTool(
                name="Maps Manager",
                tool_function="maps_manager",
                description="Tool to use to answer maps and location queries",
                capabilities=[
                    ManagerCapability(action="find locations", description="Such as restaurants, bowling alleys, museums and others"),
                    ManagerCapability(action="display location info", description="Shows address, name, URL, price range")
                ]
            ),
            ManagerTool(
                name="Google images tool",
                tool_function="google_image_tool",
                description="Tool to use to get images",
                capabilities=[
                    ManagerCapability(action="get image", description="returns a url of the image"),
                ]),
            ManagerTool(
                name="Contacts Manager",
                tool_function="contacts_manager",
                description="Tool to use to answer queries about a contact or a person",
                capabilities=[
                    ManagerCapability(action="list contacts", description="Shows all available contacts"),
                    ManagerCapability(action="get contact details", description="Retrieves information about a specific contact, like email addresses"),
                    ManagerCapability(action="delete contact", description="Removes a contact from the list"),
                    ManagerCapability(action="create contact", description="Adds a new contact to the list"),
                    ManagerCapability(action="modify contact", description="Updates information for an existing contact")
                ]
            ),
            ManagerTool(
                name="Tasks Manager",
                tool_function="tasks_manager",
                description="Tool to use to answer task related queries",
                capabilities=[
                    ManagerCapability(action="list tasks", description="Shows all available tasks"),
                    ManagerCapability(action="create task", description="Adds a new task"),
                    ManagerCapability(action="get task details", description="Retrieves information about a specific task"),
                    ManagerCapability(action="complete task", description="Marks a task as completed and deletes it"),
                    ManagerCapability(action="list_tasks_from_specific_tasklist", description="list the task from a specified tasklist"),
                    ManagerCapability(action="show_tasklists", description="show the available tasklists"),
                    ManagerCapability(action="show_tasklists", description="show the available tasklists"),


                ]
            ),
            ManagerTool(
                name="Mail Manager",
                tool_function="mail_manager",
                description="Tool to use to answer any email related queries",
                capabilities=[
                    
                    ManagerCapability(action="show inbox", description="Displays all emails in the inbox"),
                    ManagerCapability(action="display mail details", description="Retrieves the details of a specific email"),
                    ManagerCapability(action="create email", description="Composes a new email using the email adress"),
                    ManagerCapability(action="verify email content", description="Checks the content of an email"),
                    ManagerCapability(action="send email", description="Sends a composed email")
            
                ]
            ),
            ManagerTool(
                name="Calendar Manager",
                tool_function="calendar_manager",
                description="Tool to use to answer any calendar or schedule related queries",
                capabilities=[
                    ManagerCapability(action="create recurring events", description="Sets up events that repeat on a schedule"),
                    ManagerCapability(action="create quick events", description="Quickly adds a one-time event"),
                    ManagerCapability(action="refresh calendar", description="Updates the calendar with latest information"),
                    ManagerCapability(action="show calendar", description="Displays the calendar view")
                ]
            )
        ],
        description="The complete list of available manager tools"
    )

manager_tools = ManagerTools()

# For Pydantic V2 
manager_dict = manager_tools.model_dump()


def planner_node(state: State):
    class task_shema(BaseModel):
        task: str = Field(description='description of the task')
        manager_tool: str = Field(description= 'the name of the manager tool to use')
        action: str = Field(description=' the action that the manager tool must take')
    class plan_shema(BaseModel):
        tasks: List[task_shema] = Field(description='the list of tasks that the agent need to complete to succesfully complete the query')
    parser=JsonOutputParser(pydantic_object=plan_shema)
    prompt = PromptTemplate(
    template="Answer the user query.\n{format_instructions}\n{query}\n",
    input_variables=["query"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    
    chain = prompt | llm 
    try:
        response=chain.invoke({'query':f'based on this query: {state['query']} generate a plan using those manager tools: {manager_dict} to get the necessary info and to complete the query, the plan cannot contain more than 10 tasks'}) 
        try:
            response=parser.parse(response.content)
            
            return {'plan':response.get('tasks')}
        except:
            try:
                retry_parser = RetryOutputParser.from_llm(parser=parser, llm=llm)

                prompt_value = prompt.format_prompt(query=state['query'])
                response=retry_parser.parse_with_prompt(response.content, prompt_value) 
        
               
                return {'plan':response.get('tasks')}
            except:
                return {'route':'END'}
    except:
                return {'route':'END'}


def agent_node(state: State):
    class task_route(BaseModel):
        node_query: str = Field(description='the query to be passed to one of the manager tool nodes')
        route: str = Field (description='the name of the manager tool to use or if finished END')
    plan= state.get('plan')
    

    
    # node_messages=state.get('node_messages')
    parser=JsonOutputParser(pydantic_object=task_route)
    prompt = PromptTemplate(
    template="Answer the user query.\n{format_instructions}\n{query}\n",
    input_variables=["query"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    
    chain = prompt | llm 
    if plan:
        response=chain.invoke({'query':f'based on this task: {plan[0]} generate a query to be passed to the manager_tool mentionned in the task, use the informations from previous nodes {state.get('node_messages')}, and chose a route to the corresponding manager tool from this list {manager_dict}'}) 
        try:
            response=parser.parse(response.content)
            
            return {'node_query':response.get('node_query'),
                    'route':response.get('route')}
        except:
            try:
                retry_parser = RetryOutputParser.from_llm(parser=parser, llm=llm)

                prompt_value = prompt.format_prompt(query=state['query'])
                response=retry_parser.parse_with_prompt(response.content, prompt_value) 
                
                return {'node_query':response.get('node_query'),
                    'route':response.get('route')}
            except:
                return {'route':'END'}
    else:
        return {'route':'END'}


def router(state: State):
    route=state.get('route')
    routing_map = {
        'Maps Manager': 'to_maps_manager',
        'Google images tool': 'to_google_image_tool',
        'Contacts Manager': 'to_contact_manager',
        'Tasks Manager': 'to_tasks_manager',
        'Mail Manager': 'to_mail_manager',
        'Calendar Manager': 'to_calendar_manager',
        'END':'to_end'
    }
    return routing_map.get(route)

def evaluator_node(state: State):
    node_message=state.get('node_messages')
    
    class Status(BaseModel):
        status: str = Field(description='completed or failed')
    parser=JsonOutputParser(pydantic_object=Status)
    prompt = PromptTemplate(
    template="Answer the user query.\n{format_instructions}\n{query}\n",
    input_variables=["query"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    
    chain = prompt | llm 
    try:
        response=chain.invoke({'query':f'based on this node message: {node_message[-1].content} and the prompt: {state.get('node_query')}, decide if the task was completed or failed '}) 
       
        response=parser.parse(response.content)
            
    except:
        retry_parser = RetryOutputParser.from_llm(parser=parser, llm=llm)

        prompt_value = prompt.format_prompt(query=state['query'])
        response=retry_parser.parse_with_prompt(response.content, prompt_value) 
        
    status=response.get('status')          
               
    
    if status =='failed':
            return {'plan':[],
                    'node_messages':f' task: {state.get('node_query')}, failed'}
    else:
        plan=state.get('plan')
        del plan[0]
        return {'plan':plan}

def google_image_search_node(state:State):
  """Search for images using Google Custom Search API
  args: query
  return: image url
  """
  # Define the API endpoint for Google Custom Search
  url = "https://www.googleapis.com/customsearch/v1"
  query=state.get('node_query')

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
      return {'node_messages':f' here is the url for the image {image_url}'}
  else:
      return {'node_messages':'failed'}

def contacts_manager_node(state: State):
    """use this tool to answer queries about a contact or a person
    this tool can:
    list my contacts
    get a contact's details
    delete a contact
    create a contact
    modify a contact
    args: query - pass the entire contacts related queries directly here
    """
    response=contacts_agent.chat(state.get('node_query'))
    # return response
    return {'node_messages':[AIMessage(f'{response}')]}



def tasks_manager_node(state: State):
    """use this tool to answer task related queries
    this tool can:
    list tasks
    create tasks
    get task details
    complete a task (which also deletes it :) )

    args: query - pass the entire tasks related queries directly here
    
    """


    response=tasks_agent.chat(state.get('node_query'))
    # return response
    return {'node_messages':[AIMessage(f'{response}')]}


def maps_manager_node(state: State):
    """tool to use to answer maps and location queries
    this tool can:
    find locations such as restorants, bowling alleys, museums and others
    display those locations's infos (eg. adress, name, url, price range)
    args: query - pass the maps or loc related queries directly here
    return: locations with urls
    """
    response=maps_agent.chat(state.get('node_query'))
    # return response
    return {'node_messages':[AIMessage(f'{response}')]}



def mail_manager_node(state: State):
    """Tool to use to answer any email related queries
    this tool can:
    show the inbox
    get a specific mail's content to display
  
    create an email
    verify the email content
    send the email

    args: query - pass the email related queries directly here
    """
    response=mail_agent.chat(state.get('node_query'))
    # return response
    return {'node_messages':[AIMessage(f'{response}')]}


def calendar_manager_node(state: State):
    """tool to use to answere any calendar or schedule related queries
    this tool can:
    create recuring events
    create quick events
    show the calendar
    args: query - pass the entire calendar related queries directly here
    """
    response=calendar_agent.chat(state.get('node_query'))
    # return response
    return {'node_messages':[AIMessage(f'{response}')]}


class Google_agent:
    def __init__(self):
        self.agent=self._setup()
    def _setup(self):
   
        graph_builder = StateGraph(State)

        # Modification: tell the LLM which tools it can call

        graph_builder.add_node("planner", planner_node)
        graph_builder.add_node('calendar_manager', calendar_manager_node)
        graph_builder.add_node('mail_manager',mail_manager_node)
        graph_builder.add_node('tasks_manager',tasks_manager_node)
        graph_builder.add_node('contacts_manager',contacts_manager_node)
        graph_builder.add_node('maps_manager',maps_manager_node)
        graph_builder.add_node('google_image_tool',google_image_search_node)
        graph_builder.add_node('evaluator', evaluator_node)
        
        graph_builder.add_node("agent", agent_node)
        # Any time a tool is called, we return to the chatbot to decide the next step
        graph_builder.add_edge(START,'planner')
        graph_builder.add_edge("planner", "agent")
        graph_builder.add_edge("maps_manager", "evaluator")
        graph_builder.add_edge('tasks_manager','evaluator')
        graph_builder.add_edge('mail_manager','evaluator')
        graph_builder.add_edge('google_image_tool','evaluator')
        graph_builder.add_edge('contacts_manager','evaluator')
        graph_builder.add_edge('calendar_manager','evaluator')
        graph_builder.add_edge('evaluator', 'agent')
        graph_builder.add_conditional_edges(
            "agent",
            router,{
            'to_maps_manager': 'maps_manager',
            'to_google_image_tool': 'google_image_tool',
            'to_contact_manager': 'contacts_manager',
            'to_tasks_manager': 'tasks_manager',
            'to_mail_manager': 'mail_manager',
            'to_calendar_manager': 'calendar_manager',
            'to_end': END
            }
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
    def chat(self,input:str):
        config = {"configurable": {"thread_id": "1"}}
        response=self.agent.invoke({'query':input,
                                    'num_retries':0},config)
        return response.get('node_messages')[-1].content

    def stream(self,input:str):
        config = {"configurable": {"thread_id": "1"}}
        for event in self.agent.stream({'query':input,
                                        'num_retries':0}, config, stream_mode="updates"):
            print(event)
    
    def get_state(self, state_val:str):
        config = {"configurable": {"thread_id": "1"}}
        return self.agent.get_state(config).values[state_val]
