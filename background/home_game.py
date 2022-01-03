import logging
from logging.handlers import RotatingFileHandler

import discord
import pytz
import asyncio
from datetime import datetime, timedelta, time
from tzlocal import get_localzone

from hockey import hockey

class HomeGame(object):
	"""docstring for HomeGame."""

	def __init__(self, bot):
		super(HomeGame, self).__init__()
		self.bot = bot
		self.log = logging.getLogger(__name__)

		handler = RotatingFileHandler(
			"log/homegame.log", maxBytes=5 * 1024 * 1024, backupCount=5
		)
		# create a logging format
		formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
		handler.setFormatter(formatter)
		self.log.addHandler(handler)

	async def run(self):
		while True:
			try:
				localtz = get_localzone()
				curdt = localtz.localize(datetime.now())
				ettz = pytz.timezone('US/Eastern')
				curdt = curdt.astimezone(ettz)

				if curdt.hour == 6 and curdt.minute == 0:
					is_game, game_info = await hockey.is_game_today(curdt.strftime('%Y-%m-%d'))
					if not is_game:
						self.log.info("No game. Sleeping until 6am.")
					else:
						home = game_info['teams']['home']['team']['id']

						if home != 1:
							self.log.info("Not home. Sleeping until 6am.")
						else:
							away_team = game_info['teams']['away']['team']['name']
							self.log.info("Home game today! Posting...")
							meetup_channel = self.bot.get_channel(879491007538921532)
							message = await meetup_channel.send(f"Who's going to today's game against {away_team}? React with <:njd:562468864835846187>")
							await message.add_reaction("<:njd:562468864835846187>")

					curdt = curdt.replace(second=0, microsecond=0)
					ndn = datetime.combine(curdt.date() + timedelta(days=1), curdt.time())
					next_day = ettz.localize(ndn)

					sleep = next_day.timestamp() - curdt.timestamp()
					self.log.info(f"Sleeping for {str(sleep)} seconds...")
					await asyncio.sleep(sleep)
				else:
					self.log.info("It's after 06:00. Adding a day to sleep...")
					targetn = datetime.combine(curdt.date() + timedelta(days=1), time(6, 0))
					target = ettz.localize(targetn)

					sleep = target.timestamp() - curdt.timestamp()
					self.log.info(f"Sleeping for {str(sleep)} seconds...")
					await asyncio.sleep(sleep)
			except Exception:
				self.log.exception("Error in main loop")
				await asyncio.sleep(60)
