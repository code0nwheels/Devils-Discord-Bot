"""
Role management commands.
"""
import discord
from discord.ext import commands
from util.logger import setup_logger

import os
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))
mod_role_id = 1468698871743119403


class RolesMixin:
	"""Mixin for role management commands."""
	
	def is_mod_or_admin(self, ctx):
		"""Check if user has moderator or administrator permissions."""
		if ctx.author.guild_permissions.administrator:
			return True
		return any(role.id == mod_role_id for role in ctx.author.roles)
	
	async def setrole(self, ctx, role: discord.Role, user: discord.Member):
		if int(ctx.author.id) not in [364425223388528651, int(ctx.guild.owner.id)]:
			highest_role = ctx.author.roles[-1]
			all_roles = ctx.guild.roles
			
			if all_roles.index(highest_role) <= all_roles.index(role):
				await ctx.respond("You're not allowed to add a role that's equal to or above your highest role!")
				return
		
		self.log.info(f"{ctx.author} is giving {role.name} to {user.name}")
		
		if role not in user.roles:
			await user.add_roles(role)
			await ctx.respond(f"{user.name} has been given a role called: {role.name}")
		else:
			await ctx.respond(f"{user.name} already has a role called: {role.name}")
	
	async def unsetrole(self, ctx, role: discord.Role, user: discord.Member):
		if int(ctx.author.id) not in [364425223388528651, int(ctx.guild.owner.id)]:
			highest_role = ctx.author.roles[-1]
			all_roles = ctx.guild.roles
			
			if all_roles.index(highest_role) <= all_roles.index(role):
				await ctx.respond("You're not allowed to remove a role that's equal to or above your highest role!")
				return
		
		self.log.info(f"{ctx.author} is removing {role.name} from {user.name}")
		
		await user.remove_roles(role)
		
		await ctx.respond(f"{user.name} has been stripped of a role called: {role.name}")
	
	@commands.slash_command(guild_ids=[guild_id], name='role', description='Set role for users.')
	@discord.commands.option('role', description='Enter the role to give')
	@discord.commands.option('action', description='Choose the action', choices=['add', 'remove'])
	@discord.commands.option('user', description='Enter the user to give the role to')
	async def role(self, ctx, role: discord.Role, action: str, user: discord.Member):
		if not self.is_mod_or_admin(ctx):
			await ctx.respond("You don't have permission to use this command!", ephemeral=True)
			return
		if action == 'add':
			await self.setrole(ctx, role, user)
		else:
			await self.unsetrole(ctx, role, user)
	
	@role.error
	async def role_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to giving a role")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

