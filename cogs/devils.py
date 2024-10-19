# devils.py

import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

import discord
from discord.ext import commands, pages
from discord.utils import get
from discord.commands import SlashCommandGroup
import dateparser
from dotenv import load_dotenv

from util import create_embed, settings, report_view
from util.dicts import team_dict
from hockey.schedule import Schedule

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))


class Devils(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.cfg = settings.Settings()

		# Setup logging
		self.log = logging.getLogger(__name__)
		handler = RotatingFileHandler('log/devils.log', maxBytes=5*1024*1024, backupCount=5)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		handler.setFormatter(formatter)
		self.log.addHandler(handler)
		self.log.setLevel(logging.INFO)

	game_commands = SlashCommandGroup(name="game", description="Commands related to games.")

	@game_commands.command(guild_ids=[guild_id], name='fetch_game', description='Gets game for a specific date. Defaults to today.')
	@discord.commands.option(name="date", description="Enter a date. Omit for today.", required=False)
	async def fetch_game(self, ctx, date: str = None):
		self.log.info(f"{ctx.author} is requesting a game for {date or 'today'}...")
		try:
			date = datetime.strftime(dateparser.parse(date) if date else datetime.now(), "%Y-%m-%d")
		except Exception:
			self.log.exception("Error parsing date")
			await ctx.respond("Unrecognized date format")
			return

		schedule = Schedule(date)
		await schedule.fetch_team_schedule("njd")
		game = await schedule.get_game()

		if game:
			await self._send_game_embed(ctx, game, "/game")
		else:
			await self._send_no_game_embed(ctx, date, "/game")

	@fetch_game.error
	async def fetch_game_error(self, ctx, error):
		self.log.exception("Error processing the game command")
		await ctx.respond("Oops, something went wrong.")

	async def _send_game_embed(self, ctx, game, path):
		try:
			file, embed = await create_embed.create_game(game, path)
			await ctx.respond(file=file, embed=embed)
		except Exception:
			self.log.exception("Error creating game embed")
			await ctx.respond("Oops, something went wrong.")

	async def _send_no_game_embed(self, ctx, date, path, no_date=False):
		try:
			file, embed = await create_embed.no_game(date, path, no_date=no_date)
			await ctx.respond(file=file, embed=embed)
		except Exception:
			self.log.exception("Error creating no game embed")
			await ctx.respond("Oops, something went wrong.")

	async def _get_x_games(self, ctx, x, games):
		self.log.info(f"{ctx.author} is requesting the next {x} games...")
		
		# Limit the number of games to the requested number or fewer
		games = games[:x] if games else []
		print(games)

		if not games:
			await self._send_no_game_embed(ctx, '', "/nextgame")
			return

		pages_ = []

		# Correctly await the coroutine and get the results
		for g in games:
			file, embed = await create_embed.create_game(g, "/nextgame")
			pages_.append(pages.Page(embeds=[embed], files=[file]))

		paginator = pages.Paginator(pages=pages_, loop_pages=False)
		await paginator.respond(ctx.interaction, ephemeral=False)

	@game_commands.command(guild_ids=[guild_id], name='next_game', description='Gets the next upcoming game. Can specify the next time they play a specific team.')
	@discord.commands.option(name="games", description="Enter how many games in the future you want.", required=False)
	@discord.commands.option(name="team", description="Enter the team you want to see the next game against.", autocomplete=lambda ctx: sorted([team for team in team_dict.values() if team.lower().startswith(ctx.value.lower())]), required=False)
	async def next_game(self, ctx, games: int = None, team: str = None):
		self.log.info(f"{ctx.author} is requesting the next game(s)")
		await ctx.defer()
		num_games = games or 1
		schedule = Schedule()

		await schedule.fetch_team_schedule("njd")

		if not team:
			game_info = await schedule.get_schedule(num_games) if num_games > 1 else [await schedule.get_next_game()]

			game_info = [g for g in game_info if g and not (g.is_final or g.is_ppd or g.is_cancelled)]
			self.log.info(f"Game info: {game_info}")
			if game_info:
				await self._get_x_games(ctx, num_games, game_info)
			else:
				await self._send_no_game_embed(ctx, '', "/nextgame")
		else:
			team_id = next(key for key, value in team_dict.items() if value == team)
			game = await schedule.get_next_time_playing_opponent(int(team_id))
			if game:
				await self._send_game_embed(ctx, game, "/nextgame")
			else:
				await self._send_no_game_embed(ctx, '', "/nextgame", no_date=True)

	@next_game.error
	async def next_game_error(self, ctx, error):
		self.log.exception("Error processing the nextgame command")
		await ctx.respond("Oops, something went wrong.")

	@commands.slash_command(guild_ids=[guild_id], name='report', description='Report a message that breaks a rule.')
	@discord.commands.option(name="message_link", description="Enter the message link in violation.", required=True)
	@discord.commands.option(name="violation", description="Enter the violation.", required=True)
	async def report(self, ctx, message_link: str, violation: str):
		self.log.info(f"{ctx.author} is reporting a message")
		if not self._is_valid_message_link(message_link):
			await ctx.respond(self._invalid_link_message(), ephemeral=True)
			return

		try:
			message_obj = await commands.MessageConverter().convert(ctx, message_link)
		except:
			await ctx.respond("I couldn't find that message. Could it be deleted?", ephemeral=True)
			return

		await self._send_report(ctx, message_obj, violation)

	@report.error
	async def report_error(self, ctx, error):
		self.log.exception("Error processing the report command")
		#await ctx.respond("If you're seeing this, something went critically wrong. Sorry =/", ephemeral=True)

	def _is_valid_message_link(self, message_link: str) -> bool:
		return message_link.startswith("https") and "discord.com" in message_link and len(message_link[8:].split('/')) == 5

	def _invalid_link_message(self) -> str:
		return ("Invalid link. Please try again.\n\n"
				"**On Desktop:** Right-click the message > Copy Message Link\n"
				"**On Mobile:**\n"
				"**Android**: Hold the message > Share > Copy\n"
				"**iOS**: Hold the message > Copy Message Link")

	async def _send_report(self, ctx, message_obj, violation):
		channel = get(ctx.guild.text_channels, name="member-reports")
		embed = await create_embed.create('Report', f"Message author: {message_obj.author} ({message_obj.author.id})",
										  ["Violation", "Content", "URL"], 
										  [violation, message_obj.content, f"[Click here to view]({message_obj.jump_url})"],
										  f"Reported by {ctx.author} ({ctx.author.id})")
		admin_role = get(ctx.guild.roles, name="Admins")
		view = report_view.ReportView(message_obj)
		await channel.send(admin_role.mention, embed=embed, view=view)
		self.bot.add_view(view)
		await ctx.respond("Thank you! I have notified the team.", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='openhelp', description='Talk with the Admins in a private channel.')
	@discord.commands.option(name="brief_description", description="Enter a brief message of what you want to discuss.", required=False)
	async def openhelp(self, ctx, brief_description: str = None):
		self.log.info(f"{ctx.author} is opening a help thread")

		modmail_chan_id = await self.cfg.get_channels("ModMailChannels")
		modmail_chan = get(ctx.guild.text_channels, id=modmail_chan_id[0])
		existing_thread = self._find_existing_thread(ctx, modmail_chan.threads)

		if existing_thread:
			await ctx.respond(f"You already have a help thread open! {existing_thread.mention}", ephemeral=True)
			return

		thread = await modmail_chan.create_thread(name=f"{ctx.author.name.lower()}-{len(modmail_chan.threads) + len(await modmail_chan.archived_threads().flatten()) + 1}")
		embed = await create_embed.create(f'{ctx.author} ({ctx.author.id})', f"Needs help.", ["Description"], [brief_description], "")
		admin_role = get(ctx.guild.roles, name="Admins")
		await thread.send(f"{ctx.author.mention} {admin_role.mention}", embed=embed)
		await ctx.respond(f"Thank you! I have notified the team. Your thread is {thread.mention}", ephemeral=True)

	def _find_existing_thread(self, ctx, threads):
		return next((thread for thread in threads if str(ctx.author).lower().replace('#', '') in thread.name and not thread.archived), None)

	@openhelp.error
	async def openhelp_error(self, ctx, error):
		self.log.exception(f"Error processing the openhelp command: {error}")
		await ctx.respond("If you're seeing this, something went critically wrong. Sorry =/", ephemeral=True)


def setup(bot):
	bot.add_cog(Devils(bot))
