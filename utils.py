import pandas as pd
import streamlit as st

def playerstats_to_dataframe(players):
    player_data = []
    for row in players.rows:
        row_data = {
            "Position": row.pos.name,
            "Player": row.player.name if row.player else 'N/A',
            "Team": row.player.team_short_name if row.player else 'N/A',
            "Comment": row.comment if row.comment else 'N/A'
        }
        row_data.update(row.stats)
        player_data.append(row_data)
    
    df = pd.DataFrame(player_data)
    df.rename(columns={
        "Wins (Goalies only) -- Includes Overtime Wins and Shootout Wins. Skaters cannot get a win using this category - for that - use the \"regular\" Wins category.": "Wins",
        "Save Percentage -- Saves / Shots on Goal Against": "Save %"
    }, inplace=True)
    
    return df

def standings_to_dataframe(standings_collection, stat_table=None):
    for section in standings_collection.standings:
        for caption, standings in section.items():
            if caption == stat_table or stat_table is None: #ugh, will enter the first run through
                team_records_data = []
                for record in standings.team_records:
                    record_data = {
                        "team": record.team,
                        "rank": record.rank,
                    }
                    record_data.update(record.data)
                    team_records_data.append(record_data)
                return pd.DataFrame(team_records_data)
            
def fetch_standings(api):
    try:
        if 'standings_collection' not in st.session_state:
            standings_collection = api.standings()
            st.session_state['standings_collection'] = standings_collection
        else:
            standings_collection = st.session_state['standings_collection']

        if st.secrets.get("default_stat"):
            stats = st.secrets["default_stat"]

        standings_df = standings_to_dataframe(standings_collection, stats)
        return standings_df
    except Exception as e:
        st.error(f"Error fetching league standings: {e}")
        return None

def fetch_team_roster(api, team_id):
    try:
        if 'roster' not in st.session_state:
            roster = api.roster_info(team_id)
            st.session_state['roster'] = roster
        else:
            roster = st.session_state['roster']

        roster_df = playerstats_to_dataframe(roster)
        return roster_df
    except Exception as e:
        st.error(f"Error fetching roster: {e}")
        return None        