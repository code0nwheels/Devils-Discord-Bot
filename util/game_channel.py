import discord
from discord.utils import get
from util.settings import Settings

from hockey.game import Game

async def open_channel(bot, message=None):
    settings = Settings()
    channel_ids = await settings.get_channels("GameChannels")
    role_ids = await settings.get_roles("GameChannels")

    for channel_id in channel_ids:
        for role_id in role_ids:
            channel = bot.get_channel(int(channel_id))
            role = get(bot.guilds[0].roles, id=role_id)
            await channel.set_permissions(role, send_messages=None)
            if not message:
                await channel.send("Game chat is now open!")
            else:
                await channel.send(message)

async def close_channel(bot, message=None):
    settings = Settings()
    channel_ids = await settings.get_channels("GameChannels")
    role_ids = await settings.get_roles("GameChannels")

    for channel_id in channel_ids:
        for role_id in role_ids:
            channel = bot.get_channel(int(channel_id))
            role = get(bot.guilds[0].roles, id=role_id)
            if role in channel.overwrites:
                if channel.overwrites[role].send_messages == False:
                    continue
            
                await channel.set_permissions(role, send_messages=False)
                if not message:
                    await channel.send("Game chat is now closed!")
                else:
                    await channel.send(message)
                    
async def send_message(bot, message):
    settings = Settings()
    channel_ids = await settings.get_channels("GameChannels")
    for channel_id in channel_ids:
        channel = bot.get_channel(int(channel_id))
        await channel.send(message)

async def update_description_and_status(bot, game: Game) -> None:
        channel_category_name = "OFFSEASON"
        channel_description = ""
        bot_status = "Golf!"
        settings = Settings()
        channel_ids = await settings.get_channels("GameChannels")

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
        
        await bot.change_presence(activity=discord.Game(bot_status))

        channels = [bot.get_channel(int(channel_id)) for channel_id in channel_ids]
        categories = [channel.category for channel in channels]

        for channel in channels:
            await channel.edit(topic=channel_description)
        
        for category in categories:
            await category.edit(name=channel_category_name)