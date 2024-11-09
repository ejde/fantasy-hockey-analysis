import pandas as pd
import streamlit as st

def playerstats_to_dataframe(players):
    player_data = []
    for row in players.rows:
        row_data = {
            "Position": row.pos.name,
            "Player": row.player.name if row.player else 'N/A',
            "Team": row.player.team_short_name if row.player else 'N/A',
            "Latest": row.latest_comment if row.latest_comment else 'N/A'
        }
        row_data.update(row.stats)
        player_data.append(row_data)
    
    df = pd.DataFrame(player_data)
    
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

def fetch_free_agents(api, position):
    available_players = api.get_available_players(position)
    if available_players and hasattr(available_players, 'rows') and available_players.rows:
        df = playerstats_to_dataframe(available_players)
        df['RkOv'] = df['RkOv'].astype(int)
        df = df.sort_values(by='RkOv', ascending=True).head(5)
        return df.to_dict(orient='records')
    else:
        return None

def fetch_roster_news(api, team_id):
    roster_df = fetch_team_roster(api, team_id)
    return roster_df[['Player', 'Latest', 'Analysis']]

def search_roster_player_news(api, query: str):
    roster_df = fetch_team_roster(api, st.session_state['selected_team_id'])
    latest = roster_df.loc[roster_df['Player'] == query, ['Latest', 'Analysis']].values[0]
    print(latest)
    return latest


hockey_cliches = [
        "We need to get pucks in deep",
        "We just have to play our brand of hockey", 
        "It's all about putting the biscuit in the basket", 
        "Get bodies in front of the net", 
        "It is what it is", 
        "We have to play our game",
        "When you put the puck on net, good things happen",
        "We need to get more traffic in front of the net",
        "We need to give 110 percent",
        "We didn't play a full 60 minutes",
        "We really didn't give the goaltender any support",
        "We just didn't get the bounces",
        "It was a good team effort",
        "Play along the boards",
        "Gain the zone with speed",
        "We gotta take it one shift at a time",
        "Everybody's playin' through something here. Ya gotta play through it. Ya gotta battle",
        "You go til you can't go no more!",
        "We gotta set the tone!"
    ]