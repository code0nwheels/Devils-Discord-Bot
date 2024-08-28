import discord
import os

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
    channel =  bot.get_channel(456153889683800095)
    await channel.send("https://fxtwitter.com/heatdaddy69420/status/1571578791901929472")

    #close the bot
    await bot.close()

bot.run(token)