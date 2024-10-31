import streamlit as st
from fantraxapi import FantraxAPI
import pandas as pd

st.set_page_config(page_title="Available Players")
st.title("Fantrax Fantasy Hockey Analysis - Available Players")

if 'logged_in' in st.session_state and st.session_state['logged_in']:
    try:
        # Initialize the API
        league_id = st.session_state.get('league_id', None)
        if league_id and 'session' in st.session_state:
            api = FantraxAPI(league_id, session=st.session_state['session'])

            # Fetch available players
            available_players = api.get_available_players('F') 

            if available_players:
                st.subheader("List of Available Players")
                for player in available_players:
                    st.write(f"Player: {player['name']} - Position: {player['position']}")
            else:
                st.warning("No available players found.")

    except Exception as e:
        st.error(f"Error fetching available players: {str(e)}")

else:
    st.warning("Please log in from the 'Login & Team Selection' page.")
