from __future__ import annotations
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from google_agent import Google_agent
from dotenv import load_dotenv 
import gradio as gr
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai import Agent, BinaryContent, RunContext
from composio_langgraph import Action, ComposioToolSet, App
from pydantic_ai.messages import ModelMessage
from dataclasses import dataclass
from pydantic import Field
load_dotenv()
import logfire
logfire.configure(token=os.getenv('logfire_token'))
logfire.instrument_pydantic_ai()
#get the api keys from the environment variables
google_api_key=os.getenv('google_api_key')
pse=os.getenv('pse')
openai_api_key=os.getenv('openai_api_key')
composio_api_key=os.getenv('composio_api_key')

api_keys={
    'google_api_key':google_api_key,
    'pse':pse,
    'openai_api_key':openai_api_key,
    'composio_key':composio_api_key
}

llms={'pydantic_llm':GoogleModel('gemini-2.0-flash', provider=GoogleProvider(api_key=api_keys['google_api_key'])),
    'langchain_llm':ChatGoogleGenerativeAI(google_api_key=api_keys['google_api_key'], model='gemini-2.0-flash', temperature=0.3),
    'openai_llm':ChatOpenAI(model='gpt-4.1-mini', temperature=0.3)}
toolset=ComposioToolSet(api_key=api_keys['composio_key'])


#message history class for the demo agent
@dataclass
class Message_history:
    messages:list[ModelMessage]
@dataclass
class Deps:
    node_messages_dict:dict
    node_messages_list:list

#message history for the demo agent
messages=Message_history(messages=[])
#state for the demo agent

#google agent class for the google agent
google_agent=Google_agent(llms=llms, api_keys=api_keys, toolset=toolset)

#adding planning notes to the agent
google_agent.state.planning_notes='task manager:when the user asks for a list of tasks, you first need to get the list of tasklists and then get the list of tasks from the chosen tasklist\
    unless the node messages already contain a list of tasklists, so generate a plan that includes getting the list of tasklists and then getting the list of tasks from the chosen tasklist\
    '
async def google_agent_tool(ctx:RunContext[Deps], query:str):
    """
            ## Purpose
            This function provides an interface to interact with a Google agent that can perform multiple Google-related tasks simultaneously.
            ## Capabilities
            The agent can:
            - Search for images
            - Manage user emails
            - Manage Google tasks
            - Manage Google Maps
            - get contact list
            - List available tools
            - Improve planning based on user feedback with planning notes
            - Improve its query based on user feedback with query notes

            ## Parameters
            - `query` (str): A complete query string describing the desired Google agent actions
            - The query should include all necessary details for the requested operations
            - Multiple actions can be specified in a single query

            ## Returns
            - `str`: The agent's response to the query

            ## Important Notes
            - The agent can process multiple actions in a single query
            - User feedback can be provided to help improve the agent's planning and query
            - All Google-related operations should be included in the query string

            """
    res=google_agent.chat(query)
    ctx.deps.node_messages_dict=res.node_messages_dict
    ctx.deps.node_messages_list=res.node_messages_list
    return res.node_messages_list
async def reset_agent(ctx:RunContext[Deps]):
    """ use this tool to reset the agent in case you are stuck in an error or a loop or to start a new conversation
        the agent will be reset and the conversation will be cleared
    """
    google_agent.reset()
    messages.messages = []
    ctx.deps.node_messages_dict={}
    return "agent reset"

async def short_term_memory_tool(ctx:RunContext[Deps],data_to_retrieve:str):

    """
    this tool is used to retrieve information from the previous tool calls
    use this tool to answer questions by retrieving information from previous tool calls
    use the manager_tool and action to get the information from the previous tool calls:
    
    
    args:
    data_to_retrieve:str - the data to retrieve from the previous tool calls
    """
    async def retrieval(manager_tool:str, action:str):
        """
        this tool is used to retrieve information from the previous tool calls
        use this tool to answer questions by retrieving information from previous tool calls
        use the manager_tool and action to get the information from the previous tool calls:
        args:
        manager_tool:str - the manager tool that applies to the question from the user from the managers and actions dictionary
        action:str - the action that applies to the question from the user from the managers and actions dictionary
        """
        try:
            return ctx.deps.node_messages_dict.get(manager_tool)[action]
        except:
            return ctx.deps.node_messages_dict


    agent=Agent(model=llms['pydantic_llm'], tools=[retrieval], instructions='you are a memory retrieval assistant that can retrieve information from previous node messages dictionary using the manager tool and action')

    response=agent.run_sync(data_to_retrieve + f'list of previous calls: {ctx.deps.node_messages_list}, managers and actions:{google_agent.tool_functions}')
    
    return response.output

    

