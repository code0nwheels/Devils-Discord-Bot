from hockey.game import Game
from hockey.schedule import Schedule
from util import settings

from discord.utils import get
from util.game_view import GameView
from util import create_embed
from database.pickems_database import PickemsDatabase

import logging
from logging.handlers import RotatingFileHandler

from discord.ext import tasks, commands

import asyncio

from datetime import time, timezone, datetime
import pytz

class Pickems(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = settings.Settings()
        self.schedule = Schedule()
        self.db = PickemsDatabase()
        
        self.log = logging.getLogger(__name__)
        handler = RotatingFileHandler('log/pickems.log', maxBytes=5*1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self.run.start()
        self.log.info("Pickems initialized.")
    
    def cog_unload(self):
        self.run.cancel()
        self.log.info("Pickems unloaded.")
    
    async def post_game(self, channel_id, embed, view):
        try:
            channel = self.bot.get_channel(channel_id)
            message = await channel.send(embed=embed, view=view)
            return f"{channel_id}-{message.id}"
        except Exception as e:
            self.log.exception("Error posting game")
            return None
    
    async def monitor_games(self, games: list[Game]):
        locked_games = []

        while True:
            for game in games:
                if game.game_id in locked_games:
                    continue

                await game.refresh()

                now = datetime.now(pytz.timezone('UTC'))

                if now >= game.raw_game_time or game.is_live or game.is_ppd:
                    message_id = await self.db.get_message(game.game_id)
                    if not message_id:
                        self.log.error(f"Game {game.game_id} is live but no message id found in db.")
                        locked_games.append(game.game_id)
                        continue

                    channel_id = int(message_id.split('-')[0])
                    message_id = int(message_id.split('-')[1])
                    channel = self.bot.get_channel(channel_id)
                    message = await channel.fetch_message(message_id)

                    buttons = message.components[0].children[0]

                    if not buttons.disabled:
                        self.log.info(f"Disabling buttons for game {game.game_id}")
                        view = GameView(game, disabled=True)
                        await message.edit(view=view)
                        locked_games.append(game.game_id)
                
                if len(locked_games) == len(games):
                    self.log.info("All games locked.")
                    return
            self.log.info(f"Lenght of locked games: {len(locked_games)} Length of games: {len(games)}")
            now = datetime.now()
            sleep_time = 60*(30 - now.minute % 30) - now.second
            await asyncio.sleep(sleep_time)

    @tasks.loop(minutes=1)
    async def run(self):
        now = datetime.now(pytz.timezone('US/Eastern'))
        if now.hour < 3:
            # sleep until 3am ET
            sleep_time = 60*(60*(3 - now.hour) - now.minute) - now.second
            self.log.info(f"Sleeping for {sleep_time} seconds.")
            await asyncio.sleep(sleep_time)

        self.schedule.set_date(now.strftime('%Y-%m-%d'))
        await self.schedule.fetch_full_schedule()
        games: list[Game] = []

        if self.schedule.schedule:
            for game_data in self.schedule.schedule:
                games.append(await Game.init(game_data['id']))

        games = [game for game in games if game.is_regular_season]

        self.log.info(f"Found {len(games)} games.")

        if games:
            for game in games:
                self.log.info(f"Checking game {game.game_id}")
                if game.is_regular_season:
                    channel = get(self.bot.get_all_channels(), name='daily-pickems')
                    message_id = await self.db.get_message(game.game_id)
                    view = GameView(game)

                    if not message_id:
                        game_id = game.game_id
                        embed = await create_embed.create_pickems_game(game)
                        message_id = await self.post_game(channel.id, embed, view)
                        if message_id is None:
                            continue
                        await self.db.create_message(message_id, game_id)

                    self.bot.add_view(view, message_id=int(message_id.split('-')[1]))

            await self.monitor_games(games)

        # sleep until 3am ET
        self.log.info("Sleeping until 3am ET")
        now = datetime.now(pytz.timezone('US/Eastern'))
        if now.hour > 3:
            sleep_time = 60*(60*(27 - now.hour) - now.minute) - now.second
        else:
            sleep_time = 60*(60*(3 - now.hour) - now.minute) - now.second

        self.log.info(f"Sleeping for {sleep_time} seconds.")
        await asyncio.sleep(sleep_time)
    
    @run.before_loop
    async def before_run(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(Pickems(bot))