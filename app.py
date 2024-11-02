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

from webdriver_manager.core.os_manager import ChromeType
from webdriver_manager.chrome import ChromeDriverManager

from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage


# Set up logging
logging.basicConfig(filename='selenium.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

st.set_page_config(page_title="Team Roster")
st.title("Fantrax Fantasy Hockey Analysis")

if not st.session_state.get('logged_in', False):
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login to Fantrax"):
        try:
            service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
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

            # Initialize the WebDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

            # Set up wait
            wait = WebDriverWait(driver, 10)

            # Navigate to the login page
            logging.info("Navigating to the Fantrax login page.")
            driver.get("https://www.fantrax.com/login")

            # Wait for the username field to be present
            username_field = wait.until(EC.presence_of_element_located((By.ID, 'mat-input-0')))
            password_field = driver.find_element(By.ID, 'mat-input-1')
            login_button = driver.find_element(By.XPATH, '//button[@type="submit"]')

            # Enter credentials
            logging.info("Entering user credentials.")
            username_field.send_keys(username)
            password_field.send_keys(password)

            # Click the login button
            login_button.click()

            # Wait for the login process to complete
            logging.info("Waiting for login to process.")
            wait.until(EC.url_contains('/league/'))

            # Get the current URL
            current_url = driver.current_url
            logging.info(f"Current URL after login: {current_url}")

            # Extract the league_id from the URL            
            match = re.search(r'/league/(\w+)/', current_url)
            if match:
                league_id = match.group(1)
                st.session_state['league_id'] = league_id
                st.sidebar.success(f"Login successful! League ID: {league_id}")
                st.sidebar.write("Logged in as:", username)
                st.session_state['username'] = username
                st.sidebar.write("League ID:", league_id)
                logging.info(f"Extracted League ID: {league_id}")

                # Save cookies to a file
                cookies = driver.get_cookies()
                with open("fantraxloggedin.cookie", "wb") as f:
                    pickle.dump(cookies, f)

                # Create a requests session and load cookies
                session = Session()
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

                st.session_state['session'] = session
                st.session_state['logged_in'] = True

            else:
                st.error("Failed to extract league ID.")
                logging.error("League ID not found in the URL.")

        except Exception as e:
            st.error(f"An error occurred: {e}")
            logging.error(f"An exception occurred: {e}")

        finally:
            driver.quit()
else:
    # If already logged in, show logout button
    st.sidebar.write("Logged in as:", st.session_state['username'])
    st.sidebar.write("League ID:", st.session_state['league_id'])
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_set_query_params()
        raise RerunException(None)

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

            # Show summary recommendations
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

                # Show specific roster recommendations based on available player data

            else:
                st.warning("Please select a team from the 'Login & Team Selection' page.")           

        except (KeyError, AttributeError) as e:
            st.error(f"Error fetching teams: {str(e)}")

        except (KeyError, AttributeError) as e:
            st.error(f"Error fetching league data: {str(e)}")
    else:
        st.session_state.clear()
        st.experimental_set_query_params()
        raise RerunException
else:
    st.info("Please log in using the sidebar to proceed.")
