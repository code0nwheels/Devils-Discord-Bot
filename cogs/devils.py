import discord
from discord.ext import commands, pages
from discord.utils import get
from util import create_embed, settings
from hockey import hockey

from discord.commands import Option, permissions

from datetime import datetime
import dateparser

import aiofiles

import logging
from logging.handlers import RotatingFileHandler

with open('gid') as f:
	guild_id = int(f.read().strip())

class Devils(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.cfg = settings.Settings()

		logging.basicConfig(level=logging.INFO)
		self.log = logging.getLogger(__name__)
		# add a rotating handler
		handler = RotatingFileHandler('log/devils.log', maxBytes=5*1024*1024,
									  backupCount=5)

		# create a logging format
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		handler.setFormatter(formatter)
		self.log.addHandler(handler)

	@commands.slash_command(guild_ids=[guild_id], name='game', description='Gets game for a specific date. Defaults to today.')
	async def game(self, ctx, date: Option(str, "Enter a date. Omit for today.", required=False) = None):
		self.log.info(f"{ctx.author} is getting game for {str(date)}...")
		if date:
			try:
				date = datetime.strftime(dateparser.parse(date), "%Y-%m-%d")
			except:
				self.log.exception("Error parsing date")
				await ctx.respond("Unrecognized date format")
				return
		else:
			date = None

		is_game, game_info = await hockey.get_game(None, date)

		if is_game:
			try:
				file, embed = await create_embed.create_game(game_info, "/game")
				await ctx.respond(file=file, embed=embed)
			except Exception as e:
				self.log.exception("Error with creating game")
				await ctx.respond("Oops, something went wrong.")
		else:
			try:
				file, embed = await create_embed.no_game(date, "/game")
				await ctx.respond(file=file, embed=embed)
			except Exception as e:
				self.log.exception("Error with creating no_game")
				await ctx.respond("Oops, something went wrong.")

	@game.error
	async def game_error(self, ctx, error):
		self.log.exception("Error getting game")

		await ctx.respond("Oops, something went wrong.")

	async def get_x_games(self, ctx, x):
		self.log.info(f"{ctx.author} is getting next {x} games...")

		is_game, games = await hockey.get_next_x_games(x)

		if is_game:
			pages_ = []

			for g in games:
				file, embed = await create_embed.create_game(g, "/nextgame")
				pages_.append(pages.Page(embeds=[embed,], files=[file,]))

			paginator = pages.Paginator(
				pages=pages_,
				use_default_buttons=False,
				loop_pages=False,
				show_disabled=False,
				author_check=False
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
		else:
			file, embed = await create_embed.no_game('', "/nextgame")
			await ctx.respond(file=file, embed=embed)


	@commands.slash_command(guild_ids=[guild_id], name='nextgame', description='Gets the next upcoming game.')
	async def nextgame(self, ctx, games: Option(int, "Enter how many games in the future you want.", required=False) = None):
		if not games:
			self.log.info(f"{ctx.author} is getting the next upcoming game")
			is_game, game_info = await hockey.next_game()

			if is_game:
				try:
					file, embed = await create_embed.create_game(game_info, "/nextgame")
					await ctx.respond(embed=embed, file=file)
				except Exception as e:
					self.log.exception("Error with creating game")
					await ctx.respond("Oops, something went wrong.")
			else:
				await ctx.respond(':(')
		else:
			await self.get_x_games(ctx, games)

	@nextgame.error
	async def nextgame_error(self, ctx, error):
		self.log.exception("Error getting next game")

		await ctx.respond("Oops, something went wrong.")

	@commands.slash_command(guild_ids=[guild_id], name='lines', description='Gets lines from Dailyfaceoff.')
	async def lines(self, ctx):
		self.log.info(f"{ctx.author} is getting lines")
		async with aiofiles.open("lines.txt", mode='r') as f:
			content = await f.read()

		lines = content.split('\n===\n')

		fwd_all_string = lines[0]
		def_all_string = lines[1]
		g_all_string = lines[2]
		last_update = lines[3]

		names = ["Forwards", "Defense", "Goalies"]
		values = [fwd_all_string, def_all_string, g_all_string]

		embed = await create_embed.create('Lines', "The current lineup on DailyFaceoff", names, values, f"/lines | Updated on {last_update}")

		await ctx.respond(embed=embed)

	@lines.error
	async def lines_error(self, ctx, error):
		self.log.exception("Error getting lines")

		await ctx.respond("Oops, something went wrong.")

	@commands.slash_command(guild_ids=[guild_id], name='report', description='Report a message that breaks a rule.')
	async def report(self, ctx, message_link: Option(str, "Enter the message link in violation."), violation: Option(str, "Enter the violation.")):
		self.log.info(f"{ctx.author} is reporting a message")
		error_message = """Invalid link. Please try again.\

**On Desktop:** Right click the message > Copy Message Link
**On Mobile:**
**Android** Hold the message > Share > Copy
**iOS** Hold the message > Copy Message Link"""

		if not message_link.startswith("https") or "discord.com" not in message_link:
			await ctx.respond(error_message, ephemeral=True)
			return

		if len(message_link[8:].split('/')) != 5:
			await ctx.respond(error_message, ephemeral=True)
			return

		try:
			messageObj = await commands.MessageConverter().convert(ctx, message_link)
		except:
			await ctx.respond("I couldn't find that message. Could it be deleted?", ephemeral=True)
			return

		channel = get(ctx.guild.text_channels, name="member-reports")

		names = ["Violation", "Content", "URL"]
		values = [violation, messageObj.content, f"[Click here to view]({message_link})"]

		embed = await create_embed.create('Report', f"Message author: {messageObj.author} ({messageObj.author.id})", names, values, f"Reported by {ctx.author} ({ctx.author.id})")

		admin_role = get(ctx.guild.roles, id=348226061076791298)
		await channel.send(admin_role.mention, embed=embed)

		await ctx.respond("Thank you! I have notified the team.", ephemeral=True)

	@report.error
	async def report_error(self, ctx, error):
		self.log.exception("Error with the report command")

		await ctx.respond("If you're seeing this, something went critically wrong. Sorry =/", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='openhelp', description='Talk with the Admins in a private channel.')
	async def openhelp(self, ctx, brief_description: Option(str, "Enter a brief message of what you want to discuss.")):
		self.log.info(f"{ctx.author} is opening a help thread")

		modmail_chan_id = await self.cfg.get_channels("ModMailChannels")
		modmail_chan = get(ctx.guild.text_channels, id=modmail_chan_id[0])

		no_of_active_threads = len(modmail_chan.threads)
		archived_threads = modmail_chan.archived_threads(private=True)
		no_of_archived_threads = len(await archived_threads.flatten())
		no_of_threads = no_of_active_threads + no_of_archived_threads

		for thread_ in modmail_chan.threads:
			if str(ctx.author).lower().replace('#', '') in thread_.name:
				if not thread_.archived:
					await ctx.respond(f"You already have a help thread open! {thread_.mention}", ephemeral=True)
					return


		thread = await modmail_chan.create_thread(name=str(ctx.author).lower() + f"-{no_of_threads+1}")

		names = ["Description"]
		values = [brief_description]

		embed = await create_embed.create(f'{ctx.author} ({ctx.author.id})', f"Needs help.", names, values, "")

		admin_role = get(ctx.guild.roles, id=348226061076791298)
		await thread.send(f"{ctx.author.mention} {admin_role.mention}", embed=embed)

		await ctx.respond(f"Thank you! I have notified the team. Your thread is {thread.mention}", ephemeral=True)

	@openhelp.error
	async def openhelp_error(self, ctx, error):
		self.log.error(f"Error with the openhelp command: {error}")

		await ctx.respond("If you're seeing this, something went critically wrong. Sorry =/", ephemeral=True)

def setup(bot):
	bot.add_cog(Devils(bot))
