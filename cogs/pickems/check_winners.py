from hockey.schedule import Schedule
from hockey.game import Game
from database.pickems_database import PickemsDatabase

from datetime import datetime, timedelta, timezone, time

import logging
from logging.handlers import RotatingFileHandler

from discord.ext import tasks, commands

import asyncio
import pytz

class CheckWinners(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.schedule = Schedule()
        self.db = PickemsDatabase()

        self.log = logging.getLogger(__name__)
        handler = RotatingFileHandler('log/check_winners.log', maxBytes=5*1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self.run.start()

    async def get_picked_teams(self, date=None):
        user_picks = {}
        if not date:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
        picks = await self.db.get_picks(date)
        for pick in picks:
            if pick[0] in user_picks:
                user_picks[pick[0]].append(pick[1])
            else:
                user_picks[pick[0]] = [pick[1]]
        
        return user_picks
    
    @tasks.loop(time=time(hour=6, minute=0, tzinfo=timezone.utc))
    async def run(self):
        try:
            now = datetime.now(pytz.timezone('US/Eastern'))
            if now.hour != 2:
                await asyncio.sleep(3600)

            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            self.schedule.set_date(yesterday)
            await self.schedule.fetch_full_schedule()
            games: list[Game] = await self.schedule.get_schedule()

            for game in games:
                if game.is_ppd:
                    games.remove(game)
                    await self.db.delete_picks(game.game_id)

            if games:
                winners = [game.winning_team.id for game in games]
                user_picks = await self.get_picked_teams()
                for user in user_picks:
                    for pick in user_picks[user]:
                        await self.db.update_record(user, pick in winners)
        except Exception as e:
            self.log.exception("Error checking winners")

    @run.before_loop
    async def before_run(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(CheckWinners(bot))