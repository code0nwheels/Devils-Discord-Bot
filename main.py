import os
import discord
from util import settings
from discord.ext import commands

from background.gamechannel import GameChannel

import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()
try:
	token = os.getenv("DISCORD_API_KEY")
except:
	print("No token found. Please create a .env file with the token.")
	exit()

intents = discord.Intents().default()
intents.members = True
intents.message_content = True
client = commands.Bot(intents=intents)
client.remove_command('help')
client.owner_id = 364425223388528651
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

ran = False

@client.event
async def on_ready():
	global ran

	if not ran:
		lock_file = 'lock'
		if os.path.exists(lock_file):
			os.remove(lock_file)
			
		log.info(f'client connected as {client.user}')

		"""a = client.get_cog('Admins')
		await a.setup_banished()"""

		gc = GameChannel(client, cfg)
		log.info("Starting GameChannel...")
		client.loop.create_task(gc.run())

		"""ft = FourTwenty(client, cfg)
		log.info("Starting FourTwenty...")
		client.loop.create_task(ft.run())"""

		"""hg = HomeGame(client)
		log.info("Starting HomeGame...")
		client.loop.create_task(hg.run())"""

		ran = True

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
try:
	client.run(token)
except Exception:
	log.exception('uh oh')