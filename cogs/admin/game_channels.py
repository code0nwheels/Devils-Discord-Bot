"""
Game channel management commands (open/close).
"""
import discord
from discord.ext import commands
from discord.utils import get
from util import game_channel
from util.logger import setup_logger

import os
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))


class GameChannelsMixin:
	"""Mixin for game channel commands."""
	
	@commands.slash_command(guild_ids=[guild_id], name='open', description='Opens game chat.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('message', description='Enter the message to send', required=False)
	async def open(self, ctx, message: str = None):
		self.log.info(f"{ctx.author} opened game channels")
		
		await game_channel.open_channel(self.bot, message)
		
		await ctx.respond("Game channel(s) opened!", delete_after=3)
	
	@open.error
	async def open_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to open game channels")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)
	
	@commands.slash_command(guild_ids=[guild_id], name='close', description='Closes game chat.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('message', description='Enter the message to send', required=False)
	async def close(self, ctx, message: str = None):
		self.log.info(f"{ctx.author} closed game channels")
		
		await game_channel.close_channel(self.bot, message)
		
		await ctx.respond("Game channel(s) closed!", delete_after=3)
	
	@close.error
	async def close_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to close game channels")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

