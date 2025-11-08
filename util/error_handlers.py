"""
Standardized error handling utilities for Discord bot commands.
"""
from functools import wraps
import logging


def handle_command_error(logger: logging.Logger, command_name: str = None):
	"""
	Decorator factory for consistent error handling across commands.
	
	Args:
		logger: Logger instance to use for error logging
		command_name: Optional command name for logging context
	
	Usage:
		@handle_command_error(self.log, "command_name")
		async def command_error(self, ctx, error):
			...
	"""
	def decorator(func):
		@wraps(func)
		async def wrapper(self, ctx, error):
			cmd_name = command_name or func.__name__.replace('_error', '')
			logger.exception(f"{ctx.author} tried to use {cmd_name}")
			await ctx.respond("Oops, something went wrong!", ephemeral=True)
		return wrapper
	return decorator

