from datetime import time, timezone, datetime
import pytz
import asyncio

import discord
from discord.ext import tasks
from discord.ext import commands

from util import settings

import logging
from logging.handlers import RotatingFileHandler

class Four_Twenty(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.cfg = settings.Settings()
        self.log = logging.getLogger(__name__)
        handler = RotatingFileHandler('log/four_twenty.log', maxBytes=5*1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self.four_twenty.start()
        self.log.info("Four Twenty initialized.")

    @tasks.loop(time=time(hour=20, minute=20, tzinfo=timezone.utc))
    async def four_twenty(self):
        try:
            channel_stg = await self.cfg.get_channels("FourTwentyChannels")
            if channel_stg is None:
                return
            # check if really 4:20 eastern time
            now = datetime.now(pytz.timezone('US/Eastern'))
            if now.hour != 16:
                # not dst. wait an hour
                await asyncio.sleep(3600)

            channel = self.bot.get_channel(channel_stg[0])
            await channel.send("Toke up mofos!")
        except Exception:
            self.log.exception("Error running four_twenty")
    
    @four_twenty.before_loop
    async def before_420(self):
        await self.bot.wait_until_ready()

def setup(bot: discord.Bot):
    bot.add_cog(Four_Twenty(bot))