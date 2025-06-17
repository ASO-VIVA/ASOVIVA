import discord
from discord.ext import commands
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio

# 同期関数（お題取得）
def get_random_theme():
    SPREADSHEET_KEY = "1ZTxuNnVqm6eVIuF2qf-Vm4OtbSBUezlwTEhPpurA6tA"
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("イロカタ")
    themes = sheet.col_values(1)
    themes = [t for t in themes if t.strip()]
    return random.choice(themes)

# 非同期ラッパー
async def get_theme_async():
    return await asyncio.to_thread(get_random_theme)

# 正解ボタンのView（送信者のみ押せる）
class RevealAnswerView(discord.ui.View):
    def __init__(self, theme, author: discord.User):
        super().__init__(timeout=None)
        self.theme = theme
        self.author = author

    @discord.ui.button(label="正解発表", style=discord.ButtonStyle.success)
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ このボタンはコマンド送信者のみ使えます。", ephemeral=True)
            return

        await interaction.response.send_message(f"🎯 正解は… **{self.theme}** でした！")
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

# コマンド定義
async def setup(bot):
    @bot.tree.command(name="イロトカタチ", description="[イロトカタチ]を遊ぶ用のお題が送信者のみに表示されます")
    async def irakata_vegas(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # お題は送信者にのみ

        theme = await get_theme_async()
        view = RevealAnswerView(theme, interaction.user)

        # お題はエフェメラルで送信
        await interaction.followup.send(
            f"🍮 お題は: **{theme}**", 
            ephemeral=True
        )

        # 正解発表ボタンは全体表示
        await interaction.channel.send(
            f"👇正解は送信者が発表できます！",
            view=view
        )
