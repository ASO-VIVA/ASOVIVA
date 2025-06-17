import discord
from discord.ext import commands
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from discord import app_commands

# お題取得（複数）
def get_random_themes(count: int):
    SPREADSHEET_KEY = "1ZTxuNnVqm6eVIuF2qf-Vm4OtbSBUezlwTEhPpurA6tA"
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("ワードスナイパー")
    themes = sheet.col_values(1)
    themes = [t for t in themes if t.strip()]  # 空白除外
    return random.sample(themes, k=min(count, len(themes)))

# 非同期ラッパー
async def get_themes_async(count: int):
    return await asyncio.to_thread(get_random_themes, count)

# コマンド登録
async def setup(bot):
    @bot.tree.command(name="ワードスナイパーインクル", description="お題をいくつか表示します")
    @app_commands.describe(
        count="取得するお題の数（2～4）"
    )
    @app_commands.choices(
        count=[
            app_commands.Choice(name="2つ", value=2),
            app_commands.Choice(name="3つ", value=3),
            app_commands.Choice(name="4つ", value=4)
        ]
    )
    async def odai_command(interaction: discord.Interaction, count: app_commands.Choice[int]):
        await interaction.response.defer()

        themes = await get_themes_async(count.value)
        themes_text = "\n".join([f"🍮 お題 {i+1}: **{theme}**" for i, theme in enumerate(themes)])

        await interaction.followup.send(themes_text)
