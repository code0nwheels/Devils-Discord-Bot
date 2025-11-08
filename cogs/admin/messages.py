"""
Message management commands (say, editmsg, reply).
"""
import discord
from discord.ext import commands
from util.logger import setup_logger

import os
from dotenv import load_dotenv

load_dotenv()
guild_id = int(os.getenv('GUILD_ID'))


class MessagesMixin:
	"""Mixin for message commands."""
	
	async def _wait_for_message(self, ctx, timeout=300):
		"""Helper method to wait for a message from the user."""
		def check(message: discord.Message):
			return message.channel == ctx.channel and message.author == ctx.author
		
		try:
			message = await self.bot.wait_for('message', check=check, timeout=timeout)
			return message
		except:
			await ctx.send("I don't have all day! Retry if you want.")
			return None
	
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
		
		if attachment:
			file = await attachment.to_file()
		
		if not message:
			await ctx.respond("Enter the message you want to say (you have 5 minutes):")
			message_obj = await self._wait_for_message(ctx)
			if message_obj is None:
				return
			await channel.send(message_obj.content, file=file)
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
		
		ret = f"""```
{messageObj.content}
```"""
		await ctx.respond(ret)
		await ctx.send("Enter the message you want to say (you have 5 minutes):")
		message_obj = await self._wait_for_message(ctx)
		if message_obj is None:
			return
		
		await messageObj.edit(content=message_obj.content)
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
		
		if attachment:
			file = await attachment.to_file()
		
		if not message:
			await ctx.respond("Enter the message you want to say (you have 5 minutes):")
			message_obj = await self._wait_for_message(ctx)
			if message_obj is None:
				return
			await messageObj.reply(message_obj.content, file=file)
			await ctx.send("Replied!", delete_after=3, ephemeral=True)
		else:
			await messageObj.reply(message, file=file)
			await ctx.respond("Replied!", delete_after=3, ephemeral=True)
	
	@reply.error
	async def reply_error(self, ctx, error):
		self.log.exception(f"{ctx.author} tried to reply to a message")
		await ctx.respond("Oops, something went wrong!", ephemeral=True)

