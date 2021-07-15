import discord
import asyncio
import re
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
import os
import json

from hockey import hockey
from util import create_embed

REGEX = r"(?:^| )([^,:()]+?) \((\d+)\)"

logging.basicConfig(level=logging.INFO)

class Highlights(object):
	"""docstring for Highlights."""

	def __init__(self, bot, game_id, cfg):
		super(Highlights, self).__init__()
		self.game_id = game_id
		self.cfg = cfg
		self.log = logging.getLogger(__name__)
		self.bot = bot
		# add a rotating handler
		handler = RotatingFileHandler('log/highlights.log', maxBytes=5*1024*1024,
		                              backupCount=5)
		# create a logging format
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		handler.setFormatter(formatter)
		self.log.addHandler(handler)

	async def send_message(self, channel_id, message=None, file=None, embed=None):
		self.log.info(f"Sending highlight message to {channel_id}")
		channel = self.bot.get_channel(channel_id)

		return await channel.send(message, file=file, embed=embed)

	async def edit_message(self, channel_id, message_id, message=None, file=None, embed=None):
		self.log.info(f"Editing highlight message id {message_id}")
		channel = self.bot.get_channel(channel_id)
		messageObj = await channel.fetch_message(message_id)

		return await messageObj.edit(embed=embed)

	async def run(self):
		lockfile = "background/highlights.lock"
		highlight_file = f'background/json/{str(self.game_id)}_highlight.json'
		if os.path.exists(lockfile):
			return
		else:
			open(lockfile, 'a').close()

		if os.path.exists(highlight_file):
			with open(highlight_file, 'r') as f:
				highlight_cache = json.load(r)
		else:
			highlight_cache = {}
		self.log.info("Highlights started.")
		goal_milestone = 0
		goals = 0
		milestone_no = -1
		done = False

		while True:
			try:
				game_info = await hockey.get_game_content(self.game_id)
				tmp_highlight = None

				if len(game_info['media']['milestones']['items']) > 0:
					self.log.info("Checking for highlights ...")
					for x, item in enumerate(game_info['media']['milestones']['items']):
						repeat = False
						if item['title'] == 'Goal' and item['teamId'] == "1":
							if str(x) not in highlight_cache:
								for key, h in highlight_cache.items():
									if item['description'] == h['description']:
										repeat = True
										bad_key = key
										break
								if repeat:
									if str(x) not in highlight_cache:
										highlight_cache[str(x)] = highlight_cache.pop(bad_key)
									else:
										tmp_highlight = highlight_cache.pop(str(x))
										highlight_cache[str(x)] = highlight_cache.pop(bad_key)
									continue

								if tmp_highlight and item['description'] == tmp_highlight['description']:
									highlight_cache[str(x)] = tmp_highlight
									tmp_highlight = None
									continue

								self.log.info("GOAL!")
								if item['ordinalNum'] != 'SO':
									score_info = re.findall(REGEX, item['description'])

									scorer = f"{score_info[0][0]} ({score_info[0][1]})"

									if len(score_info) > 1:
										assists = ', '.join([f"{x[0]} ({x[1]})" for x in score_info[1:]])
									else:
										assists = "None"
								else:
									scorer = item['description'].split('-')[0]
									assists = "None"

								time = f"{item['periodTime']} {item['ordinalNum']}"
								gotLink = False
								try:
									for playback in item['highlight']['playbacks']:
										if playback['name'] == 	"FLASH_1800K_896x504":
											highlight_link = playback['url']
											gotLink = True
											break
								except Exception:
									self.log.exception("Error getting link")
									break

								if not gotLink:
									continue

								self.log.info(f"Scored by {scorer}, assisted by {assists} at {time}.\nLink: {highlight_link}")

								#create embed and post
								file, embed = await create_embed.goal(scorer, assists, time)
								worker_tasks = []
								for channel_id in await self.cfg.get_channels('HighlightChannels'):
									wt = asyncio.ensure_future(self.send_message(int(channel_id), file=file, embed=embed))
									worker_tasks.append(wt)

								messages = await asyncio.gather(*worker_tasks)

								worker_tasks = []
								for channel_id in await self.cfg.get_channels('HighlightChannels'):
									wt = asyncio.ensure_future(self.send_message(int(channel_id), highlight_link))
									worker_tasks.append(wt)

								results = await asyncio.gather(*worker_tasks)
								milestone_no = x
								goal_milestone = milestone_no
								goals += 1
								highlight_cache[str(x)] = {'description': item['description'], 'goal': goals, 'messages': [[m.id, m.channel.id] for m in messages]}

								with open(highlight_file, 'w') as f:
									json.dump(highlight_cache, f)
							elif item['description'] != highlight_cache[str(x)]['description']:
								self.log.info(f"Scoring change for goal {highlight_cache[str(x)]['goal']}")

								if item['ordinalNum'] != 'SO':
									score_info = re.findall(REGEX, item['description'])

									scorer = f"{score_info[0][0]} ({score_info[0][1]})"

									if len(score_info) > 1:
										assists = ', '.join([f"{x[0]} ({x[1]})" for x in score_info[1:]])
									else:
										assists = "None"
								else:
									scorer = game_info['description'].split('-')[0]
									assists = "None"

								time = f"{item['periodTime']} {item['ordinalNum']}"

								#create embed and post
								file, embed = await create_embed.goal(scorer, assists, time)
								worker_tasks = []
								for message_id, channel_id in highlight_cache[str(x)]['messages']:
									wt = asyncio.ensure_future(self.edit_message(channel_id, message_id, file=file, embed=embed))
									worker_tasks.append(wt)

								messages = await asyncio.gather(*worker_tasks)

								highlight_cache[str(x)]['description'] = item['description']

								with open(highlight_file, 'w') as f:
									json.dump(highlight_cache, f)
						elif item['title'] == 'Broadcast End':
							self.log.info("Game over.")
							is_game, game = await hockey.get_game(self.game_id)

							away_id = game['teams']['away']['team']['id']
							if away_id == 1 and goals == game['teams']['away']['score']:
								self.log.info("No more highlights. Bye!")
								done = True
								break
							elif goals == game['teams']['home']['score']:
								self.log.info("No more highlights. Bye!")
								done = True
								break

							end_time = datetime.strptime(item['timeAbsolute'], "%Y-%m-%dT%H:%M:%S%z")
							if (datetime.now(timezone.utc) - end_time).total_seconds() >= 3600:
								self.log.info("1 hour passed. Bye!")
								done = True
								break
				if done:
					break
			except Exception:
				self.log.exception("e")


			self.log.info("Sleeping for 5min and checking for more highlights...")
			await asyncio.sleep(5*60)

		os.remove(lockfile)
