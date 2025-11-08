from datetime import time, timezone, datetime
import zoneinfo
import asyncio

import discord
from discord.ext import tasks
from discord.ext import commands

from hockey.schedule import Schedule

from util import settings
from util.logger import setup_logger

eastern = zoneinfo.ZoneInfo("US/Eastern")

class Home_Game(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.cfg = settings.Settings()
        self.log = setup_logger(__name__, 'log/home_game.log')

        self.home_game.start()
        self.log.info("Home_Game initialized.")
    
    def cog_unload(self):
        self.home_game.cancel()
        self.log.info("Home_Game Cog Unloaded")

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=eastern))
    async def home_game(self):
        try:
            channel_stg = await self.cfg.get_channels("MeetupChannels")
            if channel_stg is None:
                return

            schedule = Schedule(datetime.now().strftime("%Y-%m-%d"))
            await schedule.fetch_team_schedule("njd")

            # get game data
            game = await schedule.get_game()

            if not game:
                self.log.info("No game today")
                self.log.info(f"Game: {game}")
                return

            home = await game.get_home_team()

            if home.id != 1:
                self.log.info("Game is not at home")
                return # game is not at home
            else:
                away_team = await game.get_away_team()
                
                meetup_channel = self.bot.get_channel(channel_stg[0])
                self.log.info(f"Posting home game message for {away_team.full_name}")
                message = await meetup_channel.send(f"Who's going to today's game against {away_team.full_name}? React with <:njd:562468864835846187>")
                await message.add_reaction("<:njd:562468864835846187>")
        except Exception as e:
            self.log.exception("Error in home_game loop")
    
    @home_game.before_loop
    async def before_hg(self):
        await self.bot.wait_until_ready()

def setup(bot: discord.Bot):
    bot.add_cog(Home_Game(bot))