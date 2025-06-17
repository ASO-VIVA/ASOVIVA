import discord
from discord import app_commands
from discord.ext import commands
import random

HIRAGANA = list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ")


class SakiyomiSeikai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="先読みそれ正解", description="先読み朝までそれ正解で遊ぶ")
    async def sakiyomi_command(self, interaction: discord.Interaction):
        view = TopicInputView(interaction.user)
        await interaction.response.send_message(
            embed=discord.Embed(
                description="◯から始まる、△△といえば？\nボタンを押して△△の部分を入力してください。",
                color=discord.Color.green()
            ),
            view=view,
            ephemeral=False
        )

# --- ボタンビュー（お題入力） ---
class TopicInputView(discord.ui.View):
    def __init__(self, owner: discord.User):
        super().__init__(timeout=None)
        self.owner = owner
        self.message = None  # 後でメッセージ参照用に設定
        self.input_button_ref = self.input_button  # ボタン参照を保持

    @discord.ui.button(label="お題入力", style=discord.ButtonStyle.primary, custom_id="topic_input_button")
    async def input_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("このボタンはコマンド実行者のみ使用できます。", ephemeral=True)
            return

        # モーダル表示（ビューを渡す）
        await interaction.response.send_modal(TopicInputModal(self.owner, self))


# --- モーダル（お題入力） ---
class TopicInputModal(discord.ui.Modal, title="お題を入力してください"):
    topic = discord.ui.TextInput(label="△△の部分を入力", style=discord.TextStyle.short, required=True)

    def __init__(self, owner: discord.User, view: TopicInputView):
        super().__init__()
        self.owner = owner
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        random_char = random.choice(HIRAGANA)
        topic_text = self.topic.value

        # ボタンを無効化し、元メッセージを更新
        for child in self.view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.message.edit(view=self.view)

        await interaction.response.defer()

        # 回答用メッセージ送信
        await interaction.followup.send(
            embed=discord.Embed(
                title="お題",
                description=f"『{random_char}』から始まる、△△といえば？",
                color=discord.Color.blue()
            ),
            view=RevealView(self.owner, random_char, topic_text),
            ephemeral=False
        )



# --- ボタンビュー（全文表示） ---
class RevealView(discord.ui.View):
    def __init__(self, owner: discord.User, char: str, topic: str):
        super().__init__(timeout=None)
        self.owner = owner
        self.char = char
        self.topic = topic

    @discord.ui.button(label="全文表示", style=discord.ButtonStyle.secondary, custom_id="reveal_button")
    async def reveal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner.id:
            await interaction.response.send_message("このボタンはコマンド実行者のみ使用できます。", ephemeral=True)
            return

        button.disabled = True
        await interaction.message.edit(view=self)

        await interaction.response.send_message(
            embed=discord.Embed(
                title="完全なお題",
                description=f"『{self.char}』から始まる、__{self.topic}__といえば？",
                color=discord.Color.orange()
            ),
            ephemeral=False
        )

async def setup(bot):
    await bot.add_cog(SakiyomiSeikai(bot))
