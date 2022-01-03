import asyncio
import aiohttp
from datetime import datetime, timedelta
#import logger

BASE_URL = 'https://statsapi.web.nhl.com/api/v1'

async def is_game_today(date=None):
	game_date = ""
	if date:
		game_date = f"&date={date}"
	try:
		timeout = aiohttp.ClientTimeout(total=20)
		async with aiohttp.ClientSession(timeout=timeout) as session:
			async with session.get(f"{BASE_URL}/schedule?teamId=1{game_date}") as resp:
				data = await resp.json()
	except Exception as e:
		print(e)
		#log.debug(_("Error grabbing the schedule for today."), exc_info=True)
		return False, None

	if data['totalGames'] > 0:
		if data['dates'][0]['games'][0]['status']['detailedState'] not in ['Final', 'Game Over', 'Postponed']:
			return True, data['dates'][0]['games'][0]
	return False, None

async def next_game():
	try:
		timeout = aiohttp.ClientTimeout(total=20)
		async with aiohttp.ClientSession(timeout=timeout) as session:
			async with session.get(f"{BASE_URL}/teams/1?expand=team.schedule.next") as resp:
				data = await resp.json()

		if 'nextGameSchedule' in data['teams'][0]:
			if data['teams'][0]['nextGameSchedule']['dates'][0]['games'][0]['status']['detailedState'] != "Postponed":
				return True, data['teams'][0]['nextGameSchedule']['dates'][0]['games'][0]
	except Exception as e:
		print(e)
		#log.debug(_("Error grabbing the schedule for today."), exc_info=True)

	start = datetime.now()
	end = start + timedelta(days=30)
	start_date = start.strftime('%Y-%m-%d')
	end_date = end.strftime('%Y-%m-%d')
	print(f"{BASE_URL}/schedule?teamId=1&startDate={start_date}&endDate={end_date}")
	try:
		timeout = aiohttp.ClientTimeout(total=20)
		async with aiohttp.ClientSession(timeout=timeout) as session:
			async with session.get(f"{BASE_URL}/schedule?teamId=1&startDate={start_date}&endDate={end_date}") as resp:
				data = await resp.json()
	except Exception as e:
		print(e)
		#log.debug(_("Error grabbing the schedule for today."), exc_info=True)
		return False, None

	for date in data['dates']:
		if date['games'][0]['status']['detailedState'] == "Scheduled":
			return True, date['games'][0]
	return False, None

async def get_team(team_id):
	try:
		timeout = aiohttp.ClientTimeout(total=20)
		async with aiohttp.ClientSession(timeout=timeout) as session:
			async with session.get(f"{BASE_URL}/teams/{team_id}") as resp:
				data = await resp.json()
	except Exception as e:
		print(e)
		return None

	return data['teams'][0]

async def get_game(game_id, date=None):
	params = {}
	if game_id:
		params['gamePk'] = game_id
	if date:
		params['date'] = date
	params['teamId'] = '1'
	try:
		timeout = aiohttp.ClientTimeout(total=20)
		async with aiohttp.ClientSession(timeout=timeout) as session:
			async with session.get(f"{BASE_URL}/schedule", params=params) as resp:
				data = await resp.json()
	except Exception as e:
		print(e)
		return None, None

	if game_id:
		return True, data['dates'][0]['games'][0]
	else:
		if data['totalGames'] > 0:
			return True, data['dates'][0]['games'][0]
	return False, None

async def get_next_x_games(x):
	params = {}
	params['startDate'] = datetime.now().strftime("%Y-%m-%d")
	params['endDate'] = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
	params['teamId'] = '1'
	try:
		timeout = aiohttp.ClientTimeout(total=20)
		async with aiohttp.ClientSession(timeout=timeout) as session:
			async with session.get(f"{BASE_URL}/schedule", params=params) as resp:
				data = await resp.json()
	except Exception as e:
		print(e)
		return None, None

	if data['totalGames'] > 0:
		dates = data['dates']
		games = []
		i = 0

		for d in dates:
			games.append(d['games'][0])
			i += 1

			if i == x:
				break

		return True, games
	return False, None

async def get_game_content(game_id):
	try:
		timeout = aiohttp.ClientTimeout(total=20)
		async with aiohttp.ClientSession(timeout=timeout) as session:
			async with session.get(f"{BASE_URL}/game/{game_id}/content") as resp:
				data = await resp.json()
	except Exception as e:
		print(e)
		return None

	return data

async def get_game_boxscore(game_id):
	try:
		timeout = aiohttp.ClientTimeout(total=20)
		async with aiohttp.ClientSession(timeout=timeout) as session:
			async with session.get(f"{BASE_URL}/game/{game_id}/boxscore") as resp:
				data = await resp.json()
	except Exception as e:
		print(e)
		return None

	return data
