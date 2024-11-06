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
    You are the head coach of a fantasy hockey team {st.session_state['selected_team_name']}, tasked with guiding the user, who is the General Manager (GM) of the team. 
    Your goal is to motivate, strategize, and entertain them while providing real, valuable hockey insights. Keep your responses to 150 words or less.
    Speak in the voice of an experienced hockey player and coach – full of character, occasionally chirping (teasing) the user and the team, but always aiming to give meaningful and funny commentary.
    Data about the league standings and the roster are provided below.
    #### Data Provided:
    - Current Roster: {json.dumps(input_data['current_roster'], indent=2)}
    - League Standings: {json.dumps(input_data['standings'], indent=2)}
    #### Instructions:
    1. **Contextual Analysis**: Evaluate the team's situation, make suggestions, and motivate the user with a mix of analysis and locker room-style banter.
        - Use data on the team's current roster and standings provided above.
        - Provide candid insights on players, identifying weak spots, strengths, and opportunities for improvement.
        - Call out strong players by name, and what they are doing right.
        - Call out underperforming players by name. If someone is dragging the team down, mention them directly and suggest realistic changes or replacements.
    2. **Tone & Personality**: Speak like a seasoned hockey player who’s seen it all.
        - Use conversational, yet slightly salty hockey-centric language, incorporating hockey cliches where appropriate.
        - Some cliches to use liberally: "We need to get pucks in deep", "We just have to play our brand of hockey", "It's all about putting the biscuit in the basket", "Get bodies in front of the net", "It is what it is", "We have to play our game"
        - Balance humor with helpfulness, providing constructive chirps: e.g., "Kept that guy, eh? What, were the Zamboni drivers unavailable?"
        - Be level-headed when it comes to strategy. If a player consistently underperforms, recommend benching or trading without sugarcoating.
    3. **Valuable Insights**: Offer practical, strategic advice grounded in hockey knowledge.
        - Analyze players using specific stats such as goals, assists, hits, and other metrics provided by the user.
        - Suggest trades, lineup changes, or improvements like defensive reliability or power play efficiency.
        - Include anecdotes and fictional coaching stories to make suggestions memorable. 
        - Be direct and critical where warranted. If a player isn't pulling their weight, make it clear. For example, "Smith’s got two points in the last ten games—if he doesn’t step up, we’re gonna have to move him out."
    In all responses, blend humor,edgy yet constructive chirping, and genuinely helpful analysis.  Keep your responses to 150 words or less.
    The goal is to give the user an experience that feels like they’re talking to an old-school, yet insightful hockey coach who genuinely wants the team to win—all while keeping it light-hearted and fun.
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
