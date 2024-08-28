import discord
import os

from hockey.schedule import Schedule

from util import settings

from dotenv import load_dotenv

load_dotenv("../.env")
try:
    token = os.getenv("DISCORD_API_KEY")
except:
    print("No token found. Please create a .env file with the token.")
    exit()

class HomeGame(object):
    """docstring for HomeGame."""

    def __init__(self, bot):
        super(HomeGame, self).__init__()
        self.bot = bot
        self.cfg = settings.Settings()

    async def post(self):
        try:
            schedule = Schedule()
            await schedule.fetch_team_schedule("njd")

            # get game data
            game = await schedule.get_next_game()
            

            home = await game.get_home_team()

            if home.id != 1:
                return # game is not at home
            else:
                if self.cfg.get("MeetupChannels") is None:
                    return
                
                away_team = await game.get_away_team()
                
                meetup_channel = self.bot.get_channel(self.cfg.get("MeetupChannels")[0])
                message = await meetup_channel.send(f"Who's going to today's game against {away_team.full_name}? React with <:njd:562468864835846187>")
                await message.add_reaction("<:njd:562468864835846187>")
        except Exception as e:
            print(e)

# setup bot
bot = discord.Bot()

# on ready
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

    # create home game object
    home_game = HomeGame(bot)

    # post home game message
    await home_game.post()

    # close bot
    await bot.close()

# run bot
bot.run(token)