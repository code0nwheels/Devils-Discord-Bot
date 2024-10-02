from discord.ui import Button, View
from discord import ButtonStyle

from datetime import datetime
from pytz import timezone
from tzlocal import get_localzone

from hockey.game import Game
from database.pickems_database import PickemsDatabase
from util.dicts import emoji_dict, team_dict

class GameView(View):
    def __init__(self, game: Game, disabled=False) -> None:
        super().__init__()
        self.game = game

        self.db = PickemsDatabase()

        away_emoji = None
        home_emoji = None
        away_id = game.away_team_id
        home_id = game.home_team_id
        away_team = game.away_team_full_name
        home_team = game.home_team_full_name
        game_id = game.game_id
        season = game.season
        away_button_style = ButtonStyle.gray
        home_button_style = ButtonStyle.gray

        if away_id == 1:
            away_button_style = ButtonStyle.red
        elif home_id == 1:
            home_button_style = ButtonStyle.red

        if str(away_id) in emoji_dict:
            away_emoji = emoji_dict[str(away_id)]
        
        if str(home_id) in emoji_dict:
            home_emoji = emoji_dict[str(home_id)]

        away_button = Button(label=away_team, custom_id=f"{game_id}-{away_id}-{season}", emoji=away_emoji, disabled=disabled, style=away_button_style)
        self.add_item(away_button)
        away_button.callback = self.button_callback

        home_button = Button(label=home_team, custom_id=f"{game_id}-{home_id}-{season}", emoji=home_emoji, disabled=disabled, style=home_button_style)
        self.add_item(home_button)
        home_button.callback = self.button_callback

        self.timeout = None
    
    async def button_callback(self, interaction):
        localtz = get_localzone()
        esttz = timezone('US/Eastern')

        curdt = localtz.localize(datetime.now())
        est = curdt.astimezone(esttz)

        user_id = interaction.user.id
        game_id = interaction.custom_id.split('-')[0]
        team_id = interaction.custom_id.split('-')[1]
        season = interaction.custom_id.split('-')[2]
        team_name = team_dict[str(team_id)]

        pick = await self.db.get_pick(user_id, game_id)

        if pick:
            if pick != team_id:
                if await self.db.update_pick(user_id, game_id, team_id, est):
                    await interaction.response.send_message(f"Pick updated to {team_name}!", ephemeral=True, delete_after=5)
                else:
                    await interaction.response.send_message(f"Something went wrong! Try again in a few minutes.", ephemeral=True, delete_after=5)
            else:
                await interaction.response.send_message(f"You already picked {team_name}!", ephemeral=True, delete_after=5)
        else:
            if await self.db.create_pick(user_id, game_id, team_id, season, est):
                await interaction.response.send_message(f"You picked {team_name}!", ephemeral=True, delete_after=5)
            else:
                await interaction.response.send_message(f"Something went wrong! Try again in a few minutes.", ephemeral=True, delete_after=5)