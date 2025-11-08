"""
Banish/unbanish commands and timer management.
"""
import discord
from discord.ext import commands
from discord.utils import get
from util import parseduration, timer
from util.logger import setup_logger
from datetime import datetime, timedelta

import os
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))


class BanishMixin:
	"""Mixin for banish/unbanish commands."""
	
	def __init__(self):
		"""Initialize banish timers dictionary."""
		self.banish_timers = {}
	
	async def setup_banished(self):
		"""Set up banished users from database."""
		banished_user_data = await self.db.get_banished()
		for d in banished_user_data:
			user = get(self.bot.guilds[0].members, id=int(d[0]))
			
			if user:
				unbanish_at = d[1]
				
				if datetime.now() >= unbanish_at:
					await self._unbanish_cb(user)
				else:
					total_banish_secs = (unbanish_at - datetime.now()).total_seconds()
					timer_ = timer.Timer(total_banish_secs, self._unbanish_cb, user)
					self.banish_timers[str(user.id)] = timer_
	
	async def _unbanish_cb(self, user: discord.Member, ctx=None, reply=False):
		"""Callback for unbanishing a user."""
		if not reply:
			self.log.info(f"Bot is unbanishing {user}")
		else:
			self.log.info(f"{ctx.author} is unbanishing {user}")
		
		nitro_role = get(self.bot.guilds[0].roles, name='Nitro Booster')
		
		user_id = str(user.id)
		if reply:
			unbanished_by = str(ctx.author.id)
		else:
			unbanished_by = str(self.bot.user.id)
		unbanished_at = datetime.now()
		
		try:
			is_banished, is_updated, roles = await self.db.create_unbanish(user_id, unbanished_by, unbanished_at)
			if is_banished:
				if reply:
					await ctx.respond("User isn't banished!")
				return
			if not is_updated:
				if reply:
					await ctx.respond("Could not update banishment in database. Someone fix manually!")
		except Exception as e:
			self.log.exception("Error unbanishing")
			if reply:
				await ctx.respond("Could not update banishment in database. Someone fix manually.")
		
		add_roles = []
		roles = roles.split(',')
		for role in roles:
			add_roles.append(get(self.bot.guilds[0].roles, id=int(role)))
		
		if nitro_role in user.roles:
			add_roles.append(nitro_role)
		
		await user.edit(roles=add_roles)
		
		if nitro_role in user.roles:
			vip_channel = get(self.bot.guilds[0].channels, name='vip-lounge')
			await vip_channel.set_permissions(user, overwrite=None)
		
		if reply:
			await ctx.respond("User unbanished successfully!")
			
			timer_ = self.banish_timers.pop(str(user.id))
			timer_.cancel()
	
	@commands.slash_command(guild_ids=[guild_id], name='banish', description='Banish users.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('user', description='Enter the user to banish')
	@discord.commands.option('duration', description='Enter the duration')
	@discord.commands.option('reason', description='Enter the reason for the banish', required=False)
	async def banish(self, ctx, user: discord.Member, duration: str, reason: str = 'None'):
		self.log.info(f"{ctx.author} is banishing {user.name}")
		
		try:
			length_str, secs_to_add = await parseduration.parse_pretty(duration)
		except Exception as e:
			self.log.exception('Error parsing duration')
			await ctx.respond(f"Error banishing: {e}")
			return
		
		nitro_role = get(ctx.guild.roles, name='Nitro Booster')
		
		roles = ','.join([str(role.id) for role in user.roles if nitro_role != role])
		
		user_id = str(user.id)
		banished_by = str(ctx.author.id)
		banished_at = datetime.now()
		unbanish_at = banished_at + timedelta(seconds=secs_to_add)
		total_banish_secs = (unbanish_at - banished_at).total_seconds()
		
		try:
			is_banished, added_to_db = await self.db.create_banish(user_id, roles, banished_at, unbanish_at, reason, banished_by)
			if is_banished:
				await ctx.respond('User is already banished!')
				return
			if added_to_db:
				broles = []
				for r in await self.cfg.get_roles('BanishedRole'):
					broles.append(get(ctx.guild.roles, id=int(r)))
				
				if nitro_role in user.roles:
					broles.append(nitro_role)
				
				await user.edit(roles=broles)
				
				timer_ = timer.Timer(total_banish_secs, self._unbanish_cb, user, ctx)
				await ctx.respond(f"{user} banished for {length_str}")
			else:
				await ctx.respond("Could not insert into database. Banish cancelled.")
				return
		except Exception as e:
			self.log.exception('Error')
			await ctx.respond("Could not insert into database. Banish cancelled.")
			return
		
		self.banish_timers[str(user.id)] = timer_
	
	@banish.error
	async def banish_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to banish users")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)
	
	@commands.slash_command(guild_ids=[guild_id], name='unbanish', description='Unbanish users.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('user', description='Enter the user to unbanish')
	async def unbanish(self, ctx, user: discord.Member):
		await self._unbanish_cb(user, ctx, True)
	
	@unbanish.error
	async def unbanish_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to unbanish users")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

