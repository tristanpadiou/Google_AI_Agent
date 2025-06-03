from __future__ import annotations
from composio_langgraph import Action, ComposioToolSet, App
from composio_tools_agent import Composio_agent

from pydantic_graph import BaseNode, End, GraphRunContext, Graph
from pydantic_ai import Agent
from datetime import datetime

from pydantic import BaseModel,Field
from dataclasses import dataclass

from typing import Annotated, List, Optional

#get graph visuals
from IPython.display import Image, display
import os
import requests
import nest_asyncio
nest_asyncio.apply()






@dataclass
class State:
    node_messages_dict:dict
    node_messages_list:list
    evaluator_message:str
    node_query:str
    query: str
    plan: List
    route:str
    n_retries:int
    #planning notes are notes to improve the planning or use of a tool based on a prompt
    planning_notes:str
    #query notes are notes to help the agent to fulfill the requirements of the user
    query_notes:dict
    #action exclusive outputs
    #mail inbox is the inbox of the user
    mail_inbox:dict
class Google_agent:
    def __init__(self,llms: dict, api_keys:dict):
        """
        Args:
            llm (any): The language model to use using langchain_framework
            api_keys (dict): The API keys to use
        """
        # tools is the composio toolset
        self.tools=ComposioToolSet(api_key=api_keys['composio_key'])
        # tool_shemas is a dictionary of the tool names and the actions they can perform
        self.tool_shemas={
            'Mail Manager':{tool.name:tool for tool in self.tools.get_action_schemas(apps=[App.GMAIL])},
            'Maps Manager':{tool.name:tool for tool in self.tools.get_action_schemas(apps=[App.GOOGLE_MAPS])},
            'Tasks Manager':{tool.name:tool for tool in self.tools.get_action_schemas(apps=[App.GOOGLETASKS])},
            'Google images tool':{'search_images':'search for images'},
            'Get_current_time':{'get_current_time':'get the current time'},
            'Planning_notes_editor':{'planning_notes_editor':'notes to improve the planning or use of a tool based on a prompt'},
            'List_tools':{'list_tools':'list the tools available'},
            'Query_notes_editor':{'query_notes_editor':'edit the query notes to fulfill the requirements of the tool'}
        }
        # tool_functions is a dictionary of the tool names and the actions they can perform
        self.tool_functions={
            'managers':{
                'Mail Manager':{
                    'actions':{tool.name:{'description':tool.description} for tool in self.tools.get_tools(apps=[App.GMAIL])}
                },
                'Maps Manager':{
                    'actions':{tool.name:{'description':tool.description} for tool in self.tools.get_tools(apps=[App.GOOGLE_MAPS])}
                },
                'Tasks Manager':{
                    'actions':{tool.name:{'description':tool.description} for tool in self.tools.get_tools(apps=[App.GOOGLETASKS])}
                },
                'Google images tool':{
                    'actions':{'search_images':{'description':'search for images'}}
                },
                'Planning_notes_editor':{
                    'actions':{'planning_notes_editor':{'description':'notes to improve the planning or use of a tool based on a prompt'}}
                },
                'Get_current_time':{
                    'actions':{'get_current_time':{'description':'get the current time'}}
                },
                'List_tools':{
                    'actions':{'list_tools':{'description':'list the tools available'}}
                },
                'Query_notes_editor':{
                    'actions':{'query_notes_editor':{'description':'edit the query notes to fulfill the requirements of the manager tool'}}
                },
                'Agent_node':{
                    'actions':{'agent_node':{'description':'the agent node that generates the plan, come back to this node if you need to modify the plan based on previous node messages'}}
                }
            }
        }
        # agents are the composio agents for the tools
        self.mail_agent=Composio_agent(self.tools.get_tools(apps=[App.GMAIL]),llms['openai_llm'])
        self.maps_agent=Composio_agent(self.tools.get_tools(apps=[App.GOOGLE_MAPS]),llms['openai_llm'])
        self.tasks_agent=Composio_agent(self.tools.get_tools(apps=[App.GOOGLETASKS]),llms['openai_llm'])
        
    

        # Nodes:
        # planner_node is the node that generates the plan
        @dataclass
        class Agent_node(BaseNode[State]):
            llm=llms['pydantic_llm']
            tool_functions=self.tool_functions
            async def run(self,ctx: GraphRunContext[State])->Query_generator_node | End:
                class task_shema(BaseModel):
                    task: str = Field(description='the task to be passed to one of the manager tool nodes')
                    manager_tool: str = Field(description= 'the name of the manager tool to use')
                    action: str = Field(description=' the action that the manager tool must take from the actions of the manager tool')
                class plan_shema(BaseModel):
                    tasks: List[task_shema] = Field(description='the list of tasks that the agent need to complete to succesfully complete the query')
                #generate the plan
                plan_agent=Agent(self.llm,output_type=plan_shema, instructions=f'based on a query, and the previous node messages (if any), generate a plan using those manager tools: {self.tool_functions} to get the necessary info and to complete the query, use the planning notes to improve the planning, if any, the plan cannot contain more than 10 tasks')
                try:
                    response=plan_agent.run_sync(f'query:{ctx.state.query}, planning_notes:{ctx.state.planning_notes}, previous_node_messages:{ctx.state.node_messages_list}') 
                    ctx.state.plan=response.output.tasks
                    return Query_generator_node()
                #if the plan is not generated, return the state
                except Exception as e:
                    ctx.state.node_messages_list.append({'error':f'error: {e}'})
                    return End(ctx.state)
        @dataclass
        class Query_generator_node(BaseNode[State]):
            llm=llms['pydantic_llm']
            async def run(self,ctx: GraphRunContext[State])->router_node | End:
           
                #generate the query
                class Query_generator_shema(BaseModel):
                    query: str = Field(description='the query to be passed to one of the manager tool nodes')
                agent=Agent(self.llm,output_type=Query_generator_shema, instructions=f'based on a query, and the previous node messages (if any) generate a detailed query, use the query notes if any to improve the query so it fits the requirements of the user, use all the infos necessary for the agent to understand and answer the query')
                plan=ctx.state.plan
                if plan:
                    if ctx.state.query_notes.get(plan[0].manager_tool):
                        if ctx.state.query_notes[plan[0].manager_tool].get(plan[0].action):
                            query_notes=ctx.state.query_notes[plan[0].manager_tool][plan[0].action]["query_notes"]
                        else:
                            query_notes="no query notes"
                    else:
                        query_notes="no query notes"

                
                    response=agent.run_sync(f'query:{plan[0].task}, query_notes:{query_notes}, previous_node_messages:{ctx.state.node_messages_list}')    
                    ctx.state.node_query=response.output.query
                    return router_node()
                else:
                    return End(ctx.state)
        # agent_node is the node that uses the plan to complete the task and update the node_query if needed
        @dataclass
        class router_node(BaseNode[State]):
            async def run(self,ctx: GraphRunContext[State])-> get_current_time_node | maps_manager_node | tasks_manager_node | mail_manager_node | google_image_search_node | list_tools_node | planning_notes_editor_node | query_notes_editor_node | Agent_node | End:
                plan= ctx.state.plan
                
                #get the manager tool to use
                ctx.state.route=plan[0].manager_tool
                if ctx.state.route=='Get_current_time':
                    return get_current_time_node()
                elif ctx.state.route=='Maps Manager':
                    return maps_manager_node()
                elif ctx.state.route=='Tasks Manager':
                    return tasks_manager_node()
                elif ctx.state.route=='Mail Manager':
                    return mail_manager_node()
                elif ctx.state.route=='Google images tool':
                    return google_image_search_node()
                elif ctx.state.route=='Planning_notes_editor':
                    return planning_notes_editor_node()
                elif ctx.state.route=='List_tools':
                    return list_tools_node()
                elif ctx.state.route=='Query_notes_editor':
                    return query_notes_editor_node()
                elif ctx.state.route=='Agent_node':
                    return Agent_node()
                else:
                    return End(ctx.state)
                    

        # evaluator_node is the node that evaluates the task and prompts the agent to retry or update the node_query if needed
        class evaluator_node(BaseNode[State]):
            llm=llms['pydantic_llm']
            async def run(self,ctx: GraphRunContext[State])-> Query_generator_node | End:
            
                class Status(BaseModel):
                    status: str = Field(description='completed, failed')
                    reason: Optional[str] = Field(default_factory=None,description='the reason for the status, if the status is completed, the reason should be None')
                evaluator_agent=Agent(self.llm,output_type=Status, instructions=f'based on the node message and the prompt, decide if the task was completed or failed,look for errors in the node message, if failed, explain why')

                
                response=evaluator_agent.run_sync(f'node_message:{ctx.state.node_messages_list[-1]}, node_query:{ctx.state.plan[0].task}')
                    
                status=response.output.status          
                        
                # if the task is failed, prompt the agent to retry or update the node_query if needed
                if status =='failed':
                    if ctx.state.n_retries<2:
                        ctx.state.evaluator_message=f'failed, reason: {response.output.reason}'
                        ctx.state.n_retries+=1
                        if len(ctx.state.node_messages_list)>10:
                            del ctx.state.node_messages_list[0]
                        ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:ctx.state.evaluator_message}})
                        return Agent_node()
                    else:
                        ctx.state.n_retries=0
                        ctx.state.evaluator_message=f'failed, reason: {response.output.reason}'
                        if len(ctx.state.node_messages_list)>10:
                            del ctx.state.node_messages_list[0]
                        if ctx.state.node_messages_dict.get(ctx.state.plan[0].manager_tool):
                            ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool][ctx.state.plan[0].action]=ctx.state.evaluator_message
                        else:
                            ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool]={ctx.state.plan[0].action:ctx.state.evaluator_message}
                        ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:ctx.state.evaluator_message}})
                        return End(ctx.state)
                else:
                    ctx.state.evaluator_message=''
                    if len(ctx.state.node_messages_list)>10:
                        del ctx.state.node_messages_list[0]
                    del ctx.state.plan[0]
                    
                    return Query_generator_node()


        class google_image_search_node(BaseNode[State]):
            async def run(self,ctx: GraphRunContext[State])->evaluator_node:
                """Search for images using Google Custom Search API
                args: query
                return: image url
                """
                # Define the API endpoint for Google Custom Search
                url = "https://www.googleapis.com/customsearch/v1"
                query=ctx.state.node_query

                params = {
                    "q": query,
                    "cx": api_keys['pse'],
                    "key": api_keys['google_api_key'],
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
                    if ctx.state.node_messages_dict.get(ctx.state.plan[0].manager_tool):
                        ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool][ctx.state.plan[0].action]=f'here is the url for the image {image_url}'
                    else:
                        ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool]={ctx.state.plan[0].action:f'here is the url for the image {image_url}'}
                    ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:f'here is the url for the image {image_url}'}})
                    return evaluator_node()
                else:
                    if ctx.state.node_messages_dict.get(ctx.state.plan[0].manager_tool):
                        ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool][ctx.state.plan[0].action]='failed to find image'
                    else:
                        ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool]={ctx.state.plan[0].action:'failed to find image'}
                    ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:'failed to find image'}})
                    return evaluator_node()
        @dataclass
        class planning_notes_editor_node(BaseNode[State]):
            llm=llms['pydantic_llm']
            tool_functions=self.tool_functions
            async def run(self,ctx: GraphRunContext[State])->End:
                class planning_improve_shema(BaseModel):
                    planning_improvement: str = Field(description='the planning improvement notes')
                agent=Agent(self.llm,output_type=planning_improve_shema, instructions=f'based on the dict of tools and the prompt, and the previous planning notes (if any), create a notes to improve the planning or use of a tool for the planner node')
                response=agent.run_sync(f'prompt:{ctx.state.query}, tool_functions:{self.tool_functions}, previous_planning_notes:{ctx.state.planning_notes if ctx.state.planning_notes else "no previous planning notes"}')
                ctx.state.planning_notes=response.output.planning_improvement
                if ctx.state.node_messages_dict.get(ctx.state.plan[0].manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool][ctx.state.plan[0].action]=response.output.planning_improvement
                else:
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool]={ctx.state.plan[0].action:response.output.planning_improvement}
                ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:response.output.planning_improvement}})
                return End(ctx.state)
        
        @dataclass
        class query_notes_editor_node(BaseNode[State]):
            llm=llms['pydantic_llm']
            tool_functions=self.tool_functions
            async def run(self,ctx: GraphRunContext[State])->End:
                class query_notes_shema(BaseModel):
                    query_notes: str = Field(description='the query notes has to be an explanation of how to use the tool to complete the task')
                    manager_tool: str = Field(description='the name of the manager tool for the query')
                    action: str = Field(description='the action that the manager tool must take')

                agent=Agent(self.llm,output_type=query_notes_shema, instructions=f'based on the user query, and the tools, edit the query notes to help the agent to fulfill the requirements of the user')
                response=agent.run_sync(f'prompt:{ctx.state.query}, tool_functions:{self.tool_functions}')
                if ctx.state.query_notes.get(response.output.manager_tool):
                    ctx.state.query_notes[response.output.manager_tool][response.output.action]={'query_notes':response.output.query_notes}
                else:
                    ctx.state.query_notes[response.output.manager_tool]={response.output.action:{'query_notes':response.output.query_notes}}
                if ctx.state.node_messages_dict.get(ctx.state.plan[0].manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool][ctx.state.plan[0].action]=response.output.query_notes
                else:
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool]={ctx.state.plan[0].action:{'query_notes':response.output.query_notes}}
                ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:{'query_notes':response.output.query_notes}}})
                return End(ctx.state)

        @dataclass
        class tasks_manager_node(BaseNode[State]):
            """use this tool to answer task related queries
            this tool can:
            list tasks
            create tasks
            get task details
            complete a task (which also deletes it :) )

            args: query - pass the entire tasks related queries directly here
            
            """
            tasks_agent=self.tasks_agent
            async def run(self,ctx: GraphRunContext[State])->evaluator_node:
                response=self.tasks_agent.chat(ctx.state.node_query+ 'if there is an error, explain it in detail')
                # return response
                if ctx.state.node_messages_dict.get(ctx.state.plan[0].manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool][ctx.state.plan[0].action]=response
                else:
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool]={ctx.state.plan[0].action:response}
                ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:response}})
                return evaluator_node()


        @dataclass
        class maps_manager_node(BaseNode[State]):
            """tool to use to answer maps and location queries
            this tool can:
            find locations such as restorants, bowling alleys, museums and others
            display those locations's infos (eg. adress, name, url, price range)
            args: query - pass the maps or loc related queries directly here
            return: locations with urls
            """
            maps_agent=self.maps_agent
            async def run(self,ctx: GraphRunContext[State])->evaluator_node:
                response=self.maps_agent.chat(ctx.state.node_query + 'if there is an error, explain it in detail')
                # return response
                if ctx.state.node_messages_dict.get(ctx.state.plan[0].manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool][ctx.state.plan[0].action]=response
                else:
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool]={ctx.state.plan[0].action:response}
                ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:response}})
                return evaluator_node()



        @dataclass
        class mail_manager_node(BaseNode[State]):
            """Tool to use to answer any email related queries
            this tool can:
            show the inbox
            
            create an email
            create a draft email
            verify the email content
            send the email

            args: query - pass the email related queries directly here
            """
            
            mail_agent=self.mail_agent
            async def run(self,ctx: GraphRunContext[State])->evaluator_node:
                
                response=self.mail_agent.chat(ctx.state.node_query + f'if the query is about sending an email, do not send any attachements, just send the url in the body, if there is an error, explain it in detail')
                #save the inbox in the state for future use
                if ctx.state.plan[0].action=='GMAIL_FETCH_EMAILS':
                    inbox=[]
                    for i in response['data']['messages']:
                        mail={'message_id':i.get('messageId'),'thread_id':i.get('threadId'),'subject':i.get('subject'),'sender':i.get('sender'),'date':i.get('messageTimestamp'),'snippet':i.get('preview'), 'messageText':i.get('messageText')}
                        inbox.append(mail)
                    ctx.state.mail_inbox=inbox
                    if ctx.state.node_messages_dict.get(ctx.state.plan[0].manager_tool):
                        ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool][ctx.state.plan[0].action]=inbox
                    else:
                        ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool]={ctx.state.plan[0].action:inbox}
                    ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:inbox}})
                else:
                    # return response
                    if ctx.state.node_messages_dict.get(ctx.state.plan[0].manager_tool):
                        ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool][ctx.state.plan[0].action]=response
                    else:
                        ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool]={ctx.state.plan[0].action:response}
                    ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:response}})
                return evaluator_node()



        
        class get_current_time_node(BaseNode[State]):
            """
            Use this tool to get the current time.
            Returns:
                str: The current time in a formatted string
            """
            async def run(self,ctx: GraphRunContext[State])->evaluator_node:
                if ctx.state.node_messages_dict.get(ctx.state.plan[0].manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool][ctx.state.plan[0].action]=f"The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                else:
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool]={ctx.state.plan[0].action:f"The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:f"The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}})
                return evaluator_node()
            
        @dataclass
        class list_tools_node(BaseNode[State]):
            tools=self.tool_functions
            async def run(self,ctx: GraphRunContext[State])->End:
                if ctx.state.node_messages_dict.get(ctx.state.plan[0].manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool][ctx.state.plan[0].action]=self.tools
                else:
                    ctx.state.node_messages_dict[ctx.state.plan[0].manager_tool]={ctx.state.plan[0].action:self.tools}
                ctx.state.node_messages_list.append({ctx.state.plan[0].manager_tool:{ctx.state.plan[0].action:self.tools}})
                return evaluator_node()

        self.graph=Graph(nodes=[Agent_node, router_node, evaluator_node, google_image_search_node, tasks_manager_node, maps_manager_node, mail_manager_node, get_current_time_node, list_tools_node, planning_notes_editor_node, query_notes_editor_node, Query_generator_node])
        self.state=State(node_messages_dict={}, node_messages_list=[], evaluator_message='', node_query='', query='', plan=[], route='', n_retries=0, planning_notes='', query_notes={}, mail_inbox=[])
        self.Agent_node=Agent_node()
        
    def chat(self,query:str):
        """Chat with the google agent,
        Args:
            query (str): The query to search for
        Returns:
            dict: The state of the google agent
        """
        self.state.query=query
        response=self.graph.run_sync(self.Agent_node,state=self.state)
        return response.output

    def display_graph(self):
        """Display the graph of the google agent
        Returns:
            Image: The image of the graph
        """
        image=self.graph.mermaid_image()
        return display(Image(image))
    def reset(self):
        """Reset the state of the google agent
        """
        self.state=State(node_messages_dict={}, node_messages_list=[], evaluator_message='', node_query='', query='', plan=[], route='', n_retries=0, planning_notes='', query_notes={}, mail_inbox=[])
        return 'agent reset'