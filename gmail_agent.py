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
from dotenv import load_dotenv 

import os.path
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.message import EmailMessage

class State(TypedDict):
    """
    A dictionnary representing the state of the agent.
    """
    messages: Annotated[list, add_messages]
    inbox: dict
    current_draft: dict
    drafts: dict




if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json")
try:
    # create gmail api client
    service = build("gmail", "v1", credentials=creds)

except HttpError as error:
    print(f"An error occurred: {error}")




@tool
def get_new_mail(maxResults: int ,tool_call_id: Annotated[str, InjectedToolCallId])-> Command:

    """
    Tool to get the latest emails
    args: maxResults: int - the number of emails to return
    return: a dict structured as such {email_id:{email content}}
    """
    ids=service.users().messages().list(userId='me', includeSpamTrash=False , maxResults=maxResults).execute().get('messages',[])
    messages={}
    errors=[]
    for id in ids:
        mdata=service.users().messages().get(userId="me", id=id["id"], format='full' ).execute()
        id=mdata.get('id')
        thread=mdata.get('threadId')
        label=mdata.get('labelIds')
        headers={h.get('name'):h.get('value') for h in mdata.get('payload').get('headers')}
        sender=headers.get('From')
        date=headers.get('Date')
        receiver=headers.get('To')
        subject=headers.get('Subject')
        snippet=mdata.get('snippet')
        try:
            body=base64.urlsafe_b64decode(mdata['payload']['parts'][0]['body']['data'].encode("utf-8")).decode("utf-8")
        except:
            try:

                body=base64.urlsafe_b64decode(mdata['payload']['parts'][0]['parts'][0]['body']['data'].encode("utf-8")).decode("utf-8")
            except:
                try: 

                    body=base64.urlsafe_b64decode(mdata['payload']['body']['data'].encode("utf-8")).decode("utf-8")
                except:
                    errors.append(mdata)
        messages[id]={'From':sender,
                    'To':receiver,
                    'Date':date,
                    'label':label,
                    'subject':subject,
                    'Snippet':snippet,
                    'email_id':id,
                    'thread':thread,
                    'body':body
                    }  
    return Command(update={'inbox':messages,
                'messages': [ToolMessage(messages,tool_call_id=tool_call_id)]})

@tool
def create_email(receiver: str, content: str, email_subject:str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    Tool to create a draft of an email
    to create an email you have to make a draft using this tool
    agrs: receiver - the email adress of the person to send the email to
          content - the body of the email
          email_subject - the subject of the email
    """
 
    message = EmailMessage()

    message.set_content(content)

    message["To"] = receiver
    message["From"] = "me"
    message["Subject"] = email_subject

    # encoded message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    create_message = {"raw": encoded_message}
    return Command(update={'current_draft':create_message,
            'messages': [ToolMessage(f'display this as is: {message}, always show the email address the email is sent to and ask if it should be sent.',tool_call_id=tool_call_id)]})

@tool
def verify_draft(state: Annotated[dict, InjectedState],tool_call_id: Annotated[str, InjectedToolCallId]):
    """tool to verify the current draft
    
    args: none
    """
    create_message=state['current_draft']
    decoded=base64.urlsafe_b64decode(create_message.get('message').get('raw').encode("utf-8")).decode("utf-8")
    return Command(update={'messages':[ToolMessage(f'display this draft: {decoded} and ask if it should be sent.',tool_call_id=tool_call_id)]})

@tool
def send_email(state: Annotated[dict, InjectedState],tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    Tool to send the current draft
    args: - none
    """
    try:
        create_message=state['current_draft']
        # pylint: disable=E1101
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        return Command(update={'messages': [ToolMessage(f'email sent! ',tool_call_id=tool_call_id)]})
    except:
        return Command(update={'messages': [ToolMessage(f'failed to send draft ',tool_call_id=tool_call_id)]})

@tool
def show_inbox(state: Annotated[dict, InjectedState],tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    tool to get the info and show the emails in the inbox do not use this tool to collect new mail
    args: none
    returns: the emails in the inbox
    """
     
    try:
        return state['inbox']
    except: 
        ids=service.users().messages().list(userId='me', includeSpamTrash=False, maxResults=10 ).execute().get('messages',[])
        messages={}
        errors=[]
        for id in ids:
            mdata=service.users().messages().get(userId="me", id=id["id"], format='full' ).execute()
            id=mdata.get('id')
            thread=mdata.get('threadId')
            label=mdata.get('labelIds')
            headers={h.get('name'):h.get('value') for h in mdata.get('payload').get('headers')}
            sender=headers.get('From')
            date=headers.get('Date')
            receiver=headers.get('To')
            subject=headers.get('Subject')
            snippet=mdata.get('snippet')
            try:
                body=base64.urlsafe_b64decode(mdata['payload']['parts'][0]['body']['data'].encode("utf-8")).decode("utf-8")
            except:
                try:

                    body=base64.urlsafe_b64decode(mdata['payload']['parts'][0]['parts'][0]['body']['data'].encode("utf-8")).decode("utf-8")
                except:
                    try: 

                        body=base64.urlsafe_b64decode(mdata['payload']['body']['data'].encode("utf-8")).decode("utf-8")
                    except:
                        errors.append(mdata)
            messages[id]={'From':sender,
                        'To':receiver,
                        'Date':date,
                        'label':label,
                        'subject':subject,
                        'Snippet':snippet,
                        'email_id':id,
                        'thread':thread,
                        'body':body
                        }   
            return Command(update={'inbox':messages,
                        'messages': [ToolMessage(messages,tool_call_id=tool_call_id)]})


@tool
def display_email(id: str, state: Annotated[dict, InjectedState],tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:

    """
    tool to display a specific email
    args: id - the id associated with the email to read
    returns: the body of the email
    """
    
    try:
        if id in state['inbox']:
            email=state['inbox'].get(str(id))
            return Command(update={'messages': [ToolMessage(email,tool_call_id=tool_call_id)]})
    except: 
        return Command(update={'messages': [ToolMessage(f'failed to get the email ',tool_call_id=tool_call_id)]})









class gmail_agent:
    def __init__(self,llm : any):
        self.agent=self._setup(llm)
        
    def _setup(self,llm):
        langgraph_tools=[get_new_mail,create_email,display_email,show_inbox,verify_draft,send_email]



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