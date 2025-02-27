
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
from langchain_core.tools.base import InjectedToolCallId


from typing_extensions import TypedDict
from typing import Annotated

#get graph visuals
from IPython.display import Image, display
from langchain_core.runnables.graph import MermaidDrawMethod
import os




import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class State(TypedDict):
    messages: Annotated[list, add_messages]
    calendar: dict

if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json")

try:
    service = build("calendar", "v3", credentials=creds)

except HttpError as error:
    print(f"An error occurred: {error}")



# Call the Calendar API
def get_events_node(state: State):
    now = datetime.datetime.now().isoformat() + "Z"  # 'Z' indicates UTC time

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])
    ev={}
    for e in events:
        try:
            id= e.get('id')
            summary=e.get('summary')
            creator=e.get('creator')
            start=e.get("start").get("dateTime", e.get("start").get("date"))
            end=e.get("end").get("dateTime", e.get("end").get("date"))
            ev[start]={'summary':summary,
                    'creator':creator,
                    'start':start,
                    'end':end,
                        'event_id':id}
        except: ev[start]=e

    return Command(update={'calendar':ev,
                           })

@tool()
def creating_event(tool_call_id: Annotated[str, InjectedToolCallId],summary: str, location:str, description: str, start_time: str, end_time: str, timezone:str, recurrence: str):
    
  """
  Tool to create more complex events with a detailed description and optionnal recurrence.
  args: 
    summary: str = Field(description='the title of the event')
    location: str = Field(description='the address or location of the event')
    description: str = Field(description='the description of the event')
    start_time: str = Field(description=='the start time of an event, has to be formatted as such: eg. 2015-05-28T09:00:00-07:00')
    end_time: str = Field(description=='the end time of an event, has to be formatted as such: eg. 2015-05-28T09:00:00-07:00')
    timezone: str = Field(description='The timezone of the event (Formatted as an IANA Time Zone Database name, e.g. "Europe/Zurich".)')
    recurrence: str = Field(description='to defice the recurrence of the event(DAILY, WEEKLY, MONTHLY, YEARLY), follow this format eg. RRULE:FREQ=DAILY;COUNT=2')
  If an argument is not mentionned, simply input an empty string eg. ''.
  """
  event = {
  'summary': summary,
  'location': location,
  'description': description,
  'start': {
    'dateTime': start_time,
    'timeZone': timezone,
  },
  'end': {
    'dateTime': end_time,
    'timeZone': timezone,
  },
  'recurrence': [
    recurrence
  ],
  'reminders': {
    'useDefault': False,
    'overrides': [
      {'method': 'email', 'minutes': 24 * 60},
      {'method': 'popup', 'minutes': 10},
    ],
  },
}
  try:
    event = service.events().insert(calendarId='primary', body=event).execute()
    return Command(goto='get_events',
                   update={'messages':[ ToolMessage('succesfully created the event', tool_call_id=tool_call_id)]})
  except: 
    return Command(update={'messages':[ ToolMessage('failed to create the event', tool_call_id=tool_call_id)]})

@tool
def quick_add_event(event_description:str,tool_call_id: Annotated[str, InjectedToolCallId]):
    """
    tool to create a quick event
    args: event_description - a description of the event, including the start and end time (eg. 'Appointment at Somewhere on June 3rd 10am-10:25am' )
    """
    try:
        created_event = service.events().quickAdd(
        calendarId='primary',
        text=event_description).execute()
        return Command(goto='get_events',
                       update={'messages':[ ToolMessage('succesfully created the event', tool_call_id=tool_call_id)]})
    except: 
        return Command(update={'messages':[ ToolMessage('failed to create the event', tool_call_id=tool_call_id)]})
    
@tool
def get_calendar(state: Annotated[dict, InjectedState],tool_call_id: Annotated[str, InjectedToolCallId]):
    """
    tool to get the calendar to answer questions
    args: none
    """

    try:
        calendar=state['calendar']
        return Command(update={'messages':[ ToolMessage(str(calendar), tool_call_id=tool_call_id)]})
    except:
        now = datetime.datetime.now().isoformat() + "Z"  # 'Z' indicates UTC time

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=20,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        ev={}
        for e in events:
            try:
                id= e.get('id')
                summary=e.get('summary')
                creator=e.get('creator')
                start=e.get("start").get("dateTime", e.get("start").get("date"))
                end=e.get("end").get("dateTime", e.get("end").get("date"))
                ev[start]={'summary':summary,
                        'creator':creator,
                        'start':start,
                        'end':end,
                            'event_id':id}
            except:
                    ev[start]=e

        return Command(update={'calendar':ev,
             'messages':[ToolMessage(str(ev), tool_call_id=tool_call_id)]})
    
@tool
def update_calendar(tool_call_id: Annotated[str, InjectedToolCallId]):
    """
    tool to return the latest version of the calendar
    agrs: none
    """
    now = datetime.datetime.now().isoformat() + "Z"  # 'Z' indicates UTC time

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=20,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])
    ev={}
    for e in events:
        try:
            id= e.get('id')
            summary=e.get('summary')
            creator=e.get('creator')
            start=e.get("start").get("dateTime", e.get("start").get("date"))
            end=e.get("end").get("dateTime", e.get("end").get("date"))
            ev[start]={'summary':summary,
                    'creator':creator,
                    'start':start,
                    'end':end,
                        'event_id':id}
        except:
                ev[start]=e

    return Command(update={'calendar':ev,
        'messages':[ToolMessage('updated calendar', tool_call_id=tool_call_id)]})

class Calendar_agent:
    def __init__(self,llm:any):
        self.agent=self._setup(llm)
    def _setup(self,llm):
   
        langgraph_tools=[quick_add_event,get_calendar,creating_event,update_calendar]



        graph_builder = StateGraph(State)

        # Modification: tell the LLM which tools it can call
        llm_with_tools = llm.bind_tools(langgraph_tools)
        tool_node = ToolNode(tools=langgraph_tools)
        def chatbot(state: State):
            """ travel assistant that answers user questions about their trip.
            Depending on the request, leverage which tools to use if necessary."""
            return {"messages": [llm_with_tools.invoke(state['messages'])]}

        graph_builder.add_node("chatbot", chatbot)

        graph_builder.add_node('get_events',get_events_node)
        graph_builder.add_node("tools", tool_node)
        # Any time a tool is called, we return to the chatbot to decide the next step
        graph_builder.add_edge(START,'chatbot')
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_conditional_edges(
            "chatbot",
            tools_condition,
        )
        memory=MemorySaver()
        graph=graph_builder.compile(checkpointer=memory)
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