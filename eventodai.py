import discord
from discord.ext import commands
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio

# 同期関数
def get_random_theme():
    SPREADSHEET_KEY = "1VXa6w2KQ7GTZs6QWSpzSSoZxu1zKkVleOBAy2UR-fZU"
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("お題イベ用")
    themes = sheet.col_values(1)
    return random.choice(themes)

# 非同期で実行するためのラッパー関数
async def get_theme_async():
    return await asyncio.to_thread(get_random_theme)

# setup関数を定義し、Botにコマンドを追加
async def setup(bot):
    @bot.tree.command(name="お題イベ用", description="イベント用のお題が表示されます")
    async def irakata_vegas(interaction: discord.Interaction):
        await interaction.response.defer()  # 応答猶予を延長
        theme = await get_theme_async()
        await interaction.followup.send(f"🍮 お題は: **{theme}**")
