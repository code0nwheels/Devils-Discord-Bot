"""RUN THIS AS A CRONJOB"""

from bs4 import BeautifulSoup
import requests

import re

def dailyfaceoff_lines_parser(lines, soup):
	"""A sub-function of the dailyfaceoff_lines(...) that takes a BS4 Soup
		and parses it to break it down by individual player & position.
	Args:
		lines: Existing lines dictionary (append)
		soup: A valid souped response
	Return:
		lines: Modified lines dictionary
	"""

	for player in soup:
		try:
			soup_position = player["id"]
			line = soup_position[-1]
			position = soup_position[0:-1]
			player_position = f"{line}{position}"
			name = player.find("a").text

			# Add player & position to existing lines dictionary
			lines[player_position] = name
		except KeyError:
			pass  # This is a valid exception - not a player.

	return lines

def main():
	fwd_lines = dict()
	def_lines = dict()
	goalie_lines = dict()
	lines = dict()
	regex = r"(?<!\w)(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}>?, \d{4,}>?(?!\w)"

	headers = {
		'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0",
	}

	resp = requests.get("https://www.dailyfaceoff.com/teams/new-jersey-devils/line-combinations/", headers=headers)
	text = resp.text
	soup = BeautifulSoup(text, "lxml")

	combos = soup.find("div", class_="team-line-combination-wrap")
	soup_forwards = combos.find("table", {"id": "forwards"}).find("tbody").find_all("td")
	soup_defense = combos.find("table", {"id": "defense"}).find("tbody").find_all("td")
	soup_goalies = combos.find("table", {"id": "goalie_list"}).find("tbody").find_all("td")
	soup_update = soup.find("div", class_="team-line-combination-last-updated")

	date_match = re.search(regex, soup_update.text)
	if date_match:
		last_update = date_match.group(0)
	else:
		last_update = soup_update.text.replace("\n", "").strip().split(": ")[1]

	fwd_lines = dailyfaceoff_lines_parser(fwd_lines, soup_forwards)
	def_lines = dailyfaceoff_lines_parser(def_lines, soup_defense)
	goalie_lines = dailyfaceoff_lines_parser(goalie_lines, soup_goalies)

	# Now create the forward & defense strings
	# Iterate over the forwards dictionary & take into account 11/7 lineups
	fwd_line_string = list()
	fwd_all_list = list()

	fwd_num = len(fwd_lines.items())
	for idx, (_, player) in enumerate(fwd_lines.items()):
		last_name = " ".join(player.split()[1:])
		fwd_line_string.append(last_name)
		if len(fwd_line_string) == 3 or (idx + 1) == fwd_num:
			fwd_line_string = " - ".join(fwd_line_string)
			fwd_all_list.append(fwd_line_string)
			fwd_line_string = list()

	# Iterate over the defense dictionary & take into account 11/7 lineups
	def_line_string = list()
	def_all_list = list()

	def_num = len(def_lines.items())
	for idx, (_, player) in enumerate(def_lines.items()):
		last_name = " ".join(player.split()[1:])
		def_line_string.append(last_name)
		if len(def_line_string) == 2 or (idx + 1) == def_num:
			def_line_string = " - ".join(def_line_string)
			def_all_list.append(def_line_string)
			def_line_string = list()

	g_all_list = list()
	g_num = len(goalie_lines.items())
	for idx, (_, player) in enumerate(goalie_lines.items()):
		last_name = " ".join(player.split()[1:])
		g_all_list.append(last_name)

	# Combine the 'all-strings' separated by new lines
	fwd_all_string = "\n".join(fwd_all_list)
	def_all_string = "\n".join(def_all_list)
	g_all_string = "\n".join(g_all_list)

	with open("lines.txt", 'w') as f:
		f.write(fwd_all_string + '\n===\n')
		f.write(def_all_string + '\n===\n')
		f.write(g_all_string + '\n===\n')
		f.write(last_update)

if __name__ == '__main__':
	main()
