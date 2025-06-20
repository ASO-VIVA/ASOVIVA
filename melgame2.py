import discord
from discord.ext import commands
from discord import app_commands
import random

class MelGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game_states = {}  # チャンネルIDごとに状態管理

    @app_commands.command(name="みんなでメルゲーム", description="メルゲームを開始します")
    async def start_game(self, interaction: discord.Interaction):
        channel_id = interaction.channel.id
        self.game_states[channel_id] = {
            "parent_id": interaction.user.id,
            "available_numbers": list(range(1, 16)),
            "used_numbers": [],
            "selections": {},
            "points": {},
            "trap": {},
            "trap3_words": ["ポンすぎる", "残念な", "ドMの", "クズの", "変態の","異様な","裸の","完全無欠な","発情期の","愛玩具の","負け犬の","エロボの","超絶怒涛の","空前絶後の","濡れている"]
        }

        view = TrapSetupView(self, channel_id, interaction.user.id)
        await interaction.response.send_message("罠を仕掛ける場所を選んでください", view=view)

class TrapSetupView(discord.ui.View):
    def __init__(self, cog, channel_id, parent_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id
        self.parent_id = parent_id

    @discord.ui.button(label="罠設置", style=discord.ButtonStyle.danger)
    async def setup_trap(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.parent_id:
            await interaction.response.send_message("あなたはこのボタンを使えません。", ephemeral=True)
            return

        state = self.cog.game_states[self.channel_id]
        available = ",".join(str(n) for n in state["available_numbers"])

        await interaction.response.send_modal(TrapModal(self.cog, self.channel_id, available))

class TrapModal(discord.ui.Modal, title="罠を設置してください"):
    def __init__(self, cog, channel_id, available_text):
        super().__init__()
        self.cog = cog
        self.channel_id = channel_id

        label_text = f"使用可能番号（{available_text}）"

        self.description = discord.ui.TextInput(label=label_text,placeholder="※この欄はそのままでOKです",
            required=False,style=discord.TextStyle.short,max_length=1)
        self.trap1 = discord.ui.TextInput(label="罠①：使用不可", placeholder="半角数字", required=True, max_length=2)
        self.trap2 = discord.ui.TextInput(label="罠②：使用不可", placeholder="半角数字", required=True, max_length=2)
        self.trap3 = discord.ui.TextInput(label="罠③：名前に罰ワード", placeholder="半角数字", required=True, max_length=2)
        self.safe = discord.ui.TextInput(label="セーフ：得点獲得", placeholder="半角数字", required=True, max_length=2)
        self.add_item(self.description)
        self.add_item(self.trap1)
        self.add_item(self.trap2)
        self.add_item(self.trap3)
        self.add_item(self.safe)

    async def on_submit(self, interaction: discord.Interaction):
        state = self.cog.game_states[self.channel_id]
        nums = state["available_numbers"]

        try:
            t1 = int(self.trap1.value)
            t2 = int(self.trap2.value)
            t3 = int(self.trap3.value)
            s = int(self.safe.value)
        except ValueError:
            await interaction.response.send_message("すべての入力に半角数字を入力してください。", ephemeral=True)
            return

        if not all(x in nums for x in [t1, t2, t3, s]):
            await interaction.response.send_message("入力された数字は使用できません。", ephemeral=True)
            return
        
        if len({t1, t2, t3, s}) != 4:
            await interaction.response.send_message("数字が重複しています。別の数字を指定してください。", ephemeral=True)
            return

        state["trap"] = {"trap1": t1, "trap2": t2, "trap3": t3, "safe": s}
        
        view = NumberSelectView(self.cog, self.channel_id, state["parent_id"])
        await interaction.response.edit_message(
            content="参加プレーヤーはボタンを1つ選んでください\n"
                    "2度目以降の選択は上書きされます\n"
                    "番号決定者に名前が表示されない場合はもう一度押してください\n"
                    "〈番号決定者〉\n" + self._build_selection_text(state),
            view=view
        )

    def _build_selection_text(self, state):
        return "\n".join([f"<@{k}>" for k in state["selections"].keys()])

class NumberSelectView(discord.ui.View):
    def __init__(self, cog, channel_id, parent_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id
        self.parent_id = parent_id
        state = cog.game_states[channel_id]

        for i in range(1, 16):
            disabled = i in state["used_numbers"]
            self.add_item(NumberButton(i, disabled))

        self.add_item(ExecuteButton(cog, channel_id, parent_id))

class NumberButton(discord.ui.Button):
    def __init__(self, number, disabled):
        super().__init__(label=str(number), style=discord.ButtonStyle.primary, row=(number-1)//5, disabled=disabled)
        self.number = number

    async def callback(self, interaction: discord.Interaction):
        state = self.view.cog.game_states[self.view.channel_id]
        state["selections"][interaction.user.id] = self.number

        await interaction.response.edit_message(
            content="参加プレーヤーはボタンを1つ選んでください\n"
                    "2度目以降の選択は上書きされます\n"
                    "番号決定者に名前が表示されない場合はもう一度押してください\n"
                    "〈番号決定者〉\n" + "\n".join([
                f"<@{k}>" for k in state["selections"].keys()
            ]),
            view=self.view
        )

        await interaction.followup.send(content=f"あなたが選んだ番号は `{self.number}` です。",ephemeral=True)

class ExecuteButton(discord.ui.Button):
    def __init__(self, cog, channel_id, parent_id):
        super().__init__(label="実行", style=discord.ButtonStyle.success, row=3)
        self.cog = cog
        self.channel_id = channel_id
        self.parent_id = parent_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_id:
            await interaction.response.send_message("あなたはこのボタンを使えません。", ephemeral=True)
            return

        state = self.cog.game_states[self.channel_id]
        trap = state["trap"]

        text = (f"罠①ボタン消滅：{trap['trap1']}\n罠②ボタン消滅：{trap['trap2']}\n罠③名前追加：{trap['trap3']}\n得点確定：{trap['safe']}\n"
                + "\n".join([f"<@{k}> → {v}" for k, v in state["selections"].items()]))

        await interaction.response.edit_message(content=text, view=ExecutionView(self.cog, self.channel_id, self.parent_id))

class ExecutionView(discord.ui.View):
    def __init__(self, cog, channel_id, parent_id):
        super().__init__(timeout=None)
        self.add_item(ScoreButton(cog, channel_id, parent_id))

class ScoreButton(discord.ui.Button):
    def __init__(self, cog, channel_id, parent_id):
        super().__init__(label="得点と執行", style=discord.ButtonStyle.primary)
        self.cog = cog
        self.channel_id = channel_id
        self.parent_id = parent_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_id:
            await interaction.response.send_message("あなたはこのボタンを使えません。", ephemeral=True)
            return

        state = self.cog.game_states[self.channel_id]
        trap = state["trap"]
        result = "〈得点〉\n"

        await interaction.response.edit_message(content=interaction.message.content, view=None)

        for uid, number in state["selections"].items():
            user_points = state["points"].setdefault(uid, {"temp": 0, "confirmed": 0})
            if number in (trap["trap1"], trap["trap2"], trap["trap3"]):
                # 罠1,2,3を踏んだ時は暫定点数リセット
                user_points["temp"] = 0
                # 罠3の場合は名前ペナルティ
                if number == trap["trap3"]:
                    word = random.choice(state["trap3_words"])
                    member = interaction.guild.get_member(uid)
                    if member:
                        try:
                            new_nick = f"{word}{member.display_name}"
                            await member.edit(nick=new_nick[:32])
                        except:
                            pass
            elif number == trap["safe"]:
                # safeはまず暫定点数に数字を加算
                user_points["temp"] += number
                # そして暫定点数を確定点数に移動しリセット
                user_points["confirmed"] += user_points["temp"]
                user_points["temp"] = 0

            else:
                # 罠以外の数字は暫定点数に加算
                user_points["temp"] += number

        result += "\n".join([
            f"<@{uid}>：暫定 {p['temp']} 点 ／ 確定 {p['confirmed']} 点"
            for uid, p in state["points"].items()
        ])
        # trap1, trap2 の番号を無効にした新しい NumberSelectView を作成
        trap1 = trap["trap1"]
        trap2 = trap["trap2"]
        state["used_numbers"].extend([trap1, trap2])
        state["available_numbers"] = [n for n in range(1, 16) if n not in state["used_numbers"]]

        result += "\n\n以後使用できない番号（罠①②）：" + ", ".join(map(str, [trap1, trap2]))


        await interaction.followup.send(content=result, view=NextRoundView(self.cog, self.channel_id, self.parent_id))

class NextRoundView(discord.ui.View):
    def __init__(self, cog, channel_id, parent_id):
        super().__init__(timeout=None)
        self.add_item(NextRoundButton(cog, channel_id, parent_id))
        self.add_item(EndButton(cog, channel_id, parent_id))

class NextRoundButton(discord.ui.Button):
    def __init__(self, cog, channel_id, parent_id):
        super().__init__(label="次のラウンドへ", style=discord.ButtonStyle.secondary)
        self.cog = cog
        self.channel_id = channel_id
        self.parent_id = parent_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_id:
            await interaction.response.send_message("あなたはこのボタンを使えません", ephemeral=True)
            return
        
        await interaction.response.edit_message(content=interaction.message.content, view=None)
        
        # リセットして罠設置フェーズに戻る
        state = self.cog.game_states[self.channel_id]
        state["selections"] = {}
        view = TrapSetupView(self.cog, self.channel_id, self.parent_id)
        await interaction.followup.send(content="罠を仕掛ける場所を選んでください", view=view)

class EndButton(discord.ui.Button):
    def __init__(self, cog, channel_id, parent_id):
        super().__init__(label="終了", style=discord.ButtonStyle.danger)
        self.cog = cog
        self.channel_id = channel_id
        self.parent_id = parent_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_id:
            await interaction.response.send_message("あなたはこのボタンを使えません", ephemeral=True)
            return
        
        await interaction.response.edit_message(content=interaction.message.content, view=None)
        
        state = self.cog.game_states[self.channel_id]
        text = "メルゲームが終了されました。\n〈最終得点〉\n"
        text += "\n".join([
            f"<@{uid}>：{p['temp'] + p['confirmed']} 点  （暫定{p['temp']}点＋確定{p['confirmed']}点）"
            for uid, p in state["points"].items()
        ])

        await interaction.followup.send(content=text)

async def setup(bot):
    await bot.add_cog(MelGame(bot))
