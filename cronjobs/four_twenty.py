import discord

bot = discord.Bot()

with open("../token", "r") as f:
    token = f.read()

@bot.event
async def on_ready():
    channel =  bot.get_channel(531145900169363460)
    await channel.send("Toke up mofos!")

    #close the bot
    await bot.close()

bot.run(token)