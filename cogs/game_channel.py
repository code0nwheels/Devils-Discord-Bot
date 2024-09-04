from hockey.schedule import Schedule
from hockey.game import Game
from util import settings

import discord
from discord.ext import commands, tasks

import logging
from logging.handlers import RotatingFileHandler

import asyncio
from datetime import datetime, timedelta

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
            await self.update_description_and_status(self.current_game)
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

    async def update_description_and_status(self, game: Game) -> None:
        self.log.info("Updating channel description and bot status.")
        channel_category_name = "OFFSEASON"
        channel_description = ""
        bot_status = "Golf!"

        if game:
            away_team_name = game.away_team_full_name
            away_team_abbr = game.away_team_abbr
            home_team_name = game.home_team_full_name
            home_team_abbr = game.home_team_abbr
            game_time_category = game.game_time("%-I:%M %p ET")
            game_date = game.game_time("%-m/%-d")

            channel_category_name = f"{away_team_abbr} @ {home_team_abbr} {game_date} {game_time_category}"
            channel_description = f"{away_team_name} @ {home_team_name} {game_date}"
            bot_status = f"{away_team_abbr} @ {home_team_abbr} {game_date} {game_time_category}"
        
        await self.bot.change_presence(activity=discord.Game(bot_status))
        self.log.info(f"Bot status updated to: {bot_status}")

        channels = await self.get_channels()
        categories = [channel.category for channel in channels]

        for channel in channels:
            await channel.edit(topic=channel_description)
            self.log.info(f"Channel {channel.id} description updated to: {channel_description}")
        
        for category in categories:
            await category.edit(name=channel_category_name)
            self.log.info(f"Category {category.id} name updated to: {channel_category_name}")

    async def open_game_channel(self, game: Game) -> None:
        self.log.info("Opening game channel.")
        channels = await self.get_channels()
        roles = await self.get_roles()
        channels_and_roles_to_update: dict[discord.TextChannel, discord.Role] = {}
        playing_against = game.away_team_name if game.home_team_id == 1 else game.home_team_name

        for channel in channels:
            for role in roles:
                if role in channel.overwrites:
                    if not channel.overwrites[role].send_messages:
                        channels_and_roles_to_update[channel] = role

        for channel, role in channels_and_roles_to_update.items():
            await channel.set_permissions(role, send_messages=True)
            await channel.send(f"Game chat is now open! We're playing the **{playing_against}**!")
            self.log.info(f"Game channel {channel.id} opened for role {role.id}.")

    async def close_game_channel(self, cur_game: Game, next_game: Game) -> None:
        self.log.info("Closing game channel.")
        channels = await self.get_channels()
        roles = await self.get_roles()
        channels_and_roles_to_update: dict[discord.TextChannel, discord.Role] = {}
        closing_message = ""

        if next_game:
            next_game_datetime = next_game.raw_game_time.timestamp()
            next_game_date = f"<t:{next_game_datetime}:D>"
            next_game_time = f"<t:{next_game_datetime}:T>"
            closing_message = f"Game chat is now closed. Next game is **{next_game.away_team_abbr} @ {next_game.home_team_abbr}** on **{next_game_date}** at **{next_game_time}**!"
        else:
            closing_message = "Game chat is now closed. Enjoy the offseason!"

        for channel in channels:
            for role in roles:
                if role in channel.overwrites:
                    if channel.overwrites[role].send_messages:
                        channels_and_roles_to_update[channel] = role

        if channels_and_roles_to_update:
            for channel in channels_and_roles_to_update.keys():
                await channel.send(CLOSE_DELAY_MESSAGE)
                self.log.info(f"Close delay message sent to channel {channel.id}.")
            await asyncio.sleep(CLOSE_DELAY)

            for channel, role in channels_and_roles_to_update.items():
                await channel.set_permissions(role, send_messages=False)
                await channel.send(closing_message)
                self.log.info(f"Game channel {channel.id} closed for role {role.id}.")

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

    async def get_channels(self) -> list[discord.TextChannel]:
        channels = []
        channel_ids = await self.cfg.get_channels("GameChannels")

        for channel_id in channel_ids:
            channels.append(self.bot.get_channel(channel_id))

        self.log.info(f"Retrieved {len(channels)} channels for game communication.")
        return channels

    async def get_roles(self) -> list[discord.Role]:
        roles = []
        role_ids = await self.cfg.get_roles("GameChannels")

        for role_id in role_ids:
            roles.append(self.bot.get_role(role_id))

        self.log.info(f"Retrieved {len(roles)} roles for game communication.")
        return roles

def setup(bot: commands.Bot) -> None:
    bot.add_cog(GameChannel(bot))
    logging.getLogger(__name__).info("GameChannel cog setup complete.")