import streamlit as st
import google.generativeai as genai
import time
import random
import json
from fantraxapi import FantraxAPI
import utils

st.title("💬 Chat With Yer Team")

if not st.session_state.get('logged_in'):
    st.info("Please log in using the sidebar on the main page to proceed.") 
    st.page_link("pages/Home.py", label="Main Page")
    st.stop()

if not st.session_state["selected_team_name"]:
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

sys_instr = f"""
    You are the head coach of a fantasy hockey team {st.session_state['selected_team_name']}, tasked with guiding the user, the GM, with humor, strategy, and insights. 
    You must keep responses under 75 words. 
    #### Data Provided:
    - Current Roster: {json.dumps(input_data['current_roster'], indent=2)}
    - League Standings: {json.dumps(input_data['standings'], indent=2)}
    #### Tone:
    - Speak like a seasoned hockey player and coach—gritty, humorous, occasionally chirping the user and team with appropriate hockey cliches but always constructive.
    - Answer questions directly using the roster and standings already given.
    - Here is a list of cliches to choose from {utils.hockey_cliches}
    #### Contextual Analysis:
    - Analyze the team's current situation based on the provided roster and standings, using specific stats to highlight strengths, weaknesses, and opportunities.
    - Call out strong performers and critique underperformers by name, suggesting realistic actions.
    #### Valuable Advice:
    - Offer practical, strategic advice: trades, lineup changes, or improvements like power play efficiency.
    The goal: Make the GM feel like they're talking to an old-school, yet insightful coach who wants the team to win, keeping it light-hearted and fun.
    """

if st.session_state['league_id'] in st.secrets.get("league_whitelist", []):
    llm_api_key = st.secrets.get("gemini_key")
else:
    llm_api_key = st.text_input("Enter your Google Generative AI API key:", type="password")     

# Initialize the Generative Model
genai.configure(api_key=llm_api_key)
model = genai.GenerativeModel("gemini-1.5-flash-8b", system_instruction=sys_instr)
chat = model.start_chat(history = st.session_state.messages)

with st.sidebar:
    if st.button("Clear Chat Window", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

for message in chat.history:
    if message.role == 'model':
        role = "coach"
    elif message.role == 'user':
        role = "GM"
    else:
        role = message.role

    with st.chat_message(role):
        if role != 'system':
            st.markdown(message.parts[0].text)

if prompt := st.chat_input("Are you ready? Good, cuz yer goin!"):
    prompt = prompt.replace('\n', ' \n')
    with st.chat_message("GM"):
        st.markdown(prompt)
    with st.chat_message("coach"):
        message_placeholder = st.empty()
        message_placeholder.markdown("S'YeahSo...")
        try:
            full_response = ""
            for chunk in chat.send_message(prompt, stream=True):
                word_count = 0
                random_int = random.randint(5,10)
                for word in chunk.text:
                    full_response+=word
                    word_count+=1
                    if word_count == random_int:
                        time.sleep(0.05)
                        message_placeholder.markdown(full_response + "_")
                        word_count = 0
                        random_int = random.randint(5,10)
            message_placeholder.markdown(full_response)
        except genai.types.generation_types.BlockedPromptException as e:
            st.exception(e)
        except Exception as e:
            st.exception(e)
        st.session_state.messages = chat.history
