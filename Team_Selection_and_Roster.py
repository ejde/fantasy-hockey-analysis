import streamlit as st

import pickle
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from requests import Session
from streamlit.runtime.scriptrunner import RerunException


st.set_page_config(page_title="Team Roster")
st.title("Fantrax Fantasy Hockey Analysis")
st.markdown("## Team Selection and Roster")

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
            service = Service(ChromeDriverManager().install())
            options = Options()
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

        except Exception as e:
            st.sidebar.error(f"Login failed: {str(e)}")
else:
    # If already logged in, show logout button
    if st.sidebar.button("Logout"):
        # Clear all keys from session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Force a rerun to refresh the UI
        st.experimental_set_query_params()
        raise RerunException

# *** MAIN ROSTER PAGE ***
import streamlit as st
from fantraxapi import FantraxAPI

if 'logged_in' in st.session_state and st.session_state['logged_in']:
    if st.session_state['league_id']:
        try:
            api = FantraxAPI(st.session_state['league_id'], session=st.session_state['session'])
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
            st.markdown(f"### {roster.team.name} Roster")
            st.write(f"Active: {roster.active}, Reserve: {roster.reserve}, Injured: {roster.injured}, Max: {roster.max}")
    
            from utils import roster_to_dataframe
            st.dataframe(roster_to_dataframe(roster))
        except Exception as e:
            st.error(f"Error fetching teams: {str(e)}")

        except Exception as e:
            st.error(f"Error fetching league data: {str(e)}")
else:
    st.info("Please log in using the sidebar to proceed.")