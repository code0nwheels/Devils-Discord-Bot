from hockey.team import Team
from datetime import datetime, timedelta
import pytz
import aiohttp
from typing import Dict, Any

GAME_STATES = {
    "LIVE": "Live",
    "CRIT": "Live",
    "FINAL": "Final",
    "OFF": "Final",
    "OVER": "Final",
    "FUT": "Scheduled",
    "PRE": "Scheduled"
}

GAME_SCHEDULE_STATES = {
    "OK": "Scheduled",
    "TBD": "To Be Determined",
    "PPD": "Postponed",
    "SUSP": "Suspended",
    "CNCL": "Cancelled"
}

GAME_TYPES = {
    1: "Preseason",
    2: "Regular Season",
    3: "Playoffs"
}

API_URL = 'https://api-web.nhle.com/v1/gamecenter/{}/landing'

class Game:
    def __init__(self, game_id: int):
        """
        Initialize the Game object with a game ID.
        """
        self.game = None
        self.game_id = game_id
        self.game_object: Dict[str, Any] = {}

        self.round = 0
    
    @classmethod
    async def init(cls, game_id: int):
        self = cls(game_id)
        await self._fetch_game()
        return self

    async def _fetch_game(self) -> None:
        """
        Fetch game data from the API and store it in the game_object.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL.format(self.game_id)) as response:
                    response.raise_for_status()
                    data = await response.json()
                    self.game_object = data
        except Exception as e:
            print(f"Failed to fetch game data: {e}")
    
    async def refresh(self) -> None:
        """
        Refresh the game data.
        """
        await self._fetch_game()
    
    @property
    def season(self) -> str:
        """
        Get the season of the game.
        """
        return self.game_object.get('season', "Unknown")

    async def get_away_team(self) -> Team:
        """
        Get the away team information.
        """
        return await Team.init(self.game_object.get('awayTeam', {}).get('id'))

    async def get_home_team(self) -> Team:
        """
        Get the home team information.
        """
        return await Team.init(self.game_object.get('homeTeam', {}).get('id'))
    
    @property
    def away_team_abbr(self) -> str:
        """
        Get the away team's abbreviation.
        """
        return self.game_object.get('awayTeam', {}).get('abbrev', 'UNK')
    
    @property
    def home_team_abbr(self) -> str:
        """
        Get the home team's abbreviation.
        """
        return self.game_object.get('homeTeam', {}).get('abbrev', 'UNK')

    @property
    def away_team_full_name(self) -> str:
        """
        Get the away team's full name.
        """
        return self.game_object.get('awayTeam', {}).get('placeName', {}).get("default", "Unknown") + " " + self.game_object.get('awayTeam', {}).get('commonName', {}).get("default", "Unknown")
    
    @property
    def home_team_full_name(self) -> str:
        """
        Get the home team's full name.
        """
        return self.game_object.get('homeTeam', {}).get('placeName', {}).get("default", "Unknown") + " " + self.game_object.get('homeTeam', {}).get('commonName', {}).get("default", "Unknown")
    
    @property
    def away_team_name(self) -> str:
        """
        Get the away team's name.
        """
        return self.game_object.get('awayTeam', {}).get('commonName', {}).get("default", "Unknown")
    
    @property
    def home_team_name(self) -> str:
        """
        Get the home team's name.
        """
        return self.game_object.get('homeTeam', {}).get('commonName', {}).get("default", "Unknown")
    
    @property
    def away_team_id(self) -> int:
        """
        Get the away team's ID.
        """
        return self.game_object.get('awayTeam', {}).get('id', 0)
    
    @property
    def home_team_id(self) -> int:
        """
        Get the home team's ID.
        """
        return self.game_object.get('homeTeam', {}).get('id', 0)

    @property
    def game_state(self) -> str:
        """
        Get the current state of the game.
        """
        return GAME_STATES.get(self.game_object.get('gameState'), 'Unknown')

    @property
    def schedule_state(self) -> str:
        """
        Get the schedule state of the game.
        """
        return GAME_SCHEDULE_STATES.get(self.game_object.get('gameScheduleState'), 'Unknown')

    def game_time(self, format: str, timezone: str = "US/Eastern") -> str:
        """
        Get the game start time in the specified format.
        """
        utc = datetime.strptime(self.game_object['startTimeUTC'], "%Y-%m-%dT%H:%M:%SZ")
        utc = pytz.utc.localize(utc)
        return utc.astimezone(pytz.timezone(timezone)).strftime(format)
    
    @property
    def raw_game_time(self) -> datetime:
        """
        Get the raw game start time.
        """
        utctz = pytz.timezone('UTC')
        return utctz.localize(datetime.strptime(self.game_object['startTimeUTC'], "%Y-%m-%dT%H:%M:%SZ"))
    
    @property
    def raw_pregame_time(self) -> datetime:
        """
        Get the raw pregame time (30 minutes before game start).
        """
        return self.raw_game_time - timedelta(minutes=30)
    
    def pregame_time(self, format: str, timezone: str = "US/Eastern", minutes_before_start: int=30) -> str:
        """
        Get the pregame time in the specified format.
        """
        pregame_dt = self.raw_game_time - timedelta(minutes=minutes_before_start)
        return pregame_dt.astimezone(pytz.timezone(timezone)).strftime(format)

    @property
    def away_team_record(self) -> str:
        """
        Get the away team's record.
        """
        # check if regular season
        if self.is_regular_season:
            return self.game_object.get('awayTeam', {}).get('record', {})
        elif self.is_playoffs:
            return self.game_object.get('summary', {}).get('seasonSeriesWins', {}).get('awayTeamWins', "0") + "-" + self.game_object.get('summary', {}).get('seasonSeriesWins', {}).get('homeTeamWins', "0")
        else:
            return "0-0-0"
    
    @property
    def home_team_record(self) -> str:
        """
        Get the home team's record.
        """
        # check if regular season
        if self.is_regular_season:
            return self.game_object.get('homeTeam', {}).get('record', {})
        elif self.is_playoffs:
            return self.game_object.get('summary', {}).get('seasonSeriesWins', {}).get('homeTeamWins', "0") + "-" + self.game_object.get('summary', {}).get('seasonSeriesWins', {}).get('awayTeamWins', "0")
        else:
            return "0-0-0"
    
    @property
    def away_team_wins(self) -> int:
        """
        Get the number of wins for the away team.
        """
        return int(self.away_team_record.split("-")[0])
    
    @property
    def away_team_losses(self) -> int:
        """
        Get the number of losses for the away team.
        """
        return int(self.away_team_record.split("-")[1])
    
    @property
    def away_team_ot_losses(self) -> int:
        """
        Get the number of overtime losses for the away team.
        """
        if not self.is_playoffs:
            return int(self.away_team_record.split("-")[2])
        
        return 0
    
    @property
    def home_team_wins(self) -> int:
        """
        Get the number of wins for the home team.
        """
        return int(self.home_team_record.split("-")[0])
    
    @property
    def home_team_losses(self) -> int:
        """
        Get the number of losses for the home team.
        """
        return int(self.home_team_record.split("-")[1])
    
    @property
    def home_team_ot_losses(self) -> int:
        """
        Get the number of overtime losses for the home team.
        """
        if not self.is_playoffs:
            return int(self.home_team_record.split("-")[2])
        
        return 0

    @property
    def game_type(self) -> str:
        """
        Get the type of the game.
        """
        return GAME_TYPES.get(self.game_object.get('gameType'), 'Unknown')

    @property
    def venue(self) -> str:
        """
        Get the venue of the game.
        """
        return self.game_object.get('venue', {}).get('default', 'Unknown')

    @property
    def time_remaining(self) -> str:
        """
        Get the time remaining in the game.
        """
        period_descriptor = self.game_object.get('periodDescriptor', {})
        period_number = period_descriptor.get('number', 0)
        clock = self.game_object.get('clock', {}).get('timeRemaining', '00:00')

        if self.game_object.get('gameType', 0) < 3:
            periods = {1: "1st", 2: "2nd", 3: "3rd", 4: "OT", 5: "SO"}
        else:
            periods = {1: "1st", 2: "2nd", 3: "3rd"}
            if period_number > 3:
                period_number -= 3
                periods[period_number] = f"{period_number} OT"

        period = periods.get(period_number, 'Unknown')
        return f"{period} {clock}"

    @property
    def away_score(self) -> int:
        """
        Get the away team's score.
        """
        return self.game_object.get('awayTeam', {}).get('score', 0)
    
    @property
    def home_score(self) -> int:
        """
        Get the home team's score.
        """
        return self.game_object.get('homeTeam', {}).get('score', 0)
    
    @property
    def is_today(self) -> bool:
        """
        Check if the game is today.
        """
        return self.raw_game_time.date() == datetime.now().date()
    
    @property
    def is_ppd(self) -> bool:
        """
        Check if the game is postponed.
        """
        return self.schedule_state == "Postponed"
    
    @property
    def is_scheduled(self) -> bool:
        """
        Check if the game is scheduled.
        """
        return self.schedule_state == "Scheduled"
    
    @property
    def is_live(self) -> bool:
        """
        Check if the game is live.
        """
        return self.game_state == "Live"

    @property
    def is_final(self) -> bool:
        """
        Check if the game is final.
        """
        return self.game_state == "Final"
    
    @property
    def is_suspended(self) -> bool:
        """
        Check if the game is suspended.
        """
        return self.game_state == "Suspended"
    
    @property
    def is_cancelled(self) -> bool:
        """
        Check if the game is cancelled.
        """
        return self.game_state == "Cancelled"
    
    @property
    def is_tbd(self) -> bool:
        """
        Check if the game time is to be determined.
        """
        return self.schedule_state == "To Be Determined"
    
    @property
    def is_playoffs(self) -> bool:
        """
        Check if the game is a playoff game.
        """
        return self.game_type == "Playoffs"
    
    @property
    def is_regular_season(self) -> bool:
        """
        Check if the game is a regular season game.
        """
        return self.game_type == "Regular Season"
    
    @property
    def is_preseason(self) -> bool:
        """
        Check if the game is a preseason game.
        """
        return self.game_type == "Preseason"
    
    @property
    def is_overtime(self) -> bool:
        """
        Check if the game is in overtime.
        """
        return self.game_object.get('periodDescriptor', {}).get('number', 0) > 3
    
    async def winning_team(self) -> Team:
        """
        Get the winning team.
        """
        if self.away_score > self.home_score:
            return await self.get_away_team()
        else:
            return await self.get_home_team()
    
    @property
    def winning_team_id(self) -> int:
        """
        Get the winning team's ID.
        """
        if self.away_score > self.home_score:
            return self.away_team_id
        else:
            return self.home_team_id
        
    @property
    def playing_against(self) -> str:
        """
        Get the team that the home team is playing against.
        """
        if self.away_team_id == 1:
            return self.home_team_full_name
        else:
            return self.away_team_full_name
        
    @property
    def playing_against_abbr(self) -> str:
        """
        Get the team that the home team is playing against.
        """
        if self.away_team_id == 1:
            return self.home_team_abbr
        else:
            return self.away_team_abbr
        
    def set_round(self, round: int) -> None:
        """
        Set the round of the game.
        """
        self.round = round
    
    def __eq__(self, value: object) -> bool:
        """
        Check if two games are equal.
        """
        if not isinstance(value, Game):
            return False
        
        return self.game_id == value.game_id
    
    def __str__(self) -> str:
        """
        Get the string representation of the game.
        """
        return f"{self.away_team_full_name} @ {self.home_team_full_name} - {self.game_time('%Y-%m-%d %I:%M %p')}"