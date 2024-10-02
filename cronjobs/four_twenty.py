import discord
import os
from util import settings

bot = discord.Bot()

from dotenv import load_dotenv

load_dotenv("../.env")
try:
    token = os.getenv("DISCORD_API_KEY")
except:
    print("No token found. Please create a .env file with the token.")
    exit()

@bot.event
async def on_ready():
    setting = settings.Settings()
    if setting.get("FourTwentyChannels") is None:
        return
    
    channel =  bot.get_channel(setting.get("FourTwentyChannels")[0])
    await channel.send("Toke up mofos!")

    #close the bot
    await bot.close()

bot.run(token)