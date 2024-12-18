import streamlit as st
from streamlit.runtime.scriptrunner import RerunException
import pickle
import json
import logging
import re
from requests import Session
import pandas as pd

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from langchain_google_genai import ChatGoogleGenerativeAI

from fantraxapi import FantraxAPI

import utils

logging.basicConfig(filename='selenium.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

st.title("Fantrax Fantasy Hockey Analysis")

# *** SOME HELPERS ***
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
        if 'standings_collection' not in st.session_state:
            standings_collection = api.standings()
            st.session_state['standings_collection'] = standings_collection
        else:
            standings_collection = st.session_state['standings_collection']

        stats_tables = [caption for section in standings_collection.standings for caption, _ in section.items()]

        if st.secrets.get("default_stat"):
            stats = st.secrets["default_stat"]
        else:
            stats = st.selectbox("Choose your Stat:", stats_tables, index=0)

        standings_df = utils.standings_to_dataframe(standings_collection, stats)
        
        st.markdown(f"#### {stats}")
        st.dataframe(standings_df)
        
        return standings_df
    except Exception as e:
        st.error(f"Error fetching league standings: {e}")
        return None

def fetch_and_display_team_roster(api):
    st.session_state['selected_team_name'] = api.default_team_name
    st.session_state['selected_team_id'] = api.default_team_id
    
    try:
        roster_df = utils.fetch_team_roster(api, st.session_state['selected_team_id'])
        roster = st.session_state['roster']

        st.markdown(f"#### {roster.team.name} Roster")
        st.write(f"Active: {roster.active}, Reserve: {roster.reserve}, Injured: {roster.injured}, Max: {roster.max}")
        st.dataframe(roster_df)
        return roster_df
    except Exception as e:
        st.error(f"Error fetching roster: {e}")
        return None        

@st.cache_data(show_spinner=True)
def generate_recommendations(prompt):
    try:
        response = chat_model.invoke(prompt)
        if response:
            return response.content
    except Exception as e:
        st.error(f"Error fetching recommendations: {e}")
    return None

def run_player_evaluation(api, context):
    try:
        free_agents = []
        evaluations = []
        for position in ['F','D','G']:
            fa = utils.fetch_free_agents(api, position)
            if fa is not None:
                for p in fa:
                    free_agents.append(p)

            for player in free_agents:
                evaluation_prompt = f"""
                    Given the player details {player} and the context {context}, evaluate if this player is a good fit for the team.
                    If adding this player, suggest who they should replace on the current roste. Provide concise reasons using key stats. Use the following template:
                    - **[Player Name]** is a good fit for [Position]: [Reason in relation to team needs and recommendations], or
                    - **[Player Name]** is a not good fit for [Position]: [Reason in relation to team needs and recommendations] 
                """               
                response = generate_recommendations(evaluation_prompt)
                if response:
                    if 'is a good fit' in response.lower():
                        evaluations.append({"player": player, "evaluation": response})
                        free_agents = []
                        break
        
        return evaluations
    except Exception as e:
        print(f"Error during player evaluation execution: {e}")
        return []

# *** SIDEBAR ***
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
if 'logged_in' in st.session_state and st.session_state['logged_in']:
    api = FantraxAPI(st.session_state['league_id'], session=st.session_state['session'])
    standings_df = fetch_and_display_standings(api)
    roster_df = fetch_and_display_team_roster(api)

    if standings_df is not None and roster_df is not None:
        # Prompt and Recommendations
        input_data = {
            "current_roster": json.loads(roster_df.to_json(orient="records")),
            "standings": json.loads(standings_df.to_json(orient="records"))
        }

        recommendation_prompt = f"""
            You are an expert fantasy hockey advisor. Analyze the current roster and league standings to suggest improvements for {st.session_state['selected_team_name']}.
            Current Roster: {json.dumps(input_data['current_roster'], indent=2)}
            League Standings: {json.dumps(input_data['standings'], indent=2)}
            Instructions:
            - Provide a detailed analysis of the team's strengths and weaknesses. Use the response template provided.
            - Recommend actions: pick up, drop, or trade players. Justify each recommendation with specific statistics.
            - For player pickups, describe desired characteristics (e.g., high goal-scoring ability) to assist in searching free agents.
            - Be blunt when assessing underperformers—no sugarcoating - name players explicitly when assessing underperformers.
            - Keep responses to 275 words max.
            Response Template:
            Current Situation: [Team Name] is ranked [Current Rank] with [Points Total] points. Areas that need improvement include:
            - Statistic 1: (e.g., Goals: [X], below league leaders.)
            - Statistic 2: (e.g., Assists: [X], significantly lower than the top teams.)
            - Goalie Stats: (e.g., Save percentage and shutouts fall below league average.)
            - Overall Performance: [Team Name] lags in combined offensive and defensive stats.
            - Top Performers: (e.g., [Top Player] excels in goals/assists.)
            - Bottom Performers: (e.g., [Underperforming Player] is falling short.)
            Recommendations:
              * Focus Area 1:
                - Recommendation: (e.g., Acquire a high-scoring forward. Look for consistent scorers with 10+ goals or 15+ assists.)
                - Rationale: (e.g., More scoring power is key to closing the gap with the league leaders.)
              * Focus Area 2:
                - Recommendation: (e.g., Improve goaltending by adding a goalie with a save percentage above .910.)
                - Rationale: (e.g., Stronger goaltending will improve point stability and boost ranking.) 
        """            

        if st.session_state['league_id'] in st.secrets.get("league_whitelist", []):
            llm_api_key = st.secrets.get("gemini_key")
        else:
            llm_api_key = st.text_input("Enter your Google Generative AI API key:", type="password")     

        if llm_api_key:
            chat_model = ChatGoogleGenerativeAI(model='gemini-1.5-flash-8b', google_api_key=llm_api_key, temperature=0.8)
            response_content = generate_recommendations(recommendation_prompt)
            if response_content:
                st.subheader(f"Recommendations for Team: {st.session_state['selected_team_name']}")
                st.write(response_content)
                context = {"recommendation": response_content}
                evaluations = run_player_evaluation(api, context)
                
                if evaluations:
                    st.markdown("#### Possible Free Agents to Add")
                    for eval in evaluations:
                        st.markdown(f"{eval['evaluation']}")               
else:
    st.info("Please log in using the sidebar to proceed.")
