import discord
from discord.ext import commands
from util import create_embed

class Reflex(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

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

def setup(bot):
	bot.add_cog(Reflex(bot))
