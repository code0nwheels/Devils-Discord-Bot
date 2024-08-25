import discord

bot = discord.Bot()

with open("../token", "r") as f:
    token = f.read()

@bot.event
async def on_ready():
    channel =  bot.get_channel(456153889683800095)
    await channel.send("https://fxtwitter.com/heatdaddy69420/status/1571578791901929472")

    #close the bot
    await bot.close()

bot.run(token)