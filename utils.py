import pandas as pd
import re

def roster_to_dataframe(roster):
    """
    Convert a roster object into a pandas DataFrame for easier visualization.
    
    Args:
        roster (Roster): The Roster object representing the roster.
    
    Returns:
        pd.DataFrame: DataFrame representation of the roster.
    """
    roster_data = []
    for row in roster.rows:
        row_data = {
            "Position": row.pos.name,
            "Player": row.player.name if row.player else 'N/A',
            "Team": row.player.team_short_name if row.player else 'N/A',
            "Opponent": re.sub(r"<br\s*/?>", " ", row.stats.get("Opponent", "N/A")),
            "Comment": row.comment if row.comment else 'N/A'
        }
        row_data.update(row.stats)
        roster_data.append(row_data)
    
    df = pd.DataFrame(roster_data)
    # Rename columns to be shorter and easier to display
    df.rename(columns={
        "Wins (Goalies only) -- Includes Overtime Wins and Shootout Wins. Skaters cannot get a win using this category - for that - use the \"regular\" Wins category.": "Wins",
        "Save Percentage -- Saves / Shots on Goal Against": "Save %"
    }, inplace=True)
    
    return df
