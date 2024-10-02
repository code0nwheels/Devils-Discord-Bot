import discord
import logging
from logging.handlers import RotatingFileHandler
from discord.utils import get
from pytz import timezone
from datetime import datetime, timedelta

import asyncio

from hockey.schedule import Schedule
from hockey.game import Game
#from background.highlights import Highlights

TOPIC_TEMPLATE = "{away_team} at {home_team}"
CLOSING_TIME = 5
CLOSING_MSG = f"Closing chat in {CLOSING_TIME} minutes!"
IN_GAME_SLEEP = 1
OPEN_MSG = "Game chat is open! We're playing the **{}**"
CLOSE_MSG = "Chat is closed!\n{}"

logging.basicConfig(level=logging.INFO)

class GameChannel(object):
	def __init__(self, bot, cfg):
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

	async def check_perms(self, channel_id, role_id):
		self.log.info(f"Checking permissions for {channel_id} for {role_id}...")
		channel = self.bot.get_channel(channel_id)
		role = get(self.guild.roles, id=role_id)

		cur_perms = channel.permissions_for(role)
		return channel, role, cur_perms.send_messages

	async def open_channel(self, channel, role):
		self.log.info(f"Opening {channel} for {role}...")
		try:
			await channel.set_permissions(role, read_messages=True,
														  send_messages=None)

		except Exception as e:
			self.log.exception(f"Fatal error in opening {channel} for {role}")

	async def close_channel(self, channel_id, role_id):
		self.log.info(f"Closing {channel_id} for {role_id}...")
		try:
			channel = self.bot.get_channel(channel_id)
			role = get(self.guild.roles, id=role_id)
			await channel.set_permissions(role, read_messages=True,
															  send_messages=False)
		except Exception as e:
			self.log.exception(f"Fatal error in closing {channel_id} for {role_id}")

	async def update_description(self, channel_id, new_topic):
		self.log.info(f"Updating description for {channel_id}...")
		try:
			channel = self.bot.get_channel(channel_id)
			await channel.edit(topic=new_topic)
		except Exception as e:
			self.log.exception(f"Fatal error in updating description for {channel_id}")

	async def update_game_channels(self, away, home, game_date, game_time):
		worker_tasks = []
		for channel_id in await self.cfg.get_channels('GameChannels'):
			self.log.info("Updating game channels category name")
			channel = self.bot.get_channel(int(channel_id))
			category = channel.category

			await category.edit(name=f"{away.abbreviation} @ {home.abbreviation} {game_date} {game_time}")

			self.log.info("Updating description with teams")
			wt = asyncio.ensure_future(self.update_description(int(channel_id), TOPIC_TEMPLATE.format(away_team=away.full_name, home_team=home.full_name)))
			worker_tasks.append(wt)

		await asyncio.gather(*worker_tasks)

	async def monitor_game(self, game: Game):
		self.log.info("In monitor_game...")
		try:
			"""h = Highlights(self.bot, game_id, self.cfg)
			self.log.info("Starting Highlights...")
			try:
				self.bot.loop.create_task(h.run())
			except Exception:
				self.log.exception("Error starting Highlights")"""

			final = 0
			while True:
				try:
					if game.is_final or game.is_ppd or game.is_cancelled:
						final += 1

						if final == 2:
							self.log.info("Game ended. Leaving monitor_game.")
							#self.post_reminder.cancel()
							return
					elif final > 0:
						final = 0
					await game.refresh()
				except Exception as e:
					self.log.exception("Fatal error in monitor_game")
				finally:
					self.log.info(f"Sleeping...")
					await asyncio.sleep((IN_GAME_SLEEP * 60))
		except Exception as e:
			self.log.exception("Fatal error in monitor_game")

	async def send_message(self, channel, message):
		self.log.info(f"Sending message to {channel}...")
		try:
			if isinstance(channel, int):
				channel = self.bot.get_channel(channel)
			return await channel.send(message)
		except Exception as e:
			self.log.exception(f"Fatal error in sending message to {channel}")

	async def run(self):
		self.log.info("GameChannel started.")
		while True:
			go = True
			schedule = Schedule()
			await schedule.fetch_team_schedule('njd')
			game = await schedule.get_next_game()
			worker_tasks = []
			is_game = game and game.is_today and not game.is_final and not game.is_ppd and not game.is_cancelled

			if not is_game:
				if not game:
					self.log.info("No game. Sleeping until 3am.")
					await self.bot.change_presence(activity = discord.Game('Golf!'))
					now = datetime.now()
					to = (now + timedelta(days = 1)).replace(hour=3, minute=0, second=0)
					#self.log.info(now, to)
					await asyncio.sleep((to - now).total_seconds())
					continue

			away = await game.get_away_team()
			home = await game.get_home_team()

			self.log.info(f"Next game is {away.abbreviation} @ {home.abbreviation}.")

			if not game.is_tbd:
				raw_game_time = game.raw_game_time
				game_time = game.game_time("%-I:%M %p ET")
				
				epoch = int(raw_game_time.timestamp())
			else:
				game_time = 'TBD'

			game_date = datetime.strftime(raw_game_time,  "%-m/%-d")
			if away.id != 1:
				await self.bot.change_presence(activity = discord.Game(f"{away.abbreviation} on {game_date} {game_time}"))
			else:
				await self.bot.change_presence(activity = discord.Game(f"{home.abbreviation} on {game_date} {game_time}"))

			await self.update_game_channels(away, home, game_date, game_time)

			while True:
				try:
					if game.is_tbd:
						if not game.is_today:
							self.log.info("Game is TBD and not today. Sleeping until 3am...")
							now = datetime.now()
							to = (now + timedelta(days = 1)).replace(hour=3, minute=0, second=0)
							#self.log.info(now, to)
							await asyncio.sleep((to - now).total_seconds())
							await game.refresh()
							continue

						self.log.info("Game is TBD. Sleeping for 5min...")
						await asyncio.sleep(300)
						await game.refresh()
						continue
					elif not game.is_today:
						self.log.info("Game is not today. Sleeping until 3am...")
						now = datetime.now()
						to = (now + timedelta(days = 1)).replace(hour=3, minute=0, second=0)
						#self.log.info(now, to)
						await asyncio.sleep((to - now).total_seconds())
						await game.refresh()

						# check if next game is the same
						if schedule.get_next_game() != game:
							go = False
							break
						continue
					
					await self.update_game_channels(away, home, game_date, game_time)
					
					if game.is_final or game.is_ppd or game.is_cancelled:
						go = False
						break
					
					if game.is_today:
						game_utc = game.raw_game_time
						pregame_time = game_utc - timedelta(minutes=30)

						#loop until pregame
						self.log.info(datetime.utcnow())
						self.log.info(game_utc)
						if datetime.utcnow() >= pregame_time:
							self.log.info("Pregame!")
							away_wins = game.away_team_wins
							home_wins = game.home_team_wins
							break
						min = datetime.now().minute
						second = datetime.now().second
						sleep = ((15 - (min % 15)) * 60) - second
						self.log.info("Still good but not pregame yet. Sleeping for 15min (or until next 15th min)...")
						await asyncio.sleep(sleep)
					else:
						self.log.info("Game is not today. Sleeping until 3am...")
						now = datetime.now()
						to = (now + timedelta(days = 1)).replace(hour=3, minute=0, second=0)
						#self.log.info(now, to)
						await asyncio.sleep((to - now).total_seconds())
						await game.refresh()

						# check if next game is the same
						if schedule.get_next_game() != game:
							go = False
							break
						
				except Exception as e:
					self.log.error(e)
					self.log.info("Error getting game info. Sleeping for 5min...")
					await asyncio.sleep(300)
				finally:
					await game.refresh()

			if go:
				open_channels = []
				for channel_id in await self.cfg.get_channels('GameChannels'):
					for role in await self.cfg.get_roles('GameChannels'):
						channel, role, open = await self.check_perms(int(channel_id), int(role))
						if not open:
							open_channels.append([channel, role])
				if not game.is_final and not game.is_ppd and not game.is_cancelled:
					if open_channels:
						if away.id == 1:
							playing_against = home.full_name
						else:
							playing_against = away.full_name
						#open chats
						self.log.info("Opening game channels.")
						for channel in open_channels:
							wt = asyncio.ensure_future(self.open_channel(channel[0], channel[1]))
							worker_tasks.append(wt)
							wt = asyncio.ensure_future(self.send_message(channel[0], OPEN_MSG.format(playing_against)))
							worker_tasks.append(wt)

						await asyncio.gather(*worker_tasks)

				#monitor the game
				await self.monitor_game(game)

				#game over
				# check if chat is still open
				open_channels = []
				for channel_id in await self.cfg.get_channels('GameChannels'):
					for role in await self.cfg.get_roles('GameChannels'):
						channel, role, open = await self.check_perms(int(channel_id), int(role))
						if open:
							open_channels.append([channel, role])
				
				if open_channels:
					self.log.info("Sending closing warning...")
					worker_tasks = []
					for channel in open_channels:
						wt = asyncio.ensure_future(self.send_message(channel[0], CLOSING_MSG))
						worker_tasks.append(wt)

					await asyncio.gather(*worker_tasks)

					await asyncio.sleep(CLOSING_TIME*60)

					self.log.info("Closing game channels.")
					worker_tasks = []
					for channel in open_channels:
						wt = asyncio.ensure_future(self.close_channel(channel[0].id, channel[1].id))
						worker_tasks.append(wt)

					await asyncio.gather(*worker_tasks)

				game = await schedule.get_next_game()

				if game:
					post_next_game = True
					# check if playoffs and if so, how many wins the Devils have
					if game.is_playoffs:
						# get the game winner
						winner = game.winning_team

						if winner.id == 1:
							# determine if devils are home or away
							if game.away_team.id == 1:
								num_wins = away_wins + 1
							else:
								num_wins = home_wins + 1

							if num_wins == 4:
								message = CLOSE_MSG.format('The Devils have won the series!\nSee you next round!')
								post_next_game = False
						else:
							if game.away_team.id == 1:
								num_wins = home_wins + 1
							else:
								num_wins = away_wins + 1

							if num_wins == 4:
								message = CLOSE_MSG.format('The Devils have been eliminated.\nSee you next season!')
								post_next_game = False
					
					if post_next_game:
						game_time = game.raw_game_time
						epoch_obj = game_time.astimezone(timezone('US/Eastern'))
						away = await game.get_away_team()
						home = await game.get_home_team()

						epoch = int(epoch_obj.timestamp())
						game_time = f"<t:{epoch}:t> on <t:{epoch}:D>"
						if away.id == 1:
							game_msg = f"at the **{home.full_name}**"
						else:
							game_msg = f"against the **{away.full_name}**"

						message = CLOSE_MSG.format(f"Join us again when we're playing {game_msg} @{game_time} next!")
				else:
					# check if postseason and if so, how many wins the Devils have
					if game.is_playoffs:
						# get the game winner
						winner = game.winning_team

						if winner.id == 1:
							# determine if devils are home or away
							if game.away_team.id == 1:
								num_wins = game.away_team_wins
							else:
								num_wins = game.home_team_wins

							if num_wins == 4:
								message = CLOSE_MSG.format('The Devils have won the series!\nSee you next round!')
							else:
								message = CLOSE_MSG.format('This API is confusing! At least we won!\nSee you next game!')
						else:
							if game.away_team.id == 1:
								num_wins = game.home_team_wins
							else:
								num_wins = game.away_team_wins

							if num_wins == 4:
								message = CLOSE_MSG.format('The Devils have been eliminated.\nSee you next season!')
							else:
								message = CLOSE_MSG.format('This API is confusing! We\'ll get em next time!\nSee you next game!')
					else:
						message = CLOSE_MSG.format(':(\nSee you next season!')

				worker_tasks = []
				for channel_id in await self.cfg.get_channels('GameChannels'):
					wt = asyncio.ensure_future(self.send_message(int(channel_id), message))
					worker_tasks.append(wt)

				await asyncio.gather(*worker_tasks)
