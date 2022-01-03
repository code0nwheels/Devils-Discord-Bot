import discord
import logging
import re
from logging.handlers import RotatingFileHandler
from discord.utils import get
from discord.ext import tasks
from discord.ext.commands import Bot
from pytz import timezone
from datetime import datetime, timedelta
import time
from tzlocal import get_localzone

import asyncio

from hockey import hockey
from background.highlights import Highlights

TOPIC_TEMPLATE = "{away_team} at {home_team}"
CLOSING_TIME = 5
CLOSING_MSG = f"Closing chat in {CLOSING_TIME} minutes!"
IN_GAME_SLEEP = 2
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

	async def update_description(self, channel_id, new_topic):
		self.log.info(f"Updating description for {channel_id}...")
		try:
			channel = self.bot.get_channel(channel_id)
			await channel.edit(topic=new_topic)
		except Exception as e:
			self.log.exception(f"Fatal error in updating description for {channel_id}")

	async def monitor_game(self, game_id):
		self.log.info("In monitor_game...")
		try:
			h = Highlights(self.bot, game_id, self.cfg)
			self.log.info("Starting Highlights...")
			try:
				self.bot.loop.create_task(h.run())
			except Exception:
				self.log.exception("Error starting Highlights")

			final = 0
			while True:
				try:
					is_game, game_info = await hockey.get_game(game_id)
					status = game_info['status']['detailedState']
					#self.log.info(f'Status: {status}\nFinal: {final}')
					if status in ['Final', 'Game Over', 'Postponed']:# and away_score != home_score:
						final += 1

						if final == 2:
							self.log.info("Game ended. Leaving get score.")
							#self.post_reminder.cancel()
							return
					elif final > 0:
						final = 0
				except Exception as e:
					self.log.exception("Fatal error in getting score")
				finally:
					self.log.info(f"Sleeping...")
					await asyncio.sleep((IN_GAME_SLEEP * 60) - (time.time() - start_loop))
		except Exception as e:
			self.log.exception("Fatal error in getting score")

	async def send_message(self, channel, message):
		self.log.info(f"Sending message to {channel}...")
		try:
			if isinstance(channel, int):
				channel = self.bot.get_channel(channel_id)
			return await channel.send(message)
		except Exception as e:
			self.log.exception(f"Fatal error in sending message to {channel}")

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

				worker_tasks = []
				for channel_id in await self.cfg.get_channels('GameChannels'):
					self.log.info("Updating game channels category name")
					channel = self.bot.get_channel(int(channel_id))
					category = channel.category

					await category.edit(name=f"{away['abbreviation']} @ {home['abbreviation']} {date} {time}")

					self.log.info("Updating description with teams")
					wt = asyncio.ensure_future(self.update_description(int(channel_id), TOPIC_TEMPLATE.format(away_team=away['name'], home_team=home['name'])))
					worker_tasks.append(wt)

				results = await asyncio.gather(*worker_tasks)

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

				fifteen_minutes_before_pg = datetime.strptime(dttime, "%Y-%m-%dT%H:%M:%SZ")  - timedelta(minutes=45)
				pg = datetime.strptime(dttime, "%Y-%m-%dT%H:%M:%SZ")  - timedelta(minutes=30)

				#loop until pregame
				self.log.info(datetime.utcnow())
				self.log.info(utc)
				if datetime.utcnow() >= fifteen_minutes_before_pg:
					self.log.info("Pregame!")
					break
				min = datetime.now().minute
				second = datetime.now().second
				sleep = ((15 - (min % 15)) * 60) - second
				self.log.info("Still good but not pregame yet. Sleeping for 15min (or until next 15th min)...")
				await asyncio.sleep(sleep)

			if go:
				open_channels = []
				for channel_id in await self.cfg.get_channels('GameChannels'):
					for role in await self.cfg.get_roles('GameChannels'):
						channel, role, open = await self.check_perms(int(channel_id), int(role))
						if not open:
							open_channels.append([channel, role])
				if game_info['status']['detailedState'] not in ['Final', 'Game Over', 'Postponed']:# and "In Progress" not in game_info['status']['detailedState']:
					if datetime.utcnow() < pg:
						sleep = (datetime.utcnow() - pg).total_seconds()
						message = f"Opening in {round(sleep/60)} minutes!"

						if open_channels:
							for o in open_channels:
								wt = asyncio.ensure_future(self.send_message(o[0], message))
								worker_tasks.append(wt)

							messages = await asyncio.gather(*worker_tasks)

							worker_tasks = []

							await asyncio.sleep(sleep)

					if open_channels:
						away_id = game_info['teams']['away']['team']['id']
						if away_id == 1:
							playing_against = game_info['teams']['home']['team']['name']
						else:
							playing_against = game_info['teams']['away']['team']['name']
						#open chats
						self.log.info("Opening game channels.")
						for o in open_channels:
							wt = asyncio.ensure_future(self.open_channel(o[0], o[1]))
							worker_tasks.append(wt)
							wt = asyncio.ensure_future(self.send_message(o[0], OPEN_MSG.format(playing_against)))
							worker_tasks.append(wt)

						results = await asyncio.gather(*worker_tasks)

				#monitor the game
				await self.monitor_game(game_info['gamePk'])

				#game over
				self.log.info("Sending closing warning...")
				worker_tasks = []
				for channel_id in await self.cfg.get_channels('GameChannels'):
					wt = asyncio.ensure_future(self.send_message(int(channel_id), CLOSING_MSG))
					worker_tasks.append(wt)

				results = await asyncio.gather(*worker_tasks)

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
