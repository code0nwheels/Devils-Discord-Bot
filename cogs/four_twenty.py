from datetime import time, timezone, datetime
import pytz
import asyncio

import discord
from discord.ext import tasks
from discord.ext import commands

from util import settings

class Four_Twenty(commands.Cog):
    def __init__(self, bot: discord.Bot):
        print('Four_Twenty Cog Loaded')
        self.bot = bot
        self.cfg = settings.Settings()

        self.four_twenty.start()

    @tasks.loop(time=time(hour=20, minute=20, tzinfo=timezone.utc))
    async def four_twenty(self):
        if self.cfg.get_channels("FourTwentyChannels") is None:
            return
        # check if really 4:20 eastern time
        now = datetime.now(pytz.timezone('US/Eastern'))
        if now.hour != 16:
            # not dst. wait an hour
            await asyncio.sleep(3600)

        channel = self.bot.get_channel(self.cfg.get_channels("FourTwentyChannels")[0])
        await channel.send("Toke up mofos!")
    
    @four_twenty.before_loop
    async def before_420(self):
        await self.bot.wait_until_ready()

def setup(bot: discord.Bot):
    bot.add_cog(Four_Twenty(bot))