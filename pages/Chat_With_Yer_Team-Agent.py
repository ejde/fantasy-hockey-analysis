import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
import json
from fantraxapi import FantraxAPI
import utils
import os
from langchain.agents import create_structured_chat_agent
from langchain_core.tools import StructuredTool
from langchain import hub
from langchain_community.tools import TavilySearchResults
from langchain.agents import AgentExecutor
import ollama
from langchain_ollama import OllamaLLM

st.title("💬 Chat With Yer Team - Agent Style")

if not st.session_state.get('logged_in'):
    st.info("Please log in using the sidebar on the main page to proceed.")
    st.page_link("Home.py", label="Go Home")
    st.stop()

if 'selected_team_name' not in st.session_state or 'roster' not in st.session_state:
    st.info("Please wait for the login process on the Home page to complete")
    st.stop()

# Initialize Streamlit session state for messages
if 'messages' not in st.session_state:
    st.session_state.messages = []

os.environ['TAVILY_API_KEY'] = st.secrets.get('tavily_key')

# Langsmith tracking
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_ENDPOINT'] = "https://api.smith.langchain.com"
os.environ['LANGCHAIN_API_KEY'] = st.secrets.get('langsmith_key')
os.environ['LANGCHAIN_PROJECT'] = st.secrets.get('langsmith_project')

api = FantraxAPI(st.session_state['league_id'], session=st.session_state['session'])
standings_df = utils.fetch_standings(api)
roster_df = utils.fetch_team_roster(api, st.session_state['selected_team_id'])
input_data = {
    "current_roster": json.loads(roster_df.to_json(orient="records")),
    "standings": json.loads(standings_df.to_json(orient="records"))
}

def fetch_league_standings():
    standings = utils.fetch_standings(api)
    standings['is_my_team'] = standings['team'].apply(lambda x: str(x).lower() == st.session_state['selected_team_name'].lower())
    return standings

def fetch_user_team_roster():
    return utils.fetch_team_roster(api, st.session_state['selected_team_id'])

def fetch_opposing_team_roster(team_name):
    tl = [team for team in api.teams if team.name == team_name]
    if not tl:
        return None
    return utils.fetch_team_roster(api, tl[0])

def fetch_user_team_name():
    return st.session_state['selected_team_name']

def fetch_current_free_agents(position: str):
    return utils.fetch_free_agents(api, position)

def search_player_news(query: str):
    search_tool = TavilySearchResults(
        max_results=5,
        search_params={
            "time_range": "1d",
            "sort_by": "date"
        }
    )
    return search_tool.invoke({"query": query + " Performance in last game"})

def search_game_scores(query: str):
    search_tool = TavilySearchResults(
        max_results=5,
        search_params={
            "time_range": "1d",
            "sort_by": "date"
        }
    )
    return search_tool.invoke({"query": query})

tools = [
    StructuredTool.from_function(search_player_news, name="Search Player News", description="Search for recent player information and performance, pass a string whose value is the player name"),
    StructuredTool.from_function(fetch_league_standings, name="Fetch League Standings", description="Fetch the league standings, returns a dataframe with columns 'team', 'rank', and other stats. The 'is_my_team' column is a boolean indicating if the team is the user's team"),
    StructuredTool.from_function(fetch_user_team_roster, name="Fetch User's Team Roster", description="Get the roster of the user's team"),
    StructuredTool.from_function(fetch_user_team_name, name="Fetch User's Team Name", description="Get the name of the user's team"),
    StructuredTool.from_function(fetch_current_free_agents, name="Fetch Free Agents", description="Get a list of top available free agents for a given position, pass a string whose value is one of 'F', 'D' or 'G'"),
    StructuredTool.from_function(fetch_opposing_team_roster, name="Fetch Opposing Team Roster", description="Get the roster of an opposing team for potential trades, pass a string whose value is an opposing team name"),
    StructuredTool.from_function(search_game_scores, name="Search Game Scores", description="Search for recent game scores of a given team, pass a string whose value is the team name")
]

# Properly format tools and tool_names for inclusion in the prompt
chat_prompt_template = hub.pull("danglesnipecelly/fantasy-hockey-coach:e8792e65")
chat_prompt = chat_prompt_template

def get_llm():
    # Add model selection dropdown
    if st.session_state['league_id'] not in st.secrets.get("league_whitelist", []):
        model_choice = st.sidebar.selectbox(
            "Select LLM Provider:",
            ["OpenAI", "Groq", "Ollama"],
            help="Choose your preferred language model provider"
        )
        
        if model_choice == "Groq":
            groq_key = st.sidebar.text_input("Enter your Groq API key:", type="password")
            if groq_key:
                return ChatGroq(api_key=groq_key, model="llama3-8b-8192")
            
        elif model_choice == "Ollama":
            ollama_server = st.sidebar.text_input("Enter Ollama server URL:", value="http://localhost:11434")
            ollama_model = st.sidebar.text_input("Enter Ollama model name:", value="mistral")
            if ollama_server and ollama_model:
                client = ollama.Client(host=ollama_server)
                return OllamaLLM(client=client, model=ollama_model)
                
        else:  # OpenAI
            openai_key = st.sidebar.text_input("Enter your OpenAI API key:", type="password")
            model_name = st.sidebar.selectbox(
                "Select OpenAI Model:",
                ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                help="Choose your preferred OpenAI model"
            )
            if openai_key:
                return ChatOpenAI(openai_api_key=openai_key, model_name=model_name)
    else:
        return ChatGroq(api_key=st.secrets.get("groq_api_key"), model="llama3-8b-8192")
    
    st.warning("Please provide the required API credentials to continue.")
    st.stop()

# Initialize LLM
if 'llm' not in st.session_state:
    st.session_state.llm = get_llm()
llm = st.session_state.llm

agent = create_structured_chat_agent(llm=llm, tools=tools, prompt=chat_prompt)

# Wrap the agent in an AgentExecutor to manage interaction flow
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=False, handle_parsing_errors=True)

with st.sidebar:
    if st.button("Clear Chat Window", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

    if st.session_state['league_id'] not in st.secrets.get("league_whitelist", []):
        if st.sidebar.button("Change LLM Settings"):
            del st.session_state.llm
            st.rerun()

for message in st.session_state.messages:
    if message['role'] in ['user', 'ai']:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

if prompt := st.chat_input("Are you ready? Good, cuz yer goin!"):
    prompt = prompt.replace('\n', ' \n')
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message("ai"):
        message_placeholder = st.empty()
        message_placeholder.markdown("S'YeahSo...")
        response = ''
        try:
            response = agent_executor.invoke({"input": prompt, "chat_history": st.session_state.messages})
            if isinstance(response, dict) and 'output' in response:
                response_text = response['output']
            else:
                response_text = response
            message_placeholder.markdown(response_text)
            st.session_state.messages.append({'role': 'ai', 'content': response_text})
        except Exception as e:
            st.exception(e)
