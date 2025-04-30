import requests
import json

def get_players_season(team_id, season):
    players_data = []

    # Make a GET request to the NHL API to retrieve team roster for the specified season
    response = requests.get(f'https://statsapi.web.nhl.com/api/v1/teams/{team_id}/roster?season={season}')

    if response.status_code == 200:
        roster_data = response.json()

        # Iterate over each player in the roster and extract their data
        for player in roster_data['roster']:
            player_id = player['person']['id']
            player_name = player['person']['fullName']

            player_data = {
                'id': player_id,
                'name': player_name,
                'team_id': team_id,
                'season': season
            }
            players_data.append(player_data)

    else:
        # Handle the case when the API request fails
        print(f'Failed to retrieve player data for season {season} and team {team_id}.')

    return players_data

def get_team_ids(season):
    # Endpoint to retrieve NHL teams
    url = f'https://statsapi.web.nhl.com/api/v1/teams?season={season}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Extract team IDs
        team_ids = [team['id'] for team in data['teams']]
        
        return team_ids
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")


# Define the range of seasons you want to retrieve player data for
start_season = 19171918
end_season = 20222023

# Create an empty dictionary to store the player data
all_players_data = {}

# Iterate through all seasons
for season in range(start_season, end_season + 1, 10001):
    season_str = str(season)
    season_players_data = {}
    team_ids = get_team_ids(season_str)

    # Iterate through all team IDs
    for team_id in team_ids:
        team_players = get_players_season(team_id, season_str)
        season_players_data[str(team_id)] = team_players

    # Store the player data for the current season in the dictionary
    all_players_data[season_str] = season_players_data

# Write the player data to a JSON file
with open('nhl_players.json', 'w') as file:
    json.dump(all_players_data, file)

print('Player data has been written to nhl_players.json.')
