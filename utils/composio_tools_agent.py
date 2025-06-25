


from dotenv import load_dotenv
from typing import Literal
from langchain_openai import ChatOpenAI
# from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import MessagesState, StateGraph,END
from langgraph.prebuilt import ToolNode
from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles
import json

class Composio_agent:
    def __init__(self,tools:list,llm:ChatOpenAI):
       """
       This function is used to initialize the agent

       Args:

           tools: list of tools from composio

           llm: the llm to use, it should be a ChatOpenAI model from langchain

       """
       self.agent=self.setup_agent(tools,llm)
       

    def setup_agent(self,tools:list,llm:ChatOpenAI):
        """
        This function is used to setup the agent
        Args:
            tools: list of tools from composio
        Returns:
            app: the agent
        """
        
        tool_node = ToolNode(tools)

        model_with_tools = llm.bind_tools(tools)

        def call_model(state: MessagesState):
            """
            Process messages through the LLM and return the response
            """
            messages = state["messages"]
            response = model_with_tools.invoke(messages)
            return {"messages": [response]}

        workflow = StateGraph(MessagesState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        workflow.add_edge("__start__", "agent")
        workflow.add_edge("agent", "tools")
        workflow.add_edge("tools", END)
        app = workflow.compile()
        return app

    def chat(self,query:str):  

        """
        This tool is an agent used to interact with the agent it has a list of functionnalities that can be used to interact with the agent
        simply pass the query to the tool with the necessary information like ids if needed and it will return the response
        Args:
            query: str simply pass the query to the tool
        Returns:
            res: str
        """
        res=self.agent.invoke(
            {
                "messages": [
                (
                    "human",
                    query,
                )
            ]
        }
    )
        try:
            return json.loads(res['messages'][-1].content)
        except:
            try:
                return res['messages'][-1].content
            except:
                return res


    def display_graph(self):
        return display(
                        Image(
                                self.agent.get_graph().draw_mermaid_png(
                                    draw_method=MermaidDrawMethod.API,
                                )
                            )
                        )
