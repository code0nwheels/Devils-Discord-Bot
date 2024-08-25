import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
import os

from hockey import hockey
from util import create_embed

logging.basicConfig(level=logging.INFO)

class Highlights():
	def __init__(self, bot, game_id, cfg):
		self.bot = bot
		self.game_id = game_id
		self.cfg = cfg
		self.log = logging.getLogger(__name__)

		self.goal_scorers_dict = {}
		self.highlight_ids = []
		self.highlights_cache = {}

		# add a rotating handler
		handler = RotatingFileHandler('log/highlights.log', maxBytes=5*1024*1024,
		                              backupCount=5)
		# create a logging format
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		handler.setFormatter(formatter)
		self.log.addHandler(handler)

	# post the goal highlight to discord
	async def send_message(self, channel_id, message=None, file=None, embed=None):
		self.log.info(f"Sending highlight message to {channel_id}")
		channel = self.bot.get_channel(channel_id)

		return await channel.send(message, file=file, embed=embed)

	async def edit_message(self, channel_id, message_id, embed=None):
		self.log.info(f"Editing highlight message id {message_id}")
		channel = self.bot.get_channel(channel_id)
		messageObj = await channel.fetch_message(message_id)

		return await messageObj.edit(embed=embed)

	# get goal nj devils scorers for a game from nhl api
	# also get who assisted on the goal; only get devils goals
	#create a dictionary of the goal scorers and their assists; key is goal number, value is a list of the goal scorer and their assists
	async def get_goal_scorers(self):
		# get the goal scorers for the game
		_, goal_scorers_info = await hockey.get_game(self.game_id)
		goal_scorers = goal_scorers_info['summary']['scoring']

		# get the goal scorers' names and assists
		
		for goal_ in goal_scorers:
			period = goal_['period']
			if period == 1:
				period = '1st'
			elif period == 2:
				period = '2nd'
			elif period == 3:
				period = '3rd'
			
			# check if the goal scorer is a devils player
			for goal in goal_['goals']:
				if goal['teamAbbrev'] == 'NJD':
					goal_scorers = []
					# get the highlight id
					if 'highlightClip' not in goal:
						continue
					highlight_id = goal['highlightClip']
					# get the goal scorer's name
					goal_scorer = goal['firstName'] + ' ' + goal['lastName']
					#print(goal_scorer)
					# get the goal scorer's total goals
					goal_scorer_goals = goal['goalsToDate']
					#print(goal_scorer_goals)
					goal_scorers.append([goal_scorer, goal_scorer_goals])

					# get the goal scorer's assists
					assists = []
					for assist in goal['assists']:
						# get the assist's name
						assister = assist['firstName'] + ' ' + assist['lastName']
						# get the assist's total assists
						assister_assists = assist['assistsToDate']
						assists.append([assister, assister_assists])
					
					# get time of goal; ex: 1st 10:00
					time = goal['timeInPeriod']
					time_of_goal = f'{period} {time}'

					# add the goal scorer, assists, and time of goal to the goal scorers dictionary
					self.goal_scorers_dict[highlight_id] = [goal_scorers, assists, time_of_goal]
					
					self.highlight_ids.append(highlight_id)

	# get highlight for a goal from nhl api
	# Args: highlight_id - the id of the highlight
	async def get_highlight(self, highlight_id):
		# get the goal highlight
		highlight_url = await hockey.get_goal_highlight_url(highlight_id)
		return highlight_url

	async def run(self):
		highlight_file = f'background/json/{str(self.game_id)}_highlight.json'
		final_count = 0
		devils_goals = 0

		# wait until the game starts
		while True:
			is_game, game_info = await hockey.get_game(self.game_id)
			
			if game_info['gameState'] == 'LIVE':
				break
			elif game_info['gameScheduleState'] in ['PPD', 'SUSP', 'CNCL']:
				return
			await asyncio.sleep(30)
		
		# check if highlight file exists
		if os.path.exists(highlight_file):
			with open(highlight_file, 'r') as f:
				self.highlights_cache = json.load(f)
		
		while True:
			# check if the game is over
			is_game, game_info = await hockey.get_game(self.game_id)
			gamestatus = game_info['gameState']
			schedstatus = game_info['gameScheduleState']
			#self.log.info(f'Status: {status}\nFinal: {final}')
			if gamestatus in ['OVER', 'FINAL', 'OFF'] or schedstatus in ['PPD', 'SUSP', 'CNCL']:
				final_count += 1
			else:
				final_count = 0
			
			# get devils goal count
			# determine if devils are home or away
			if game_info['homeTeam']['id'] == 1:
				devils_goals = game_info['homeTeam']['score']
			else:
				devils_goals = game_info['awayTeam']['score']
			# get the goal scorers and their assists
			await self.get_goal_scorers()

			# get the goal highlight then add it to the highlight cache
			for key, goal_scorer in self.goal_scorers_dict.items():
				print(key,goal_scorer)
				# get the goal scorer's name and how many goals they have; ex: Jack Hughes (2)
				goal_scorer_name = goal_scorer[0][0][0] + ' (' + str(goal_scorer[0][0][1]) + ')'
				# get the goal scorer's assists and how many assists they have; ex: Nico Hischier (2)
				assists = []
				for assister in goal_scorer[1]:
					assists.append(assister[0] + ' (' + str(assister[1]) + ')')
				# format the assists
				if assists:
					assists = ', '.join(assists)
				else:
					assists = 'None'
				# get the time of the goal
				time_of_goal = goal_scorer[2]
				if key in self.highlights_cache:
					# check if the same goal scorer and assists
					if self.highlights_cache[key]['goal_scorer'] == goal_scorer_name and self.highlights_cache[key]['assists'] == assists and self.highlights_cache[key]['time'] == time_of_goal:
						print('same goal scorer and assists')
						continue
					else:
						# update the goal scorer and assists
						self.highlights_cache[key]['goal_scorer'] = goal_scorer_name
						self.highlights_cache[key]['assists'] = assists
						time_of_goal = self.highlights_cache[key]['time']
						message_id = self.highlights_cache[key]['message_id']

						# create the embed
						file, embed = await create_embed.goal(goal_scorer_name, assists, time_of_goal)
						# send the updated embed
						await self.channel.edit_message(message_id, embed=embed)
				else:
					url = await self.get_highlight(key)
					url = f"[Link]({url})"
				if url:
					self.log.info(f'Highlight found for {goal_scorer_name}')
					# create the embed
					file, embed = await create_embed.goal(goal_scorer_name, assists, time_of_goal)
					# send the embed
					self.log.info(f'Sending embed for {goal_scorer_name}')
					channel_id = await self.cfg.get_channels('HighlightChannels')
					channel_id = channel_id[0]
					message = await self.send_message(int(channel_id), embed=embed, file=file)
					# send the highlight url
					self.log.info(f'Sending highlight for {goal_scorer_name}')
					await self.send_message(int(channel_id), url)

					# add the goal scorerk assists, and message id to the highlight cache as a dictionary with labels
					self.highlights_cache[key] = {'goal_scorer': goal_scorer_name, 'assists': assists, 'time': time_of_goal, 'message_id': message.id}
			
			# save the highlight cache to a json file
			with open(highlight_file, 'w') as f:
				json.dump(self.highlights_cache, f, indent=4)
			
			# check if the game is over
			if final_count >= 3:
				# if devils_goals == the number of goals in the highlight cache, we're done
				if devils_goals == len(self.highlights_cache):
					self.log.info('No more goals to be scored')
					break
				# if final_count is 12, an hour has passed since the game ended
				if final_count == 12:
					self.log.info('An hour has passed since the game ended')
					break
		
			# wait 5 minutes
			await asyncio.sleep(300)