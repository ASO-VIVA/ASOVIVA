import discord
from discord.ext import commands
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets認証とデータ取得
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
gc = gspread.authorize(credentials)

SPREADSHEET_NAME = "1ZTxuNnVqm6eVIuF2qf-Vm4OtbSBUezlwTEhPpurA6tA"
IMAGE_SHEET_NAME = "人物画像"
WORD_SHEET_NAME = "ゲスラブ"

sessions: dict[int, dict] = {}  # チャンネルごとのセッション管理

# Google DriveのURLを表示用に変換
def convert_google_drive_url(url):
    if "/file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=view&id={file_id}"
    return url

# Google DriveのURLを表示用に変換
def convert_drive_url(url: str) -> str:
    if "drive.google.com/file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=view&id={file_id}"
    return url

# スプレッドシートから画像URLを取得
def get_random_image_url():
    sh = gc.open_by_key(SPREADSHEET_NAME)
    worksheet = sh.worksheet(IMAGE_SHEET_NAME)
    urls = [convert_drive_url(url) for url in worksheet.col_values(1) if url.strip()]
    return random.choice(urls) if urls else None

# スプレッドシートから属性を取得
def get_random_words(exclude=[], count=3):
    sh = gc.open_by_key(SPREADSHEET_NAME)
    worksheet = sh.worksheet(WORD_SHEET_NAME)
    words = [w for w in worksheet.col_values(1) if w.strip() and w not in exclude]
    return random.sample(words, min(count, len(words)))

class ChangeImageButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(label="キャラ変更", style=discord.ButtonStyle.primary)
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        session = sessions.get(self.channel_id)
        if not session or interaction.user.id != session['author_id']:
            return await interaction.response.send_message("このボタンは作成者のみ使用できます。", ephemeral=True)
        session['current_image'] = get_random_image_url()
        embed = discord.Embed(title="オリキャラ妄想図鑑-初期属性数決め", description="キャラを変更しました")
        embed.set_image(url=session['current_image'])
        await interaction.response.edit_message(embed=embed)

class InitialAttrButton(discord.ui.Button):
    def __init__(self, n: int, channel_id: int):
        super().__init__(label=f"属性{n}個", style=discord.ButtonStyle.secondary)
        self.n = n
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        session = sessions.get(self.channel_id)
        if not session or interaction.user.id != session['author_id']:
            return await interaction.response.send_message("このボタンは作成者のみ使用できます。", ephemeral=True)
        session['initial'] = get_random_words([], self.n)
        session['candidates'] = get_random_words(session['initial'], 10)
        session['selected'] = {}
        embed = discord.Embed(title="オリキャラ妄想図鑑-選択肢数決め")
        embed.set_image(url=session['current_image'])
        embed.add_field(name="【初期属性】", value=" / ".join(session['initial']), inline=False)
        view = SelectCountView(self.channel_id)
        await interaction.response.edit_message(embed=embed, view=view)

class SelectCountView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=f"追加属性{n}個") for n in range(5, 11)]
        self.add_item(SelectCount(options, channel_id))

class SelectCount(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption], channel_id: int):
        super().__init__(placeholder="追加属性数を選択", min_values=1, max_values=1, options=options)
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        session = sessions.get(self.channel_id)
        if not session or interaction.user.id != session['author_id']:
            return await interaction.response.send_message("この操作は作成者のみです。", ephemeral=True)
        count = int(self.values[0].replace("追加属性", "").replace("個", ""))
        session['extra'] = get_random_words(session['initial'], count)
        view = SelectWordView(self.channel_id)
        await interaction.response.edit_message(view=view)

class SelectWordView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        session = sessions[channel_id]
        for w in session['extra']:
            self.add_item(WordButton(w, channel_id))
        self.add_item(FinishButton(channel_id))

class WordButton(discord.ui.Button):
    def __init__(self, label: str, channel_id: int):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        session = sessions.get(self.channel_id)
        if not session:
            return
        # ユーザー選択を記録
        session['selected'][interaction.user.id] = self.label
        # 選択者一覧
        summary = "".join(f"<@{uid}>" for uid in session['selected']) or "誰もいません"
        # Embedを再構築（画像・初期属性・追加属性・選択者一覧）
        embed = discord.Embed(title="オリキャラ妄想図鑑-追加属性選択")
        embed.set_image(url=session['current_image'])
        if session.get('initial'):
            embed.add_field(name="【初期属性】", value=" / ".join(session['initial']), inline=False)
        if session.get('extra'):
            embed.add_field(name="【追加属性】", value=" / ".join(session['extra']), inline=False)
        embed.add_field(name="【選択者一覧】", value=summary, inline=False)
        # メッセージを更新
        await interaction.response.edit_message(embed=embed, view=self.view)
        # エフェメラルで選択通知
        await interaction.followup.send(
            f"あなたは「{self.label}」を選びました。", ephemeral=True
        )

class FinishButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(label="選択終了", style=discord.ButtonStyle.danger, row=3)
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        session = sessions.get(self.channel_id)
        if not session or interaction.user.id != session['author_id']:
            return await interaction.response.send_message("この操作は作成者のみです。", ephemeral=True)
        embed = discord.Embed(title="オリキャラ妄想図鑑-結果発表")
        embed.set_image(url=session['current_image'])
        embed.add_field(name="【初期属性】", value=" / ".join(session['initial']), inline=False)
        embed.add_field(name="【追加属性】", value=" / ".join(session['extra']), inline=False)
        sel = session['selected']
        embed.add_field(name="【ユーザー選択】", value="\n".join(f"<@{u}>：{w}" for u,w in sel.items()) or "なし", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)

# =============================
# コマンド登録
# =============================
async def setup(bot: commands.Bot):
    @bot.tree.command(name="オリキャラ妄想図鑑", description="オリキャラ妄想図鑑で遊べます")
    async def orikyarazukan(interaction: discord.Interaction):
        channel_id = interaction.channel_id
        author_id = interaction.user.id
        image_url = get_random_image_url()

        if not image_url:
            return await interaction.response.send_message(
                "画像がスプレッドシートに登録されていません。", ephemeral=True
            )

        # セッション初期化
        sessions[channel_id] = {
            'author_id': author_id,
            'current_image': image_url,
            'initial': [],
            'candidates': [],
            'extra': [],
            'selected': {}
        }

        embed = discord.Embed(title="オリキャラ妄想図鑑-初期属性数決め", description="今回はこのキャラ！")
        embed.set_image(url=image_url)

        view = discord.ui.View(timeout=None)
        view.add_item(ChangeImageButton(channel_id))
        for n in [3, 4, 5]:
            view.add_item(InitialAttrButton(n, channel_id))
        await interaction.response.send_message(embed=embed, view=view)
