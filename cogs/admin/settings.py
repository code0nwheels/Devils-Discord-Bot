"""
Settings management commands.
"""
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
from util import create_embed
from util.logger import setup_logger

import os
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))


class SettingsMixin:
	"""Mixin for settings commands."""
	
	settings_cmd = SlashCommandGroup(
		name='settings',
		description='Settings for the bot',
		checks=[commands.has_permissions(administrator=True)],
		default_member_permissions=discord.Permissions(administrator=True)
	)
	
	@settings_cmd.command(guild_ids=[guild_id], name='role', description='Set or remove roles for various categories.')
	@discord.commands.option('category', description='Select the category', choices=['gamechat', 'banished'])
	@discord.commands.option('action', description='Choose the action', choices=['add', 'remove'])
	@discord.commands.option('role', description='Enter the role to manage')
	async def settings_role(self, ctx, category: str, action: str, role: discord.Role):
		role_map = {
			'gamechat': 'GameChannels',
			'banished': 'BanishedRole'
		}
		
		setting_key = role_map.get(category)
		if not setting_key:
			await ctx.respond("Invalid category.")
			return
		
		self.log.info(f"{ctx.author} is {action} role for {category}: {str(role)}")
		await self.cfg.update_role_setting(ctx, setting_key, action, role)
	
	@settings_role.error
	async def settings_role_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to set a role")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)
	
	@settings_cmd.command(guild_ids=[guild_id], name='channel', description='Set or remove channels for various categories.')
	@discord.commands.option('category', description='Select the category', choices=['game', 'meetup', 'highlight', 'socialmedia', 'fourtwenty', 'modmail'])
	@discord.commands.option('action', description='Choose the action', choices=['add', 'remove'])
	@discord.commands.option('channel', description='Enter the channel to manage')
	async def settings_channel(self, ctx, category: str, action: str, channel: discord.TextChannel):
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
		await self.cfg.update_channel_setting(ctx, setting_key, action, channel)
	
	@settings_channel.error
	async def settings_channel_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to set a channel")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)
	
	@settings_cmd.command(guild_ids=[guild_id], name='reactalert', description='Set or remove message(s) for reactalerts.')
	@discord.commands.option('action', description='Choose the action', choices=['add', 'remove'])
	@discord.commands.option('message', description='Enter the message ID for receiving react alerts')
	async def reactalert(self, ctx, action: str, message: str):
		self.log.info(f"{ctx.author} is {action} reactalert messages: {str(message)}")
		await self.cfg.update_message_setting(ctx, 'ReactAlert', action, message)
	
	@reactalert.error
	async def reactalert_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to reactalert")
	
	@commands.slash_command(guild_ids=[guild_id], name='getconfig', description='Gets bot\'s settings.')
	@commands.has_permissions(administrator=True)
	@discord.default_permissions(administrator=True)
	async def getconfig(self, ctx):
		self.log.info(f"{ctx.author} is getting config")
		names = ["Game Channels", "Game Channels Role", "Highlight Channels", "ModMail Channel", "Social Media Channels", "Four Twenty Channels", "Banished Roles", "Meetup Channels"]
		
		gc = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('GameChannels')) if await self.cfg.get_channels('GameChannels') else 'None'
		gr = ', '.join(f"<@&{r}>" for r in await self.cfg.get_roles('GameChannels')) if await self.cfg.get_roles('GameChannels') else 'None'
		hc = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('HighlightChannels')) if await self.cfg.get_channels('HighlightChannels') else 'None'
		mmc = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('ModMailChannels')) if await self.cfg.get_channels('ModMailChannels') else 'None'
		smf = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('SocialMediaChannels')) if await self.cfg.get_channels('SocialMediaChannels') else 'None'
		ft = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('FourTwentyChannels')) if await self.cfg.get_channels('FourTwentyChannels') else 'None'
		br = ', '.join(f"<@&{r}>" for r in await self.cfg.get_roles('BanishedRole')) if await self.cfg.get_roles('BanishedRole') else 'None'
		mt = ', '.join(f"<#{ch}>" for ch in await self.cfg.get_channels('MeetupChannels')) if await self.cfg.get_channels('MeetupChannels') else 'None'
		
		values = [gc, gr, hc, mmc, smf, ft, br, mt]
		
		embed = await create_embed.create('Config', "Bot's settings", names, values, f"/getconfig")
		
		await ctx.respond(embed=embed)
	
	@getconfig.error
	async def getconfig_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to get config")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

