import discord
from discord.ext import commands, pages
from util import create_embed, settings, parseduration, timer
from discord.utils import get
from discord.commands import SlashCommandGroup

import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

import asyncio
import os

from discord.ext.commands import Bot

from dotenv import load_dotenv

from database.database import Database

BANISH_TIMERS = {}
load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))

class Admins(commands.Cog):
	def __init__(self, bot: Bot):
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

		self.db: Database = None
	
	settings_cmd = SlashCommandGroup(name='settings', description='Settings for the bot', checks=[commands.has_permissions(administrator=True)], default_member_permissions=discord.Permissions(administrator=True))

	def set_db(self, db: Database):
		self.db = db
		
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
					await self._unbanish_cb(user)
				else:
					total_banish_secs = (unbanish_at-datetime.now()).total_seconds()
					timer_ = timer.Timer(total_banish_secs, self._unbanish_cb, user)
					BANISH_TIMERS[str(user.id)] = timer_

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

	@commands.slash_command(guild_ids=[guild_id], name='open', description='Opens game chat.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	async def open(self, ctx):
		self.log.info(f"{ctx.author} opened game channels")
		worker_tasks = []

		for channel_id in await self.cfg.get_channels('GameChannels'):
			for role in await self.cfg.get_roles('GameChannels'):
				wt = asyncio.ensure_future(self.open_channel(channel_id, int(role), ctx))
				worker_tasks.append(wt)

		await asyncio.gather(*worker_tasks)

		await ctx.respond("Game channel(s) opened!", delete_after=3)

	async def open_channel(self, channel_id, role, ctx):
		self.log.info(f'Opening {channel_id} for {role}')
		channel = self.bot.get_channel(int(channel_id))
		role = get(ctx.guild.roles, id=role)
		await channel.set_permissions(role, read_messages=True,
														  send_messages=None)
		await channel.send('Game chat is open!')

	@open.error
	async def open_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to open game channels")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='close', description='Closes game chat.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	async def close(self, ctx):
		self.log.info(f"{ctx.author} closed game channels")

		worker_tasks = []

		for channel_id in await self.cfg.get_channels('GameChannels'):
			for role in await self.cfg.get_roles('GameChannels'):
				wt = asyncio.ensure_future(self.close_channel(channel_id, int(role), ctx))
				worker_tasks.append(wt)

		await asyncio.gather(*worker_tasks)

		await ctx.respond("Game channel(s) closed!", delete_after=3)

	async def close_channel(self, channel_id, role, ctx):
		self.log.info(f'Closing {channel_id}')
		channel = self.bot.get_channel(int(channel_id))
		role = get(ctx.guild.roles, id=role)
		await channel.set_permissions(role, read_messages=True,
														  send_messages=False)
		await channel.send('Game chat is closed!')

	@close.error
	async def close_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to close game channels")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@settings_cmd.command(guild_ids=[guild_id], name='role', description='Set or remove roles for various categories.')
	@discord.commands.option('category', description='Select the category', choices=['gamechat', 'banished'])
	@discord.commands.option('action', description='Choose the action', choices=['add', 'remove'])
	@discord.commands.option('role', description='Enter the role to manage')
	async def role(self, ctx, category: str, action: str, role: discord.Role):
		role_map = {
			'gamechat': 'GameChannels',
			'banished': 'BanishedRole'
		}

		setting_key = role_map.get(category)
		if not setting_key:
			await ctx.respond("Invalid category.")
			return

		self.log.info(f"{ctx.author} is {action} role for {category}: {str(role)}")
		await self.update_role_setting(ctx, setting_key, action, role)

	@role.error
	async def role_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to set a role")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@settings_cmd.command(guild_ids=[guild_id], name='channel', description='Set or remove channels for various categories.')
	@discord.commands.option('category', description='Select the category', choices=['game', 'meetup', 'highlight', 'socialmedia', 'fourtwenty', 'modmail'])
	@discord.commands.option('action', description='Choose the action', choices=['add', 'remove'])
	@discord.commands.option('channel', description='Enter the channel to manage')
	async def channel(self, ctx, category: str, action: str, channel: discord.TextChannel):
		category_map = {
			'game': 'GameChannels',
			'meetup': 'MeetupChannels',
			'highlight': 'HighlightChannels',
			'socialmedia': 'SocialMediaChannels',
			'fourtwenty': 'FourTwentyChannels',
			'modmail': 'ModMailChannels'
		}

		setting_key = category_map.get(category)
		if not setting_key:
			await ctx.respond("Invalid category.")
			return

		self.log.info(f"{ctx.author} is {action} {category} channels: {str(channel)}")
		await self.update_channel_setting(ctx, setting_key, action, channel)

	@channel.error
	async def channel_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to set a channel")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@settings_cmd.command(guild_ids=[guild_id], name='reactalert', description='Set or remove message(s) for reactalerts.')
	@discord.commands.option('action', description='Choose the action', choices=['add', 'remove'])
	@discord.commands.option('message', description='Enter the message ID for receiving react alerts')
	async def reactalert(self, ctx, action: str, message: int):
		self.log.info(f"{ctx.author} is {action} reactalert messages: {str(message)}")
		await self.update_message_setting(ctx, 'ReactAlert', action, int(message))

	@reactalert.error
	async def reactalert_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to reactalert")

	async def setrole(self, ctx, role: discord.Role, user: discord.Member):
		if int(ctx.author.id) not in [364425223388528651, int(ctx.guild.owner.id)]:
			highest_role = ctx.author.roles[-1]
			all_roles = ctx.guild.roles

			if all_roles.index(highest_role) <= all_roles.index(role):
				await ctx.respond("You're not allowed to add a role that's equal to or above your highest role!")
				return

		self.log.info(f"{ctx.author} is giving {role.name} to {user.name}")

		if role not in user.roles:
			await user.add_roles(role)

			await ctx.respond(f"{user.name} has been given a role called: {role.name}")
		else:
			await ctx.respond(f"{user.name} already has a role called: {role.name}")

	async def unsetrole(self, ctx, role: discord.Role, user: discord.Member):
		if int(ctx.author.id) not in [364425223388528651, int(ctx.guild.owner.id)]:
			highest_role = ctx.author.roles[-1]
			all_roles = ctx.guild.roles

			if all_roles.index(highest_role) <= all_roles.index(role):
				await ctx.respond("You're not allowed to remove a role that's equal to or above your highest role!")
				return

		self.log.info(f"{ctx.author} is removing {role.name} from {user.name}")

		await user.remove_roles(role)

		await ctx.respond(f"{user.name} has been stripped of a role called: {role.name}")

	@commands.slash_command(guild_ids=[guild_id], name='role', description='Set role for users.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('role', description='Enter the role to give')
	@discord.commands.option('action', description='Choose the action', choices=['add', 'remove'])
	@discord.commands.option('user', description='Enter the user to give the role to')
	async def role(self, ctx, role: discord.Role, action: str, user: discord.Member):
		if action == 'add':
			await self.setrole(ctx, role, user)
		else:
			await self.unsetrole(ctx, role, user)

	@role.error
	async def role_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to giving a role")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='getconfig', description='Gets bot\'s settings.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	async def getconfig(self, ctx):
		self.log.info(f"{ctx.author} is getting config")
		names = ["Game Channels", "Game Channels Role", "Highlight Channels", "ModMail Channel", "Social Media Channels", "Four Twenty Channels", "Banished Roles"]

		gc = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('GameChannels')) if await self.cfg.get_channels('GameChannels') else 'None'
		gr = ', '.join(f"<@&{r}>" for r in await self.cfg.get_roles('GameChannels')) if await self.cfg.get_roles('GameChannels') else 'None'
		hc = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('HighlightChannels')) if await self.cfg.get_channels('HighlightChannels') else 'None'
		mmc = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('ModMailChannels')) if await self.cfg.get_channels('ModMailChannels') else 'None'
		smf = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('SocialMediaChannels')) if await self.cfg.get_channels('SocialMediaChannels') else 'None'
		ft = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('FourTwentyChannels')) if await self.cfg.get_channels('FourTwentyChannels') else 'None'
		br = ', '.join(f"<@&{r}>" for r in await self.cfg.get_roles('BanishedRole')) if await self.cfg.get_roles('BanishedRole') else 'None'

		values = [gc, gr, hc, mmc, smf, ft, br]

		embed = await create_embed.create('Config', "Bot's settings", names, values, f"/getconfig")

		await ctx.respond(embed=embed)

	@getconfig.error
	async def getconfig_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to get config")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	async def _unbanish_cb(self, user: discord.Member, ctx=None, reply=False):
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
					await ctx.respond("User isn't banished!")
				return
			if not is_updated:
				if reply:
					await ctx.respond("Could not update banishment in database. Someone fix manually!")
		except Exception as e:
			self.log.exception("Error unbanishing")
			if reply:
				await ctx.respond("Could not update banishment in database. Someone fix manually!")

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
			await ctx.respond("User unbanished successfully!")

			timer_ = BANISH_TIMERS.pop(str(user.id))
			timer_.cancel()

	@commands.slash_command(guild_ids=[guild_id], name='banish', description='Banish users.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('user', description='Enter the user to banish')
	@discord.commands.option('duration', description='Enter the duration')
	@discord.commands.option('reason', description='Enter the reason for the banish', required=False)
	async def banish(self, ctx, user: discord.Member, duration: str, reason: str = 'None'):
		global BANISH_TIMERS

		self.log.info(f"{ctx.author} is banishing {user.name}")

		try:
			length_str, secs_to_add = await parseduration.parse_pretty(duration)
		except Exception as e:
			self.log.exception('Error parsing duration')
			await ctx.respond(f"Error banishing: {e}")
			return

		nitro_role = get(ctx.guild.roles, name='Nitro Booster')

		roles = ','.join([str(role.id) for role in user.roles if nitro_role != role])

		user_id = str(user.id)
		banished_by = str(ctx.author.id)
		banished_at = datetime.now()
		unbanish_at = banished_at + timedelta(seconds=secs_to_add)
		total_banish_secs = (unbanish_at-banished_at).total_seconds()

		try:
			is_banished, added_to_db = await self.db.create_banish(user_id, roles, banished_at, unbanish_at, reason, banished_by)
			if is_banished:
				await ctx.respond('User is already banished!')
				return
			if added_to_db:
				broles = []
				for r in await self.cfg.get_roles('BanishedRole'):
					broles.append(get(ctx.guild.roles, id=int(r)))

				if nitro_role in user.roles:
					broles.append(nitro_role)

				await user.edit(roles=broles)

				"""if nitro_role in user.roles:
					vip_channel = get(ctx.guild.channels, name='vip-lounge')
					await vip_channel.set_permissions(user, read_messages=False,
																	send_messages=None)"""

				timer_ = timer.Timer(total_banish_secs, self._unbanish_cb, user, ctx)
				await ctx.respond(f"{user} banished for {length_str}")
			else:
				await ctx.respond("Could not insert into database. Banish cancelled.")
				return
		except Exception as e:
			self.log.exception('Error')
			await ctx.respond("Could not insert into database. Banish cancelled.")
			return

		BANISH_TIMERS[str(user.id)] = timer_


	@banish.error
	async def banish_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to banish users")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='unbanish', description='Unbanish users.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('user', description='Enter the user to unbanish')
	async def unbanish(self, ctx, user: discord.Member):
		await self._unbanish_cb(user, ctx, True)

	@unbanish.error
	async def unbanish_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to unbanish users")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='restart', description='Restarts the bot.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	async def restart(self, ctx):
		self.log.info(f"{ctx.author} is restarting the bot")

		await ctx.respond("BRB...")
		os.system("service devsbot restart")

	@restart.error
	async def restart_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to restart the bot")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='say', description='Send a message as the bot.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('message', description='Enter the message to send', required=False)
	@discord.commands.option('channel', description='Enter the channel to send the message to', type=discord.TextChannel, required=False)
	@discord.commands.option('attachment', description='Attach a file', required=False)
	async def say(self, ctx, channel: discord.TextChannel = None, message: str = None, attachment: discord.Attachment = None):
		if not channel:
			channel = ctx.channel

		self.log.info(f"{ctx.author} is sending a message to {channel.name}")
		file = None

		def check(message: discord.Message):
			return message.channel == ctx.channel and message.author == ctx.author

		if attachment:
			file = await attachment.to_file()

		if not message:
			await ctx.respond("Enter the message you want to say (you have 5 minutes):")
			try:
				message = await self.bot.wait_for('message', check=check, timeout=300)
			except:
				await ctx.send("I don't have all day! Retry if you want.")
				return
			await channel.send(message.content, file=file)
			await ctx.send("Sent!", delete_after=3, ephemeral=True)
		else:
			await channel.send(message, file=file)
			await ctx.respond("Sent!", delete_after=3, ephemeral=True)

	@say.error
	async def say_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to send a message")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='editmsg', description='Edit a message the bot posted.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('message_id', description='Enter the message ID to edit')
	async def editmsg(self, ctx, message_id: str):
		messageObj = await commands.MessageConverter().convert(ctx, message_id)
		self.log.info(f"{ctx.author} is editing message {messageObj.id}")

		if messageObj.author.id != self.bot.user.id:
			await ctx.respond("I cannot edit other users messages!")
			return

		def check(message: discord.Message):
			return message.channel == ctx.channel and message.author == ctx.author

		ret = f"""```
{messageObj.content}
```"""
		await ctx.respond(ret)
		await ctx.send("Enter the message you want to say (you have 5 minutes):")
		try:
			message = await self.bot.wait_for('message', check=check, timeout=300)
		except:
			await ctx.send("I don't have all day! Retry if you want.")
			return

		await messageObj.edit(content=message.content)
		await ctx.send("Message edited!")


	@editmsg.error
	async def editmsg_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to edit message")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='reply', description='Reply to a message as the bot.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('message_id', description='Enter the message ID to reply to')
	@discord.commands.option('message', description='Enter the message to send', required=False)
	@discord.commands.option('attachment', description='Attach a file', required=False)
	async def reply(self, ctx, message_id: str, message: str = None, attachment: discord.Attachment = None):
		messageObj = await commands.MessageConverter().convert(ctx, message_id)
		self.log.info(f"{ctx.author} is replying to a message")
		file = None

		def check(message: discord.Message):
			return message.channel == ctx.channel and message.author == ctx.author

		if attachment:
			file = await attachment.to_file()

		if not message:
			await ctx.respond("Enter the message you want to say (you have 5 minutes):")
			try:
				message = await self.bot.wait_for('message', check=check, timeout=300)
			except:
				await ctx.send("I don't have all day! Retry if you want.")
				return
			await messageObj.reply(message.content, file=file)
			await ctx.send("Replied!", delete_after=3, ephemeral=True)
		else:
			await messageObj.reply(message, file=file)
			await ctx.respond("Replied!", delete_after=3, ephemeral=True)

	@reply.error
	async def reply_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to reply to a message")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='kill', description='Kills the bot.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	async def kill(self, ctx):
		self.log.info(f"{ctx.author} is killing the bot")

		await ctx.respond("Goodbye cruel world!")
		os.system("service devsbot stop")

	@kill.error
	async def kill_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to kill the bot")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='incident', description='Create an incident report.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('user', description='Enter the user to create an incident report for')
	@discord.commands.option('description', description='Enter the description of the incident')
	@discord.commands.option('decision', description='Enter the decision of the incident')
	async def incident(self, ctx, user: discord.Member, description: str, decision: str):
		self.log.info(f"{ctx.author} is creating an incident report.")

		reported_by = str(ctx.author.id)
		reported_at = datetime.now()

		if await self.db.create_incident(str(user.id), description, decision, reported_by, reported_at):
			await ctx.respond("Incident report created!")
		else:
			await ctx.respond("Incident report not created!")

	@incident.error
	async def incident_error(self, ctx, error):
		self.log.exception("Create report error")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name="getincident", description="Gets incident reports for the specified user")
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('user', description='Enter the user to get incident reports for', required=False)
	@discord.commands.option('user_id', description='Enter the user to get incident reports for', required=False)
	async def getincident(self, ctx, user: discord.Member = None, user_id: str = None):
		if not user and not user_id:
			ctx.respond("I can't read your mind! Enter a user.")
			
		self.log.info(f"{ctx.author} is getting incident reports for user {user if user else user_id}")
		await ctx.defer()

		if user:
			incidents = await self.db.get_incident(str(user.id))
		else:
			incidents = await self.db.get_incident(user_id)

		incident_embeds = []
		if len(incidents) > 0:
			for i in incidents:
				incident_embeds.append(await create_embed.incident(i[0], i[1], i[2], i[3], i[4], i[5]))
		else:
			incident_embeds = ["No incidents found for this user."]

		paginator = pages.Paginator(
			pages=incident_embeds,
			use_default_buttons=False,
			loop_pages=False,
			show_disabled=False,
		)
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
		await paginator.respond(ctx.interaction, ephemeral=False)

	@getincident.error
	async def getincident_error(self, ctx, error):
		self.log.exception("Get incident error")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)

	@commands.slash_command(guild_ids=[guild_id], name='timeout', description='Timeout users.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	@discord.commands.option('user', description='Enter the user to timeout')
	@discord.commands.option('duration', description='Enter the duration')
	@discord.commands.option('reason', description='Enter the reason for the timeout', required=False)
	async def timeout(self, ctx, user: discord.Member, duration: str, reason: str = 'None'):
		self.log.info(f"{ctx.author} is timeouting {user.name}")

		try:
			length_str, secs_to_add = await parseduration.parse_pretty(duration)
		except Exception as e:
			self.log.exception('Error parsing duration')
			await ctx.respond(f"Error timeouting: {e}")
			return
		
		timeouted_by = str(ctx.author.id)
		timeouted_at = datetime.now()
		untimeout_at = timedelta(seconds=secs_to_add)

		await user.timeout_for(untimeout_at)

		await ctx.respond(f"{user} has been timed out for {length_str}")

		await self.db.create_incident(str(user.id), reason, f"Timed out for {length_str}", timeouted_by, timeouted_at)

	@timeout.error
	async def timeout_error(self, ctx, error):
		self.log.exception("Timeout error")

		await ctx.respond("Oops, something went wrong!", ephemeral=True)


def setup(bot):
	bot.add_cog(Admins(bot))
