import streamlit as st
from langchain_openai import ChatOpenAI
import json
from fantraxapi import FantraxAPI
import utils
import os
from langchain.agents import create_structured_chat_agent
from langchain_core.tools import StructuredTool
from langchain import hub
from langchain_community.tools import TavilySearchResults


st.title("💬 Chat With Yer Team - Agent Style")
st.text("This is a test")

os.environ['TAVILY_API_KEY'] = st.secrets.get('tavily_key')

# Langsmith tracking
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_ENDPOINT'] = "https://api.smith.langchain.com"
os.environ['LANGCHAIN_API_KEY'] = st.secrets.get('langsmith_key')
os.environ['LANGCHAIN_PROJECT'] = st.secrets.get('langsmith_project')


if not st.session_state.get('logged_in'):
    st.info("Please log in using the sidebar on the main page to proceed.") 
    st.page_link("Home.py", label="Go Home")
    st.stop()

if 'selected_team_name' not in st.session_state and 'roster' not in st.session_state:
    st.info("Please wait for the login process on the Home page to complete") 
    st.stop()

# Initialize Streamlit session state for messages
if 'messages' not in st.session_state:
    st.session_state.messages = []
    
api = FantraxAPI(st.session_state['league_id'], session=st.session_state['session'])
standings_df = utils.fetch_standings(api)
roster_df = utils.fetch_team_roster(api, st.session_state['selected_team_id'])
input_data = {
    "current_roster": json.loads(roster_df.to_json(orient="records")),
    "standings": json.loads(standings_df.to_json(orient="records"))
}

def featch_league_standings():
    return utils.fetch_standings(api)

def fetch_user_team_roster():
    return utils.fetch_team_roster(api, st.session_state['selected_team_id'])
    
def fetch_opposing_team_roster(team_name):
    tl = [team for team in api.teams if team.name == team_name]
    if not tl:
        return None

    return utils.fetch_team_roster(api, tl[0])

def fetch_user_team_name():
    return st.session_state['selected_team_name']

def fetch_current_free_agents(position):
    return utils.fetch_free_agents(api, position)

def search_player_news(query: str):
    search_tool = TavilySearchResults()
    return search_tool.invoke({"query": query + " Latest News"})

def search_game_scores(query: str):
    search_tool = TavilySearchResults()
    return search_tool.invoke({"query": query})

tools = [
    StructuredTool.from_function(search_player_news, name="Search Player Info", description="Search for recent player information and performance"),
    #StructuredTool.from_function(utils.search_roster_player_news, name="Search Roster Player News", description="Search for recent roster player performance and analysis"),
    #StructuredTool.from_function(utils.fetch_roster_news, name="Fetch Roster News", description="Fetch latest news for each player on the roster of the user's team"),

    StructuredTool.from_function(featch_league_standings, name="Fetch League Standings", description="Fetch the league standings"),    

    StructuredTool.from_function(fetch_user_team_roster, name="Fetch User's Team Roster", description="Get the roster of the user's team"),
    StructuredTool.from_function(fetch_user_team_name, name="Fetch User's Team Name", description="Get the name of the user's team"),

    StructuredTool.from_function(fetch_current_free_agents, name="Fetch Free Agents", description="Get a list of top available free agents of a given position, 'F', 'D' or 'G'"),
    StructuredTool.from_function(fetch_opposing_team_roster, name="Fetch Opposing Team Roster", description="Get the roster of an opposing team for potential trades"),

    StructuredTool.from_function(search_game_scores, name="Search Game Scores", description="Search for recent game scores of a given team")
]

if st.session_state['league_id'] in st.secrets.get("league_whitelist", []):
    llm_api_key = st.secrets.get("openai_key")
else:
    llm_api_key = st.text_input("Enter your OpenAI API key:", type="password")     

llm = llm = ChatOpenAI(openai_api_key=llm_api_key, model_name="gpt-4")
chat_prompt = hub.pull("danglesnipecelly/fantasy-hockey-coach")
agent = create_structured_chat_agent(llm=llm, tools=tools, prompt=chat_prompt)

# Wrap the agent in an AgentExecutor to manage interaction flow
from langchain.agents import AgentExecutor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=False)

with st.sidebar:
    if st.button("Clear Chat Window", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

for message in st.session_state.messages:
     if message['role'] in ['user', 'ai']:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

if prompt := st.chat_input("Are you ready? Good, cuz yer goin!"):
    prompt = prompt.replace('\n', ' \n')
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("ai"):
        message_placeholder = st.empty()
        message_placeholder.markdown("S'YeahSo...")
        response = ''
        try:
            response = agent_executor.invoke({"input": prompt, "chat_history": st.session_state.messages})
            message_placeholder.markdown(response['output'])
        except Exception as e:
            st.exception(e)
        
        st.session_state.messages.append({'role': 'user', 'content': prompt})
        st.session_state.messages.append({'role': 'ai', 'content': response})
