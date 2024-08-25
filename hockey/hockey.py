import asyncio
import aiohttp
from datetime import datetime, timedelta
#import logger

BASE_URL = 'https://api-web.nhle.com/v1'


async def is_game_today(date=None):
    game_date = ""
    if date:
        game_date = f"&date={date}"
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{BASE_URL}/scoreboard/njd/now") as resp:
                data = await resp.json()
    except Exception as e:
        print(e)
        #log.debug(_("Error grabbing the schedule for today."), exc_info=True)
        return False, None

    if data['focusedDateCount'] > 0:
        nextgame = data['gamesByDate'][0]['games'][0]
        if nextgame['gameState'] == 'FUT':
            return True, nextgame
    return False, None


async def next_game():
    today = datetime.today()
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{BASE_URL}/scoreboard/njd/now") as resp:
                data = await resp.json()

        if data['focusedDateCount'] > 0:
            for date in data['gamesByDate']:
                if date['date'] < today.strftime("%Y-%m-%d"):
                    continue
                for game in date['games']:
                    if game['gameState'] in ('FUT', 'PRE', 'LIVE'):
                        return True, game
        return False, None

    except Exception as e:
        print(e)
        #log.debug(_("Error grabbing the schedule for today."), exc_info=True)
        


async def get_team(team_id):
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("https://api.nhle.com/stats/rest/en/team") as resp:
                data = await resp.json()
    except Exception as e:
        print(e)
        return None

    for team in data['data']:
        if team['id'] == team_id:
            return team['fullName']


async def get_game(game_id, date=None):
    if date:
        game_id = await get_game_by_date(date)

    if game_id:
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{BASE_URL}/gamecenter/{game_id}/landing") as resp:
                    data = await resp.json()
                    return True, data
        except Exception as e:
            print(e)
            return None, None
    return False, None

async def get_game_by_date(date):
    if date:
        today = datetime.today()
        if today.month > 7:
            season = str(today.year) + str(today.year + 1)
        else:
            season = str(today.year - 1) + str(today.year)
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{BASE_URL}/club-schedule-season/njd/{season}") as resp:
                    data = await resp.json()
        except Exception as e:
            print(e)
            return None, None
        
        if len(data['games']) > 0:
            for game in data['games']:
                if game['gameDate'] == date:
                    return game['id']
        return None
    


async def get_next_x_games(x):
    # determine which season to use. if it's after july, use the next year
    # for example, if it's july 2021, use 20212022 season
    today = datetime.today()
    if today.month > 7:
        season = str(today.year) + str(today.year + 1)
    else:
        season = str(today.year - 1) + str(today.year)
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{BASE_URL}/club-schedule-season/njd/{season}") as resp:
                data = await resp.json()
    except Exception as e:
        print(e)
        return None, None

    if len(data['games']) > 0:
        games = []
        i = 0

        for game in data['games']:
            if datetime.strptime(game['gameDate'], "%Y-%m-%d") < today:
                continue
            if game['gameDate'] == today.strftime("%Y-%m-%d"):
                if game['gameState'] != 'FUT':
                    continue  # skip today's game if it's not FUT
            games.append(game)
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


async def get_game_feed_live(game_id):
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{BASE_URL}/game/{game_id}/feed/live") as resp:
                data = await resp.json()
    except Exception as e:
        print(e)
        return None

    return data


async def get_goal_highlight_url(highlight_id):
    url = f"https://edge.api.brightcove.com/playback/v1/accounts/6415718365001/videos/{highlight_id}"
    headers = {
        'Host': 'edge.api.brightcove.com',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0',
        'accept': 'application/json;pk=BCpkADawqM3l37Vq8trLJ95vVwxubXYZXYglAopEZXQTHTWX3YdalyF9xmkuknxjBgiMYwt8VZ_OZ1jAjYxz_yzuNh_cjC3uOaMspVTD-hZfNUHtNnBnhVD0Gmsih8TBF8QlQFXiCQM3W_u4ydJ1qK2Rx8ZutCUg3PHb7Q',
        'accept-language': 'en-US,en;q=0.5',
        'origin': 'https://players.brightcove.net',
        'dnt': '1',
        'referer': 'https://players.brightcove.net/',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'sec-gpc': '1',
        # Requests doesn't support trailers
        # 'te': 'trailers',
    }
    
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
    except Exception as e:
        print(e)
        return None
    
    # check if the highlight is available
    if 'error_code' in data:
        return None
    
    # get the highlight url - 720p
    for source in data['sources']:
        if 'codec' in source and source['codec'] == 'H264' and source['height'] == 720:
            return source['src']

    return None

async def get_team_record(team_name):
    date = datetime.now().strftime("%Y-%m-%d")
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{BASE_URL}/standings/{date}") as resp:
                data = await resp.json()
    except Exception as e:
        print(e)
        return None

    if len(data['standings']) == 0:
        return 0, 0, 0
    
    for team in data['standings']:
        if team['teamName'] == team_name:
            return team['wins'], team['losses'], team['ot']