import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

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

def standings_to_dataframe(standings_collection, stat_table):
    for section in standings_collection.standings:
        for caption, standings in section.items():
            if caption == stat_table:
                team_records_data = []
                for record in standings.team_records:
                    record_data = {
                        "team": record.team,
                        "rank": record.rank,
                    }
                    record_data.update(record.data)
                    team_records_data.append(record_data)
                return pd.DataFrame(team_records_data)


# Create a function to add HTML tooltips to your DataFrame
def add_tooltips(df, column):
    df[column] = df[column].apply(lambda x: f'<span title="{x}">{x[:250]}...</span>' if len(x) > 30 else x)
    return df.to_html(escape=False)