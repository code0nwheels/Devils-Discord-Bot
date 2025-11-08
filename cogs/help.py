import discord
from discord.ext import commands, pages
from util import create_embed
from util.logger import setup_logger

import os
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))

class Help(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.log = setup_logger(__name__, 'log/help.log')

	async def create_embeds(self, commands_):
		embeds = []

		for category, cmds in commands_.items():
			embeds.append(await create_embed.help(category, cmds))

		return embeds

	async def create_pages(self, items):
		paginator = pages.Paginator(pages=items, show_disabled=False, show_indicator=True, timeout=180)

		# set up buttons
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

		return paginator

	@commands.slash_command(guild_ids=[guild_id], name='help', description='List commands the bot has.')
	async def help(self, ctx):
		cmds = {}

		bot_commands = sorted(self.bot.application_commands, key=lambda x: x.cog.__cog_name__)
		#sort the commands by cog
		for command in bot_commands:
			if command.cog and command.cog.__cog_name__ == 'Help':
				continue
			if command.cog and command.cog.__cog_name__ not in cmds:
				cmds[command.cog.__cog_name__] = [(command.name, command.description)]
			else:
				cmds[command.cog.__cog_name__].append((command.name, command.description))

		#sort the commands within each cog
		for key in cmds:
			cmds[key] = sorted(cmds[key])

		# break the commands into groups of 5; if there are more than 5 commands, name the group "key", "key 2", etc.
		# this is to prevent the embed from being too long
		tmp = {}
		for key in cmds:
			if len(cmds[key]) > 5:
				tmp[key] = cmds[key][:5]
				for i in range(1, len(cmds[key]) // 5):
					tmp[f"{key} {i + 1}"] = cmds[key][i * 5:(i + 1) * 5]
			else:
				tmp[key] = cmds[key]
			
		cmds = tmp

		help_embeds = await self.create_embeds(cmds)
		paginator = await self.create_pages(help_embeds)

		await paginator.respond(ctx.interaction, ephemeral=True)

	@help.error
	async def help_error(self, ctx, error):
		self.log.exception("Error")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

def setup(bot: commands.Bot):
	bot.add_cog(Help(bot))
