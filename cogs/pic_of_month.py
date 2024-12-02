from datetime import time, timezone, datetime, timedelta, date
import pytz
import asyncio

import discord
from discord.ext import tasks, commands
from discord.utils import get

import logging
from logging.handlers import RotatingFileHandler

class PicOfMonth(commands.Cog):
    def __init__(self, bot: discord.Bot):
        print('PicOfMonth Cog Loaded')
        self.bot = bot
        
        self.log = logging.getLogger(__name__)
        handler = RotatingFileHandler('log/picofmonth.log', maxBytes=5*1024*1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self.pic_of_month.start()
        
    def cog_unload(self):
        self.pic_of_month.cancel()
        self.log.info("PicOfMonth Cog Unloaded")

    @tasks.loop(time=time(hour=4, minute=0, tzinfo=timezone.utc))
    async def pic_of_month(self):
        # check if first of month
        if datetime.now().day != 1:
            return
        # check if really 12:00 eastern time
        now = datetime.now(pytz.timezone('US/Eastern'))
        if now.hour != 0:
            # not dst. wait an hour
            await asyncio.sleep(3600)
        try:
            reaction_count = {}
            channels = ['food-topia', 'nature-talk']
            winner_roles = [1310645896010268672, 1310646176701354094]
            congrats_message = "Congratulations {0.mention}! Your message has been selected as the picture of the month! 🎉🎉🎉\n[Click here to view]({1.url})"

            # get all messages in channel from last month
            today = date.today()
            
            # Get the first day of the previous month
            if today.month == 1:
                first_day_prev_month = date(today.year - 1, 12, 1)
            else:
                first_day_prev_month = date(today.year, today.month, 1) - timedelta(days=1)
                first_day_prev_month = date(first_day_prev_month.year, first_day_prev_month.month, 1)

            # Get the last day of the previous month
            last_day_prev_month = first_day_prev_month + timedelta(days=32)
            last_day_prev_month = last_day_prev_month - timedelta(days=last_day_prev_month.day)

            first_day_prev_month -= timedelta(days=1)
            last_day_prev_month += timedelta(days=1)

            # Convert the dates to UTC datetime objects
            first_day_prev_month_utc = datetime.combine(first_day_prev_month, datetime.max.time())
            last_day_prev_month_utc = datetime.combine(last_day_prev_month, datetime.min.time())
            first_day_prev_month_utc = first_day_prev_month_utc.astimezone(pytz.timezone('US/Eastern')).astimezone(pytz.utc)
            last_day_prev_month_utc = last_day_prev_month_utc.astimezone(pytz.timezone('US/Eastern')).astimezone(pytz.utc)
            print(first_day_prev_month_utc, last_day_prev_month_utc)

            guild = await self.bot.fetch_guilds().flatten()
            guild = guild[0]

            for i, channel_name in enumerate(channels):
                channel = get(self.bot.get_all_channels(), name=channel_name)
                reaction_count = {}
                
                async for message in channel.history(after=first_day_prev_month_utc, before=last_day_prev_month_utc, oldest_first=True, limit=None):# check if message has an attachment
                    if len(message.attachments) == 0 and len(message.embeds) == 0:
                        continue
                    
                    # check if message has a reaction
                    if len(message.reactions) == 0:
                        continue

                    # check if message has a star reaction
                    for reaction in message.reactions:
                        print(reaction.emoji)
                        if reaction.emoji == "⭐":
                            reaction_count[message.id] = reaction.count
                            break

                # get the message with the most star reactions
                self.log.info(f"Reaction count: {reaction_count},channel: {channel_name}")
                max_reaction = max(reaction_count, key=reaction_count.get)
                message = await channel.fetch_message(max_reaction)
                
                role = get(message.author.guild.roles, id=winner_roles[i])
                members = role.members
                if len(members) > 0:
                    for member in members:
                        await member.remove_roles(role)
                    
                
                self.log.info(f"Message: {message.id}")
                await message.author.add_roles(role)
                await message.channel.send(congrats_message.format(message.author, message))
                await message.pin()
        except Exception as e:
            self.log.exception(f"Error: {e}")
    
    @pic_of_month.before_loop
    async def before_pic_of_month(self):
        await self.bot.wait_until_ready()

def setup(bot: discord.Bot):
    bot.add_cog(PicOfMonth(bot))