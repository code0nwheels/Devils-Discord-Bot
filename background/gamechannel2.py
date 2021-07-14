import discord
from discord.utils import get
from discord.ext.tasks import loop
from discord.ext.commands import Bot
from pytz import timezone
from datetime import datetime, timedelta
from tzlocal import get_localzone

import asyncio

from hockey import hockey
from background.highlights import Highlights

SCORE_TEMPLATE = "{away_team} {away_score} - {home_team} {home_score}"
CLOSING_TIME = 5
CLOSING_MSG = f"Closing chat in {CLOSING_TIME} minutes!"
IN_GAME_SLEEP = 5
OPEN_MSG = "Game chat is open! We're playing the **{}**"
CLOSE_MSG = "Chat is closed!\n{}"

class GameChannel(object):
	"""docstring for GameChannel."""

	def __init__(self, bot, cfg):
		super(GameChannel, self).__init__()
		self.bot = bot
		self.guild = self.bot.guilds[0]
		self.cfg = cfg

	async def open_channel(self, channel_id, role_id):
		channel = self.bot.get_channel(channel_id)
		role = get(self.guild.roles, id=role_id)
		await channel.set_permissions(role, read_messages=True,
														  send_messages=True)
	async def close_channel(self, channel_id, role_id):
		channel = self.bot.get_channel(channel_id)
		role = get(self.guild.roles, id=role_id)
		await channel.set_permissions(role, read_messages=False,
														  send_messages=False)
	async def update_score(self, channel_id, new_topic):
		channel = self.bot.get_channel(channel_id)

		try:
			await channel.edit(topic=new_topic)
		except Exception as e:
			print(e)

	async def get_score(self, game_id):
		worker_tasks = []
		is_game, game_info = await hockey.get_game(game_id)
		away_team = game_info['teams']['away']['team']['name']
		home_team = game_info['teams']['home']['team']['name']
		away_score = game_info['teams']['away']['score']
		home_score = game_info['teams']['home']['score']

		for channel_id in await self.cfg.get_channels('GameChannels'):
			wt = asyncio.ensure_future(self.update_score(int(channel_id), SCORE_TEMPLATE.format(away_team=away_team, away_score=away_score, home_team=home_team, home_score=home_score)))
			worker_tasks.append(wt)

		results = await asyncio.gather(*worker_tasks)

		while True:
			is_game, game_info = await hockey.get_game(game_id)

			if away_score != game_info['teams']['away']['score'] or home_score != game_info['teams']['home']['score']:
				away_score = game_info['teams']['away']['score']
				home_score = game_info['teams']['home']['score']

				for channel_id in await self.cfg.get_channels('GameChannels'):
					wt = asyncio.ensure_future(self.update_score(int(channel_id), SCORE_TEMPLATE.format(away_team=away_team, away_score=away_score, home_team=home_team, home_score=home_score)))
					worker_tasks.append(wt)

				results = await asyncio.gather(*worker_tasks)

			if game_info['status']['detailedState'] in ['Final', 'Game Over', 'Postponed']:
				break

			await asyncio.sleep(IN_GAME_SLEEP * 60)

	async def send_message(self, channel_id, message):
		channel = self.bot.get_channel(channel_id)

		await channel.send(message)

	async def run(self):
		while True:
			go = True
			is_game, game_info = await hockey.is_game_today()
			worker_tasks = []

			if not is_game:
				is_game, game_info = await hockey.next_game()
				if not is_game:
					print("No game. Sleeping until 3am.")
					now = datetime.now()
					to = (now + timedelta(days = 1)).replace(hour=3, minute=0, second=0)
					print(now, to)
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

					while True:
						is_game, game_info = await hockey.next_game()
						if 'TBD' in game_info['status']['detailedState'] or game_info['status']['startTimeTBD']:
							time = 'TBD'
						else:
							time = datetime.strftime(est,  "%-I:%M %p")
						date = datetime.strftime(est,  "%-m/%-d")

						for channel_id in await self.cfg.get_channels('GameChannels'):
							channel = self.bot.get_channel(int(channel_id))
							category = channel.category

							await category.edit(name=f"{away['abbreviation']} @ {home['abbreviation']} {date} {time}")

						if time != 'TBD':
							break
						else:
							print("Time is TBD. Checking again in 60min.")
							await asyncio.sleep(3600)

			pk = game_info['gamePk']
			while True:
				is_game, game_info = await hockey.get_game(pk)
				if game_info['status']['detailedState'] in ['Final', 'Game Over', 'Postponed']:
					go = False
					break
				time = game_info['gameDate']
				utc = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")  - timedelta(minutes=30)

				#loop until pregame
				if datetime.utcnow() >= utc:
					break
				min = datetime.now().minute
				second = datetime.now().second
				sleep = ((30 - (min % 30)) * 60) - second
				print("Still good but not pregame yet. Sleeping for 30min (or until next 30th min)...")
				await asyncio.sleep(sleep)

			if go:
				h = Highlights(game_info['gamePk'], self.cfg)
				bot.loop.create_task(h.run())

				away_id = game_info['teams']['away']['team']['id']
				if away_id == 1:
					playing_against = game_info['teams']['home']['team']['name']
				else:
					playing_against = game_info['teams']['away']['team']['name']
				#open chats
				for channel_id in await self.cfg.get_channels('GameChannels'):
					for role in await self.cfg.get_roles('GameChannels'):
						wt = asyncio.ensure_future(self.open_channel(int(channel_id), int(role)))
						worker_tasks.append(wt)
						wt = asyncio.ensure_future(self.send_message(int(channel_id), OPEN_MSG.format(playing_against)))
						worker_tasks.append(wt)

				results = await asyncio.gather(*worker_tasks)

				#monitor and update game channel topics
				await self.get_score(game_info['gamePk'])

				#game over
				worker_tasks = []
				for channel_id in await self.cfg.get_channels('GameChannels'):
					wt = asyncio.ensure_future(self.send_message(int(channel_id), CLOSING_MSG))
					worker_tasks.append(wt)

				results = await asyncio.gather(*worker_tasks)

				await asyncio.sleep(CLOSING_TIME*60)

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
					time = datetime.strftime(est,  "%I:%M %p on %B, %d %Y")
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
