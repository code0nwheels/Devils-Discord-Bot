"""
System management commands (restart, kill, cog management, timeout).
"""
import discord
from discord.ext import commands
from util import parseduration
from util.logger import setup_logger
from datetime import datetime, timedelta

import os
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))
mod_role_id = 1468698871743119403


class SystemMixin:
	"""Mixin for system commands."""
	
	def is_mod_or_admin(self, ctx):
		"""Check if user has moderator or administrator permissions."""
		if ctx.author.guild_permissions.administrator:
			return True
		return any(role.id == mod_role_id for role in ctx.author.roles)
	
	@commands.slash_command(guild_ids=[guild_id], name='restart', description='Restarts the bot.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	async def restart(self, ctx):
		self.log.info(f"{ctx.author} is restarting the bot")
		
		await ctx.respond("BRB...")
		os.system("service bryce restart")
	
	@restart.error
	async def restart_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to restart the bot")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)
	
	@commands.slash_command(guild_ids=[guild_id], name='kill', description='Kills the bot.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	async def kill(self, ctx):
		self.log.info(f"{ctx.author} is killing the bot")
		
		await ctx.respond("Goodbye cruel world!")
		os.system("service bryce stop")
	
	@kill.error
	async def kill_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to kill the bot")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)
	
	@commands.slash_command(guild_ids=[guild_id], name='loadcog', description='Load a cog.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('cog', description='Enter the cog to load')
	async def loadcog(self, ctx, cog: str):
		self.log.info(f"{ctx.author} is loading cog {cog}")
		
		try:
			self.bot.load_extension(f'cogs.{cog}')
			await ctx.respond(f"Cog {cog} loaded!")
		except Exception as e:
			self.log.exception("Error loading cog")
			await ctx.respond(f"Error loading cog: {e}")
	
	@loadcog.error
	async def loadcog_error(self, ctx, error):
		self.log.exception("Load cog error")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)
	
	@commands.slash_command(guild_ids=[guild_id], name='unloadcog', description='Unload a cog.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('cog', description='Enter the cog to unload')
	async def unloadcog(self, ctx, cog: str):
		self.log.info(f"{ctx.author} is unloading cog {cog}")
		
		try:
			self.bot.unload_extension(f'cogs.{cog}')
			await ctx.respond(f"Cog {cog} unloaded!")
		except Exception as e:
			self.log.exception("Error unloading cog")
			await ctx.respond(f"Error unloading cog: {e}")
	
	@unloadcog.error
	async def unloadcog_error(self, ctx, error):
		self.log.exception("Unload cog error")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)
	
	@commands.slash_command(guild_ids=[guild_id], name='reloadcog', description='Reload a cog.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('cog', description='Enter the cog to reload')
	async def reloadcog(self, ctx, cog: str):
		self.log.info(f"{ctx.author} is reloading cog {cog}")
		
		try:
			extensions = set(self.bot.extensions.keys())
			for extension in extensions:
				if cog in extension:
					self.bot.reload_extension(extension)
			await ctx.respond(f"Cog {cog} reloaded!")
		except Exception as e:
			self.log.exception("Error reloading cog")
			await ctx.respond(f"Error reloading cog: {e}")
	
	@reloadcog.error
	async def reloadcog_error(self, ctx, error):
		self.log.exception("Reload cog error")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)
	
	@commands.slash_command(guild_ids=[guild_id], name='timeout', description='Timeout users.')
	@discord.commands.option('user', description='Enter the user to timeout')
	@discord.commands.option('duration', description='Enter the duration')
	@discord.commands.option('reason', description='Enter the reason for the timeout', required=False)
	async def timeout(self, ctx, user: discord.Member, duration: str, reason: str = 'None'):
		if not self.is_mod_or_admin(ctx):
			await ctx.respond("You don't have permission to use this command!", ephemeral=True)
			return
		
		self.log.info(f"{ctx.author} is timeouting {user.name}")
		
		try:
			length_str, secs_to_add = await parseduration.parse_pretty(duration)
		except Exception as e:
			self.log.exception('Error parsing duration')
			await ctx.respond(f"Error timeouting: {e}")
			return
		
		timeouted_by = str(ctx.author.id)
		timeouted_at = datetime.now()
		untimeout_at = timedelta(seconds=secs_to_add)
		
		await user.timeout_for(untimeout_at)
		
		await ctx.respond(f"{user} has been timed out for {length_str}")
		
		await self.db.create_incident(str(user.id), reason, f"Timed out for {length_str}", timeouted_by, timeouted_at)
	
	@timeout.error
	async def timeout_error(self, ctx, error):
		self.log.exception("Timeout error")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

