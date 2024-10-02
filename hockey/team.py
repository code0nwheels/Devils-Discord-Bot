from typing import Optional
import discord
import aiohttp

API_URL = 'https://records.nhl.com/site/api/franchise?include=teams.id&include=teams.active&include=teams.triCode&include=teams.placeName&include=teams.commonName&include=teams.fullName&include=teams.logos&include=teams.conference.name&include=teams.division.name'

class Team:
    def __init__(self, team_id: int):
        """
        Initialize the Team object with team data.
        """
        self.team_id = team_id
        self.team = {}

    @classmethod
    async def init(cls, team_id: int):
        self = cls(team_id)
        await self._fetch_team()
        return self
    
    async def _fetch_team(self) -> None:
        """
        Fetch team data from the API and store it in the team object.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL.format(self.team_id)) as response:
                    response.raise_for_status()
                    data = await response.json()

            for franchise in data['data']:
                for team in franchise['teams']:
                    if team['id'] == self.team_id:
                        self.team = team
        except Exception as e:
            print(f"Failed to fetch team data: {e}")

    @property
    def id(self) -> Optional[int]:
        """
        Get the ID of the team.
        """
        return self.team.get('id')
    
    @property
    def abbreviation(self) -> Optional[str]:
        """
        Get the abbreviation of the team.
        """
        return self.team.get('triCode')

    @property
    def city(self) -> Optional[str]:
        """
        Get the city of the team.
        """
        return self.team.get('placeName')

    @property
    def division(self) -> Optional[str]:
        """
        Get the division of the team.
        """
        return self.team.get('division', {}).get('name')

    @property
    def conference(self) -> Optional[str]:
        """
        Get the conference of the team.
        """
        return self.team.get('conference', {}).get('name')

    @property
    def full_name(self) -> Optional[str]:
        """
        Get the full name of the team.
        """
        return self.team.get('fullName')

    def get_team_logo(self) -> Optional[discord.File]:
        """
        Get the logo of the team.
        """
        team_name = self.full_name
        if not team_name:
            return None
        # Remove spaces, periods, and accents
        team_name = team_name.replace(" ", "").replace(".", "").replace("é", "e")
        return discord.File(f"images/NHL/Logos/{team_name}.png", filename=f"{team_name}.png")