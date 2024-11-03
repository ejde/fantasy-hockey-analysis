import streamlit as st
from streamlit.runtime.scriptrunner import RerunException
import pickle
import utils
import json
import logging
import re
from requests import Session

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage


logging.basicConfig(filename='selenium.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

st.set_page_config(page_title="Team Roster")
st.title("Fantrax Fantasy Hockey Analysis")

def initialize_driver():
    service = Service()
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)")
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(service=service, options=options)

def login_to_fantrax(username, password):
    driver = initialize_driver()
    wait = WebDriverWait(driver, 10)
    try:
        logging.info("Navigating to the Fantrax login page.")
        driver.get("https://www.fantrax.com/login")
        username_field = wait.until(EC.presence_of_element_located((By.ID, 'mat-input-0')))
        password_field = driver.find_element(By.ID, 'mat-input-1')
        login_button = driver.find_element(By.XPATH, '//button[@type="submit"]')

        logging.info("Entering user credentials.")
        username_field.send_keys(username)
        password_field.send_keys(password)
        login_button.click()

        logging.info("Waiting for login to process.")
        wait.until(EC.url_contains('/league/'))

        current_url = driver.current_url       
        match = re.search(r'/league/(\w+)/', current_url)
        if match:
            league_id = match.group(1)
            st.session_state['league_id'] = league_id
            st.session_state['username'] = username
            st.session_state['logged_in'] = True

            cookies = driver.get_cookies()
            with open("fantraxloggedin.cookie", "wb") as f:
                pickle.dump(cookies, f)

            session = Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            st.session_state['session'] = session

            st.sidebar.success(f"Login successful! League ID: {league_id}")
            logging.info(f"Extracted League ID: {league_id}")
        else:
            st.error("Failed to extract league ID.")
    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        driver.quit()

def display_login():
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login to Fantrax"):
        login_to_fantrax(username, password)

def fetch_and_display_standings(api):
    try:
        standings_collection = api.standings()
        stats_tables = [caption for section in standings_collection.standings for caption, _ in section.items()]

        if st.secrets["default_stat"]:
            stats = st.secrets["default_stat"]
        else:
            stats = st.selectbox("Choose your Stat:", stats_tables, index=0)

        stats = st.selectbox("Choose your Stat:", stats_tables, index=0)
        st.markdown(f"#### {stats}")
        standings_df = utils.standings_to_dataframe(standings_collection, stats)
        st.dataframe(standings_df)
        return standings_df
    except Exception as e:
        st.error(f"Error fetching league standings: {e}")
        return None

def fetch_and_display_team_roster(api, team_dict):
    selected_team_name = st.selectbox("Choose your team:", list(team_dict.keys()))
    st.session_state['selected_team_name'] = selected_team_name
    selected_team_id = team_dict[selected_team_name]
    st.session_state['selected_team_id'] = selected_team_id

    roster = api.roster_info(selected_team_id)
    st.markdown(f"#### {roster.team.name} Roster")
    st.write(f"Active: {roster.active}, Reserve: {roster.reserve}, Injured: {roster.injured}, Max: {roster.max}")
    roster_df = utils.playerstats_to_dataframe(roster)
    st.dataframe(roster_df)
    return roster_df

def generate_recommendations(api_key, prompt):
    chat_model = ChatGoogleGenerativeAI(model='gemini-1.5-flash', google_api_key=api_key, temperature=0.8)
    human_message = HumanMessage(content=prompt)
    try:
        response = chat_model([human_message])
        if response:
            return response.content
    except Exception as e:
        st.error(f"Error fetching recommendations: {e}")
    return None

# Sidebar
if not st.session_state.get('logged_in', False):
    display_login()
else:
    st.sidebar.write("Logged in as:", st.session_state['username'])
    st.sidebar.write("League ID:", st.session_state['league_id'])
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_set_query_params()
        raise RerunException(None)

    # *** MAIN ROSTER PAGE ***
from fantraxapi import FantraxAPI
if 'logged_in' in st.session_state and st.session_state['logged_in']:
    api = FantraxAPI(st.session_state['league_id'], session=st.session_state['session'])
    standings_df = fetch_and_display_standings(api)

    if standings_df is not None:
        teams = api.teams
        if teams:
            team_dict = {team.name: team.team_id for team in teams}
            roster_df = fetch_and_display_team_roster(api, team_dict)

            # Prompt and Recommendations
            input_data = {
                "current_roster": json.loads(roster_df.to_json(orient="records")),
                "standings": json.loads(standings_df.to_json(orient="records"))
            }

            prompt = f"""
            You are an expert fantasy hockey advisor. Analyze the current roster and league standings to suggest improvements for {st.session_state['selected_team_name']}.
            Current Roster: {json.dumps(input_data['current_roster'], indent=2)}
            League Standings: {json.dumps(input_data['standings'], indent=2)}
            ### Task:
            Recommend strategies in numbered list format for {st.session_state['selected_team_name']} to improve their standings in the league. 
            Be detailed in your analysis and provide a clear rationale for each recommendation, but limit your response to 250 words.
            """

            if st.session_state['league_id'] in st.secrets["league_whitelist"]:
                api_key = st.secrets["gemini_key"]
            else:
                api_key = st.text_input("Enter your Google Generative AI API key:", type="password")     

            if api_key:
                response_content = generate_recommendations(api_key, prompt)
                if response_content:
                    st.subheader(f"Recommendations for Team: {st.session_state['selected_team_name']}")
                    st.write(response_content)
        else:
            st.warning("No teams found in this league.")
else:
    st.info("Please log in using the sidebar to proceed.")

