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
		self.config.read(CONFIG_FILE)
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
		self.config.read(CONFIG_FILE)
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
		self.config.read(CONFIG_FILE)
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

	async def set_messages(self, section, messages):
		if section not in self.config.sections():
			self.config.add_section(section)

		self.config[section]['messages'] = str(messages)

		with open(CONFIG_FILE, 'w') as f:
			self.config.write(f)

	async def get_messages(self, section):
		self.config.read(CONFIG_FILE)
		if section not in self.config.sections():
			print('lul')
			return None

		try:
			messages = ast.literal_eval(self.config[section]['messages'])
			if messages and len(messages) > 0 and messages[0]:
				return [int(m) for m in messages]
			return None
		except Exception as e:
			print(e)
			return None

	async def update_channel_setting(self, ctx, channel_id, action, channel):
		channels_existing = await self.cfg.get_channels(channel_id)
		if action == 'add':
			try:
				if channels_existing is None:
					await self.cfg.set_channels(channel_id, [channel.id])
					await ctx.respond('Added channel.')
				else:
					if channel.id not in channels_existing:
						channels_existing.append(channel.id)
						await self.cfg.set_channels(channel_id, [c for c in channels_existing])
						await ctx.respond('Added channel.')
					else:
						await ctx.respond('Channel already exists in settings!')
			except Exception as e:
				self.log.exception("Error with updating channels")
				await ctx.respond('Error. Have my owner check logs.')
		elif action == 'remove':
			try:
				if channels_existing is None:
					await ctx.respond("Oops, no channels are set. Try `add`ing some.")
				else:
					tmp = list(channels_existing)
					if channel.id in tmp:
						tmp.remove(channel.id)

					if len(tmp) > 0:
						channels = tmp
						await self.cfg.set_channels(channel_id, [c for c in channels])
					else:
						channels = None
						await self.cfg.set_channels(channel_id, channels)
					await ctx.respond('Removed channel.')
			except Exception as e:
				self.log.exception("Error with deleting channels")
				await ctx.respond('Error. Have my owner check logs.')

	async def update_message_setting(self, ctx, message_id, action, message):
		messages_existing = await self.cfg.get_messages(message_id)

		if action == 'add':
			try:
				if messages_existing is None:
					await self.cfg.set_messages(message_id, [message])
					await ctx.respond('Added message.')
				else:
					if message not in messages_existing:
						messages_existing.append(message)
						await self.cfg.set_messages(message_id, [m for m in messages_existing])
						await ctx.respond('Added message.')
					else:
						await ctx.respond('Message already exists in settings!')
			except Exception as e:
				self.log.exception("Error with updating messages")
				await ctx.respond('Error. Have my owner check logs.')
		elif action == 'remove':
			try:
				if messages_existing is None:
					await ctx.respond("Oops, no messages are set. Try `add`ing some.")
				else:
					tmp = list(messages_existing)
					if int(message) in tmp:
						tmp.remove(message)

					if len(tmp) > 0:
						messages = tmp
						await self.cfg.set_messages(message_id, [m for m in messages])
					else:
						messages = None
						await self.cfg.set_messages(message_id, messages)
					await ctx.respond('Removed message.')
			except Exception as e:
				self.log.exception("Error with deleting messages")
				await ctx.respond('Error. Have my owner check logs.')

	async def update_role_setting(self, ctx, role_id, action, role):
		roles_existing = await self.cfg.get_roles(role_id)
		if action == 'add':
			try:
				if roles_existing is None:
					await self.cfg.set_roles(role_id, [role.id])
					await ctx.respond('Added role.')
				else:
					if role.id not in roles_existing:
						roles = roles_existing.append(role.id)
						await self.cfg.set_roles(role_id, [r for r in roles])
						await ctx.respond('Added role.')
					else:
						await ctx.respond('Role already exists in settings!')
			except Exception as e:
				self.log.exception("Error with updating roles")
				await ctx.respond('Error. Have my owner check logs.')
		elif action == 'remove':
			try:
				if roles_existing is None:
					await ctx.respond("Oops, no roles are set. Try `add`ing some.")
				else:
					tmp = list(roles_existing)
					if role.id in tmp:
						tmp.remove(role.id)

					if len(tmp) > 0:
						roles = tmp
						await self.cfg.set_roles(role_id, [r for r in roles])
					else:
						roles = None
						await self.cfg.set_roles(role_id, roles)
					await ctx.respond('Removed role.')
			except Exception as e:
				self.log.exception("Error with deleting roles")
				await ctx.respond('Error. Have my owner check logs.')