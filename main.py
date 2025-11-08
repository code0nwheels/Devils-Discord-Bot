import os
import discord
from util import settings
from util.logger import setup_logger
from discord.ext import commands
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
bot = commands.Bot(intents=intents)
bot.remove_command('help')
bot.owner_id = os.getenv("OWNER_ID")
cfg = settings.Settings()
log = setup_logger(__name__, 'log/main.log')

# loop through the cogs directory and load all the cogs
for filename in os.listdir('./cogs'):
	if filename.endswith('.py'):
		bot.load_extension(f'cogs.{filename[:-3]}')
	else:
		#cogs within a folder; load them recursively
		bot.load_extension(f'cogs.{filename}', recursive=True)

ran = False

@bot.event
async def on_ready():
	global ran

	if not ran:
		lock_file = 'lock'
		if os.path.exists(lock_file):
			os.remove(lock_file)
			
		log.info(f'client connected as {bot.user}')

		ran = True

try:
	bot.run(token)
except Exception:
	log.exception('uh oh')