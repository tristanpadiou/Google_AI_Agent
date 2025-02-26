
from langchain.tools import tool

from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition,InjectedState
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools.base import InjectedToolCallId

from typing_extensions import TypedDict
from typing import Annotated

#get graph visuals
from IPython.display import Image, display
from langchain_core.runnables.graph import MermaidDrawMethod

import os

#getting current location
import geocoder
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from google.maps import places_v1


#getting authorization from oauth
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json")
try:

    client = places_v1.PlacesClient(credentials=creds)

except HttpError as error:
    print(f"An error occurred: {error}")


class State(TypedDict):
  """
  A dictionnary representing the state of the agent.
  """
  messages: Annotated[list, add_messages]

  #location data
  latitude: str
  longitude: str
  address: str
  #results from place search
  places: dict


@tool
def get_current_location_tool(tool_call_id: Annotated[str, InjectedToolCallId]):
    """
    Tool to get the current location of the user.
    agrs: none
    """
    current_location = geocoder.ip("me")
    if current_location.latlng:
        latitude, longitude = current_location.latlng
        address = current_location.address
        return Command(update={'messages':[ToolMessage(F'The current location is: address:{address}, longitude:{longitude},lattitude:{latitude}', tool_call_id=tool_call_id)],
                               'latitude':latitude,
                                'longitude':longitude,
                                'address':address})
    else:
        return None
    

@tool
def look_for_places(query: str, tool_call_id: Annotated[str, InjectedToolCallId]):
    """
    Tool to look for places based on the user query and location.
    Use this tool for more complex user queries like sentences, and if the location is specified in the query.
    Places includes restaurants, bars, speakeasy, games, anything.
    args: query - the query.
    Alaways include the links in the respons
    """
    try:
        request=places_v1.SearchTextRequest(text_query=query)
        response=client.search_text(request=request,metadata=[("x-goog-fieldmask", "places.displayName,places.formattedAddress,places.priceLevel,places.googleMapsUri")]) 
        places={}
        for i in response.places:
            address=i.formatted_address
            name=i.display_name.text
            price_level=i.price_level
            url=i.google_maps_uri
            places[name]={'address':address,
                        'price_level':price_level,
                        'google_maps_url':url}
                
        return Command(update={'places':places,
                               'messages':[ToolMessage(f'I found {len(places)} places', tool_call_id=tool_call_id)]})
    except: 
        return Command(update={
                               'messages':[ToolMessage(f'Couldn t find places', tool_call_id=tool_call_id)]})
    
@tool
def show_places_found(state: Annotated[dict, InjectedState],tool_call_id: Annotated[str, InjectedToolCallId]):
    """
    Tool to get the places found and to show/display them.
    It has links within that can also be used for directions
    args: none
    """
    try:
        return Command(update={'messages': [ToolMessage(state['places'],tool_call_id=tool_call_id)]})
    except:
        return Command(update={ 'messages':[ToolMessage(f'No places to show', tool_call_id=tool_call_id)]})


class maps_agent:
    def __init__(self,llm: any):
        self.agent=self._setup(llm)
        

    def _setup(self,llm):
        langgraph_tools=[get_current_location_tool,look_for_places, show_places_found]


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
    def get_state(self, state_val:str):
        config = {"configurable": {"thread_id": "1"}}
        return self.agent.get_state(config).values[state_val]
    
    def stream(self,input:str):
        config = {"configurable": {"thread_id": "1"}}
        input_message = HumanMessage(content=input)
        for event in self.agent.stream({"messages": [input_message]}, config, stream_mode="values"):
            event["messages"][-1].pretty_print()

    def chat(self,input:str):
        config = {"configurable": {"thread_id": "1"}}
        response=self.agent.invoke({'messages':HumanMessage(content=str(input))},config)
        return response['messages'][-1].content