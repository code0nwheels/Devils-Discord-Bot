import discord
import asyncio
import os
import requests

from dotenv import load_dotenv

load_dotenv()
try:
    token = os.getenv("DISCORD_API_KEY")
except:
    print("No token found. Please create a .env file with the token.")
    exit()

class BanSpyPet(object):
    """docstring for BanSpyPet."""

    def __init__(self, bot):
        super(BanSpyPet, self).__init__()
        self.bot = bot
    
    async def get_banned_ids(self):
        if not os.path.exists("../bannedspypetids.txt"):
            return []
        with open("../bannedspypetids.txt", "r") as f:
            ids = f.read().split("\n")
        
        return ids
    
    async def save_banned_ids(self, ids):
        with open("../bannedspypetids.txt", "a") as f:
            for id in ids:
                f.write(f"{id}\n")

    async def save_spypet_ids(self, ids):
        with open("../spypetids.txt", "w") as f:
            for id in ids:
                f.write(f"{id}\n")
    
    async def ban(self):
        url = "https://kickthespy.pet/ids"
        r = requests.get(url)
        already_banned = await self.get_banned_ids()
        banned_ids = []

        ids = r.json()
        # filter out already banned ids from ids
        ids = [i for i in ids if i not in already_banned]
        await self.save_spypet_ids(ids)

        ids = [int(i) for i in ids]
        guild = await self.bot.fetch_guild(348223375598157825) # your guild id
        for id in ids:
            try:
                member = await guild.fetch_member(id)
                await member.ban(reason="SpyPet account")
                print(f"Banned {member.id}")
                banned_ids.append(str(id))
                
            except Exception as e:
                print(e)
                pass
            await asyncio.sleep(1)
        
        if banned_ids:
            await self.save_banned_ids(banned_ids)

# create bot
bot = discord.Bot()

# create BanSpyPet object
bsp = BanSpyPet(bot)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    await bsp.ban()
    await bot.close()

bot.run(token)