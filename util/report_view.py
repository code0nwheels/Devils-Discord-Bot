from discord.ui import Button, View
from discord import ButtonStyle, Interaction, Message

class ReportView(View):
    def __init__(self, message: Message):
        super().__init__()
        self.message = message
        message_id = f"{message.channel.id}-{message.id}"

        self.delete_button = Button(label="Delete", custom_id=f"{message_id}", style=ButtonStyle.red)
        self.add_item(self.delete_button)
        self.delete_button.callback = self.button_callback


        self.timeout = None
    
    async def button_callback(self, interaction: Interaction):
        channel_id = interaction.custom_id.split("-")[0]
        message_id = interaction.custom_id.split("-")[1]
        channel = interaction.guild.get_channel(int(channel_id))
        message = await channel.fetch_message(int(message_id))

        try:
            await message.delete()
            await interaction.respond(f"Message deleted by {interaction.user.mention}")

            self.delete_button.disabled = True
            await interaction.message.edit(view=self)
        except Exception as e:
            await interaction.respond(f"Error deleting message: {e}")