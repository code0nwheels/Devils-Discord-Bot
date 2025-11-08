# import pycord commands
import os
import discord
from discord.ext import commands
from discord.utils import get

from datetime import datetime

from util import create_embed, leaderboard
from util.dicts import team_dict
from util.logger import setup_logger
from database.pickems_database import PickemsDatabase

from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))

class PickemsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = PickemsDatabase()
        self.log = setup_logger(__name__, 'log/pickems_commands.log')

    @commands.slash_command(guild_ids=[guild_id], name="get_leaderboard", description="Get the full leaderboard")
    @discord.commands.option(name="season", description="The season to get the leaderboard for (ex: 20242025). Omit for the current season.", required=False)
    async def get_leaderboard(self, ctx, season: int = None):
        self.log.info(f"get_leaderboard called by {ctx.author.name} in {ctx.guild.name} for season {season}")
        # get the paginated leaderboard
        paginator = await leaderboard.setup_paginator(str(season))

        if not season:
            season = "the current season"

        if paginator is None:
            await ctx.respond(f"No leaderboard found for {season}", ephemeral=True)
            return
        # send the paginated leaderboard
        await paginator.respond(ctx.interaction, ephemeral=True)

    @get_leaderboard.error
    async def get_leaderboard_error(self, ctx, error):
        self.log.exception(f"Error in get_leaderboard: {error}")
        await ctx.respond("An error occurred", ephemeral=True)
    
    @commands.slash_command(guild_ids=[guild_id], name="get_user_position", description="Get a user's leaderboard position")
    @discord.commands.option(name="user", description="The user to get the position of. Omit for yourself.", required=False)
    @discord.commands.option(name="season", description="The season to get the position for (ex: 20242025). Omit for the current season.", required=False)
    async def get_user_position(self, ctx, user: discord.User = None, season: int = None):
        self.log.info(f"get_user_position called by {ctx.author.name} in {ctx.guild.name} for user {user} in season {season}")
        # get the user
        if user is None:
            user = ctx.author
        
        # make user a string
        user_str = str(user.id)
        # get the user's position
        position = await leaderboard.get_user_position(user_str, str(season))

        if position:
            # extract winsm losses, and position
            wins = position[1]
            losses = position[2]
            position = position[4]

            # send the user's position
            await ctx.respond(f"{user.mention} is in position {position} with {wins} wins and {losses} losses", ephemeral=True)
        else:
            if not season:
                season = "the current season"
            await ctx.respond(f"{user.mention} is not in the leaderboard for {season}", ephemeral=True)

    @get_user_position.error
    async def get_user_position_error(self, ctx, error):
        self.log.exception(f"Error in get_user_position: {error}")
        await ctx.respond("An error occurred", ephemeral=True)
    
    # command to get a user's picks for a date
    # date is optional, if not provided, get today's picks
    @commands.slash_command(guild_ids=[guild_id], name="get_picks", description="Get your picks for a date")
    @discord.commands.option(name="date", description="The date of the picks in yyyy-mm-dd format. Omit for today.", required=False)
    async def get_picks(self, ctx, date: str = None):
        self.log.info(f"get_picks called by {ctx.author.name} in {ctx.guild.name} for date {date}")
        # check if date is provided; if not, get today's date. if so, check if it's a valid date and convert to datetime
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        else:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                await ctx.respond("Invalid date", ephemeral=True)
                return
        
        # get the user's picks
        picks = await self.db.get_user_picks(str(ctx.author.id), date)
        # if picks is None, the user has no picks for the date
        if not picks:
            await ctx.respond(f"{ctx.author.mention} has no picks for {date}", ephemeral=True)
        else:
            # convert team ids to team names
            picks = [team_dict[team] for team in picks]
            # create the embed
            embed = await create_embed.create_user_picks_embed(ctx.author, picks, date)
            # send the embed
            await ctx.respond(embed=embed, ephemeral=True)

    @get_picks.error
    async def get_picks_error(self, ctx, error):
        self.log.exception(f"Error in get_picks: {error}")
        await ctx.respond("An error occurred", ephemeral=True)

    # command to post the leaderboard (admin only)
    @commands.slash_command(guild_ids=[guild_id], name="post_leaderboard", description="Post the leaderboard")
    @commands.has_permissions(administrator=True)
    @discord.default_permissions(administrator=True)
    async def post_leaderboard(self, ctx):
        self.log.info(f"post_leaderboard called by {ctx.author.name} in {ctx.guild.name}")
        # find channel by name
        channel = get(self.bot.get_all_channels(), name='leaderboard')
        await leaderboard.post_leaderboard(channel)

        await ctx.respond("Leaderboard posted", ephemeral=True)

# add the cog to the bot
def setup(bot):
    bot.add_cog(PickemsCommands(bot))