import logging
from logging.handlers import RotatingFileHandler
import sys
import re

import aiohttp
import asyncio
import discord
from bs4 import BeautifulSoup
from util import create_embed

from datetime import datetime, timedelta
from tzlocal import get_localzone
import pytz

NUM_PAGES = 10  # Number of CapFriendly Pages Per Run

BASE_URL = "https://capfriendly.com"
ARMCHAIR_URL = f"{BASE_URL}/armchair-gm"
FILTER_TEAM = "New Jersey Devils"

logging.basicConfig(level=logging.INFO)


class ArmchairGM(object):
	def __init__(self, bot, cfg):
		super(ArmchairGM, self).__init__()
		self.bot = bot
		self.cfg = cfg
		self.log = logging.getLogger(__name__)

		handler = RotatingFileHandler(
			"log/armchairgm.log", maxBytes=5 * 1024 * 1024, backupCount=5
		)
		# create a logging format
		formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
		handler.setFormatter(formatter)
		self.log.addHandler(handler)


	async def get_latest_armchairs(self, page=1):
		paged_url = f"{ARMCHAIR_URL}?page={page}"
		self.log.info("CapFriendly Armchair GM Paged URL: %s", paged_url)

		all_links = list()

		async with aiohttp.ClientSession() as session:
			async with session.get(paged_url) as resp:
				text = await resp.read()

		soup = BeautifulSoup(text.decode("utf-8"), "lxml")
		# r = requests.get("https://www.capfriendly.com/armchair-gm")
		# soup = BeautifulSoup(r.content, "lxml")

		armchairs = soup.find("table").find_all("tr")
		for i in armchairs:
			tr_class = i["class"]
			if "column_head" in tr_class:
				continue

			elements = i.find_all("td")
			create_team = elements[0].find("img")["src"]
			create_team_filter = FILTER_TEAM.lower().replace(" ", "_")
			trade_teams = elements[2].find_all("img")
			all_trade_teams = [x["alt"] for x in trade_teams]
			m = re.search('^.*/(.*.svg)$', create_team)
			team = m.group(1).replace(".svg", "").replace("_", " ").title()
			team = ''.join([c for c in team if not c.isdigit()]).strip()
			if create_team_filter not in create_team and "New Jersey Devils" not in all_trade_teams:
				continue

			name = elements[0]
			name_text = name.text
			name_link = name.find("a", href=True)["href"]
			name_link = f"{BASE_URL}{name_link}"
			armchair_dict = {"name": name_text, "url": name_link, "team": team}
			all_links.append(armchair_dict)

		#print(all_links)
		return all_links

	async def run(self):
		while True:
			try:
				localtz = get_localzone()
				curdt = localtz.localize(datetime.now())
				ettz = pytz.timezone('US/Eastern')
				curdt = curdt.astimezone(ettz)

				if curdt.hour % 2 == 0 and curdt.minute == 0:
					self.log.info("Time to scrape!")
					channels = await self.cfg.get_channels('SocialMediaChannels')
					social_channel = self.bot.get_channel(channels[0])
					self.log.info(social_channel)
					channel_history = await social_channel.history(limit=800).flatten()
					titles = []
					urls = []

					for i in range(1, NUM_PAGES):
						armchairs = await self.get_latest_armchairs(page=i)
						for i in armchairs:
							send_armchair = True
							name = i["name"]
							url = i["url"]
							team = i["team"]

							self.log.info("Checking channel history (800 posts) for this Armchair GM post by URL.")
							for message in channel_history:
								if url in message.clean_content:
									#self.log.info("Armchair already sent - skip this one.")
									send_armchair = False
									break

								if message.embeds:
									embed = message.embeds[0].to_dict()
									if embed.get("title") is None or "ARMCHAIR GM" not in embed.get("title"):
										#self.log.info("This is not an armchair GM post.")
										continue
									if url in str(embed):
										send_armchair = False
										break

							if send_armchair == False:
								continue

							self.log.info("URL not detected - adding to list.")
							titles.append(name + f" ({team})")
							urls.append(url)
							#message_text = f"🪑 **CapFriendly Armchair GM** - {name}\n<{url}>"
							#await social_channel.send(message_text)
					if len(titles) > 0:
						embed = await create_embed.create("ARMCHAIR GM", "", titles, urls, "")
						self.log.info("Sending embed.")
						await social_channel.send(embed=embed)

					sleep = 7200 - datetime.now().second
					self.log.info(f"Sleeping for {str(sleep)} seconds...")
					await asyncio.sleep(sleep)
				else:
					if curdt.hour % 2 != 0:
						hours = 1
					else:
						hours = 2

					next_even = curdt + timedelta(hours=hours)
					next_even = next_even.replace(minute=0, second=0, microsecond=0)

					sleep = next_even.timestamp() - curdt.timestamp()
					self.log.info(f"Sleeping for {str(sleep)} seconds...")
					await asyncio.sleep(sleep)
			except Exception:
				self.log.exception("Error in main loop")
				await asyncio.sleep(60)
