import discord
import pytz
from datetime import datetime
from tzlocal import get_localzone

import discord.ext.pages as pages

from util import create_embed
from database import pickems_database

db = pickems_database.PickemsDatabase()

# set up a paginator for the leaderboard embeds
# each page will be a leaderboard embed with 10 leaderboards each
# Args: leaderboards - dict of leaderboards containing user_id, wins, losses; user_id is key
async def setup_paginator(season: str = None):
    # fetch most recent records updated_at from db
    records_updated = await db.get_records_updated_at()
    try:
        records_updated = datetime.strptime(str(records_updated), '%Y-%m-%d %H:%M:%S')
    except:
        records_updated = datetime.strptime(str(records_updated), '%Y-%m-%d %H:%M:%S.%f')
    
    if not season:
        now = datetime.now(pytz.timezone('US/Eastern'))
        if now.month < 7 and now.month >= 1:
            season = str(now.year - 1) + '-' + str(now.year)
        else:
            season = str(now.year) + '-' + str(now.year + 1)

    # get the leaderboard from db
    leaderboard_ = await db.get_leaderboard(season)

    if not leaderboard_:
        return None
        
    # convert records_updated to ET
    localtz = get_localzone()
    esttz = pytz.timezone('US/Eastern')

    curdt = localtz.localize(records_updated)
    est = curdt.astimezone(esttz)
    
    # format est to month day, year at h:mm; ex: January 1, 2021 at 4:30am
    est_str = est.strftime('%B %d, %Y at %I:%M%p ET')

    # list of leaderboards
    leaderboards_list = {}

    # create leaderboard embeds
    embeds = []

    for i, leaderboard in enumerate(leaderboard_):
        # add leaderboard to leaderboards_list
        leaderboards_list[leaderboard] = leaderboard_[leaderboard]

        # if 10 leaderboards have been added to leaderboards_list, create leaderboard embed
        if (i + 1) % 10 == 0:
            embed = await create_embed.create_leaderboard(leaderboards_list, est_str)
            embeds.append(embed)
            leaderboards_list.clear()
    if leaderboards_list:
        embed = await create_embed.create_leaderboard(leaderboards_list, est_str)
        embeds.append(embed)

    # create paginator
    paginator = pages.Paginator(pages=embeds)

    # set up buttons
    paginator.add_button(
        pages.PaginatorButton(
            "first", label='<<', style=discord.ButtonStyle.red, loop_label="fst"
        )
    )
    paginator.add_button(
        pages.PaginatorButton(
            "prev", label="<", style=discord.ButtonStyle.green, loop_label="prv"
        )
    )
    paginator.add_button(
        pages.PaginatorButton(
            "page_indicator", style=discord.ButtonStyle.gray, disabled=True
        )
    )
    paginator.add_button(
        pages.PaginatorButton(
            "next", label='>', style=discord.ButtonStyle.green, loop_label="nxt"
        )
    )
    paginator.add_button(
        pages.PaginatorButton(
            "last", label='>>', style=discord.ButtonStyle.red, loop_label="lst"
        )
    )

    return paginator

# get a user's rank in the leaderboard; use get_user_leaderboard_position in Database.py
# Args: user_id - user's id
# Returns: rank - user's rank and record in leaderboard
async def get_user_position(user_id, season: str = None):
    if not season:
        now = datetime.now(pytz.timezone('US/Eastern'))
        if now.month < 7 and now.month >= 1:
            season = str(now.year - 1) + '-' + str(now.year)
        else:
            season = str(now.year) + '-' + str(now.year + 1)

    return await db.get_user_leaderboard_position(user_id, season)

# post leaderboard embed to channel
async def post_leaderboard(channel: discord.TextChannel, season: str = None):
    # fetch most recent records updated_at from db
    records_updated = await db.get_records_updated_at()
    # convert records_updated to ET
    localtz = get_localzone()
    esttz = pytz.timezone('US/Eastern')
    curdt = localtz.localize(records_updated)
    est = curdt.astimezone(esttz)
    
    # format est to month day, year at h:mm; ex: January 1, 2021 at 4:30am
    est_str = est.strftime('%B %d, %Y at %I:%M%p ET')

    if not season:
        now = datetime.now(pytz.timezone('US/Eastern'))
        if now.month < 7 and now.month >= 1:
            season = str(now.year - 1) + '-' + str(now.year)
        else:
            season = str(now.year) + '-' + str(now.year + 1)

    # get leaderboards from db
    leaderboards = await db.get_leaderboard(season)

    if leaderboards:
        # get first 10 leaderboards
        leaderboards_list = {}
        for i, leaderboard in enumerate(leaderboards):
            leaderboards_list[leaderboard] = leaderboards[leaderboard]
            if i == 9:
                break
        
        # create leaderboard embed
        embed = await create_embed.create_leaderboard(leaderboards_list, est_str)

        # post embed to channel
        await channel.send(embed=embed)