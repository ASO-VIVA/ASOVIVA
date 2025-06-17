import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')  # .env からトークンを取得

extensions = (
    'irokata',              # イロトカタチ
    'moziokuri',            # 1文字ずつ送信
    'pokemon',              # ランダムにポケモン1匹
    'pokemon2',             # 送信者のみにランダムにポケモン1匹
    'issyo',                # これで一緒
    'eventodai',            # イベント用のお題表示
    'wordsniper',           # ワードスナイパーインクル
    'hayaosi',              # 早押しボタン
    'sakiyomiseikai',       # 先読み朝までそれ正解
    'answerflip',           # 集計した回答を各自で発表
    'worldend',             # WORLDEND
    'orikyarazukan',        # オリキャラ妄想図鑑
)

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=discord.Intents.all(),
        )

    async def setup_hook(self):
        for extension in extensions:
            await self.load_extension(extension)  # 拡張モジュールをロード
        await self.tree.sync()  # コマンドツリーを同期

if __name__ == '__main__':
    bot = MyBot()
    bot.run(TOKEN)  # Botを起動
