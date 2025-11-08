"""
Incident report management commands.
"""
import discord
from discord.ext import commands, pages
from util import create_embed
from util.logger import setup_logger
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))


class IncidentsMixin:
	"""Mixin for incident report commands."""
	
	@commands.slash_command(guild_ids=[guild_id], name='create_incident', description='Create an incident report.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('user', description='Enter the user to create an incident report for')
	@discord.commands.option('description', description='Enter the description of the incident')
	@discord.commands.option('decision', description='Enter the decision of the incident')
	async def create_incident(self, ctx, user: discord.Member, description: str, decision: str):
		self.log.info(f"{ctx.author} is creating an incident report.")
		
		reported_by = str(ctx.author.id)
		reported_at = datetime.now()
		
		if await self.db.create_incident(str(user.id), description, decision, reported_by, reported_at):
			await ctx.respond("Incident report created!")
		else:
			await ctx.respond("Incident report not created!")
	
	@create_incident.error
	async def create_incident_error(self, ctx, error):
		self.log.exception("Create report error")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)
	
	@commands.slash_command(guild_ids=[guild_id], name="get_incident", description="Gets incident reports for the specified user")
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('user', description='Enter the user to get incident reports for', required=False)
	@discord.commands.option('user_id', description='Enter the user to get incident reports for', required=False)
	async def get_incident(self, ctx, user: discord.Member = None, user_id: str = None):
		if not user and not user_id:
			await ctx.respond("I can't read your mind! Enter a user.")
			return
		
		self.log.info(f"{ctx.author} is getting incident reports for user {user if user else user_id}")
		await ctx.defer()
		
		if user:
			incidents = await self.db.get_incident(str(user.id))
		else:
			incidents = await self.db.get_incident(user_id)
		
		incident_embeds = []
		if incidents is not None and len(incidents) > 0:
			for i in incidents:
				incident_embeds.append(await create_embed.incident(i[0], i[1], i[2], i[3], i[4], i[5]))
		else:
			incident_embeds = ["No incidents found for this user."]
		
		paginator = pages.Paginator(
			pages=incident_embeds,
			use_default_buttons=False,
			loop_pages=False,
			show_disabled=False,
		)
		paginator.add_button(
			pages.PaginatorButton(
				"first", label='<<', style=discord.ButtonStyle.red, loop_label="fst"
			)
		)
		paginator.add_button(
			pages.PaginatorButton(
				"prev", label="<", style=discord.ButtonStyle.green, loop_label="prv"
			)
		)
		paginator.add_button(
			pages.PaginatorButton(
				"page_indicator", style=discord.ButtonStyle.gray, disabled=True
			)
		)
		paginator.add_button(
			pages.PaginatorButton(
				"next", label='>', style=discord.ButtonStyle.green, loop_label="nxt"
			)
		)
		paginator.add_button(
			pages.PaginatorButton(
				"last", label='>>', style=discord.ButtonStyle.red, loop_label="lst"
			)
		)
		await paginator.respond(ctx.interaction, ephemeral=False)
	
	@get_incident.error
	async def get_incident_error(self, ctx, error):
		self.log.exception("Get incident error")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

