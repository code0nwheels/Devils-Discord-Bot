from datetime import time, timezone, datetime
import pytz
import asyncio

import discord
from discord.ext import tasks, commands
from discord.utils import get

from util import settings

class Shiny(commands.Cog):
    def __init__(self, bot: discord.Bot):
        print('Shiny Cog Loaded')
        self.bot = bot
        self.cfg = settings.Settings()

        self.shiny.start()

    def cog_unload(self):
        self.shiny.cancel()
        print('Shiny Cog Unloaded')

    @tasks.loop(time=time(hour=19, minute=15, tzinfo=timezone.utc))
    async def shiny(self):
        # check if sunday
        if datetime.now().weekday() != 6:
            return
        # check if really 3:15 eastern time
        now = datetime.now(pytz.timezone('US/Eastern'))
        if now.hour != 15:
            # not dst. wait an hour
            await asyncio.sleep(3600)

        channel = get(self.bot.get_all_channels(), name="sports")
        await channel.send("https://fxtwitter.com/heatdaddy69420/status/1571578791901929472")
    
    @shiny.before_loop
    async def before_shiny(self):
        await self.bot.wait_until_ready()

def setup(bot: discord.Bot):
    bot.add_cog(Shiny(bot))