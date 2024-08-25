import discord
from discord.ext import commands
from util import create_embed, settings, parseduration, timer
from discord.utils import get

import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

import asyncio

from typing import Union

PREFIX = '$'
BANISH_TIMERS = {}

class Admins(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.cfg = settings.Settings()

		logging.basicConfig(level=logging.INFO)
		self.log = logging.getLogger(__name__)
		# add a rotating handler
		handler = RotatingFileHandler('log/admin.log', maxBytes=5*1024*1024,
									  backupCount=5)

		# create a logging format
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		handler.setFormatter(formatter)
		self.log.addHandler(handler)

		self.db = self.bot.get_cog('Database')

	def cog_unload(self):
		if self.loop is not None:
			self.loop.close()

	async def setup_banished(self):
		banished_user_data = await self.db.get_banished()
		for d in banished_user_data:
			user = get(self.bot.guilds[0].members, id=int(d[0]))

			if user:
				unbanish_at = d[1]

				if datetime.now() >= unbanish_at:
					await self.unbanish_cb(user)
				else:
					total_banish_secs = (unbanish_at-datetime.now()).total_seconds()
					timer_ = timer.Timer(total_banish_secs, self.unbanish_cb, user)
					BANISH_TIMERS[str(user.id)] = timer_

	@commands.slash_command(guild_ids=[865256332646154300], name='open', description='Opens game chat. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def open(self, ctx):
		self.log.info(f"{ctx.author} opened game channels")
		worker_tasks = []

		for channel_id in await self.cfg.get_channels('GameChannels'):
			for role in await self.cfg.get_roles('GameChannels'):
				wt = asyncio.ensure_future(self.open_channel(channel_id, int(role), ctx))
				worker_tasks.append(wt)

		results = await asyncio.gather(*worker_tasks)

	async def open_channel(self, channel_id, role, ctx):
		self.log.info(f'Opening {channel_id} for {role}')
		channel = self.bot.get_channel(int(channel_id))
		role = get(ctx.guild.roles, id=role)
		await channel.set_permissions(role, read_messages=True,
														  send_messages=None)
		await channel.send('Game chat is open!')

	@open.error
	async def open_error(self, ctx, error):
		self.log.info(f"{ctx.author} tried to open game channels")

	@commands.slash_command(guild_ids=[865256332646154300], name='close', description='Closes game chat. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def close(self, ctx):
		self.log.info(f"{ctx.author} closed game channels")

		worker_tasks = []

		for channel_id in await self.cfg.get_channels('GameChannels'):
			for role in await self.cfg.get_roles('GameChannels'):
				wt = asyncio.ensure_future(self.close_channel(channel_id, int(role), ctx))
				worker_tasks.append(wt)

		results = await asyncio.gather(*worker_tasks)

	async def close_channel(self, channel_id, role, ctx):
		self.log.info(f'Closing {channel_id}')
		channel = self.bot.get_channel(int(channel_id))
		role = get(ctx.guild.roles, id=role)
		await channel.set_permissions(role, read_messages=True,
														  send_messages=False)
		await channel.send('Game chat is closed!')

	@close.error
	async def close_error(self, ctx, error):
		self.log.info(f"{ctx.author} tried to close game channels")

	@commands.slash_command(guild_ids=[865256332646154300], name='gamechatrole', description='Set or remove role(s) for game chat. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def gamechatrole(self, ctx, action, *roles):
		roles = [await commands.RoleConverter(role) for role in roles]
		self.log.info(f"{ctx.author} is {action} roles: {str(roles)}")
		roles_existing = await self.cfg.get_roles('GameChannels')
		if action == 'add':
			try:
				if roles_existing is None:
					await self.cfg.set_roles('GameChannels', [r.id for r in roles])
				else:
					add_roles = list(roles)
					for erole in roles_existing:
						if erole in roles:
							add_roles.remove(erole)
					roles = roles_existing + add_roles
					await self.cfg.set_roles('GameChannels', [r.id if isinstance(r, discord.Role) else r for r in roles])
				await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with updating game channel roles")
				await ctx.message.add_reaction('❌')
		elif action == 'remove':
			try:
				if roles_existing is None:
					await ctx.message.add_reaction('❌')
					await ctx.send("Oops, no roles are set. Try `add`ing some.")
				else:
					rem_roles = list(roles)
					tmp = list(roles_existing)
					for erole in roles_existing:
						if erole in rem_roles:
							tmp.remove(erole)

					if len(tmp) > 0:
						roles = tmp
						await self.cfg.set_roles('GameChannels', [r.id if isinstance(r, discord.Role) else r for r in roles])
					else:
						roles = None
						await self.cfg.set_roles('GameChannels', roles)
					await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with deleting game channel roles")
				await ctx.message.add_reaction('❌')
		else:
			await ctx.send(f"Invalid argument. `{PREFIX}gamechatrole <add/remove> <@roles>`")

	@gamechatrole.error
	async def gamechatrole_error(self, ctx, error):
		self.log.info(f"{ctx.author.name} tried to gamechatrole")
		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}gamechatrole <add/remove> <@roles>`")

	@commands.slash_command(guild_ids=[865256332646154300], name='banishedrole', description='Set or remove role(s) for banished role. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def banishedrole(self, ctx, action, *roles):
		roles = [await commands.RoleConverter(role) for role in roles]
		self.log.info(f"{ctx.author} is {action} roles: {str(roles)}")
		roles_existing = await self.cfg.get_roles('BanishedRole')
		if action == 'add':
			try:
				if roles_existing is None:
					await self.cfg.set_roles('BanishedRole', [r.id for r in roles])
				else:
					add_roles = list(roles)
					for erole in roles_existing:
						if erole in roles:
							add_roles.remove(erole)
					roles = roles_existing + add_roles
					await self.cfg.set_roles('BanishedRole', [r.id if isinstance(r, discord.Role) else r for r in roles])
				await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with updating banished roles")
				await ctx.message.add_reaction('❌')
		elif action == 'remove':
			try:
				if roles_existing is None:
					await ctx.message.add_reaction('❌')
					await ctx.send("Oops, no roles are set. Try `add`ing some.")
				else:
					rem_roles = list(roles)
					tmp = list(roles_existing)
					for erole in roles_existing:
						if erole in rem_roles:
							tmp.remove(erole)

					if len(tmp) > 0:
						roles = tmp
						await self.cfg.set_roles('BanishedRole', [r.id if isinstance(r, discord.Role) else r for r in roles])
					else:
						roles = None
						await self.cfg.set_roles('BanishedRole', roles)
					await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with deleting banished roles")
				await ctx.message.add_reaction('❌')
		else:
			await ctx.send(f"Invalid argument. `{PREFIX}banishedrole <add/remove> <@roles>`")

	@banishedrole.error
	async def banishedrole_error(self, ctx, error):
		self.log.info(f"{ctx.author} tried to banishedrole")
		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}banishedrole <add/remove> <@roles>`")

	@commands.slash_command(guild_ids=[865256332646154300], name='autorole', description='Set Stream Watcher role for user(s) for game chat. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def autorole(self, ctx, action, *members):
		self.log.info(f"{ctx.author} is {action} users from autorole")
		tmp = []
		for member in members:
			tmp.append(int(member.strip('<@!>')))
		members = tmp
		users_existing = await self.cfg.get_auto_role_users('GameChannels')
		if action == 'add':
			try:
				for euser in members:
					user = get(bot.get_all_members(), id=str(euser))
					if not user:
						await ctx.send(f"I can't find user with ID: {euser}")
						members.remove(euser)
				if users_existing is None:
					await self.cfg.set_auto_role_users('GameChannels', [m for m in members])
				else:
					add_users = list(members)
					for euser in add_users:
						if euser in users_existing:
							add_users.remove(euser)
					users = users_existing + add_users

					await self.cfg.set_auto_role_users('GameChannels', [m for m in users])
				await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with updating auto role users")
				await ctx.message.add_reaction('❌')
		elif action == 'remove':
			try:
				if users_existing is None:
					await ctx.message.add_reaction('❌')
					await ctx.send("Oops, no users are set. Try `add`ing some.")
				else:
					rem_users = list(members)
					tmp = list(users_existing)
					for user in rem_users:
						if user in users_existing:
							self.log.info(f"Removing {user}...")
							tmp.remove(user)
						else:
							_user = get(bot.get_all_members(), id=str(user))
							if not _user:
								await ctx.send(f"I can't find user with ID: {user}")

					if len(tmp) > 0:
						users = tmp
						await self.cfg.set_auto_role_users('GameChannels', [m for m in users])
					else:
						users = None
						await self.cfg.set_users('GameChannels', users)
					await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with deleting auto role users")
				await ctx.message.add_reaction('❌')
		else:
			await ctx.send(f"Invalid argument. `{PREFIX}autorole <add/remove> <@users>`")

	@autorole.error
	async def autorole_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to autorole")
		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}autorole <add/remove> <@users>`")

	@commands.slash_command(guild_ids=[865256332646154300], name='gamechannel', description='Set or remove channel(s) for game chat. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def gamechannel(self, ctx, action, *channels):
		channels = [await commands.TextChannelConverter.convert(channel) for channel in channels]
		self.log.info(f"{ctx.author} is {action} game channels: {str(channels)}")
		channels_existing = await self.cfg.get_channels('GameChannels')
		if action == 'add':
			try:
				if channels_existing is None:
					await self.cfg.set_channels('GameChannels', [c.id for c in channels])
				else:
					add_channels = list(channels)
					for echannel in channels_existing:
						if echannel in channels:
							add_channels.remove(echannel)
					channels = channels_existing + add_channels
					await self.cfg.set_channels('GameChannels', [c.id if isinstance(c, discord.Channel) else c for c in roles])
				await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with updating game channels")
				await ctx.message.add_reaction('❌')
		elif action == 'remove':
			try:
				if channels_existing is None:
					await ctx.message.add_reaction('❌')
					await ctx.send("Oops, no channels are set. Try `add`ing some.")
				else:
					rem_channels = list(channels)
					tmp = list(channels_existing)
					for echannel in channels_existing:
						if echannel in rem_channels:
							tmp.remove(echannel)

					if len(tmp) > 0:
						channels = tmp
						await self.cfg.set_channels('GameChannels', [c.id if isinstance(c, discord.Channel) else c for c in roles])
					else:
						channels = None
						await self.cfg.set_channels('GameChannels', channels)
					await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with deleting game channels")
				await ctx.message.add_reaction('❌')
		else:
			await ctx.send(f"Invalid argument. `{PREFIX}gamechannel <add/remove> <#channels>`")

	@gamechannel.error
	async def gamechannel_error(self, ctx, error):
		self.log.info(f"{ctx.author} tried to setgamechannel")
		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}gamechannel <add/remove> <#channels>`")

	@commands.slash_command(guild_ids=[865256332646154300], name='highlightchannel', description='Set or remove channel(s) for highlights. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def highlightchannel(self, ctx, action, *channels):
		channels = [await commands.TextChannelConverter.convert(channel) for channel in channels]
		self.log.info(f"{ctx.author} is {action} highlight channels: {str(channels)}")
		channels_existing = await self.cfg.get_channels('HighlightChannels')
		if action == 'add':
			try:
				if channels_existing is None:
					await self.cfg.set_channels('HighlightChannels', [c.id for c in channels])
				else:
					add_channels = list(channels)
					for echannel in channels_existing:
						if echannel in channels:
							add_channels.remove(echannel)
					channels = channels_existing + add_channels
					await self.cfg.set_channels('HighlightChannels', [c.id if isinstance(c, discord.Channel) else c for c in roles])
				await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with updating highlight channels")
				await ctx.message.add_reaction('❌')
		elif action == 'remove':
			try:
				if channels_existing is None:
					await ctx.message.add_reaction('❌')
					await ctx.send("Oops, no channels are set. Try `add`ing some.")
				else:
					rem_channels = list(channels)
					tmp = list(channels_existing)
					for echannel in channels_existing:
						if echannel in rem_channels:
							tmp.remove(echannel)

					if len(tmp) > 0:
						channels = tmp
						await self.cfg.set_channels('HighlightChannels', [c.id if isinstance(c, discord.Channel) else c for c in roles])
					else:
						channels = None
						await self.cfg.set_channels('HighlightChannels', channels)
					await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with deleting highlight channels")
				await ctx.message.add_reaction('❌')
		else:
			await ctx.send(f"Invalid argument. `{PREFIX}highlightchannel <add/remove> <#channels>`")

	@highlightchannel.error
	async def highlightchannel_error(self, ctx, error):
		self.log.info(f"{ctx.author} tried to highlightchannel")
		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}highlightchannel <add/remove> <#channels>`")

	@commands.slash_command(guild_ids=[865256332646154300], name='socialmediachannel', description='Set or remove channel(s) for socialmediachannels. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def socialmediachannel(self, ctx, action, *channels):
		channels = [await commands.TextChannelConverter.convert(channel) for channel in channels]
		self.log.info(f"{ctx.author} is {action} socialmediachannel channels: {str(channels)}")
		channels_existing = await self.cfg.get_channels('SocialMediaChannels')
		if action == 'add':
			try:
				if channels_existing is None:
					await self.cfg.set_channels('SocialMediaChannels', [c.id for c in channels])
				else:
					add_channels = list(channels)
					for echannel in channels_existing:
						if echannel in channels:
							add_channels.remove(echannel)
					channels = channels_existing + add_channels
					await self.cfg.set_channels('SocialMediaChannels', [c.id if isinstance(c, discord.Channel) else c for c in roles])
				await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with updating socialmediachannel channels")
				await ctx.message.add_reaction('❌')
		elif action == 'remove':
			try:
				if channels_existing is None:
					await ctx.message.add_reaction('❌')
					await ctx.send("Oops, no channels are set. Try `add`ing some.")
				else:
					rem_channels = list(channels)
					tmp = list(channels_existing)
					for echannel in channels_existing:
						if echannel in rem_channels:
							tmp.remove(echannel)

					if len(tmp) > 0:
						channels = tmp
						await self.cfg.set_channels('SocialMediaChannels', [c.id if isinstance(c, discord.Channel) else c for c in roles])
					else:
						channels = None
						await self.cfg.set_channels('SocialMediaChannels', channels)
					await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with deleting socialmediachannel channels")
				await ctx.message.add_reaction('❌')
		else:
			await ctx.send(f"Invalid argument. `{PREFIX}socialmediachannel <add/remove> <#channels>`")

	@socialmediachannel.error
	async def socialmediachannel_error(self, ctx, error):
		self.log.info(f"{ctx.author} tried to socialmediachannel")
		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}socialmediachannel <add/remove> <#channels>`")

	@commands.slash_command(guild_ids=[865256332646154300], name='fourtwentychannel', description='Set or remove channel(s) for fourtwentychannels. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def fourtwentychannel(self, ctx, action, *channels):
		channels = [await commands.TextChannelConverter.convert(channel) for channel in channels]
		self.log.info(f"{ctx.author} is {action} fourtwentychannel channels: {str(channels)}")
		channels_existing = await self.cfg.get_channels('FourTwentyChannels')
		if action == 'add':
			try:
				if channels_existing is None:
					await self.cfg.set_channels('FourTwentyChannels', [c.id for c in channels])
				else:
					add_channels = list(channels)
					for echannel in channels_existing:
						if echannel in channels:
							add_channels.remove(echannel)
					channels = channels_existing + add_channels
					await self.cfg.set_channels('FourTwentyChannels', [c.id if isinstance(c, discord.Channel) else c for c in roles])
				await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with updating fourtwentychannel channels")
				await ctx.message.add_reaction('❌')
		elif action == 'remove':
			try:
				if channels_existing is None:
					await ctx.message.add_reaction('❌')
					await ctx.send("Oops, no channels are set. Try `add`ing some.")
				else:
					rem_channels = list(channels)
					tmp = list(channels_existing)
					for echannel in channels_existing:
						if echannel in rem_channels:
							tmp.remove(echannel)

					if len(tmp) > 0:
						channels = tmp
						await self.cfg.set_channels('FourTwentyChannels', [c.id if isinstance(c, discord.Channel) else c for c in roles])
					else:
						channels = None
						await self.cfg.set_channels('FourTwentyChannels', channels)
					await ctx.message.add_reaction('✅')
			except Exception as e:
				self.log.exception("Error with deleting fourtwentychannel channels")
				await ctx.message.add_reaction('❌')
		else:
			await ctx.send(f"Invalid argument. `{PREFIX}fourtwentychannel <add/remove> <#channels>`")

	@fourtwentychannel.error
	async def fourtwentychannel_error(self, ctx, error):
		self.log.info(f"{ctx.author} tried to fourtwentychannel")
		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}fourtwentychannel <add/remove> <#channels>`")

	@commands.slash_command(guild_ids=[865256332646154300], name='setrole', description='Set role for users. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def setrole(self, ctx, role, *users):
		role = await commands.RoleConverter.convert(role)
		users = [await commands.MemberConverter.convert(user) for user in users]
		if int(ctx.author.id) not in [364425223388528651, int(ctx.guild.owner.id)]:
			highest_role = ctx.author.roles[-1]
			all_roles = ctx.guild.roles

			if all_roles.index(highest_role) <= all_roles.index(role):
				await ctx.send("You're not allowed to add a role that's equal to or above your highest role!")
				return

		for user in users:
			self.log.info(f"{ctx.author} is giving {role.name} to {user.name}")

			if role not in user.roles:
				await user.add_roles(role)
				"""if role.name == 'Stream Watcher':
					await user.edit(nick='🌐 ' + user.display_name + ' 🌐')"""
				await ctx.send(f"{user.name} has been given a role called: {role.name}")

	@setrole.error
	async def setrole_error(self, ctx, error):
		self.log.info(f"{ctx.author} tried to giving a role")
		self.log.error(traceback.format_exc())

		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}setrole @role @user(s)`")

	@commands.slash_command(guild_ids=[865256332646154300], name='unsetrole', description='Usnet role for users. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def unsetrole(self, ctx, role, *users):
		role = await commands.RoleConverter.convert(role)
		users = [await commands.MemberConverter.convert(user) for user in users]
		if int(ctx.author.id) not in [364425223388528651, int(ctx.guild.owner.id)]:
			highest_role = ctx.author.roles[-1]
			all_roles = ctx.guild.roles

			if all_roles.index(highest_role) <= all_roles.index(role):
				await ctx.send("You're not allowed to remove a role that's equal to or above your highest role!")
				return

		if isinstance(users[0], str):
			if users[0].lower() == 'all':
				users = role.members
			else:
				raise

		for user in users:
			self.log.info(f"{ctx.author} is removing {role.name} from {user.name}")

			await user.remove_roles(role)
			"""if role.name == 'Stream Watcher':
				if '🌐' in user.display_name:
					name = re.sub('🌐', '', user.display_name)
				await user.edit(nick=name)"""
			await ctx.send(f"{user.name} has been stripped of a role called: {role.name}")

	@unsetrole.error
	async def unsetrole_error(self, ctx, error):
		self.log.info(f"{ctx.author} tried to giving a role")
		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}unsetrole @role @user(s)/all`")
		self.log.exception("error")

	@commands.slash_command(guild_ids=[865256332646154300], name='getconfig', description='Gets bot\'s settings. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def getconfig(self, ctx):
		self.log.info(f"{ctx.author} is getting config")
		names = ["Game Channels", "Game Channels Role", "Highlight Channels", "Auto Stream Watcher", "Social Media Channels", "Four Twenty Channels", "Banished Roles"]

		gc = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('GameChannels')) if await self.cfg.get_channels('GameChannels') else 'None'
		gr = ', '.join(f"<@&{r}>" for r in await self.cfg.get_roles('GameChannels')) if await self.cfg.get_roles('GameChannels') else 'None'
		hc = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('HighlightChannels')) if await self.cfg.get_channels('HighlightChannels') else 'None'
		ar = ', '.join(f"<@{r}>" for r in await self.cfg.get_auto_role_users('GameChannels')) if await self.cfg.get_auto_role_users('GameChannels') else 'None'
		smf = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('SocialMediaChannels')) if await self.cfg.get_channels('SocialMediaChannels') else 'None'
		ft = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('FourTwentyChannels')) if await self.cfg.get_channels('FourTwentyChannels') else 'None'
		br = ', '.join(f"<@&{r}>" for r in await self.cfg.get_roles('BanishedRole')) if await self.cfg.get_roles('BanishedRole') else 'None'

		values = [gc, gr, hc, ar, smf, ft, br]

		embed = await create_embed.create('Config', "Bot's settings", names, values, f"{PREFIX}getconfig")

		await ctx.send(embed=embed)

	@getconfig.error
	async def getconfig_error(self, ctx, error):
		self.log.info(f"{ctx.author} tried to get config")

	async def unbanish_cb(self, user: discord.Member, ctx=None, reply=False):
		global BANISH_TIMERS
		if not reply:
			self.log.info(f"Bot is unbanishing {user}")
		else:
			self.log.info(f"{ctx.author} is unbanishing {user}")

		nitro_role = get(self.bot.guilds[0].roles, name='Nitro Booster')

		user_id = str(user.id)
		if reply:
			unbanished_by = str(ctx.author.id)
		else:
			unbanished_by = str(self.bot.user.id)
		unbanished_at = datetime.now()

		try:
			is_banished, is_updated, roles = await self.db.create_unbanish(user_id, unbanished_by, unbanished_at)
			if is_banished:
				if reply:
					await ctx.send("User isn't banished!")
				return
			if not is_updated:
				if reply:
					await ctx.send("Could not update banishment in database. Someone fix manually!")
		except Exception as e:
			self.log.exception("Error unbanishing")
			if reply:
				await ctx.send("Could not update banishment in database. Someone fix manually!")

		add_roles = []
		roles = roles.split(',')
		for role in roles:
			add_roles.append(get(self.bot.guilds[0].roles, id=int(role)))

		if nitro_role in user.roles:
			add_roles.append(nitro_role)

		await user.edit(roles=add_roles)


		if nitro_role in user.roles:
			vip_channel = get(self.bot.guilds[0].channels, name='vip-lounge')
			await vip_channel.set_permissions(user, overwrite=None)

		if reply:
			await ctx.send("User unbanished successfully!")

			timer_ = BANISH_TIMERS.pop(str(user.id))
			timer_.cancel()

	@commands.slash_command(guild_ids=[865256332646154300], name='banish', description='Banish users. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def banish(self, ctx, user, duration, *, reason='None'):
		global BANISH_TIMERS
		user = await commands.MemberConverter.convert(user)
		self.log.info(f"{ctx.author} is banishing {user.name}")

		try:
			length_str, secs_to_add = await parseduration.parse_pretty(duration)
		except Exception as e:
			self.log.exception('Error parsing duration')
			await ctx.send(f"Error banishing: {e}")
			return

		nitro_role = get(ctx.guild.roles, name='Nitro Booster')

		roles = ','.join([str(role.id) for role in user.roles if nitro_role != role])

		user_id = str(user.id)
		banished_by = str(ctx.author.id)
		banished_at = datetime.now()
		unbanish_at = banished_at + timedelta(seconds=secs_to_add)
		total_banish_secs = (unbanish_at-banished_at).total_seconds()

		broles = []
		for r in await self.cfg.get_roles('BanishedRole'):
			broles.append(get(ctx.guild.roles, id=int(r)))

		if nitro_role in user.roles:
			broles.append(nitro_role)

		await user.edit(roles=broles)

		if nitro_role in user.roles:
			vip_channel = get(ctx.guild.channels, name='vip-lounge')
			await vip_channel.set_permissions(user, read_messages=False,
															  send_messages=None)

		timer_ = timer.Timer(total_banish_secs, self.unbanish_cb, user, ctx)

		try:
			is_banished, added_to_db = await self.db.create_banish(user_id, roles, banished_at, unbanish_at, reason, banished_by)
			if is_banished:
				await ctx.send('User is already banished!')
				timer_.cancel()
				return
			if added_to_db:
				await ctx.send(f"{user} banished for {length_str}")
			else:
				await ctx.send("Could not insert into database. Banish cancelled.")
				timer_.cancel()
				return
		except Exception as e:
			self.log.exception('Error')
			await ctx.send("Could not insert into database. Banish cancelled.")
			timer_.cancel()
			return

		BANISH_TIMERS[str(user.id)] = timer_


	@banish.error
	async def banish_error(self, ctx, error):
		self.log.info(f"{ctx.author.name} tried to banish users")
		self.log.error('Error banishing')

		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}banish @user(s)`")

	@commands.slash_command(guild_ids=[865256332646154300], name='unbanish', description='unbanish users. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def unbanish(self, ctx, user):
		await self.unbanish_cb(user, ctx, True)

	@unbanish.error
	async def unbanish_error(self, ctx, error):
		self.log.info(f"{ctx.author.name} tried to unbanish users")
		self.log.error(traceback.format_exc())

		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}unbanish @user(s)`")

	@commands.slash_command(guild_ids=[865256332646154300], name='restart', description='Restarts the bot. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def restart(self, ctx):
		self.log.info(f"{ctx.author.name} is restarting the bot")

		await ctx.send("BRB...")
		os.system("service devsbot restart")

	@restart.error
	async def restart_error(self, ctx, error):
		self.log.info(f"{ctx.author.name} tried to restart the bot")

	@commands.slash_command(guild_ids=[865256332646154300], name='csay', description='Send a message to a specific channel as the bot. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def csay(self, ctx, channel, *, msg=None):
		channel = await commands.TextChannelConverter.convert(channel)
		self.log.info(f"{ctx.author.name} is sending a message to {channel.name}")

		if not ctx.message.attachments:
			await channel.send(msg)
		else:
			file = await ctx.message.attachments[0].to_file()
			await channel.send(content=msg, file=file)

	@csay.error
	async def csay_error(self, ctx, error):
		self.log.info(f"{ctx.author.name} tried to send a message to {channel.name}")

		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}csay #channel <message>`")

	@commands.slash_command(guild_ids=[865256332646154300], name='editmsg', description='Edit a message the bot posted. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def editmsg(self, ctx, message, *, msg=None):
		message = await commands.MessageConverter.convert(message)
		message_id = message.id
		self.log.info(f"{ctx.author.name} is editing message {message_id}")

		if message.author.id != bot.user.id:
			await ctx.send("I cannot edit other users messages!")
			return

		if msg:
			if not ctx.message.attachments:
				await message.edit(content=msg)
			else:
				await ctx.send("Unfortunately, attachments cannot be edited.")
		else:
			if ctx.message.attachments:
				await ctx.send("Unfortunately, attachments cannot be edited.")
			else:
				ret = f"""```
	{message.content}
	```"""
				await ctx.send(ret)

	@editmsg.error
	async def editmsg_error(self, ctx, error):
		self.log.info(f"{ctx.author.name} tried to edit message")

		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}editmsg <channel_id-message_id> <message>`")

	@commands.slash_command(guild_ids=[865256332646154300], name='reply', description='Reply to a message as the bot. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def reply(self, ctx, message, *, msg=None):
		message = await commands.MessageConverter.convert(message)
		message_id = message.id
		self.log.info(f"{ctx.author.name} is replying to a message")

		if not ctx.message.attachments:
			await message.reply(msg)
		else:
			file = await ctx.message.attachments[0].to_file()
			await message.reply(content=msg, file=file)

	@reply.error
	async def reply_error(self, ctx, error):
		self.log.info(f"{ctx.author.name} tried to reply to a message")

		if not isinstance(error, MissingPermissions):
			await ctx.send(f"Invalid argument. `{PREFIX}reply <channel_id-message_id> <message>`")

	@commands.slash_command(guild_ids=[865256332646154300], name='kill', description='Kills the bot. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def kill(self, ctx):
		self.log.info(f"{ctx.author.name} is killing the bot")

		await ctx.send("Goodbye cruel world!")
		os.system("service devsbot stop")

	@kill.error
	async def kill_error(self, ctx, error):
		self.log.info(f"{ctx.author.name} tried to kill the bot")

	@commands.slash_command(guild_ids=[865256332646154300], name='report', description='Create an incident report. ADMIN ONLY!')
	@commands.has_permissions(administrator=True)
	async def kill(self, ctx):
		self.log.info(f"{ctx.author.name} is creating an incident report.")

		def check(message: discord.Message):
			return message.channel == ctx.channel and message.author == ctx.author

		await ctx.send("Enter the user ID:")
		user_id = await self.bot.wait_for('message', check=check)

		await ctx.send("Enter the description of the infraction:")
		description = await self.bot.wait_for('message', check=check)

		await ctx.send("Enter the decision of the infraction:")
		decision = await self.bot.wait_for('message', check=check)

		reported_by = str(ctx.author.id)

		if await self.db.create_incident(user_id.content, description.content, decision.content, reported_by):
			await ctx.send("incident report created!")
		else:
			await ctx.send("incident report not created!")


def setup(bot):
	bot.add_cog(Admins(bot))
