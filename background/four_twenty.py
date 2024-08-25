import logging
from logging.handlers import RotatingFileHandler

import pytz
import asyncio
from datetime import datetime, timedelta, time as dttime
from tzlocal import get_localzone
from time import time
import fcntl

class FourTwenty(object):
	"""docstring for FourTwenty."""

	def __init__(self, bot, cfg):
		super(FourTwenty, self).__init__()
		self.bot = bot
		self.cfg = cfg
		self.log = logging.getLogger(__name__)

		handler = RotatingFileHandler(
			"log/fourtwenty.log", maxBytes=5 * 1024 * 1024, backupCount=5
		)
		# create a logging format
		formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
		handler.setFormatter(formatter)
		self.log.addHandler(handler)

	async def run(self):
		try:
			fd = open(__file__)
			fcntl.flock(fd, fcntl.LOCK_EX)
		except:
			#already running
			return
		localtz = get_localzone()
		curdt = localtz.localize(datetime.now())
		ettz = pytz.timezone('US/Eastern')
		curdt = curdt.astimezone(ettz)
		
		while True:
			start = time()
			try:
				if curdt.hour == 16 and curdt.minute == 20:
					channels = await self.cfg.get_channels('FourTwentyChannels')
					weed_channel = self.bot.get_channel(channels[0])
					self.log.info("It's time! Posting...")
					await weed_channel.send("Toke up mofos!")

					ndn = datetime.combine(curdt.date() + timedelta(days=1), curdt.time())
					target = ettz.localize(ndn)
				else:
					if curdt.hour < 16 or (curdt.hour == 16 and curdt.minute < 20):
						self.log.info("It's before 4:20...")
						targetn = datetime.combine(curdt.date(), dttime(16, 20))
						target = ettz.localize(targetn)
					else:
						self.log.info("It's after 4:20. Adding a day to sleep...")
						targetn = datetime.combine(curdt.date() + timedelta(days=1), dttime(16, 20))
						target = ettz.localize(targetn)

				target = target.replace(second=0, microsecond=0)
				sleep = (target.timestamp() - curdt.timestamp()) - (time() - start)
				self.log.info(f"Sleeping for {str(sleep)} seconds...")
				await asyncio.sleep(sleep)
				curdt = target
			except Exception:
				self.log.exception("Error in main loop")
				await asyncio.sleep(60)
