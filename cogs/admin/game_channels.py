"""
Game channel management commands (open/close).
"""
import discord
from discord.ext import commands, tasks
from discord.utils import get
from util import game_channel
from util.game_channel import REMINDER_MESSAGE, REMINDER_INTERVAL
from util.logger import setup_logger

import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))


class GameChannelsMixin:
	"""Mixin for game channel commands."""
	
	def __init__(self):
		# Initialize reminder tracking
		self.last_reminder_time = None
	
	@commands.slash_command(guild_ids=[guild_id], name='open', description='Opens game chat.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('message', description='Enter the message to send', required=False)
	async def open(self, ctx, message: str = None):
		self.log.info(f"{ctx.author} opened game channels")
		
		# Append reminder to message if provided, otherwise use default with reminder
		if message:
			full_message = f"{message}\n\n{REMINDER_MESSAGE}"
		else:
			full_message = f"Game chat is now open!\n\n{REMINDER_MESSAGE}"
		
		await game_channel.open_channel(self.bot, full_message)
		
		# Start reminder task if not already running
		if not self.periodic_reminder.is_running():
			self.last_reminder_time = datetime.now()
			self.periodic_reminder.start()
			self.log.info("Started periodic reminder task")
		
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
		
		# Stop reminder task if running
		if self.periodic_reminder.is_running():
			self.periodic_reminder.cancel()
			self.last_reminder_time = None
			self.log.info("Stopped periodic reminder task")
		
		await game_channel.close_channel(self.bot, message)
		
		await ctx.respond("Game channel(s) closed!", delete_after=3)
	
	@close.error
	async def close_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to close game channels")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)
	
	@tasks.loop(minutes=1)
	async def periodic_reminder(self):
		"""Post reminder every 15 minutes while channels are open."""
		try:
			# Check if channels are still open
			is_closed = await game_channel.is_closed(self.bot)
			if is_closed:
				# Channels are closed, stop the task
				if self.periodic_reminder.is_running():
					self.periodic_reminder.cancel()
				self.last_reminder_time = None
				self.log.info("Channels closed, stopping reminder task")
				return
			
			# Check if 15 minutes have passed since last reminder
			if self.last_reminder_time:
				current_time = datetime.now()
				time_since_last_reminder = (current_time - self.last_reminder_time).total_seconds()
				if time_since_last_reminder >= REMINDER_INTERVAL:
					self.log.info("Posting periodic reminder message")
					await game_channel.send_message(self.bot, REMINDER_MESSAGE)
					self.last_reminder_time = current_time
		except Exception as e:
			self.log.error(f"Error in periodic reminder task: {str(e)}", exc_info=True)
	
	@periodic_reminder.before_loop
	async def before_periodic_reminder(self):
		await self.bot.wait_until_ready()

