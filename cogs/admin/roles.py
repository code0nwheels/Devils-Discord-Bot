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


class RolesMixin:
	"""Mixin for role management commands."""
	
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
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('role', description='Enter the role to give')
	@discord.commands.option('action', description='Choose the action', choices=['add', 'remove'])
	@discord.commands.option('user', description='Enter the user to give the role to')
	async def role(self, ctx, role: discord.Role, action: str, user: discord.Member):
		if action == 'add':
			await self.setrole(ctx, role, user)
		else:
			await self.unsetrole(ctx, role, user)
	
	@role.error
	async def role_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to giving a role")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

