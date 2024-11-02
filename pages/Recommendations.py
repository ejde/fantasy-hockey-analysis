import streamlit as st
from fantraxapi import FantraxAPI
import utils
import json
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage

def create_position_buttons():
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Forwards"):
            st.session_state['selected_position'] = "F"
    with col2:
        if st.button("Defense"):
            st.session_state['selected_position'] = "D"
    with col3:
        if st.button("Goalies"):
            st.session_state['selected_position'] = "G"

st.set_page_config(page_title="Recommendations")
st.title("Fantrax Fantasy Hockey Analysis - Recommendations")

if 'logged_in' in st.session_state and st.session_state['logged_in']:
    try:
        # Initialize the API
        league_id = st.session_state.get('league_id', None)
        session = st.session_state.get('session', None)

        if league_id and session:
            if not league_id.strip():
                st.error("League ID is missing or empty. Please log in again.")
                st.stop()

            if not session:
                st.error("Session is invalid or expired. Please log in again.")
                st.stop()

            api = FantraxAPI(league_id, session=session)

            # Create buttons for different position types at the top of the page
            create_position_buttons()

            # Default to "Forwards" if no selection has been made yet
            if 'selected_position' not in st.session_state:
                st.session_state['selected_position'] = "F"

            # Display the currently selected position
            selected_position = st.session_state['selected_position']
            st.subheader(f"Showing Available Players for: {selected_position}")

            # Fetch available players based on the selected position
            available_players = api.get_available_players(selected_position)

            # Display the available players if they exist
            if available_players and hasattr(available_players, 'rows') and available_players.rows:
                df = utils.playerstats_to_dataframe(available_players)
                df['RkOv'] = df['RkOv'].astype(int)
                st.dataframe(df.sort_values(by='RkOv', ascending=True))
                available_players_df = df
            else:
                st.warning("No available players found or unable to fetch data.")

        # Find recommendations based on the selected position
        if 'selected_team_name' in st.session_state and 'selected_team_id' in st.session_state:
            selected_team_name = st.session_state['selected_team_name']
            selected_team_id = st.session_state['selected_team_id']

            #get other data
            standings_collection = api.standings()
            standings_df = utils.standings_to_dataframe(standings_collection, "Standings - Point Totals ")
            roster = api.roster_info(selected_team_id)
            roster_df = utils.playerstats_to_dataframe(roster)
            available_players_df['RkOv'] = available_players_df['RkOv'].astype(int)
            available_players_df.sort_values(by='RkOv', ascending=True).head(10)

            input_data = {
                "current_roster": json.loads(roster_df.to_json(orient="records")),
                "available_players": json.loads(available_players_df.to_json(orient="records")),
                "standings": json.loads(standings_df.to_json(orient="records"))
            }         

            current_roster_json = json.dumps(input_data['current_roster'], indent=2)
            available_players_json = json.dumps(input_data['available_players'], indent=2)
            standings_json = json.dumps(input_data['standings'], indent=2)   

            # Construct the prompt
            prompt = f"""
            You are an expert fantasy hockey advisor. Your task is to help improve the performance of a fantasy hockey team by analyzing their current roster, the list of available players, and the overall league standings. Your recommendations should focus on maximizing the team's points and improving their position in the standings.

            ### Current Roster:
            Below is the current roster of the selected fantasy hockey team. For each player, you will see their name, position, points, and relevant statistics:
            {current_roster_json}

            ### Available Players:
            Here are the players that are currently available for acquisition. Each player has attributes including their name, position, current points, and other relevant stats:
            {available_players_json}

            ### League Standings:
            These are the current standings of the team within the league. The standings include the rank of the team, total points scored, and other metrics:
            {standings_json}

            ### Task:
            Please suggest a sequence of actions to improve this team's performance:
            1. Recommend which players from the **current roster** should be dropped, if any, to enhance the team’s point potential.
            2. Recommend which players from the **available players** should be acquired to maximize the team's overall standings.
            3. If applicable, suggest trade strategies for players that can improve the balance of the team.

            Be detailed in your analysis and provide a clear rationale for each recommendation:
            - Specify which players to drop and why.
            - Specify which players to add and why they would be beneficial to the team.
            - Recommend the optimal positioning and strategy to balance offensive and defensive plays.

            The objective is to help this team improve its overall rank in the standings and maximize future points based on the given data.
            """
            with open('fantasy_hockey_prompt.txt', 'w') as f:
                f.write(prompt)
            st.subheader(f"Recommendations for {selected_position} for Team: {selected_team_name}")
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
                    if len(response_content) > 2000:
                        st.write("### Suggested Moves (Summary)")
                        st.write(response_content[:2000] + "...")
                        st.write("The response is too lengthy. Please refine the request or provide more specific data for more concise recommendations.")
                    else:
                        st.write("### Suggested Moves")
                        st.write(response_content)
                else:
                    st.error("Failed to get a response from Google Gemini.")

            except Exception as e:
                st.error(f"Error fetching recommendations: {str(e)}")
        else:
            st.warning("Please select a team from the 'Login & Team Selection' page.")
    
    except Exception as e:
        st.error(f"Error fetching available players: {str(e)}")
else:
    st.warning("Please log in from the 'Login & Team Selection' page.")
