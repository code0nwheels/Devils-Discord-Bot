import discord

from hockey.game import Game

SCORE_TEMPLATE = "{}-{} {}"
IMAGES_NHL = "images/NHL/"
IMAGES_ICONS = "images/icons/"

from pytz import timezone
from datetime import datetime
from tzlocal import get_localzone

async def create_game(game: Game, cmd: str):
	away_team_obj = await game.get_away_team()
	home_team_obj = await game.get_home_team()
	away_team = away_team_obj.full_name
	home_team = home_team_obj.full_name

	away_record = game.away_team_record
	home_record = game.home_team_record

	away_score = game.away_score
	home_score = game.home_score

	venue = game.venue

	game_time = game.game_time("%-I:%M %p")
	game_date = game.game_time("%B %-d, %Y")
	game_time_obj = datetime.strptime(game_time, "%I:%M %p")
	game_date_obj = datetime.strptime(game_date, "%B %d, %Y")

	game_time_epoch = int(game_time_obj.timestamp())
	game_date_epoch = int(game_date_obj.timestamp())

	if game.is_tbd:
		time = 'TBD'
	else:
		time = f"<t:{game_time_epoch}:t>" #time = datetime.strftime(est,  "%-I:%M %p")
	game_date = f"<t:{game_date_epoch}:D>"

	if away_team_obj.id == 1:
		team_file = home_team_obj.get_team_logo()
	else:
		team_file = away_team_obj.get_team_logo()

	team_file_name = team_file.filename

	embed = discord.Embed(title=game_date, color=0xff0000)
	embed.set_thumbnail(url=f"attachment://{team_file_name}")
	embed.add_field(name=away_team, value=away_record, inline=True)
	#embed.add_field(name="\u200b", value="\u200b", inline=True)
	embed.add_field(name=home_team, value=home_record, inline=True)
	embed.add_field(name="Time", value=time, inline=False)
	embed.add_field(name="Venue", value=venue, inline=True)
	if game.is_final:
		if game.get_away_team.id == 1:
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

	return team_file, embed

async def no_game(date, cmd, no_date=False):
	if not date and not no_date:
		localtz = get_localzone()
		esttz = timezone('US/Eastern')

		curdt = localtz.localize(datetime.now())
		est = curdt.astimezone(esttz)
		date = datetime.strftime(est,  "%B %-d, %Y")
	elif no_date:
		date = "No game"
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
	try:
		reported_at = datetime.strptime(reported_at, "%Y-%m-%d %H:%M:%S")
	except:
		reported_at = datetime.strptime(reported_at, "%Y-%m-%d %H:%M:%S.%f")
		
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

# Create a leaderboard embed
# Args: ranks - a dict containing the records of the users, keys are user IDs, values are list of wins, losses, win%, rank number
#       updated_at - a string containing the time the leaderboard was last updated
# footer: Last updated at <updated_at>
# omit embed field names 
async def create_leaderboard(ranks: dict, updated_at: str):
	ranks_str = ""
	embed = discord.Embed(color=0xff0000)
	embed.set_footer(text=f"Last updated at {updated_at}")
	for user_id, record in ranks.items():
		ranks_str += f"{record[3]}. <@{user_id}> {record[0]}-{record[1]} ({round(record[2]*100, 3)}%)\n"
		#embed.add_field(name="\u200b", value=f"{record[3]}. <@{user_id}> {record[0]}-{record[1]} ({round(record[2]*100, 3)}%)", inline=False)
	embed.description = ranks_str.strip()
	return embed

# Create a user picks embed
async def create_user_picks_embed(user: str, picks: list, date: str):
	embed = discord.Embed(title=f"{user}'s Picks for {date}", color=0xff0000)
	picks_str = ""

	for i, pick in enumerate(picks):
		picks_str += f"{i+1}. {pick}\n"
	
	embed.description = picks_str.strip()
	return embed
