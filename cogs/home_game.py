from datetime import time, timezone, datetime
import pytz
import asyncio

import discord
from discord.ext import tasks
from discord.ext import commands

from hockey.schedule import Schedule

from util import settings

class Home_Game(commands.Cog):
    def __init__(self, bot: discord.Bot):
        print('Home_Game Cog Loaded')
        self.bot = bot
        self.cfg = settings.Settings()

        self.home_game.start()

    @tasks.loop(time=time(hour=7, minute=0, tzinfo=timezone.utc))
    async def home_game(self):
        if self.cfg.get_channels("MeetupChannels") is None:
            return
        # check if really 3am eastern
        now = datetime.now(pytz.timezone('US/Eastern'))
        if now.hour != 3:
            # not dst. wait an hour
            await asyncio.sleep(3600)

        try:
            schedule = Schedule()
            await schedule.fetch_team_schedule("njd")

            # get game data
            game = await schedule.get_next_game()

            if not game or not game.is_today:
                return

            home = await game.get_home_team()

            if home.id != 1:
                return # game is not at home
            else:
                away_team = await game.get_away_team()
                
                meetup_channel = self.bot.get_channel(self.cfg.get_channels("MeetupChannels")[0])
                message = await meetup_channel.send(f"Who's going to today's game against {away_team.full_name}? React with <:njd:562468864835846187>")
                await message.add_reaction("<:njd:562468864835846187>")
        except Exception as e:
            print(e)
    
    @home_game.before_loop
    async def before_hg(self):
        await self.bot.wait_until_ready()

def setup(bot: discord.Bot):
    bot.add_cog(Home_Game(bot))