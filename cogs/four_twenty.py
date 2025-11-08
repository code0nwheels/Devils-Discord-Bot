from datetime import time, timezone, datetime
import zoneinfo

import discord
from discord.ext import tasks
from discord.ext import commands

from util import settings
from util.logger import setup_logger

eastern = zoneinfo.ZoneInfo("US/Eastern")

class Four_Twenty(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.cfg = settings.Settings()
        self.log = setup_logger(__name__, 'log/four_twenty.log')

        self.four_twenty.start()
        self.log.info("Four Twenty initialized.")
        self.log.info(datetime.now())

    def cog_unload(self):
        self.four_twenty.cancel()
        self.log.info("Four Twenty cog unloaded.")

    @tasks.loop(time=time(hour=16, minute=20, tzinfo=eastern))
    async def four_twenty(self):
        try:
            channel_stg = await self.cfg.get_channels("FourTwentyChannels")
            if channel_stg is None:
                return
            

            channel = self.bot.get_channel(channel_stg[0])
            await channel.send("Toke up mofos!")
        except Exception:
            self.log.exception("Error running four_twenty")
    
    @four_twenty.before_loop
    async def before_420(self):
        await self.bot.wait_until_ready()

def setup(bot: discord.Bot):
    bot.add_cog(Four_Twenty(bot))