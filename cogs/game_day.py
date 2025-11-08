from discord.ext import commands, tasks
from discord.utils import get
from datetime import datetime, timezone, time
import zoneinfo
import asyncio

from hockey.schedule import Schedule
from util.logger import setup_logger

eastern = zoneinfo.ZoneInfo("US/Eastern")

class GameDay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = setup_logger(__name__, 'log/game_day.log')

        self.check_game_day.start()
        self.log.info("GameDay initialized.")

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=eastern))
    async def check_game_day(self):
        hockey_chat = get(self.bot.get_all_channels(), name="hockey-chat")
        game_chat = get(self.bot.get_all_channels(), name="game-chat")
        schedule = Schedule(datetime.now().strftime("%Y-%m-%d"))
        await schedule.fetch_team_schedule("njd")
        game = await schedule.get_game()

        if game:
            self.log.info("Posting game day message")
            game_time = game.raw_game_time.astimezone(eastern).timestamp()
            discord_epoch = f"<t:{int(game_time)}:t>"

            # send to both channels simultaneously
            tasks_to_run = []
            
            message = f"It's game day! We're playing the {game.playing_against} at {discord_epoch}."
            tasks_to_run.append(hockey_chat.send(message))
            tasks_to_run.append(game_chat.send(message))
            await asyncio.gather(*tasks_to_run)

    @check_game_day.before_loop
    async def before_check_game_day(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(GameDay(bot))