from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition,InjectedState
from langchain_core.messages import (
    HumanMessage,
    ToolMessage,
)
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_core.tools.base import InjectedToolCallId

from typing_extensions import TypedDict
from typing import Annotated
#get graph visuals
from IPython.display import Image, display
from langchain_core.runnables.graph import MermaidDrawMethod
import os


import os.path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class State(TypedDict):
    """
    A dictionnary representing the state of the agent.
    """
    messages: Annotated[list, add_messages]
    tasklist:dict
    task: dict

store=InMemoryStore()


if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json")
try:
    # create gmail api client
    service = build("tasks", "v1", credentials=creds)

except HttpError as error:
    print(f"An error occurred: {error}")

@tool
def list_tasklists(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """Tool to get the tasklists, can be used to refresh tasklists
    agrs: none
    """
    try:
        tasklists=service.tasklists().list(maxResults=10).execute()
        tasklists={tasklist.get('title'):tasklist for tasklist in tasklists.get('items')}
       
        return Command(update={
                            'messages':[ToolMessage(tasklists,tool_call_id=tool_call_id)]})
    except:  
        return Command(update={'messages':[ToolMessage('failed to get tasklists',tool_call_id=tool_call_id)]})

@tool
def list_tasks(id:str ,tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    Tool to list tasks in a specific tasklist, can be used to refresh tasklist and to get task ids
    args: id - The id of the tasklist
    """
    try:
        
        tasklist=service.tasks().list(tasklist=id).execute()
        tasks={task.get('title'):task for task in tasklist.get('items')}
        tasks={'id':id,
               'tasks':tasks}
        return Command(update={'tasklist':tasks,
                    'messages':[ToolMessage(tasks,tool_call_id=tool_call_id)]})
    except: 
        return Command(update={'messages':[ToolMessage('failed to get tasklist',tool_call_id=tool_call_id)]})
    
@tool
def get_task(task_id: str,state: Annotated[dict, InjectedState],tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """Tool to get a task detail, can be used to refresh tasks
    args: task_id - the id of the task
    """
    try:
        tasklist_id=state['tasklist'].get('id')
        task=service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
        return Command(update={'task':task,
                            'messages':[ToolMessage(task,tool_call_id=tool_call_id)]})
    except: 
        return Command(update={'messages':[ToolMessage('failed to get task, use the list_tasklist tool to get tasklist id and then get_specific_tasklist tool to get task id',tool_call_id=tool_call_id)]})
    


@tool 
def complete_task(task_id:str ,state: Annotated[dict, InjectedState],tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """tool to complete a task, once a task is completed it is deleted
    args: task_id - the id of the task, can be found using list_tasks tool
    """
    try:
        
        tasklist_id=state['tasklist'].get('id')
        task=service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
        task['status']='completed'
        response=service.tasks().update(tasklist=tasklist_id,task=task_id, body=task).execute()
        clear=service.tasks().clear(tasklist=tasklist_id).execute()
        return Command(update={'messages':[ToolMessage('task completed', tool_call_id=tool_call_id)]})
    except:
        return Command(update={'messages':[ToolMessage('error :(', tool_call_id=tool_call_id)]})

@tool
def create_task(task:dict,state: Annotated[dict, InjectedState] ,tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    Tool to create a task following the task format

    args: 

    task - the body of the task takes the form of:
    {
  "title": string, Title of the task. Maximum length allowed: 1024 characters.
  "notes": string, Notes describing the task. Maximum length allowed: 8192 characters.Optional.
  "due": string, Due date of the task (as a RFC 3339 timestamp)}. Optional. The due date only records date information; the time portion of the timestamp is discarded when setting the due date.
    """
    try:
        tasklist_id=state['tasklist'].get('id')
        task=service.tasks().insert(tasklist=tasklist_id,body=task).execute()
        return Command(update={'messages':[ToolMessage('task created', tool_call_id=tool_call_id)]})
    except:
        return Command(update={'messages':[ToolMessage(f'error :( : {task}', tool_call_id=tool_call_id)]})


class Tasks_agent:
    def __init__(self,llm : any):
        self.agent=self._setup(llm)
    def _setup(self,llm):
        langgraph_tools=[complete_task,get_task,list_tasks, create_task, list_tasklists]



        graph_builder = StateGraph(State)

        # Modification: tell the LLM which tools it can call
        llm_with_tools = llm.bind_tools(langgraph_tools)
        tool_node = ToolNode(tools=langgraph_tools)
        def chatbot(state: State):
            """ travel assistant that answers user questions about their trip.
            Depending on the request, leverage which tools to use if necessary."""
            return {"messages": [llm_with_tools.invoke(state['messages'])]}

        graph_builder.add_node("chatbot", chatbot)

        graph_builder.add_node("tools", tool_node)
        # Any time a tool is called, we return to the chatbot to decide the next step
        graph_builder.set_entry_point("chatbot")
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_conditional_edges(
            "chatbot",
            tools_condition,
        )
        memory=MemorySaver()
        graph=graph_builder.compile(checkpointer=memory, store=store)
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