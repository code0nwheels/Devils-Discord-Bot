"""
Main Admins cog that combines all admin submodules.
"""
import discord
from discord.ext import commands
from discord.ext.commands import Bot
from util.settings import Settings
from util.logger import setup_logger
from database.database import Database

from .game_channels import GameChannelsMixin
from .settings import SettingsMixin
from .roles import RolesMixin
from .banish import BanishMixin
from .messages import MessagesMixin
from .system import SystemMixin
from .incidents import IncidentsMixin


class Admins(
	GameChannelsMixin,
	SettingsMixin,
	RolesMixin,
	BanishMixin,
	MessagesMixin,
	SystemMixin,
	IncidentsMixin,
	commands.Cog
):
	"""Main admin cog combining all admin functionality."""
	
	def __init__(self, bot: Bot):
		# Initialize mixins
		BanishMixin.__init__(self)
		
		self.bot = bot
		self.cfg = Settings()
		self.log = setup_logger(__name__, 'log/admin.log')
		self.db: Database = Database()
	
	def set_db(self, db: Database):
		"""Set the database instance."""
		self.db = db
	
	def cog_unload(self):
		"""Cleanup when cog is unloaded."""
		if hasattr(self, 'loop') and self.loop is not None:
			self.loop.close()


def setup(bot: Bot):
	bot.add_cog(Admins(bot))

