import aiohttp
import json
import aiofiles

#function to get the nhl schedule for a specific date using the nhl api
async def get_schedule(start_date, end_date=None, team_id=None):
    if end_date is None:
        end_date = start_date
    
    if team_id is None:
        url = f'https://statsapi.web.nhl.com/api/v1/schedule?startDate={start_date}&endDate={end_date}'
    else:
        url = f'https://statsapi.web.nhl.com/api/v1/schedule?startDate={start_date}&endDate={end_date}&teamId={team_id}'
    print(url)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response = await response.json()
    
    dates = response['dates']#[0]['games']
    if len(dates) == 0:
        return 'No games found.'
    games_str = ''

    for date in dates:
        if len(date['games']) == 0:
            games_str += f'No games on {date["date"]}\n'
            continue
        for game in date['games']:
            #get the home and away teams, scores, and game status
            home_team = game['teams']['home']['team']['name']
            away_team = game['teams']['away']['team']['name']
            home_score = game['teams']['home']['score']
            away_score = game['teams']['away']['score']
            game_status = game['status']['detailedState']

            #format the game status
            if game_status == 'Scheduled':
                game_status = 'Scheduled to start at'
            elif game_status == 'In Progress':
                game_status = 'In progress'
            elif game_status == 'Final':
                game_status = 'Final'
            elif game_status == 'Postponed':
                game_status = 'Postponed'
            elif game_status == 'Canceled':
                game_status = 'Canceled'
            elif game_status == 'Game Over':
                game_status = 'Game Over'
            elif game_status == 'Game Over - Shootout':
                game_status = 'Game Over - Shootout'
            elif game_status == 'Final - OT':
                game_status = 'Final - OT'

            #format the game string
            games_str += f'{away_team} @ {home_team} - {away_score} - {home_score} - {game_status}\n'

    return games_str


async def fetch_team_id(team_name):
    url = "https://statsapi.web.nhl.com/api/v1/teams"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                teams = data["teams"]
                
                for team in teams:
                    if team["name"] == team_name:
                        return team["id"]
            else:
                print("Failed to fetch team IDs.")
                return None

async def fetch_roster(team_name, season=None):
    # Get the team id
    team_id = await fetch_team_id(team_name)
    if team_id is None:
        return "Failed to find team."
    
    if season is None:
        url = f"https://statsapi.web.nhl.com/api/v1/teams/{team_id}/roster"
    else:
        season = season.replace("-", "")
        url = f"https://statsapi.web.nhl.com/api/v1/teams/{team_id}/roster?season={season}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                players = data["roster"]
                
                players_str = ''
                # format the players string - name, position, jersey number
                for player in players:
                    if "jerseyNumber" not in player:
                        continue
                    players_str += f'{player["person"]["fullName"]} - {player["position"]["abbreviation"]} - {player["jerseyNumber"]}\n'
                
                return players_str
            else:
                print("Failed to fetch players.")
                return None


async def get_player_stats(player_name, season):
    season = season.replace("-", "")
    print(player_name)
    # Get the player id
    player_id = await get_player_id(player_name, season)
    print(player_id)
    if player_id is None:
        return "Failed to find player."
    
    url = f"https://statsapi.web.nhl.com/api/v1/people/{player_id}/stats?stats=statsSingleSeason&season={season}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                stats = data["stats"][0]["splits"][0]["stat"]

                # Extract relevant stats
                games_played = stats["games"]
                goals = stats["goals"]
                assists = stats["assists"]
                points = stats["points"]

                # Format the stats as a string
                stats_string = f"Season: {season}\n" \
                            f"Games Played: {games_played}\n" \
                            f"Goals: {goals}\n" \
                            f"Assists: {assists}\n" \
                            f"Points: {points}"
                
                return stats_string
            else:
                return "Failed to fetch player stats."


async def get_player_id(player_name, season):
    # open the player id json file
    async with aiofiles.open("util/nhl_players.json", mode="r") as f:
        players = json.loads(await f.read())

    teams = players[season]

    # search for the player name in the json file
    for players in teams.values():
        for player in players:
            if player["name"].lower() == player_name.lower():
                return str(player["id"])
    
    return "Failed to find player."

async def get_standings(season):
    url = f"https://statsapi.web.nhl.com/api/v1/standings?season={season}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

    standings = []
    for record in data["records"]:
        division = record["division"]["name"]
        for team in record["teamRecords"]:
            team_name = team["team"]["name"]
            division_rank = team["divisionRank"]
            conference_rank = team["conferenceRank"]
            league_rank = team["leagueRank"]
            overall_record = team["leagueRecord"]["wins"], team["leagueRecord"]["losses"], team["leagueRecord"]["ot"], "-" + str(team["leagueRecord"]["ties"]) if "ties" in team["leagueRecord"] else ""
            position_string = f"{team_name}: division name: {division}, division rank: {division_rank}, conference rank: {conference_rank}, league rank: {league_rank}, overall record: {overall_record[0]}-{overall_record[1]}{overall_record[3]}-{overall_record[2]}"
            standings.append(position_string)

    standings_string = '\n'.join(standings)
    return standings_string


functions_dict = {
    "get_schedule": get_schedule,
    "fetch_roster": fetch_roster,
    "get_player_stats": get_player_stats,
    "get_standings": get_standings,
}

functions = [
    {
        "name": "get_schedule",
        "description": "Get the NHL schedule for a specific date using the NHL API",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "The start date to get the schedule for. Format: YYYY-MM-DD",
                },
                "end_date": {
                    "type": "string",
                    "description": "The end date to get the schedule for. Format: YYYY-MM-DD (optional)",
                },
                "team_id": {
                    "type": "integer",
                    "description": "The ID of the team to filter the schedule by (optional)",
                }
            },
            "required": ["start_date"],
        },
    },
    {
        "name": "get_player_stats",
        "description": "Get the stats of a specific player in a particular season from the NHL API",
        "parameters": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "The name of the player to get the stats for",
                },
                "season": {
                    "type": "string",
                    "description": "The season to get the stats for. Format: YYYYYYYY (e.g. 20192020)",
                },
            },
            "required": ["player_id", "season"],
        },
    },
    {
        "name": "fetch_roster",
        "description": "Get the roster of a specific team from the NHL API",
        "parameters": {
            "type": "object",
            "properties": {
                "team_name": {
                    "type": "string",
                    "description": "The name of the team to get the roster for",
                },
                "season": {
                    "type": "string",
                    "description": "The season to get the roster for. Format: YYYYYYYY (e.g. 20192020)",
                },
            },

            "required": ["team_name"],
        },
    },
    {
        "name": "get_standings",
        "description": "Get the standings for a specific season from the NHL API",
        "parameters": {
            "type": "object",
            "properties": {
                "season": {
                    "type": "string",
                    "description": "The season to get the standings for. Format: YYYYYYYY (e.g. 20192020)",
                },
            },
            "required": ["season"],
        },
    },
]