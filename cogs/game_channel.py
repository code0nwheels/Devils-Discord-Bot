from hockey.schedule import Schedule
from hockey.game import Game
from util import settings

import discord
from discord.ext import commands, tasks
from discord.utils import get

import logging
from logging.handlers import RotatingFileHandler

import asyncio
from datetime import datetime, timedelta

from util import game_channel

PREGAME_TIME = 60 * 30
CLOSE_DELAY = 60 * 5
CLOSE_DELAY_MESSAGE = "Closing game chat in 5 minutes."

class GameChannel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = settings.Settings()
        self.schedule = Schedule()
        self.current_game = None

        logging.basicConfig(level=logging.INFO)
        self.log = logging.getLogger(__name__)
        handler = RotatingFileHandler('log/game_channel.log', maxBytes=5*1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self.run_tasks.start()
        self.log.info("GameChannel cog initialized.")

    def cog_unload(self):
        self.run_tasks.cancel()
        self.log.info("GameChannel cog unloaded.")

    @tasks.loop(minutes=1)
    async def run_tasks(self):
        self.log.info("Running scheduled tasks.")
        await self.bot.wait_until_ready()

        await self.schedule.fetch_team_schedule("njd")
        self.current_game = await self.schedule.get_next_game()
        self.log.info(f"Fetched next game: {self.current_game}")

        if self.current_game:
            await game_channel.update_description_and_status(self.bot, self.current_game)
            ready = await self.wait_until_ready(self.current_game)
            if not ready:
                self.log.warning("Game was not ready in time.")
                return

            await self.open_game_channel(self.current_game)
            await self.wait_until_over(self.current_game)

            await self.schedule.fetch_team_schedule("njd")
            next_game = await self.schedule.get_next_game()
            self.log.info(f"Fetched next game after current: {next_game}")
            await self.close_game_channel(self.current_game, next_game)

    

    async def open_game_channel(self, game: Game) -> None:
        self.log.info("Opening game channel.")
        
        await game_channel.open_channel(self.bot, f"Game chat is now open for **{game.away_team_abbr} @ {game.home_team_abbr}**!")

    async def close_game_channel(self, cur_game: Game, next_game: Game) -> None:
        self.log.info("Closing game channel.")
        
        closing_message = ""

        if next_game:
            if cur_game.is_playoffs:
                winning_team = cur_game.winning_team_id
                if winning_team == 1:
                    if cur_game.home_team_id == 1:
                        if cur_game.home_team_wins + 1 >= 4:
                            if cur_game.round >= 4:
                                closing_message = "Game chat is now closed. We did it!"
                            else:
                                closing_message = "Game chat is now closed. See you next round!"
                    else:
                        if cur_game.away_team_wins + 1 >= 4:
                            if cur_game.round >= 4:
                                closing_message = "Game chat is now closed. We did it!"
                            else:
                                closing_message = "Game chat is now closed. See you next round!"
                else:
                    if cur_game.home_team_id == 1:
                        if cur_game.away_team_wins + 1 >= 4:
                            closing_message = "Game chat is now closed. Better luck next time!"
                    else:
                        if cur_game.home_team_wins + 1 >= 4:
                            closing_message = "Game chat is now closed. Better luck next time!"
            if not closing_message:
                next_game_datetime = next_game.raw_game_time.timestamp()
                next_game_date = f"<t:{next_game_datetime}:D>"
                next_game_time = f"<t:{next_game_datetime}:T>"
                closing_message = f"Game chat is now closed. Next game is **{next_game.away_team_abbr} @ {next_game.home_team_abbr}** on **{next_game_date}** at **{next_game_time}**!"
        else:
            if cur_game.is_playoffs:
                winning_team = cur_game.winning_team_id
                if winning_team == 1:
                    if cur_game.home_team_id == 1:
                        if cur_game.home_team_wins + 1 >= 4:
                            if cur_game.round >= 4:
                                closing_message = "Game chat is now closed. We did it!"
                            else:
                                closing_message = "Game chat is now closed. See you next round!"
                    else:
                        if cur_game.away_team_wins + 1 >= 4:
                            if cur_game.round >= 4:
                                closing_message = "Game chat is now closed. We did it!"
                            else:
                                closing_message = "Game chat is now closed. See you next round!"
                else:
                    if cur_game.home_team_id == 1:
                        if cur_game.away_team_wins + 1 >= 4:
                            closing_message = "Game chat is now closed. Better luck next time!"
                    else:
                        if cur_game.home_team_wins + 1 >= 4:
                            closing_message = "Game chat is now closed. Better luck next time!"
            else:
                closing_message = "Game chat is now closed. Enjoy the offseason!"

        await game_channel.open_channel(self.bot, CLOSE_DELAY_MESSAGE)
        await asyncio.sleep(CLOSE_DELAY)
        await game_channel.close_channel(self.bot, closing_message)

    async def wait_until_ready(self, game: Game) -> bool:
        self.log.info(f"Waiting until ready for game {game.game_id}.")
        while True:
            now = datetime.now()
            if now.minute % 30 == 0:
                if now >= game.raw_game_time - timedelta(minutes=PREGAME_TIME):
                    self.log.info("Game is ready to start.")
                    return True
                elif not game.is_scheduled:
                    self.log.warning("Game is not scheduled anymore.")
                    return False
                else:
                    await self.schedule.fetch_team_schedule("njd")
                    game_tmp: Game = await self.schedule.get_next_game()
                    if game_tmp.game_id != game.game_id:
                        self.log.warning("Game changed during wait.")
                        return False

            sleep_time = 30 - now.minute % 30
            await asyncio.sleep(sleep_time * 60)
            await game.refresh()
            self.log.info("Game refreshed during wait.")

    async def wait_until_over(self, game: Game) -> None:
        self.log.info(f"Waiting for game {game.game_id} to be over.")
        while True:
            await game.refresh()
            if game.is_final or game.is_ppd or game.is_cancelled:
                self.log.info(f"Game {game.game_id} is over or cancelled.")
                break
            await asyncio.sleep(60)

def setup(bot: commands.Bot) -> None:
    bot.add_cog(GameChannel(bot))
    logging.getLogger(__name__).info("GameChannel cog setup complete.")