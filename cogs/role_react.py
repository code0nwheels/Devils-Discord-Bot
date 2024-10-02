import discord
from discord.ext import commands
from discord.utils import get

from util import settings

import logging
from logging.handlers import RotatingFileHandler

class RoleReact(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.cfg = settings.Settings()

		logging.basicConfig(level=logging.INFO)
		self.log = logging.getLogger(__name__)
		handler = RotatingFileHandler('log/role_react.log', maxBytes=5*1024*1024, backupCount=5)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		handler.setFormatter(formatter)
		self.log.addHandler(handler)

		self.log.info("RoleReact cog initialized.")

	def cog_unload(self):
		self.log.info("RoleReact cog unloaded.")

	@commands.Cog.listener()
	async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
		self.log.info(f"Reaction added: {payload.emoji} by {payload.member}")
		messages_existing = await self.cfg.get_messages('ReactAlert')
		if not messages_existing or f"{payload.channel_id}-{payload.message_id}" not in messages_existing:
			return

		good_roles = [518831246034599948, 842546366840569876, 437381518424408064, 384844284089729034, 364885679425060864]
		has_role = any(role.id in good_roles for role in payload.member.roles)
		if not has_role:
			return
		
		if payload.emoji.name == '🎅':
			# add role 781959166055022593 to user
			role = get(payload.member.guild.roles, id=781959166055022593)
			await payload.member.add_roles(role)
			return

		guild = self.bot.get_guild(payload.guild_id)

		channel = get(guild.text_channels, name="admin-chat")
		await channel.send(f'{payload.member.mention} reacted with {payload.emoji}')

	@commands.Cog.listener()
	async def on_raw_reaction_remove(self, payload):
		pass

def setup(bot):
	bot.add_cog(RoleReact(bot))