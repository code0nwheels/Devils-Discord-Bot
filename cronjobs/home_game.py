import discord
from datetime import datetime
import requests

# get token from file
with open('../token', 'r') as f:
    token = f.read()

class HomeGame(object):
    """docstring for HomeGame."""

    def __init__(self, bot):
        super(HomeGame, self).__init__()
        self.bot = bot

    async def post(self):
        try:
            # get nj devils game for today from api
            # get current date and format to yyyy-mm-dd
            today = datetime.now().strftime('%Y-%m-%d')

            # get game data from api
            url = f'https://api-web.nhle.com/v1/scoreboard/njd/now'
            r = requests.get(url)

            # get game data
            try:
                for date in r.json()['gamesByDate']:
                    if date['date'] != today:
                        continue
                    for game in date['games']:
                        if game['gameState'] in ('FUT', 'PRE', 'LIVE'):
                            game_info = game
                            break
            except:
                return
            

            home = game_info['homeTeam']['id']

            if home != 1:
                return # game is not at home
            else:
                away_team = game_info['awayTeam']['name']['default']
                meetup_channel = self.bot.get_channel(879491007538921532)
                message = await meetup_channel.send(f"Who's going to today's game against {away_team}? React with <:njd:562468864835846187>")
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