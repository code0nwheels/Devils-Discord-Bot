import discord
import logging
import re
from logging.handlers import RotatingFileHandler
from discord.utils import get
from discord.ext.tasks import loop
from discord.ext.commands import Bot
from pytz import timezone
from datetime import datetime, timedelta
from tzlocal import get_localzone

import asyncio

from hockey import hockey
from background.highlights import Highlights

SCORE_TEMPLATE = "{away_team} {away_score} ({away_sog}) - {home_team} {home_score} ({home_sog})"
CLOSING_TIME = 5
CLOSING_MSG = f"Closing chat in {CLOSING_TIME} minutes!"
IN_GAME_SLEEP = 1
OPEN_MSG = "Game chat is open! We're playing the **{}**"
CLOSE_MSG = "Chat is closed!\n{}"

logging.basicConfig(level=logging.INFO)

class GameChannel(object):
	"""docstring for GameChannel."""

	def __init__(self, bot, cfg):
		super(GameChannel, self).__init__()
		self.bot = bot
		self.guild = self.bot.guilds[0]
		self.cfg = cfg
		self.log = logging.getLogger(__name__)
		# add a rotating handler
		handler = RotatingFileHandler('log/gamechannel.log', maxBytes=5*1024*1024,
		                              backupCount=5)
		# create a logging format
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		handler.setFormatter(formatter)
		self.log.addHandler(handler)

	async def open_channel(self, channel_id, role_id):
		self.log.info(f"Opening {channel_id} for {role_id}...")
		try:
			channel = self.bot.get_channel(channel_id)
			role = get(self.guild.roles, id=role_id)
			await channel.set_permissions(role, read_messages=True,
															  send_messages=None)
		except Exception as e:
			self.log.exception(f"Fatal error in opening {channel_id} for {role_id}")

	async def close_channel(self, channel_id, role_id):
		self.log.info(f"Closing {channel_id} for {role_id}...")
		try:
			channel = self.bot.get_channel(channel_id)
			role = get(self.guild.roles, id=role_id)
			await channel.set_permissions(role, read_messages=True,
															  send_messages=False)
		except Exception as e:
			self.log.exception(f"Fatal error in closing {channel_id} for {role_id}")

	async def update_score(self, channel_id, new_topic):
		self.log.info(f"Updating description with new score for {channel_id}...")
		try:
			channel = self.bot.get_channel(channel_id)
			await channel.edit(topic=new_topic)
		except Exception as e:
			self.log.exception(f"Fatal error in updating score for {channel_id}")

	async def stream_role(self, role, user, add):
		if add:
			user = await self.guild.fetch_member(int(user))
			if role not in user.roles:
				await user.add_roles(role)
				await user.edit(nick='🌐 ' + user.display_name + ' 🌐')
		else:
			if '🌐' in user.display_name:
				try:
					name = re.sub('🌐', '', user.display_name).rstrip().strip()
					await user.edit(nick=name)
				except:
					await user.edit(nick=None)

			if role in user.roles:
				await user.remove_roles(role)

	async def get_score(self, game_id):
		self.log.info("In get_score...")
		try:
			worker_tasks = []
			game_info = await hockey.get_game_boxscore(game_id)
			away_team = game_info['teams']['away']['team']['name']
			home_team = game_info['teams']['home']['team']['name']
			away_score = game_info['teams']['away']['teamStats']['teamSkaterStats']['goals']
			home_score = game_info['teams']['home']['teamStats']['teamSkaterStats']['goals']
			away_sog = game_info['teams']['away']['teamStats']['teamSkaterStats']['shots']
			home_sog = game_info['teams']['home']['teamStats']['teamSkaterStats']['shots']

			self.log.info("Updating description with score")
			for channel_id in await self.cfg.get_channels('GameChannels'):
				wt = asyncio.ensure_future(self.update_score(int(channel_id), SCORE_TEMPLATE.format(away_team=away_team, away_score=away_score, away_sog=away_sog, home_team=home_team, home_score=home_score, home_sog=home_sog)))
				worker_tasks.append(wt)

			results = await asyncio.gather(*worker_tasks)

			while True:
				is_game, game_info = await hockey.get_game(game_id)
				if "In Progress" in game_info['status']['detailedState']:
					h = Highlights(self.bot, game_info['gamePk'], self.cfg)
					self.log.info("Starting Highlights...")
					try:
						self.bot.loop.create_task(h.run())
					except Exception:
						self.log.exception("Error starting Highlights")
					finally:
						break
				await asyncio.sleep(60)

			while True:
				try:
					worker_tasks = []

					game_info = await hockey.get_game_boxscore(game_id)
					away_team = game_info['teams']['away']['team']['name']
					home_team = game_info['teams']['home']['team']['name']
					away_score = game_info['teams']['away']['teamStats']['teamSkaterStats']['goals']
					home_score = game_info['teams']['home']['teamStats']['teamSkaterStats']['goals']
					away_sog = game_info['teams']['away']['teamStats']['teamSkaterStats']['shots']
					home_sog = game_info['teams']['home']['teamStats']['teamSkaterStats']['shots']

					self.log.info("Updating description with new score")
					for channel_id in await self.cfg.get_channels('GameChannels'):
						wt = asyncio.ensure_future(self.update_score(int(channel_id), SCORE_TEMPLATE.format(away_team=away_team, away_score=away_score, away_sog=away_sog, home_team=home_team, home_score=home_score, home_sog=home_sog)))
						worker_tasks.append(wt)

					results = await asyncio.gather(*worker_tasks)

					is_game, game_info = await hockey.get_game(game_id)
					if game_info['status']['detailedState'] in ['Final', 'Game Over', 'Postponed'] and away_score != home_score:
						self.log.info("Game ended. Leaving get score.")
						break

					await asyncio.sleep(IN_GAME_SLEEP * 60)
				except Exception as e:
					self.log.exception("Fatal error in getting score")
		except Exception as e:
			self.log.exception("Fatal error in getting score")

	async def send_message(self, channel_id, message):
		self.log.info(f"Sending message to {channel_id}...")
		try:
			channel = self.bot.get_channel(channel_id)
			await channel.send(message)
		except Exception as e:
			self.log.exception(f"Fatal error in sending message to {channel_id}")

	async def run(self):
		self.log.info("GameChannel started.")
		while True:
			go = True
			is_game, game_info = await hockey.is_game_today()
			worker_tasks = []

			if not is_game:
				is_game, game_info = await hockey.next_game()
				if not is_game:
					self.log.info("No game. Sleeping until 3am.")
					now = datetime.now()
					to = (now + timedelta(days = 1)).replace(hour=3, minute=0, second=0)
					#self.log.info(now, to)
					await asyncio.sleep((to - now).total_seconds())
					continue
				else:
					away = await hockey.get_team(game_info['teams']['away']['team']['id'])
					home = await hockey.get_team(game_info['teams']['home']['team']['id'])

					utctz = timezone('UTC')
					esttz = timezone('US/Eastern')
					time = game_info['gameDate']
					utc = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
					utc2 = utctz.localize(utc)
					est = utc2.astimezone(esttz)

					gmdt = datetime.strftime(est, "%Y-%m-%dT%H:%M:%S")
					self.log.info(f"Next game is {away['abbreviation']} @ {home['abbreviation']} {gmdt}.")

					while True:
						is_game, game_info = await hockey.next_game()
						if 'TBD' in game_info['status']['detailedState'] or game_info['status']['startTimeTBD']:
							time = 'TBD'
						else:
							time = datetime.strftime(est,  "%-I:%M %p")
						date = datetime.strftime(est,  "%-m/%-d")

						for channel_id in await self.cfg.get_channels('GameChannels'):
							self.log.info("Updating game channels category name")
							channel = self.bot.get_channel(int(channel_id))
							category = channel.category

							await category.edit(name=f"{away['abbreviation']} @ {home['abbreviation']} {date} {time}")

						if time != 'TBD':
							break
						else:
							self.log.info("Time is TBD. Checking again in 60min.")
							await asyncio.sleep(3600)

			pk = game_info['gamePk']
			dttime = game_info['gameDate']
			while True:
				is_game, game_info = await hockey.get_game(pk)
				if game_info['status']['detailedState'] in ['Final', 'Game Over', 'Postponed']:
					go = False
					break
				if dttime != game_info['gameDate']:
					go = False
					break

				utc = datetime.strptime(dttime, "%Y-%m-%dT%H:%M:%SZ")  - timedelta(minutes=45)

				#loop until pregame
				self.log.info(datetime.utcnow())
				self.log.info(utc)
				if datetime.utcnow() >= utc:
					self.log.info("Pregame!")
					break
				min = datetime.now().minute
				second = datetime.now().second
				sleep = ((15 - (min % 15)) * 60) - second
				self.log.info("Still good but not pregame yet. Sleeping for 15min (or until next 15th min)...")
				await asyncio.sleep(sleep)

			if go:
				if game_info['status']['detailedState'] not in ['Final', 'Game Over', 'Postponed'] and "In Progress" not in game_info['status']['detailedState']:
					self.log.info("Sending Stream Water message and sleeping for 15min...")
					try:
						role = get(self.guild.roles, id=801626115780509726)
						channel = self.bot.get_channel(487770012984279040)
						user = await self.bot.fetch_user(118795594830446592)
						message = f"""<:njd:562468864835846187> **Welcome to our game chat!** <:njd:562468864835846187>
This channel serves as our hub for discussion about Devils games as they happen.
You can ask any Admin for a link to our server's private live stream for all Devils game, which is **NOT TO BE SHARED UNDER ANY CIRCUMSTANCES!**

Since there are Devils fans from all across the world on this server, not everyone will be watching the game in the same fashion. In order to alleviate spoilers of key game events for those watching on our provided stream (ZipStreams), we have implemented a **Stream Watcher System**.

Between the opening of {channel.mention}, and the start of the game, Admins will be asking for users who are watching the game via ZipStreams, and who intend to remain active in chat for the length of the game. These users will be designated {role.mention}. They will have a uniquely colored name, and :globe_with_meridians: emojis surrounding their name.
{user.mention} is always assumed to be a Stream Watcher.

**Reactions to key game events (subject but not limited to goals, saves, penalties, etc.) before the reaction of a Stream Watcher is prohibited, and will be enforced. (1 warning, followed by a mute for the duration of the game).**
Afterwards, feel free to go crazy as usual.

You can always refer back to this message by checking the pinned messages of this channel (the grey pushpin icon in the top right of the window)

Enjoy the game, and **LET'S GO DEVILS!** <:WOO:562131980175540225>

Game chat will open in 15 minutes!"""
					except Exception:
						message = "Opening in 15 minutes!"
						self.log.exception("Error creating announcement")

					for channel_id in await self.cfg.get_channels('GameChannels'):
						wt = asyncio.ensure_future(self.send_message(int(channel_id), message))
						worker_tasks.append(wt)

					results = await asyncio.gather(*worker_tasks)

					worker_tasks = []

					min = datetime.now().minute
					second = datetime.now().second
					sleep = ((15 - (min % 15)) * 60) - second
					await asyncio.sleep(sleep)

					away_id = game_info['teams']['away']['team']['id']
					if away_id == 1:
						playing_against = game_info['teams']['home']['team']['name']
					else:
						playing_against = game_info['teams']['away']['team']['name']
					#open chats
					self.log.info("Opening game channels.")
					for channel_id in await self.cfg.get_channels('GameChannels'):
						for role in await self.cfg.get_roles('GameChannels'):
							wt = asyncio.ensure_future(self.open_channel(int(channel_id), int(role)))
							worker_tasks.append(wt)
							wt = asyncio.ensure_future(self.send_message(int(channel_id), OPEN_MSG.format(playing_against)))
							worker_tasks.append(wt)

					results = await asyncio.gather(*worker_tasks)

				self.log.info("Adding Stream Watcher room to users...")
				try:
					worker_tasks = []
					role = get(self.guild.roles, id=801626115780509726)
					for user in await self.cfg.get_auto_role_users('GameChannels'):
						wt = asyncio.ensure_future(self.stream_role(role, user, True))
						worker_tasks.append(wt)

					results = await asyncio.gather(*worker_tasks)
				except Exception:
					self.log.exception("Error adding Stream Watcher room to users")

				#monitor and update game channel topics with score
				await self.get_score(game_info['gamePk'])

				#game over
				self.log.info("Sending closing warning...")
				worker_tasks = []
				for channel_id in await self.cfg.get_channels('GameChannels'):
					wt = asyncio.ensure_future(self.send_message(int(channel_id), CLOSING_MSG))
					worker_tasks.append(wt)

				results = await asyncio.gather(*worker_tasks)

				self.log.info("Removing Stream Watcher room to users...")
				try:
					role = get(self.guild.roles, id=801626115780509726)
					for user in role.members:
						wt = asyncio.ensure_future(self.stream_role(role, user, False))
						worker_tasks.append(wt)

					results = await asyncio.gather(*worker_tasks)
				except Exception:
					self.log.exception("Error removing Stream Watcher room to users")

				await asyncio.sleep(CLOSING_TIME*60)

				self.log.info("Closing game channels.")
				worker_tasks = []
				for channel_id in await self.cfg.get_channels('GameChannels'):
					for role in await self.cfg.get_roles('GameChannels'):
						wt = asyncio.ensure_future(self.close_channel(int(channel_id), int(role)))
						worker_tasks.append(wt)

				results = await asyncio.gather(*worker_tasks)

				is_game, game_info = await hockey.next_game()

				if is_game:
					utctz = timezone('UTC')
					time = game_info['gameDate']
					utc = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
					utc2 = utctz.localize(utc)
					est = utc2.astimezone(timezone('US/Eastern'))
					time = datetime.strftime(est,  "%-I:%M %p on %B %-d, %Y")
					if game_info['teams']['away']['team']['id'] == 1:
						game_msg = f"at the **{game_info['teams']['home']['team']['name']}**"
					else:
						game_msg = f"against the **{game_info['teams']['away']['team']['name']}**"

					message = CLOSE_MSG.format(f"Join us again when we're playing {game_msg} @{time} next!")
				else:
					message = CLOSE_MSG.format(':(')

				worker_tasks = []
				for channel_id in await self.cfg.get_channels('GameChannels'):
					wt = asyncio.ensure_future(self.send_message(int(channel_id), message))
					worker_tasks.append(wt)

				results = await asyncio.gather(*worker_tasks)
