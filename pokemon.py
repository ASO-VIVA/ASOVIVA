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
    
    # A列からE列までのデータを取得
    rows = sheet.get_all_values()  # シート内の全ての行を取得
    
    # A列からE列の内容を持っている行をランダムに1行選ぶ
    random_row = random.choice(rows)
    
    # A列からE列までの内容を返す
    return random_row

# 非同期で実行するためのラッパー関数
async def get_theme_async():
    return await asyncio.to_thread(get_random_theme)

# setup関数を定義し、Botにコマンドを追加
async def setup(bot):
    @bot.tree.command(name="ポケモン", description="ポケモン図鑑からランダムで1匹表示します")
    async def irakata_vegas(interaction: discord.Interaction):
        await interaction.response.defer()  # 応答猶予を延長
        theme = await get_theme_async()
        
        # A列からE列の内容を表示
        await interaction.followup.send(f"No.{theme[0]} \n **{theme[1]}** \nタイプ：{theme[2]} - {theme[3]}\n{theme[4]}")
