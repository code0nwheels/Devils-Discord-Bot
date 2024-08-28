import discord
from discord.ext import commands, pages
from util import create_embed

import os

import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))

class Help(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

		logging.basicConfig(level=logging.INFO)
		self.log = logging.getLogger(__name__)
		# add a rotating handler
		handler = RotatingFileHandler('log/help.log', maxBytes=5*1024*1024,
									  backupCount=5)

		# create a logging format
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		handler.setFormatter(formatter)
		self.log.addHandler(handler)

	async def create_embeds(self, commands_):
		embeds = []

		for category, cmds in commands_.items():
			embeds.append(await create_embed.help(category, cmds))

		return embeds

	async def create_pages(self, items):
		paginator = pages.Paginator(pages=items, show_disabled=False, show_indicator=True, timeout=180)

		paginator.customize_button("next", button_label=">", button_style=discord.ButtonStyle.green)
		paginator.customize_button("prev", button_label="<", button_style=discord.ButtonStyle.green)
		paginator.customize_button("first", button_label="<<", button_style=discord.ButtonStyle.red)
		paginator.customize_button("last", button_label=">>", button_style=discord.ButtonStyle.red)

		return paginator

	@commands.slash_command(guild_ids=[guild_id], name='help', description='List commands the bot has.')
	async def help(self, ctx):
		cmds = {}

		for command in self.bot.application_commands:
			if command.cog and command.cog.__cog_name__ != 'Help':
				if command.cog.__cog_name__ == "Admins" and ctx.author.guild_permissions.administrator:
					if command.cog.__cog_name__ not in cmds:
						cmds[command.cog.__cog_name__] = [(command.name, command.description)]
					else:
						cog_name = command.cog.__cog_name__
						while True:
							if cog_name in cmds and len(cmds[cog_name]) == 5:
								cog_name += " cont'd"
							else:
								break
						if cog_name not in cmds:
							cmds[cog_name] = [(command.name, command.description)]
						else:
							cmds[cog_name].append((command.name, command.description))
				elif command.cog.__cog_name__ != "Admins":
					if command.cog.__cog_name__ not in cmds:
						cmds[command.cog.__cog_name__] = [(command.name, command.description)]
					else:
						cog_name = command.cog.__cog_name__
						while True:
							if cog_name in cmds and len(cmds[cog_name]) == 5:
								cog_name += " cont'd"
							else:
								break
						if cog_name not in cmds:
							cmds[cog_name] = [(command.name, command.description)]
						else:
							cmds[cog_name].append((command.name, command.description))

		help_embeds = await self.create_embeds(cmds)
		paginator = await self.create_pages(help_embeds)

		await paginator.respond(ctx, ephemeral=True)

	@help.error
	async def help_error(self, ctx, error):
		self.log.exception("Error")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

def setup(bot):
	bot.add_cog(Help(bot))
