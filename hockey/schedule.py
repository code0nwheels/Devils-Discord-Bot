import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional
from .game import Game

API_FULL_SCHEDULE_URL = 'https://api-web.nhle.com/v1/schedule/{}'
API_TEAM_SCHEDULE_URL = 'https://api-web.nhle.com/v1/club-schedule-season/{}/{}'

class Schedule:
    def __init__(self, date: str = "now"):
        """
        Initialize the Schedule object with a date.
        """
        self.schedule: List[Dict[str, Any]] = []
        self.date = date

        if date == "now":
            current_date = datetime.now()
        else:
            current_date = datetime.strptime(date, "%Y-%m-%d")

        self.date = current_date.strftime("%Y-%m-%d")
        self.season = self._calculate_season(current_date)

    @staticmethod
    def _calculate_season(date: datetime) -> str:
        """
        Calculate the season based on the given date.
        """
        if date.month > 7:
            return f"{date.year}{date.year + 1}"
        else:
            return f"{date.year - 1}{date.year}"

    async def fetch_full_schedule(self) -> None:
        """
        Fetch the full schedule for the given date.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_FULL_SCHEDULE_URL.format(self.date)) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self.schedule = data['gameWeek'][0]['games']
        except aiohttp.ClientError as e:
            print(f"Failed to fetch full schedule: {e}")

    async def fetch_team_schedule(self, team_tri_code: str) -> None:
        """
        Fetch the schedule for a specific team for the current season.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_TEAM_SCHEDULE_URL.format(team_tri_code, self.season)) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self.schedule = data['games']
        except aiohttp.ClientError as e:
            print(f"Failed to fetch team schedule: {e}")

    async def get_schedule(self, number_of_games: int = None) -> List[Game]:
        """
        Get the current schedule.
        """
        print("schedule", self.schedule)
        games = []
        if number_of_games:
            for game in self.schedule[:number_of_games]:
                games.append(await Game.init(game['id']))
        else:
            for game in self.schedule:
                games.append(await Game.init(game['id']))
        
        return games

    async def get_game(self, *, team_id: int = None) -> Optional[Game]:
        """
        Get a game for a specific team by its ID.
        """
        for game in self.schedule:
            if team_id:
                if game['awayTeam']['id'] == team_id or game['homeTeam']['id'] == team_id:
                    if game['gameType'] != 3:
                        return await Game.init(game['id'])
                    else:
                        _game = await Game.init(game['id'])
                        _game.set_round(game['seriesStatus'])['round']
                        return _game
            else:
                if game['gameDate'] == self.date:
                    if game['gameType'] != 3:
                        return await Game.init(game['id'])
                    else:
                        _game = await Game.init(game['id'])
                        _game.set_round(game['seriesStatus'])['round']
                        return _game
        return None

    async def get_game_by_id(self, game_id: int) -> Optional[Game]:
        """
        Get a game by its ID.
        """
        for game in self.schedule:
            if game['id'] == game_id:
                if game['gameType'] != 3:
                    return await Game.init(game['id'])
                else:
                    _game = await Game.init(game['id'])
                    _game.set_round(game['seriesStatus'])['round']
                    return _game
        return None
    
    async def get_next_game(self) -> Optional[Game]:
        """
        Get the next game.
        """
        for game in self.schedule:
            if game['gameDate'] > self.date or game['gameState'] in ['FUT', 'PRE']:
                if game['gameType'] != 3:
                    return await Game.init(game['id'])
                else:
                    _game = await Game.init(game['id'])
                    _game.set_round(game['seriesStatus'])['round']
                    return _game
        return None