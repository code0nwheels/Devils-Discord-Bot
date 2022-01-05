import configparser
import os
import ast

CONFIG_FILE = 'config.ini'

class Settings(object):
	"""docstring for Settings."""

	def __init__(self):
		super(Settings, self).__init__()

		self.config = configparser.ConfigParser()

		if not os.path.exists(CONFIG_FILE):
			with open(CONFIG_FILE, 'w'):
				pass
		self.config.read(CONFIG_FILE)

	async def set_roles(self, section, roles):
		if section not in self.config.sections():
			self.config.add_section(section)

		self.config[section]['roles'] = str(roles)

		with open(CONFIG_FILE, 'w') as f:
			self.config.write(f)

	async def get_roles(self, section):
		if section not in self.config.sections():
			return None

		try:
			roles = ast.literal_eval(self.config[section]['roles'])
			if len(roles) > 0 and roles[0]:
				#print(roles)
				return roles
			return None
		except Exception as e:
			print(e)
			return None

	async def set_channels(self, section, channels):
		if section not in self.config.sections():
			self.config.add_section(section)

		self.config[section]['channels'] = str(channels)

		with open(CONFIG_FILE, 'w') as f:
			self.config.write(f)

	async def get_channels(self, section):
		if section not in self.config.sections():
			return None

		try:
			channels = ast.literal_eval(self.config[section]['channels'])
			if len(channels) > 0 and channels[0]:
				#print(channels)
				return channels
			return None
		except Exception as e:
			print(e)
			return None

	async def set_auto_role_users(self, section, users):
		if section not in self.config.sections():
			self.config.add_section(section)

		self.config[section]['autoroles'] = str(users)

		with open(CONFIG_FILE, 'w') as f:
			self.config.write(f)

	async def get_auto_role_users(self, section):
		if section not in self.config.sections():
			return None

		try:
			roles = ast.literal_eval(self.config[section]['autoroles'])
			if len(roles) > 0 and roles[0]:
				#print(roles)
				return roles
			return None
		except Exception as e:
			print(e)
			return None
