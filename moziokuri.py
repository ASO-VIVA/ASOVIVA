import discord
from discord.ext import commands

user_states = {}

class SplitView(discord.ui.View):
    def __init__(self, user_id, target_channel):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.target_channel = target_channel

    @discord.ui.button(label="▶ 次へ", style=discord.ButtonStyle.primary)
    async def next_letter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("これはあなたのボタンではありません。", ephemeral=True)
            return

        state = user_states.get(self.user_id)
        if not state:
            await interaction.response.send_message("メッセージが見つかりません。", ephemeral=True)
            return

        if state["index"] >= len(state["text"]):
            await interaction.message.channel.send("✅ **送信終了しました。**")
            await interaction.response.defer()
            return

        letter = state["text"][state["index"]]
        state["index"] += 1

        await self.target_channel.send(letter)
        await interaction.response.defer()

class SplitButton(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="送信先設定")
    async def set_target_channel(self, ctx, *, channel_mention: str):
        """送信先のチャンネルをメッセージで設定（例: !送信先設定 #general）"""
        if len(ctx.message.channel_mentions) == 0:
            await ctx.send("チャンネルをメンションで指定してください。例：`!送信先設定 #general`")
            return

        channel = ctx.message.channel_mentions[0]
        user_states[ctx.author.id] = {"target_channel": channel}
        await ctx.send(f"{channel.mention} を送信先チャンネルとして設定しました。")

    @commands.command(name="分割開始")
    async def start_split(self, ctx, *, message: str):
        """メッセージを1文字ずつ送るボタンを表示"""
        state = user_states.get(ctx.author.id)
        if not state or "target_channel" not in state:
            await ctx.send("送信先チャンネルが設定されていません。先に `!送信先設定 #チャンネル名` で設定してください。")
            return

        target_channel = state["target_channel"]
        user_states[ctx.author.id]["text"] = list(message)
        user_states[ctx.author.id]["index"] = 0

        view = SplitView(user_id=ctx.author.id, target_channel=target_channel)
        await ctx.send(f"🔤 {target_channel.mention} に1文字ずつ送信します：", view=view)

async def setup(bot):
    await bot.add_cog(SplitButton(bot))
