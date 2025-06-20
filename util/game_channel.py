import discord
from discord.utils import get
from util.settings import Settings
import logging

# Enable detailed logging for game channel operations
DEBUG_MODE = True

from hockey.game import Game

# Configure logging
logger = logging.getLogger(__name__)
if DEBUG_MODE:
    logger.setLevel(logging.DEBUG)
    # Add handler if not already added
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

async def open_channel(bot, message=None):
    settings = Settings()
    channel_ids = await settings.get_channels("GameChannels")
    role_ids = await settings.get_roles("GameChannels")

    logger.info(f"Opening {len(channel_ids)} game channels for {len(role_ids)} roles")
    
    for channel_id in channel_ids:
        try:
            channel = bot.get_channel(int(channel_id))
            if not channel:
                logger.warning(f"Channel ID {channel_id} not found")
                continue
                
            for role_id in role_ids:
                try:
                    role = get(bot.guilds[0].roles, id=int(role_id))
                    if not role:
                        logger.warning(f"Role ID {role_id} not found")
                        continue
                        
                    if role in channel.overwrites:
                        if channel.overwrites[role].send_messages:
                            logger.debug(f"Channel {channel.name} already open for role {role.name}")
                            continue
                    
                    logger.debug(f"Setting permissions for {role.name} in {channel.name}")
                    await channel.set_permissions(role, send_messages=True, view_channel=True)
                except Exception as e:
                    logger.error(f"Error setting permissions for role {role_id}: {str(e)}")
            
            # Send message after setting permissions
            try:
                if message:
                    await channel.send(message)
                else:
                    await channel.send("Game chat is now open!")
                logger.info(f"Sent open message to {channel.name}")
            except Exception as e:
                logger.error(f"Error sending open message to {channel.name}: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error opening channel {channel_id}: {str(e)}")

async def close_channel(bot, message=None):
    settings = Settings()
    channel_ids = await settings.get_channels("GameChannels")
    role_ids = await settings.get_roles("GameChannels")
    
    logger.info(f"Attempting to close {len(channel_ids)} game channels for {len(role_ids)} roles")

    for channel_id in channel_ids:
        try:
            channel = bot.get_channel(int(channel_id))
            if not channel:
                logger.warning(f"Channel ID {channel_id} not found")
                continue
                
            permissions_changed = False
            
            for role_id in role_ids:
                try:
                    role = get(bot.guilds[0].roles, id=int(role_id))
                    if not role:
                        logger.warning(f"Role ID {role_id} not found")
                        continue
                        
                    if role in channel.overwrites:
                        perms = channel.overwrites[role]
                        if perms.send_messages:
                            logger.debug(f"Closing permissions for {role.name} in {channel.name}")
                            await channel.set_permissions(role, send_messages=False, view_channel=True)
                            permissions_changed = True
                except Exception as e:
                    logger.error(f"Error closing permissions for role {role_id}: {str(e)}")
            
            # Send closing message only after processing all roles for this channel
            if permissions_changed or message:
                logger.info(f"Sending closing message to channel {channel.name}")
                try:
                    if message:
                        await channel.send(message)
                    else:
                        await channel.send("Game chat is now closed!")
                except Exception as e:
                    logger.error(f"Error sending closing message to {channel.name}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error closing channel {channel_id}: {str(e)}")
                    
async def send_message(bot, message):
    settings = Settings()
    channel_ids = await settings.get_channels("GameChannels")
    
    logger.info(f"Sending message to {len(channel_ids)} game channels")
    
    for channel_id in channel_ids:
        try:
            channel = bot.get_channel(int(channel_id))
            if not channel:
                logger.warning(f"Channel ID {channel_id} not found")
                continue
                
            await channel.send(message)
            logger.debug(f"Message sent to channel {channel.name}")
        except Exception as e:
            logger.error(f"Error sending message to channel {channel_id}: {str(e)}")

async def update_description_and_status(bot, game: Game) -> None:
    try:
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
            bot_status = f"{game.playing_against_abbr} on {game_date} {game_time_category}"
        
        await bot.change_presence(activity=discord.Game(bot_status))

        channels = []
        for channel_id in channel_ids:
            try:
                channel = bot.get_channel(int(channel_id))
                if channel:
                    channels.append(channel)
            except Exception as e:
                logger.error(f"Error getting channel {channel_id}: {str(e)}")
        
        categories = [channel.category for channel in channels if channel.category]

        for channel in channels:
            try:
                await channel.edit(topic=channel_description)
            except Exception as e:
                logger.error(f"Error updating description for {channel.name}: {str(e)}")
        
        for category in categories:
            try:
                await category.edit(name=channel_category_name)
            except Exception as e:
                logger.error(f"Error updating category name: {str(e)}")
    except Exception as e:
        logger.error(f"Error in update_description_and_status: {str(e)}")

async def is_closed(bot):
    settings = Settings()
    channel_ids = await settings.get_channels("GameChannels")
    role_ids = await settings.get_roles("GameChannels")
    
    logger.info(f"Checking if game channels are closed: {len(channel_ids)} channels, {len(role_ids)} roles")
    
    # If no channels or roles, consider it closed
    if not channel_ids or not role_ids:
        logger.warning("No channels or roles found, considering channels closed")
        return True
        
    for channel_id in channel_ids:
        try:
            channel = bot.get_channel(int(channel_id))
            if not channel:
                logger.warning(f"Channel ID {channel_id} not found")
                continue
                
            logger.debug(f"Checking channel: {channel.name} (ID: {channel_id})")
            
            for role_id in role_ids:
                try:
                    role = get(bot.guilds[0].roles, id=int(role_id))
                    if not role:
                        logger.warning(f"Role ID {role_id} not found")
                        continue
                    
                    logger.debug(f"Checking role: {role.name} (ID: {role_id}) in channel {channel.name}")
                    
                    if role in channel.overwrites:
                        perms = channel.overwrites[role]
                        logger.debug(f"Permissions for {role.name} in {channel.name}: send_messages={perms.send_messages}")
                        if perms.send_messages:
                            logger.info(f"Channel is open! Role {role.name} has send_messages=True in channel {channel.name}")
                            return False
                    else:
                        logger.warning(f"Role {role.name} not in channel {channel.name} overwrites")
                except Exception as e:
                    logger.error(f"Error checking role {role_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Error checking channel {channel_id}: {str(e)}")
    
    logger.info("All channels appear to be closed")
    return True
