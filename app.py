import streamlit as st

import pickle
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from requests import Session
from streamlit.runtime.scriptrunner import RerunException
import utils
import json
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage

st.set_page_config(page_title="Team Roster")
st.title("Fantrax Fantasy Hockey Analysis")

# *** SIDEBAR ***
if 'league_id' not in st.session_state:
    st.session_state['league_id'] = ''

league_id_input = st.sidebar.text_input("Enter League ID", value=st.session_state['league_id'])

if league_id_input != st.session_state['league_id']:
    st.session_state['league_id'] = league_id_input

if st.session_state['league_id']:
    st.sidebar.success(f"League ID: {st.session_state['league_id']}")
else:
    st.sidebar.warning("Please enter a valid League ID.")

league_id = st.session_state['league_id']

if not st.session_state.get('logged_in', False):
    if st.sidebar.button("Login to Fantrax"):
        try:
            service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
            options = Options()
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=480,640")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36")

            with webdriver.Chrome(service=service, options=options) as driver:
                driver.get("https://www.fantrax.com/login")
                st.sidebar.write("Please log in to Fantrax in the opened browser window.")
                WebDriverWait(driver, 120).until(EC.url_contains("fantrax.com/fantasy")) 
                pickle.dump(driver.get_cookies(), open("fantraxloggedin.cookie", "wb"))
                st.sidebar.success("Login successful! Cookies saved.")

            session = Session()
            with open("fantraxloggedin.cookie", "rb") as f:
                for cookie in pickle.load(f):
                    session.cookies.set(cookie["name"], cookie["value"])

            st.session_state['session'] = session
            st.session_state['logged_in'] = True

        except (WebDriverException, pickle.PickleError) as e:
            st.sidebar.error(f"Login failed: {str(e)}")
else:
    # If already logged in, show logout button
    if st.sidebar.button("Logout"):
        # Clear all keys from session state
        st.session_state.clear()
        
        # Force a rerun to refresh the UI
        st.experimental_set_query_params()
        raise RerunException

# *** MAIN ROSTER PAGE ***
from fantraxapi import FantraxAPI

if 'logged_in' in st.session_state and st.session_state['logged_in']:
    if st.session_state['league_id']:
        try:
            api = FantraxAPI(st.session_state['league_id'], session=st.session_state['session'])
            st.markdown("## Current League Standings")

            standings_collection = api.standings()
            stats_tables = []
            for section in standings_collection.standings:
                for caption, standings in section.items():
                    stats_tables.append(caption)

            stats = st.selectbox("Choose your Stat:", stats_tables, index=0)
            st.markdown(f"#### {stats}")     

            standings_df = utils.standings_to_dataframe(standings_collection, stats)
            st.dataframe(standings_df)
                        
            st.markdown("## Team Selection and Roster")
            teams = api.teams 
            if teams:
                team_dict = {team.name: team.team_id for team in teams}
                team_names = list(team_dict.keys())
                selected_team_name = st.session_state.get('selected_team_name')
                if selected_team_name in team_names:
                    selected_index = team_names.index(selected_team_name)
                else:
                    selected_index = 0

                selected_team_name = st.selectbox("Choose your team:", team_names, index=selected_index)
                st.session_state['selected_team_name'] = selected_team_name
                st.session_state['selected_team_id'] = team_dict[selected_team_name]
            else:
                st.warning("No teams found in this league.")

            # Display roster
            roster = api.roster_info(team_dict[selected_team_name])
            st.markdown(f"#### {roster.team.name} Roster")
            st.write(f"Active: {roster.active}, Reserve: {roster.reserve}, Injured: {roster.injured}, Max: {roster.max}")
            roster_df = utils.playerstats_to_dataframe(roster)
            st.dataframe(roster_df)

            # Show recommendations
            if 'selected_team_name' in st.session_state and 'selected_team_id' in st.session_state:
                selected_team_name = st.session_state['selected_team_name']
                selected_team_id = st.session_state['selected_team_id']

                input_data = {
                    "current_roster": json.loads(roster_df.to_json(orient="records")),
                    "standings": json.loads(standings_df.to_json(orient="records"))
                }         

                current_roster_json = json.dumps(input_data['current_roster'], indent=2)
                standings_json = json.dumps(input_data['standings'], indent=2)   

                # Construct the prompt
                # todo: the prompt is way too huge, consider sticking in a file
                prompt = f"""
                You are an expert fantasy hockey advisor. Your task is to help improve the performance of a fantasy hockey team by analyzing their current roster, and the overall league standings. Your recommendations should focus on maximizing the team's points and improving their position in the standings.

                ### Current Team:
                Below is the current team:
                {selected_team_name}

                ### Current Roster:
                Below is the current roster of the selected fantasy hockey team. For each player, you will see their name, position, points, and relevant statistics:
                {current_roster_json}

                ### League Standings:
                These are the current standings of the team within the league. The standings include the rank of the team, total points scored, and other metrics:
                {standings_json}

                ### Task:
                Please suggest a sequence of actions to improve this team's performance:
                1. Recommend strategies for {selected_team_name} to improve their standings in the league.

                Be detailed in your analysis and provide a clear rationale for each recommendation, but limit your response to 250 words

                The objective is to help this team improve its overall rank in the standings and maximize future points based on the given data.
                """
                st.subheader(f"Recommendations for for Team: {selected_team_name}")
                api_key = st.text_input("Enter your Google Generative AI API key:", type="password")
                if not api_key:
                    st.warning("Please enter your Google Generative AI API key to proceed.")
                    st.stop()
                
                chat_model = ChatGoogleGenerativeAI(model='gemini-1.5-pro-latest', google_api_key=api_key, temperature=0.8)
                human_message = HumanMessage(content=prompt)
                try:
                    response = None
                    attempts = 0
                    max_attempts = 3
                    while attempts < max_attempts:
                        try:
                            response = chat_model([human_message])
                            if response:
                                break
                        except Exception as e:
                            attempts += 1
                            if attempts >= max_attempts:
                                raise e
                    
                    # Assuming response is text, handle lengthy or incomplete responses
                    if response:
                        response_content = response.content
                        if len(response_content.split()) > 250:
                            st.write("### Suggested Improvements (Summary)")
                            st.write(response_content[:2000] + "...")
                            st.write("The response is too lengthy. Please refine the request or provide more specific data for more concise recommendations.")
                        else:
                            st.write("### Suggested Improvements")
                            st.write(response_content)
                    else:
                        st.error("Failed to get a response from Google Gemini.")

                except Exception as e:
                    st.error(f"Error fetching recommendations: {str(e)}")
            else:
                st.warning("Please select a team from the 'Login & Team Selection' page.")           



        except (KeyError, AttributeError) as e:
            st.error(f"Error fetching teams: {str(e)}")

        except (KeyError, AttributeError) as e:
            st.error(f"Error fetching league data: {str(e)}")
else:
    st.info("Please log in using the sidebar to proceed.")
