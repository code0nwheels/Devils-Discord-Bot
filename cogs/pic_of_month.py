from datetime import time, timezone, datetime, timedelta, date
import zoneinfo
import asyncio
import os

import discord
from discord.ext import tasks, commands
from discord.utils import get
from dotenv import load_dotenv

from util.logger import setup_logger

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))

eastern = zoneinfo.ZoneInfo("US/Eastern")

class PicOfMonth(commands.Cog):
    def __init__(self, bot: discord.Bot):
        print('PicOfMonth Cog Loaded')
        self.bot = bot
        self.log = setup_logger(__name__, 'log/picofmonth.log')

        self.pic_of_month.start()
        
    def cog_unload(self):
        self.pic_of_month.cancel()
        self.log.info("PicOfMonth Cog Unloaded")

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=eastern))
    async def pic_of_month(self):
        # check if first of month
        if datetime.now().day != 1:
            self.log.info("Not the first of the month")
            return

        await self.run_pic_of_month()

    async def run_pic_of_month(self, dry_run=False):
        summary = []
        try:
            reaction_count = {}
            channels = {
                'food-topia': 1310645896010268672,
                'nature-talk': 1310646176701354094,
                'pets': 1489345320965111859
            }
            congrats_message = "Congratulations {0.mention}! Your message has been selected as the picture of the month! 🎉🎉🎉\n[Click here to view]({1.jump_url})"

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
            first_day_prev_month_utc = first_day_prev_month_utc.astimezone(eastern).astimezone(timezone.utc)
            last_day_prev_month_utc = last_day_prev_month_utc.astimezone(eastern).astimezone(timezone.utc)
            print(first_day_prev_month_utc, last_day_prev_month_utc)

            guild = await self.bot.fetch_guilds().flatten()
            guild = guild[0]

            for channel_name, winner_role in channels.items():
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
                if len(reaction_count) == 0:
                    self.log.info(f"No reactions found in {channel_name}")
                    summary.append(f"**#{channel_name}**: no ⭐ reactions found")
                    if not dry_run:
                        await channel.send("No ⭐ reactions found :(")
                    continue

                max_reaction = max(reaction_count, key=reaction_count.get)
                message = await channel.fetch_message(max_reaction)

                role = get(message.author.guild.roles, id=winner_role)

                self.log.info(f"Message: {message.id}")
                summary.append(
                    f"**#{channel_name}**: {message.author} "
                    f"({reaction_count[max_reaction]} ⭐) — {message.jump_url}"
                )

                if dry_run:
                    continue

                members = role.members
                if len(members) > 0:
                    for member in members:
                        await member.remove_roles(role)

                await message.author.add_roles(role)
                await message.channel.send(congrats_message.format(message.author, message))
                await message.pin()
        except Exception as e:
            self.log.exception(f"Error: {e}")
            summary.append(f"Error: {e}")
        return summary
    
    @commands.slash_command(guild_ids=[guild_id], name='runpicofmonth', description='Manually run pic of the month (ignores the date check).')
    @commands.has_permissions(administrator=True)
    @discord.default_permissions(administrator=True)
    @discord.commands.option('dry_run', description='Preview the winners without assigning roles, posting, or pinning', default=True)
    async def runpicofmonth(self, ctx, dry_run: bool = True):
        self.log.info(f"{ctx.author} is manually running pic of the month (dry_run={dry_run})")
        await ctx.defer(ephemeral=True)
        summary = await self.run_pic_of_month(dry_run=dry_run)

        header = "**Dry run** — no changes made:\n" if dry_run else "**Pic of the month run complete:**\n"
        body = "\n".join(summary) if summary else "No channels processed."
        await ctx.respond(header + body, ephemeral=True)

    @runpicofmonth.error
    async def runpicofmonth_error(self, ctx, error):
        self.log.exception("Error running pic of the month manually")
        await ctx.respond(f"Oops, something went wrong: {error}", ephemeral=True)

    @pic_of_month.before_loop
    async def before_pic_of_month(self):
        await self.bot.wait_until_ready()

def setup(bot: discord.Bot):
    bot.add_cog(PicOfMonth(bot))