import asyncio
from datetime import datetime, timezone, time
import pytz

from discord.utils import get
from discord.ext import tasks, commands

from database import pickems_database
from util import leaderboard

import logging
from logging.handlers import RotatingFileHandler

class PostLeaderboard(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.db = pickems_database.PickemsDatabase()
        self.log = logging.getLogger(__name__)
        handler = RotatingFileHandler('log/leaderboard.log', maxBytes=5*1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self.run.start()
        self.log.info("Leaderboard initialized.")

    @tasks.loop(time=time(hour=8, minute=30, tzinfo=timezone.utc))
    async def run(self):
        # loop indefinitely
        # at 4:30am EST, fetch leaderboards from db, create leaderboard embed from create_embed, and post to channel
        # then sleep until 4:30am EST the next day
        # fetch most recent records updated_at from db
        try:
            now = datetime.now(pytz.timezone('US/Eastern'))
            if now.hour != 4:
                await asyncio.sleep(3600)
            records_updated = await self.db.get_records_updated_at()
            records_updated = datetime.strptime(str(records_updated), '%Y-%m-%d %H:%M:%S')
            self.log.info(f"Records updated at: {records_updated}")
            self.log.info(f"Today's date: {datetime.now().date()}")
            
            # if records_updated is today, post leaderboard
            if records_updated.date() == datetime.now().date():
                # find channel by name
                channel = get(self.bot.get_all_channels(), name='leaderboard')
                await leaderboard.post_leaderboard(channel)
        except Exception as e:
            self.log.exception("Error running leaderboard.")
    
    @run.before_loop
    async def before_run(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(PostLeaderboard(bot))