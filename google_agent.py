from __future__ import annotations
from composio_langgraph import Action, ComposioToolSet, App
from composio_tools_agent import Composio_agent

from pydantic_graph import BaseNode, End, GraphRunContext, Graph
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from langchain_openai import ChatOpenAI
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
    eval_messages_dict:dict
    
    query: str
    plan: dict
    route:str
    #n_retries is the number of retries for a task
    n_retries:int
    #planning notes are notes to improve the planning or use of a tool based on a prompt
    planning_notes:str
    #query notes are notes to help the agent to fulfill the requirements of the user
    query_notes:dict
    #action exclusive outputs
    #mail inbox is the inbox of the user
    mail_inbox:dict
class Google_agent:
    def __init__(self, api_keys:dict):
        """
        Args:
            llm (any): The language model to use using langchain_framework
            api_keys (dict): The API keys to use
            toolset (ComposioToolSet): The toolset to use
        """
        llms={'pydantic_llm':GoogleModel('gemini-2.5-flash-preview-05-20', provider=GoogleProvider(api_key=api_keys['google_api_key'])),
              
              'openai_llm':ChatOpenAI(model='gpt-4.1-nano',api_key=api_keys['openai_api_key'])}   
        # tools is the composio toolset
        self.tools=ComposioToolSet(api_key=api_keys['composio_key'])
        # tool_shemas is a dictionary of the tool names and the actions they can perform
        self.tool_shemas={
            'Mail Manager':{tool.name:tool for tool in self.tools.get_action_schemas(apps=[App.GMAIL])},
            'Tasks Manager':{tool.name:tool for tool in self.tools.get_action_schemas(apps=[App.GOOGLETASKS])},
            'Calendar Manager':{tool.name:tool for tool in self.tools.get_action_schemas(apps=[App.GOOGLECALENDAR])},
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
                'Tasks Manager':{
                    'actions':{tool.name:{'description':tool.description} for tool in self.tools.get_tools(apps=[App.GOOGLETASKS])}
                },
                'Calendar Manager':{
                    'actions':{tool.name:{'description':tool.description} for tool in self.tools.get_tools(apps=[App.GOOGLECALENDAR])}
                },
                'Google images tool':{
                    'actions':{'search_images':{'description':'search for images, this tool can search for multiple images at once'}}
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
                }
            }
        }
        # agents are the composio agents for the tools
        self.mail_agent=Composio_agent(self.tools.get_tools(apps=[App.GMAIL]),llms['openai_llm'])
        
        self.tasks_agent=Composio_agent(self.tools.get_tools(apps=[App.GOOGLETASKS]),llms['openai_llm'])
        
        self.calendar_agent=Composio_agent(self.tools.get_tools(apps=[App.GOOGLECALENDAR]),llms['openai_llm'])

        # Nodes:
        # planner_node is the node that generates the plan
        @dataclass
        class Agent_node(BaseNode[State]):
            llm=llms['pydantic_llm']
            tool_functions=self.tool_functions
            async def run(self,ctx: GraphRunContext[State])->router_node | End:
                class task_shema(BaseModel):
                    task_status: str = Field(description='the status of the task, completed, failed, in progress')
                    task_reason: str = Field(description='the reason for the task status, if the task is failed, explain why')
                    task: str = Field(description='the task to be passed to one of the manager tool nodes')
                
                class plan_shema(BaseModel):
                    tasks: List[task_shema] = Field(description='the list of tasks that the agent need to complete to succesfully complete the query')
                    manager_tool: str = Field(description='the name of the manager tool to use, if all the tasks are completed return End')
                    action: str = Field(description='the action that the manager tool must take has to be one of the actions of the manager tool if the right format,if all the tasks are completed return End')
                    task: str = Field(description='the task that the manager tool must complete, if all the tasks are completed return End')
                    
                    
                if len(ctx.state.node_messages_list)>9:
                    del ctx.state.node_messages_list[0]
                #generate the plan
                plan_agent=Agent(self.llm,output_type=plan_shema, instructions=f'based on a query, and the previous node messages (if any) and the previous plan (if any) and the eval messages (if any), generate or modify a plan using those manager tools: {self.tool_functions} to get the necessary info and to complete the query, use the planning notes to improve the planning, if any, the plan cannot contain more than 10 tasks, if a manager returns a auth error return End')
                try:
                    if ctx.state.n_retries<3:
                        response=plan_agent.run_sync(f'query:{ctx.state.query},eval_messages:{ctx.state.eval_messages_dict}, planning_notes:{ctx.state.planning_notes}, previous_node_messages:{ctx.state.node_messages_list}, previous_plan:{ctx.state.plan if ctx.state.plan else "no previous plan"}') 
                        ctx.state.plan=response.output
                        ctx.state.node_messages_dict['agent_node']=response.output
                        return router_node()
                    else:
                        ctx.state.node_messages_list.append({'eval_node':ctx.state.eval_messages_dict})
                        ctx.state.plan={}
                        ctx.state.eval_messages_dict={}
                        return End(ctx.state)
                #if the plan is not generated, return the state
                except Exception as e:
                    ctx.state.node_messages_list.append({'error':f'error: {e}'})
                    ctx.state.eval_messages_dict={}
                    ctx.state.plan={}
                    return End(ctx.state)

        # agent_node is the node that uses the plan to complete the task and update the node_query if needed
        @dataclass
        class router_node(BaseNode[State]):
            async def run(self,ctx: GraphRunContext[State])-> get_current_time_node | tasks_manager_node | mail_manager_node | google_image_search_node | list_tools_node | planning_notes_editor_node | query_notes_editor_node | calendar_manager_node | End:
                plan= ctx.state.plan
                
                #get the manager tool to use
                ctx.state.route=plan.manager_tool
                if ctx.state.route=='Get_current_time':
                    return get_current_time_node()
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
                elif ctx.state.route=='Calendar Manager':
                    return calendar_manager_node()
                else:
                    ctx.state.plan={}
                    ctx.state.eval_messages_dict={}
                    return End(ctx.state)
                    


        class google_image_search_node(BaseNode[State]):
            async def run(self,ctx: GraphRunContext[State])->eval_node:
                def get_image_url(query:str):
                    """Search for images using Google Custom Search API
                    args: query
                    return: image url
                    """
                    # Define the API endpoint for Google Custom Search
                    url = "https://www.googleapis.com/customsearch/v1"
                    

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
                        return image_url
                    else:
                        return 'no image found'
                
                class Images(BaseModel):
                    image_url:str = Field(description='the url of the image')
                    image_title:str = Field(description='the title of the image')
                
                class image_url_shema(BaseModel):
                    images:List[Images] = Field(description='the list of images')

                agent=Agent(llms['pydantic_llm'],output_type=image_url_shema,tools=[get_image_url], instructions=f'based on the query and previous node messages, get the image urls')
                response=agent.run_sync(f'query:{ctx.state.plan.task}, previous_node_messages:{ctx.state.node_messages_list}')
                images=[]
                for image in response.output.images:
                    images.append({'image_title':image.image_title, 'image_url':image.image_url})

                ctx.state.node_messages_list.append({ctx.state.plan.manager_tool:{ctx.state.plan.action:images}})
                return eval_node()
                
        @dataclass
        class planning_notes_editor_node(BaseNode[State]):
            llm=llms['pydantic_llm']
            tool_functions=self.tool_functions
            async def run(self,ctx: GraphRunContext[State])->eval_node:
                class planning_improve_shema(BaseModel):
                    planning_improvement: str = Field(description='the planning improvement notes')
                agent=Agent(self.llm,output_type=planning_improve_shema, instructions=f'based on the dict of tools and the prompt, and the previous planning notes (if any), create a notes to improve the planning or use of a tool for the planner node')
                response=agent.run_sync(f'prompt:{ctx.state.query}, tool_functions:{self.tool_functions}, previous_planning_notes:{ctx.state.planning_notes if ctx.state.planning_notes else "no previous planning notes"}')
                ctx.state.planning_notes=response.output.planning_improvement
                if ctx.state.node_messages_dict.get(ctx.state.plan.manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool][ctx.state.plan.action]=response.output.planning_improvement
                else:
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool]={ctx.state.plan.action:response.output.planning_improvement}
                ctx.state.node_messages_list.append({ctx.state.plan.manager_tool:{ctx.state.plan.action:response.output.planning_improvement}})
                return eval_node()
        
        @dataclass
        class query_notes_editor_node(BaseNode[State]):
            llm=llms['pydantic_llm']
            tool_functions=self.tool_functions
            async def run(self,ctx: GraphRunContext[State])->eval_node:
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
                if ctx.state.node_messages_dict.get(ctx.state.plan.manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool][ctx.state.plan.action]=response.output.query_notes
                else:
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool]={ctx.state.plan.action:{'query_notes':response.output.query_notes}}
                ctx.state.node_messages_list.append({ctx.state.plan.manager_tool:{ctx.state.plan.action:{'query_notes':response.output.query_notes}}})

                return eval_node()
        @dataclass
        class calendar_manager_node(BaseNode[State]):
            calendar_agent=self.calendar_agent
            async def run(self,ctx: GraphRunContext[State])->eval_node:
                response=self.calendar_agent.chat(ctx.state.plan.task)
                # return response
                if ctx.state.node_messages_dict.get(ctx.state.plan.manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool][ctx.state.plan.action]=response
                else:
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool]={ctx.state.plan.action:response}
                ctx.state.node_messages_list.append({ctx.state.plan.manager_tool:{ctx.state.plan.action:response}})
                return eval_node()

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
            async def run(self,ctx: GraphRunContext[State])->eval_node:
                response=self.tasks_agent.chat(ctx.state.plan.task+ 'if there is an error, explain it in detail')
                # return response
                if ctx.state.node_messages_dict.get(ctx.state.plan.manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool][ctx.state.plan.action]=response
                else:
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool]={ctx.state.plan.action:response}
                ctx.state.node_messages_list.append({ctx.state.plan.manager_tool:{ctx.state.plan.action:response}})
                return eval_node()




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
            async def run(self,ctx: GraphRunContext[State])->eval_node:
                
                response=self.mail_agent.chat(ctx.state.plan.task)
                #save the inbox in the state for future use
                if ctx.state.plan.action=='GMAIL_FETCH_EMAILS':
                    try:
                        inbox=[]
                        for i in response['data']['messages']:
                            mail={'message_id':i.get('messageId'),'thread_id':i.get('threadId'),'subject':i.get('subject'),'sender':i.get('sender'),'date':i.get('messageTimestamp'),'snippet':i.get('preview'), 'messageText':i.get('messageText')}
                            inbox.append(mail)
                        ctx.state.mail_inbox=inbox
                        if ctx.state.node_messages_dict.get(ctx.state.plan.manager_tool):
                            ctx.state.node_messages_dict[ctx.state.plan.manager_tool][ctx.state.plan.action]=inbox
                        else:
                            ctx.state.node_messages_dict[ctx.state.plan.manager_tool]={ctx.state.plan.action:inbox}
                        ctx.state.node_messages_list.append({ctx.state.plan.manager_tool:{ctx.state.plan.action:inbox}})
                    except:
                        if ctx.state.node_messages_dict.get(ctx.state.plan.manager_tool):
                            ctx.state.node_messages_dict[ctx.state.plan.manager_tool][ctx.state.plan.action]=response
                        else:
                            ctx.state.node_messages_dict[ctx.state.plan.manager_tool]={ctx.state.plan.action:response}
                        ctx.state.node_messages_list.append({ctx.state.plan.manager_tool:{ctx.state.plan.action:response}})
                    return eval_node()
                else:
                    # return response
                    if ctx.state.node_messages_dict.get(ctx.state.plan.manager_tool):
                        ctx.state.node_messages_dict[ctx.state.plan.manager_tool][ctx.state.plan.action]=response
                    else:
                        ctx.state.node_messages_dict[ctx.state.plan.manager_tool]={ctx.state.plan.action:response}
                    ctx.state.node_messages_list.append({ctx.state.plan.manager_tool:{ctx.state.plan.action:response}})
                return eval_node()



        
        class get_current_time_node(BaseNode[State]):
            """
            Use this tool to get the current time.
            Returns:
                str: The current time in a formatted string
            """
            async def run(self,ctx: GraphRunContext[State])->eval_node:
                if ctx.state.node_messages_dict.get(ctx.state.plan.manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool][ctx.state.plan.action]=f"The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                else:
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool]={ctx.state.plan.action:f"The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                ctx.state.node_messages_list.append({ctx.state.plan.manager_tool:{ctx.state.plan.action:f"The current time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}})
                return eval_node()
            
        @dataclass
        class list_tools_node(BaseNode[State]):
            tools=self.tool_functions
            async def run(self,ctx: GraphRunContext[State])->eval_node:
                if ctx.state.node_messages_dict.get(ctx.state.plan.manager_tool):
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool][ctx.state.plan.action]=self.tools
                else:
                    ctx.state.node_messages_dict[ctx.state.plan.manager_tool]={ctx.state.plan.action:self.tools}
                ctx.state.node_messages_list.append({ctx.state.plan.manager_tool:{ctx.state.plan.action:self.tools}})
                return eval_node()


        @dataclass
        class eval_node(BaseNode[State]):
            llm=llms['pydantic_llm']
            async def run(self,ctx: GraphRunContext[State])->Agent_node:
                class eval_shema(BaseModel):
                    eval_status: str = Field(description='the eval status, success, failed')
                    eval_messages: str = Field(description='the reason for the eval status, if the eval status is failed, explain it in detail')
                agent=Agent(self.llm,output_type=eval_shema, instructions=f'based on the task, query and the node message return the eval status and the eval messages on the task')
                response=agent.run_sync(f'task:{ctx.state.plan.task}, query:{ctx.state.query}, node_message:{ctx.state.node_messages_list[-1]}')
                ctx.state.eval_messages_dict=response.output.eval_messages
                if response.output.eval_status=='failed':
                    ctx.state.n_retries+=1
                    return Agent_node()
                else:
                    ctx.state.n_retries=0
                    return Agent_node()


        self.graph=Graph(nodes=[Agent_node, router_node, google_image_search_node, tasks_manager_node, mail_manager_node, get_current_time_node, list_tools_node, planning_notes_editor_node, query_notes_editor_node, calendar_manager_node, eval_node])
        self.state=State(node_messages_dict={}, node_messages_list=[], eval_messages_dict={}, query='', plan=[], route='', n_retries=0, planning_notes='', query_notes={}, mail_inbox=[])
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
        self.state=State(node_messages_dict={}, node_messages_list=[], eval_messages_dict={}, query='', plan=[], route='', n_retries=0, planning_notes='', query_notes={}, mail_inbox=[])
        return 'agent reset'