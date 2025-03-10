from hockey.schedule import Schedule
from hockey.game import Game
from database.pickems_database import PickemsDatabase

from datetime import datetime, timedelta, timezone, time

import logging
from logging.handlers import RotatingFileHandler

from discord.ext import tasks, commands

import asyncio
import zoneinfo

eastern = zoneinfo.ZoneInfo("US/Eastern")

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
    
    def cog_unload(self):
        self.run.cancel()
        self.log.info("Pickems unloaded.")

    async def get_picked_teams(self, date=None):
        user_picks = {}
        if not date:
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
        picks = await self.db.get_picks(date)
        
        for user, pick in picks.items():
            user_picks[user] = pick
        
        return user_picks
    
    @tasks.loop(time=time(hour=2, minute=0, tzinfo=eastern))
    async def run(self):
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            self.schedule.set_date(yesterday)
            await self.schedule.fetch_full_schedule()
            games: list[Game] = await self.schedule.get_schedule()

            for game in games:
                if game.is_ppd or game.is_cancelled or not game.is_regular_season:
                    games.remove(game)

                    if game.is_ppd or game.is_cancelled:
                        await self.db.delete_picks(game.game_id)

            if games:
                now = datetime.now(eastern)
                if now.month < 7 and now.month >= 1:
                    season = str(now.year - 1) +str(now.year)
                else:
                    season = str(now.year) +str(now.year + 1)
                self.log.info(f"Checking winners for {len(games)} games.")
                winners = [game.winning_team_id for game in games]

                user_picks = await self.get_picked_teams()

                for user in user_picks:
                    for pick in user_picks[user]:
                        pick = int(pick)
                        await self.db.update_record(user, pick in winners, season)
        except Exception as e:
            self.log.exception("Error checking winners")

    @run.before_loop
    async def before_run(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(CheckWinners(bot))