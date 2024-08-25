import discord, re
from discord.ext import commands
from util import create_embed
from discord.utils import get
import aiofiles

from util import settings

class Reflex(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.cfg = settings.Settings()

	@commands.Cog.listener()
	async def on_thread_join(self, thread):
		await thread.join()

	@commands.Cog.listener()
	async def on_message(self, message):
		if not message.guild and message.author.id != self.bot.user.id:
			if message.author.id != self.bot.owner_id:
				names = ["Content"]
				values = [message.content]

				embed = await create_embed.create('DM', f"Message author: {message.author}", names, values, f"{message.author.id}", thumbnail=message.author.avatar.url)

				owner = await self.bot.fetch_user(self.bot.owner_id)
				await owner.send(embed=embed)
			elif message.reference:
				ref = message.reference
				reply_to_msg = ref.resolved

				embed = reply_to_msg.embeds[0].to_dict()
				reply_to = await self.bot.fetch_user(int(embed.get("footer")['text']))

				await reply_to.send(message.content)
			elif message.content.startswith('!'):
				space = message.content.index(' ')
				user_id = message.content[1:space]
				message_to_send = message.content[space + 1:]

				user = await self.bot.fetch_user(int(user_id))
				await user.send(message_to_send)

	@commands.Cog.listener()
	async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
		messages_existing = await self.cfg.get_messages('ReactAlert')
		if not messages_existing or payload.message_id not in messages_existing:
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
	async def on_member_join(self, member):
		# read the file
		async with aiofiles.open("/root/discord/hn/spypetids.txt", mode="r") as f:
			ids = await f.read()
			ids = ids.split("\n")
			ids = [int(i) for i in ids]
		
		if member.id in ids:
			await member.ban(reason="SpyPet account")

			async with aiofiles.open("/root/discord/hn/bannedspypetids.txt", mode="a") as f:
				await f.write(f"{member.id}\n")

def setup(bot):
	bot.add_cog(Reflex(bot))
