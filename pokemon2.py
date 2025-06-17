import discord
from discord.ext import commands
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio

# 同期関数
def get_random_theme():
    SPREADSHEET_KEY = "1ZTxuNnVqm6eVIuF2qf-Vm4OtbSBUezlwTEhPpurA6tA"
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("ポケモン図鑑")
    rows = sheet.get_all_values()
    random_row = random.choice(rows)
    return random_row

# 非同期ラッパー
async def get_theme_async():
    return await asyncio.to_thread(get_random_theme)

# 正解ボタンのView
class RevealAnswerView(discord.ui.View):
    def __init__(self, theme_row, author: discord.User):
        super().__init__(timeout=None)
        self.theme_row = theme_row  # A〜E列のデータ
        self.author = author

    @discord.ui.button(label="正解発表", style=discord.ButtonStyle.success)
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ このボタンはコマンド送信者のみ使えます。", ephemeral=True)
            return

        message = (
            f"🎯 正解は… **{self.theme_row[1]}** でした！\n"
            f"No.{self.theme_row[0]} \n"
            f"タイプ：{self.theme_row[2]} - {self.theme_row[3]}\n"
        )
        if len(self.theme_row) >= 5 and self.theme_row[4].startswith("http"):
            message += self.theme_row[4]

        await interaction.response.send_message(message)

        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

# コマンド定義
async def setup(bot):
    @bot.tree.command(name="ポケモン隠し", description="ポケモン図鑑からランダムで1匹表示します")
    async def irakata_vegas(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        theme = await get_theme_async()

        # エフェメラルでお題を送信
        message = f"No.{theme[0]} \n **{theme[1]}** \nタイプ：{theme[2]} - {theme[3]}\n"
        if len(theme) >= 5 and theme[4].startswith("http"):
            message += theme[4]

        await interaction.followup.send(message, ephemeral=True)


        # 正解発表ボタン（通常メッセージ）
        view = RevealAnswerView(theme, interaction.user)
        await interaction.channel.send("👇正解は送信者が発表できます！", view=view)
