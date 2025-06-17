import discord
from discord.ext import commands
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio

# 同期関数：ランダムで2つ取得（重複なし）
def get_random_themes():
    SPREADSHEET_KEY = "1ZTxuNnVqm6eVIuF2qf-Vm4OtbSBUezlwTEhPpurA6tA"
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("これで一緒")
    themes = sheet.col_values(1)
    themes = [t for t in themes if t.strip()]  # 空白除去

    if len(themes) < 2:
        raise ValueError("お題が2つ以上必要です")

    return random.sample(themes, 2)  # 2つの被らないテーマ

# 非同期で実行するためのラッパー関数
async def get_themes_async():
    return await asyncio.to_thread(get_random_themes)

# setup関数を定義し、Botにコマンドを追加
async def setup(bot):
    @bot.tree.command(name="これで一緒", description="[これで一緒♪]を遊ぶ用のお題が表示されます")
    async def irakata_vegas(interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            theme1, theme2 = await get_themes_async()
            await interaction.followup.send(
                f"どちらかの前か後に文章を追加して2つの好感度を同じにしてね♪\n🍮 お題は...\n \n**{theme1}** と **{theme2}**",
            )
        except ValueError as e:
            await interaction.followup.send(str(e))
