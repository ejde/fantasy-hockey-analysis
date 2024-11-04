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

from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage

import utils

logging.basicConfig(filename='selenium.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

st.title("Fantrax Fantasy Hockey Analysis")

# *** SOME HELPERS ***
def login_to_fantrax(username, password):
    driver = utils.initialize_driver()
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

        st.markdown(f"#### {stats}")
        standings_df = utils.standings_to_dataframe(standings_collection, stats)
        st.dataframe(standings_df)
        return standings_df
    except Exception as e:
        st.error(f"Error fetching league standings: {e}")
        return None

def fetch_and_display_team_roster(api, team_dict):
    #selected_team_name = st.selectbox("Choose your team:", list(team_dict.keys()))
    #selected_team_id = team_dict[selected_team_name]
    st.session_state['selected_team_name'] = api.default_team_name
    st.session_state['selected_team_id'] = api.default_team_id
    
    try:
        roster = api.roster_info(api.default_team_id)
        st.markdown(f"#### {roster.team.name} Roster")
        st.write(f"Active: {roster.active}, Reserve: {roster.reserve}, Injured: {roster.injured}, Max: {roster.max}")
        roster_df = utils.playerstats_to_dataframe(roster)
        st.dataframe(roster_df)
        return roster_df
    except Exception as e:
        st.error(f"Error fetching roster: {e}")
        return None        
    
def fetch_free_agents(api, position):
    available_players = api.get_available_players(position)
    if available_players and hasattr(available_players, 'rows') and available_players.rows:
        df = utils.playerstats_to_dataframe(available_players)
        df['RkOv'] = df['RkOv'].astype(int)
        df = df.sort_values(by='RkOv', ascending=True).head(3)
        return df.to_dict(orient='records')
    else:
        return None

def generate_recommendations(chat_model, prompt):
    human_message = HumanMessage(content=prompt)
    try:
        response = chat_model([human_message])
        if response:
            return response.content
    except Exception as e:
        st.error(f"Error fetching recommendations: {e}")
    return None

def run_player_evaluation(api, context):
    try:
        free_agents = []
        for position in ['F','D','G']:
            fa = fetch_free_agents(api, position)
            if fa is not None:
                for p in fa:
                    free_agents.append(p)

        if free_agents is None:
            return []
        
        evaluations = []
        for player in free_agents:
            evaluation_prompt = f"""
            Given the following player details: {player}, and the context: {context}, determine if this player is a good fit for the team. 
            Respond with 'Yes, this player is a good fit' or 'No, this player is not a good fit'. Mention the player's name in your response. 
            In addition, give reasons why you think this player is a good fit but keep it concise. Use the following response template:
            [Player Name] - [Position]: [Reason in relation to team and recommendations]
            """               
            response = generate_recommendations(chat_model, evaluation_prompt)
            if response:
                if 'yes, this player is a good fit' in response.lower():
                    evaluations.append({"player": player, "evaluation": response})
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

            recommendation_prompt = f"""
            You are an expert fantasy hockey advisor. Analyze the current roster and league standings to suggest improvements for {st.session_state['selected_team_name']}.
            #### Current Roster: {json.dumps(input_data['current_roster'], indent=2)}
            #### League Standings: {json.dumps(input_data['standings'], indent=2)}
            #### Instructions:
            Be detailed in your analysis and provide a clear rationale for each recommendation using the template below.
            If the recommendation is to pick up players, mention the characteristics of the player that would be useful for the team as it will be used to search through the list of free agents to add.
            If there are players on the current roster that the team should drop and mention their names and your reasons to consider dropping them.
            Keep your response concise, no more than 300 words. Use the response template below.
            #### Template
            #### Current Situation:
            [Team Name] is currently ranked [Current Rank] in the league, with a points total of [Points Total]. While this position shows that the team is competitive, there are certain areas that lag behind the top teams. Specific areas of concern include:
            * [Statistic 1]: (e.g., Goals: The team has [X] goals, but the top teams are consistently outperforming in this category.)
            * [Statistic 2]: (e.g., Assists: [X] assists is respectable, but the top teams are significantly higher.)
            * [Goalie Statistic]: (e.g., Goaltending stats like shutouts and save percentage fall slightly below the league average, impacting overall points.)
            * Overall Performance: (e.g., Combined goals and assists fall below the top-ranked teams.)
              * Top Performers: (e.g. Auston Matthews has the highest goals, etc.)
              * Bottom Performers: (e.g. Conner McDavid is underperforming, etc.)

            #### Recommendations:
            1. [Focus Area 1 - Improvement Area]
              * Recommendation: (e.g., Acquire a high-scoring forward with a strong track record of points. Look for players who consistently score 10+ goals or provide 15+ assists.)
              * Rationale: (e.g., Improving point production is critical to closing the gap between [Team Name] and the top-ranked teams. Current players lack high point-scoring consistency, and acquiring such a forward will elevate the overall score.)
            2. [Focus Area 2 - Improvement Area]
              * Recommendation: (e.g., Strengthen goaltending by seeking a goalie with a save percentage above .910 and a record of shutouts.)
              * Rationale: (e.g., Boosting goaltending stats, particularly shutouts and save percentage, will lead to consistent wins and more fantasy points. This area has been a key differentiator for the higher-ranked teams.)
            3. [Focus Area 3 - Improvement Area]
              * Recommendation: (e.g., Add a defenseman known for a strong plus/minus rating to improve both defensive support and offensive play.)
              * Rationale: (e.g., A defenseman with a strong plus/minus is valuable not only for defensive stability but also for contributing to goals and assists, enhancing the team’s offensive structure.)         
            """            

            if st.session_state['league_id'] in st.secrets.get("league_whitelist", []):
                llm_api_key = st.secrets.get("gemini_key")
            else:
                llm_api_key = st.text_input("Enter your Google Generative AI API key:", type="password")     

            if llm_api_key:
                chat_model = ChatGoogleGenerativeAI(model='gemini-1.5-flash-8b', google_api_key=llm_api_key, temperature=0.8)
                response_content = generate_recommendations(chat_model, recommendation_prompt)
                if response_content:
                    st.subheader(f"Recommendations for Team: {st.session_state['selected_team_name']}")
                    st.write(response_content)
                    context = {"recommendation": response_content}
                    evaluations = run_player_evaluation(api, context)
                    
                    if evaluations:
                        st.markdown("#### Possible Free Agents to Add")
                        for eval in evaluations:
                            st.markdown(f"* {eval['evaluation']}")               
        else:
            st.warning("No teams found in this league.")
else:
    st.info("Please log in using the sidebar to proceed.")
