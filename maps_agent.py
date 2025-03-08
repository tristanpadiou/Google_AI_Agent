


from langgraph.graph import StateGraph, START, END

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from langgraph.checkpoint.memory import MemorySaver

from langchain_core.output_parsers import JsonOutputParser

from typing_extensions import TypedDict


#get graph visuals
from IPython.display import Image, display
from langchain_core.runnables.graph import MermaidDrawMethod
from pydantic import BaseModel, Field
import os

from dotenv import load_dotenv 

#getting current location
import geocoder
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from google.maps import places_v1
load_dotenv()

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
  query: str
  node_message:str
  #location data
  latitude: str
  longitude: str
  address: str
  route: str
  #results from place search
  places: dict


def router_node(state=State):
    route=state.get('route')
    if route=='look_for_places':
        return 'to_look_for_places' 
    elif route=='current_loc':
        return 'to_current_loc'
    
def get_current_location_node(state: State):
    """
    Tool to get the current location of the user.
    agrs: none
    """
    current_location = geocoder.ip("me")
    if current_location.latlng:
        latitude, longitude = current_location.latlng
        address = current_location.address
        return {
            'latitude':latitude,
            'longitude':longitude,
            'address':address}
    else:
        return {'node_message':'failed'}
    
def look_for_places_node(state: State):
    """
    Tool to look for places based on the user query and location.
    Use this tool for more complex user queries like sentences, and if the location is specified in the query.
    Places includes restaurants, bars, speakeasy, games, anything.
    args: query - the query.
    Alaways include the links in the response
    """
    try:
        request=places_v1.SearchTextRequest(text_query=state['query'])
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
                
        return {'places':places}
                               
    except: 
        return {'node_message':'failed'}
    
class Maps_agent:
    def __init__(self,llm: any):
        self.agent=self._setup(llm)
        

    def _setup(self,llm):
        # langgraph_tools=[get_current_location_tool,look_for_places, show_places_found]
        def agent_node(state:State):
            class Form(BaseModel):
                route: str = Field(description= 'return current_loc or look_for_places')
            parser=JsonOutputParser(pydantic_object=Form)
            instruction=parser.get_format_instructions()
            response=llm.invoke([HumanMessage(content=f'based on this query:{state['query']}, return current_loc or look_for_places'+'\n\n'+instruction)])
            response=parser.parse(response.content)
            response=response.get('route')
            return {'route':response}

        graph_builder = StateGraph(State)
        
        # Modification: tell the LLM which tools it can call
        # llm_with_tools = llm.bind_tools(langgraph_tools)
        # tool_node = ToolNode(tools=langgraph_tools)
        # def chatbot(state: State):
        #     """ maps assistant that answers user questions about locations or maps.
        #     Depending on the request, leverage which tools to use if necessary."""
        #     return {"messages": [llm_with_tools.invoke(state['messages'])]}

        # graph_builder.add_node("chatbot", chatbot)

 
        # graph_builder.add_node("tools", tool_node)
        # # Any time a tool is called, we return to the chatbot to decide the next step
        # graph_builder.set_entry_point("chatbot")

        # graph_builder.add_edge("tools", "chatbot")
        # graph_builder.add_conditional_edges(
        #     "chatbot",
        #     tools_condition,
        # )

        graph_builder.add_node('current_loc', get_current_location_node)
        graph_builder.add_node('look_for_places',look_for_places_node)
        
        graph_builder.add_node('agent',agent_node)
        graph_builder.add_edge(START,'agent')
        graph_builder.add_conditional_edges('agent',router_node,{'to_current_loc':'current_loc', 'to_look_for_places':'look_for_places'})
        graph_builder.add_edge('current_loc',END)
        graph_builder.add_edge('look_for_places',END)
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
    
    # def stream(self,input:str):
    #     config = {"configurable": {"thread_id": "1"}}
    #     input_message = HumanMessage(content=input)
    #     for event in self.agent.stream({"messages": [input_message]}, config, stream_mode="values"):
    #         event["messages"][-1].pretty_print()

    # def chat(self,input:str):
    #     config = {"configurable": {"thread_id": "1"}}
    #     response=self.agent.invoke({'messages':HumanMessage(content=str(input))},config)
    #     return response['messages'][-1].content
    def chat(self,input:str):
        config = {"configurable": {"thread_id": "1"}}
        response=self.agent.invoke({'query':input},config)
        return response

    def stream(self,input:str):
        config = {"configurable": {"thread_id": "1"}}
        for event in self.agent.stream({'query':input}, config, stream_mode="updates"):
            print(event)
    