deps=Deps(node_messages_dict={},node_messages_list=[])
agent=Agent(model=llms['pydantic_llm'], tools=[google_agent_tool, reset_agent, short_term_memory_tool], instructions='you are a helpful assistant that can answer any query related to google services using the tools provided\
            , howver not all queries require the use of the tools, you can use the short_term_memory_tool to answer questions by retrieving information from the previous tool calls messages')
# initialize the message history

def get_mail_inbox():
    """Get the current mail inbox from the agent state"""
    return google_agent.state.mail_inbox if google_agent.state.mail_inbox else [] 

def chatbot(input, history, audio=None):
    """Handle chat interactions with text and/or audio"""
    
    if audio is not None:
        # Handle audio input
        with open(audio, 'rb') as f:
            audio_data = f.read()
        
        if input and input.strip():
            # Both text and audio provided
            response = agent.run_sync([input, BinaryContent(data=audio_data, media_type='audio/wav')], message_history=messages.messages, deps=deps)
        else:
            # Only audio provided
            response = agent.run_sync([BinaryContent(data=audio_data, media_type='audio/wav')], message_history=messages.messages, deps=deps)
    else:
        # Only text input
        response = agent.run_sync(input, message_history=messages.messages, deps=deps)
    
    messages.messages = response.all_messages()
    return response.output

def get_email_list():
    """Get formatted email list for dropdown"""
    inbox = get_mail_inbox()
    if not inbox:
        return []
    
    email_options = []
    for i, email in enumerate(inbox):
        # Create a readable label for each email
        subject = email.get('subject', 'No Subject')
        sender = email.get('sender', 'Unknown Sender')
        date = email.get('date', 'No Date')
        
        # Truncate subject if too long
        if len(subject) > 50:
            subject = subject[:50] + "..."
            
        label = f"{subject} | From: {sender} | {date}"
        email_options.append(label)
    
    return email_options

def render_email_html(selected_email_index):
    """Render the selected email as HTML"""
    inbox = get_mail_inbox()
    
    if not inbox or selected_email_index is None:
        return "<p>No email selected or inbox is empty.</p>"
    
    try:
        # Get the email by index
        email_idx = int(selected_email_index)
        if email_idx >= len(inbox):
            return "<p>Invalid email selection.</p>"
            
        email = inbox[email_idx]
        
        # Extract email information using correct field names
        subject = email.get('subject', 'No Subject')
        sender = email.get('sender', 'Unknown Sender')
        date = email.get('date', 'No Date')
        message_text = email.get('messageText', 'No content available')
        message_id = email.get('message_id', 'N/A')
        snippet = email.get('snippet', 'No preview available')
        
        # Format the date if it's in ISO format
        try:
            from datetime import datetime
            if 'T' in str(date) and 'Z' in str(date):
                dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%B %d, %Y at %I:%M %p')
            else:
                formatted_date = str(date)
        except:
            formatted_date = str(date)
        
        # Create HTML structure with better styling
        html_content = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 10px;">
            <div style="background-color: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="border-bottom: 2px solid #e0e0e0; padding-bottom: 15px; margin-bottom: 20px;">
                    <h2 style="color: #000000 !important; margin: 0 0 10px 0; font-size: 24px; font-weight: 600;">{subject}</h2>
                    <div style="color: #222222 !important; font-size: 14px; line-height: 1.4;">
                        <p style="margin: 5px 0; color: #000000 !important;"><strong style="color: #000000 !important;">From:</strong> {sender}</p>
                        <p style="margin: 5px 0; color: #000000 !important;"><strong style="color: #000000 !important;">Date:</strong> {formatted_date}</p>
                        <p style="margin: 5px 0; color: #000000 !important;"><strong style="color: #000000 !important;">Message ID:</strong> <code style="background-color: #ecf0f1; padding: 2px 4px; border-radius: 3px; font-size: 12px; color: #000000 !important;">{message_id}</code></p>
                    </div>
                </div>
                
                {f'<div style="background-color: #e8f5e8; border-left: 4px solid #27ae60; padding: 10px; margin-bottom: 20px; border-radius: 4px;"><p style="margin: 0; color: #000000 !important; font-style: italic; font-weight: 500;"><strong style="color: #000000 !important;">Preview:</strong> {snippet}</p></div>' if snippet and snippet != 'No preview available' else ''}
                
                <div style="line-height: 1.6; color: #000000 !important; background-color: white; padding: 15px; border-radius: 6px; border: 1px solid #ecf0f1; word-wrap: break-word; overflow-wrap: break-word; word-break: break-word;">
                    <h3 style="color: #000000 !important; margin-top: 0; margin-bottom: 15px; font-size: 18px; font-weight: 600;">Email Content:</h3>
                    <div style="font-size: 14px; color: #000000 !important; line-height: 1.7; word-wrap: break-word; overflow-wrap: break-word; word-break: break-word; white-space: pre-wrap; max-width: 100%; overflow-x: auto;">
                        <style>
                            .email-content * {{
                                color: #000000 !important;
                                word-wrap: break-word !important;
                                overflow-wrap: break-word !important;
                                word-break: break-word !important;
                                max-width: 100% !important;
                            }}
                            .email-content a {{
                                color: #0066cc !important;
                                word-wrap: break-word !important;
                                overflow-wrap: break-word !important;
                                word-break: break-all !important;
                                text-decoration: underline !important;
                            }}
                            .email-content p, .email-content div, .email-content span {{
                                color: #000000 !important;
                                word-wrap: break-word !important;
                                overflow-wrap: break-word !important;
                                word-break: break-word !important;
                                max-width: 100% !important;
                            }}
                        </style>
                        <div class="email-content">
                            {message_text}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        return html_content
        
    except (ValueError, IndexError, TypeError) as e:
        return f"<div style='color: red; padding: 20px; font-family: Arial, sans-serif;'><p><strong>Error rendering email:</strong> {str(e)}</p></div>"

