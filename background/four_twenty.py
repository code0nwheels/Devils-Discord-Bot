import logging
from logging.handlers import RotatingFileHandler

import discord
import pytz
import asyncio
from datetime import datetime, timedelta, time
from tzlocal import get_localzone

THE_HOT_BOX = 531145900169363460

class FourTwenty(object):
	"""docstring for FourTwenty."""

	def __init__(self, bot):
		super(FourTwenty, self).__init__()
		self.bot = bot
		self.weed_channel = self.bot.get_channel(THE_HOT_BOX)

		self.log = logging.getLogger(__name__)

		handler = RotatingFileHandler(
			"/root/discord/hn/log/fourtwenty.log", maxBytes=5 * 1024 * 1024, backupCount=5
		)
		# create a logging format
		formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
		handler.setFormatter(formatter)
		self.log.addHandler(handler)

	async def run(self):
		while True:
			localtz = get_localzone()
			curdt = localtz.localize(datetime.now())
			ettz = pytz.timezone('US/Eastern')
			curdt = curdt.astimezone(ettz)

			if curdt.hour == 16 and curdt.minute == 20:
				self.log.info("It's time! Posting...")
				await self.weed_channel.send("Toke up mofos!")

				curdt = curdt.replace(second=0, microsecond=0)
				ndn = datetime.combine(curdt.date() + timedelta(days=1), curdt.time())
				next_day = ettz.localize(ndn)

				sleep = next_day.timestamp() - curdt.timestamp()
				self.log.info(f"Sleeping for {str(sleep)} seconds...")
				await asyncio.sleep(sleep)
			else:
				if curdt.hour < 16 or (curdt.hour == 16 and curdt.minute < 20):
					self.log.info("It's before 4:20...")
					targetn = datetime.combine(curdt.date(), time(16, 20))
					target = ettz.localize(targetn)
				else:
					self.log.info("It's after 4:20. Adding a day to sleep...")
					targetn = datetime.combine(curdt.date() + timedelta(days=1), time(16, 20))
					target = ettz.localize(targetn)

				sleep = target.timestamp() - curdt.timestamp()
				self.log.info(f"Sleeping for {str(sleep)} seconds...")
				await asyncio.sleep(sleep)
