import discord
import re
import os

from hockey import hockey

RECORD_TEMPLATE = "{}-{}-{}"
SCORE_TEMPLATE = "{}-{} {}"
IMAGES_NHL = "images/NHL/"
IMAGES_ICONS = "images/icons/"

from pytz import timezone
from datetime import datetime, timedelta
from tzlocal import get_localzone

async def create_game(game, cmd):
	away_id = game['teams']['away']['team']['id']
	#team = await hockey.get_team(away_id)
	away_team = game['teams']['away']['team']['name']#team['teamName']
	#home_id = game['teams']['home']['team']['id']
	#team = await hockey.get_team(home_id)
	home_team = game['teams']['home']['team']['name']#team['teamName']
	away_ot = game['teams']['away']['leagueRecord']['ot'] if 'ot' in game['teams']['away']['leagueRecord'] else 0
	home_ot = game['teams']['home']['leagueRecord']['ot'] if 'ot' in game['teams']['home']['leagueRecord'] else 0

	away_record = RECORD_TEMPLATE.format(game['teams']['away']['leagueRecord']['wins'], game['teams']['away']['leagueRecord']['losses'], away_ot)
	home_record = RECORD_TEMPLATE.format(game['teams']['home']['leagueRecord']['wins'], game['teams']['home']['leagueRecord']['losses'], home_ot)

	if game['gameType'] == 'R':
		away_pts = game['teams']['away']['leagueRecord']['wins'] * 2 + away_ot
		home_pts = game['teams']['home']['leagueRecord']['wins'] * 2 + home_ot
		away_record = f"{away_pts} PTS " + away_record
		home_record = f"{home_pts} PTS " + home_record

	away_score = game['teams']['away']['score']
	home_score = game['teams']['home']['score']

	venue = game['venue']['name']

	utctz = timezone('UTC')
	esttz = timezone('US/Eastern')
	time = game['gameDate']
	utc = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
	utc2 = utctz.localize(utc)
	est = utc2.astimezone(esttz)

	epoch = int(est.timestamp())

	if 'TBD' in game['status']['detailedState'] or game['status']['startTimeTBD']:
		time = 'TBD'
	else:
		time = f"<t:{epoch}:t>" #time = datetime.strftime(est,  "%-I:%M %p")
	date = f"<t:{epoch}:D>" #date = datetime.strftime(est,  "%B %-d, %Y")

	if away_id == 1:
		teamlogo = re.sub(' ', '', home_team)
	else:
		teamlogo = re.sub(' ', '', away_team)

	#teamlogo = teamlogo.replace('é', 'e')

	embed = discord.Embed(title=date, color=0xff0000)
	#file = discord.File(f"{IMAGES_NHL}Logos/{teamlogo}.png", filename=f"{teamlogo}.png")
	embed.set_thumbnail(url=f"https://devsdiscord.com/images/NHL/Logos/{teamlogo}.png")
	embed.add_field(name=away_team, value=away_record, inline=True)
	#embed.add_field(name="\u200b", value="\u200b", inline=True)
	embed.add_field(name=home_team, value=home_record, inline=True)
	embed.add_field(name="Time", value=time, inline=False)
	embed.add_field(name="Venue", value=venue, inline=True)
	if game['status']['detailedState'] == 'Final':
		if away_id == 1:
			if away_score > home_score:
				embed.add_field(name="Score", value=SCORE_TEMPLATE.format(away_score, home_score, 'W'), inline=True)
			else:
				embed.add_field(name="Score", value=SCORE_TEMPLATE.format(away_score, home_score, 'L'), inline=True)
		else:
			if away_score < home_score:
				embed.add_field(name="Score", value=SCORE_TEMPLATE.format(away_score, home_score, 'W'), inline=True)
			else:
				embed.add_field(name="Score", value=SCORE_TEMPLATE.format(away_score, home_score, 'L'), inline=True)
	embed.set_footer(text=cmd)

	return embed

async def no_game(date, cmd):
	if not date:
		localtz = get_localzone()
		esttz = timezone('US/Eastern')

		curdt = localtz.localize(datetime.now())
		est = curdt.astimezone(esttz)
	else:
		est = datetime.strptime(date, "%Y-%m-%d")

	date = datetime.strftime(est,  "%B %-d, %Y")

	embed = discord.Embed(title=date, color=0xff0000)
	file = discord.File(f"{IMAGES_ICONS}FeelsDevilsMan.png", filename=f"FeelsDevilsMan.png")
	embed.set_thumbnail(url=f"attachment://FeelsDevilsMan.png")
	embed.add_field(name="No game!", value="\u200b", inline=True)
	embed.set_footer(text=cmd)

	return file, embed

async def goal(scorer, assists, time):
	embed = discord.Embed(title="GOAL", color=0xff0000)
	file = discord.File(f"{IMAGES_ICONS}GoalLight.gif", filename=f"GoalLight.gif")
	embed.set_thumbnail(url=f"attachment://GoalLight.gif")
	embed.add_field(name="Scored by", value=scorer, inline=True)
	embed.add_field(name="Assists", value=assists, inline=True)
	embed.add_field(name="Time", value=time, inline=False)

	return file, embed

async def help(category, commands):
	embed = discord.Embed(title=category, description="", color=0x0080ff)
	file = discord.File(f"{IMAGES_ICONS}DevilsWhat.png", filename=f"DevilsWhat.png")
	embed.set_image(url=f"attachment://DevilsWhat.png")
	for command in commands:
		embed.add_field(name=command[0], value=command[1], inline=False)
	embed.set_footer(text="/help")

	return embed

async def incident(incident_id, user_id, description, decision, reported_by, reported_at):
	embed=discord.Embed(title=f"Incident #{incident_id}", description=f"<@{user_id}>")
	embed.add_field(name="Description", value=description, inline=False)
	embed.add_field(name="Decision", value=decision, inline=True)
	embed.add_field(name="Reported by", value=f"<@{reported_by}>", inline=True)
	embed.set_footer(text=reported_at.strftime("%D %I:%M %p"))

	return embed

async def create(title, description, names, values, cmd, thumbnail=None):
	embed = discord.Embed(title=title, description=description)
	if thumbnail:
		embed.set_thumbnail(url=thumbnail)
	for i, name in enumerate(names):
		embed.add_field(name=name, value=values[i], inline=False)
	embed.set_footer(text=cmd)

	return embed