def refresh_email_list():
    """Refresh the email list and return updated options"""
    # First fetch fresh emails by calling the agent
    google_agent.chat("fetch 10 emails from inbox")
    return gr.update(choices=get_email_list(), value=None)

def on_email_select(selected_email, selected_index):
    """Handle email selection and return HTML content"""
    if selected_email is None:
        return "<p>No email selected.</p>"
    
    # Find the index of the selected email
    email_options = get_email_list()
    try:
        index = email_options.index(selected_email)
        return render_email_html(index)
    except (ValueError, IndexError):
        return "<p>Error loading selected email.</p>"
# Create the Gradio interface
with gr.Blocks(title="Google AI Agent - Email Viewer", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Google AI Agent - Email Viewer")
    gr.Markdown("Chat with the AI agent and view your emails with HTML rendering.")
    
    with gr.Row():
        with gr.Column(scale=1):
            # Chat interface
            gr.Markdown("## Chat Interface")
            # Chat history display
            chat_history = gr.Chatbot(label="Conversation")
            # Audio recording component
            audio_input = gr.Audio(
                sources=["microphone"],
                type="filepath",
                label="Record Audio (optional)",
                format="wav"
            )
            
            # Text input
            text_input = gr.Textbox(
                placeholder="Type your message here or record audio above...",
                label="Text Input",
                lines=2
            )
            
            # Send button
            send_btn = gr.Button("Send", variant="primary")
            
            # Clear button
            clear_btn = gr.Button("Clear Chat", variant="secondary")
            
        with gr.Column(scale=1):
            # Email viewer interface
            gr.Markdown("## Email Viewer")
            
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Inbox", variant="secondary")
            
            email_dropdown = gr.Dropdown(
                choices=get_email_list(),
                label="Select Email",
                interactive=True
            )
            
            email_html_viewer = gr.HTML(
                value="<p>Select an email from the dropdown above to view its content.</p>",
                label="Email Content"
            )
    
    # Helper function to handle chat submission
    def handle_chat_submit(text, audio, history):
        """Handle chat submission with text and/or audio"""
        if not text and not audio:
            return history, "", None, gr.update()
        
        # Add user message to history
        user_message = ""
        if text:
            user_message += text
        if audio:
            user_message += " [Audio message included]" if text else "[Audio message]"
        
        history.append([user_message, None])
        
        # Get bot response
        bot_response = chatbot(text, history, audio)
        history[-1][1] = bot_response
        
        # Refresh email dropdown in case emails were fetched
        updated_email_choices = get_email_list()
        
        return history, "", None, gr.update(choices=updated_email_choices, value=None)
    
    def clear_chat():
        """Clear chat history"""
        messages.messages = []
        return [], gr.update()
    
    # Event handlers
    send_btn.click(
        fn=handle_chat_submit,
        inputs=[text_input, audio_input, chat_history],
        outputs=[chat_history, text_input, audio_input, email_dropdown]
    )
    
    text_input.submit(
        fn=handle_chat_submit,
        inputs=[text_input, audio_input, chat_history],
        outputs=[chat_history, text_input, audio_input, email_dropdown]
    )
    
    clear_btn.click(
        fn=clear_chat,
        outputs=[chat_history, email_dropdown]
    )
    
    refresh_btn.click(
        fn=refresh_email_list,
        outputs=email_dropdown
    )
    
    email_dropdown.change(
        fn=on_email_select,
        inputs=[email_dropdown, email_dropdown],
        outputs=email_html_viewer
    )

if __name__ == "__main__":
    demo.launch()