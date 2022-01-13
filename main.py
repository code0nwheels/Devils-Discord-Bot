import discord
from util import create_embed, settings
from discord.ext import commands

from background.gamechannel import GameChannel
from background.four_twenty import FourTwenty
from background.home_game import HomeGame

import logging
from logging.handlers import RotatingFileHandler

import os

intents = discord.Intents().default()
intents.members = True
client = commands.Bot(intents=intents)
client.remove_command('help')
client.owner_id = 364425223388528651
with open('token', 'r') as f:
	TOKEN = f.read().strip()
cfg = settings.Settings()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
# add a rotating handler
handler = RotatingFileHandler('log/main.log', maxBytes=5*1024*1024,
							  backupCount=5)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

client.load_extension('sql.database')
client.load_extension('cogs.admins')
client.load_extension('cogs.devils')
client.load_extension('cogs.reflex')
client.load_extension('cogs.help')

lockfile = "background/highlights.lock"
if os.path.exists(lockfile):
	os.remove(lockfile)

@client.event
async def on_ready():
	log.info(f'client connected as {client.user}')

	a = client.get_cog('Admins')
	await a.setup_banished()

	gc = GameChannel(client, cfg)
	log.info("Starting GameChannel...")
	client.loop.create_task(gc.run())

	ft = FourTwenty(client, cfg)
	log.info("Starting FourTwenty...")
	client.loop.create_task(ft.run())

	hg = HomeGame(client)
	log.info("Starting HomeGame...")
	client.loop.create_task(hg.run())

"""@client.command(name='reloadcog')
@commands.is_owner()
async def reloadcog(ctx, cog):
	try:
		client.reload_extension(cog)
		await ctx.send(f"Reloaded {cog}")
	except Exception as e:
		await ctx.send(f"Could not reload {cog}: {e}")

@client.command(name='loadcog')
@commands.is_owner()
async def loadcog(ctx, cog):
	try:
		client.load_extension(cog)
		await ctx.send(f"Loaded {cog}")
	except Exception as e:
		await ctx.send(f"Could not load {cog}: {e}")

@client.command(name='unloadcog')
@commands.is_owner()
async def unloadcog(ctx, cog):
	try:
		client.unload_extension(cog)
		await ctx.send(f"Unloaded {cog}")
	except Exception as e:
		await ctx.send(f"Could not unload {cog}: {e}")"""

client.run(TOKEN)
