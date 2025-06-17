import discord
from discord import app_commands
from discord.ext import commands
import random

# チャンネル単位でゲーム状態を管理
game_states = {}

# 定数
INITIAL_POS_PREFIX = "initial_pos_"
GAME_START_ID = "game_start"
INITIAL_SELECT_ID = "initial_select"
MOVE_BUTTON_PREFIX = "move_"
DESTROY_BUTTON_PREFIX = "destroy_"
NEXT_PLAYER_ID = "next_player"
AREA_DESTROY_ID = "area_destroy"

MOVE_VALUES = [-5, +1, +5, -1]
MOVE_LABELS = {
    -5: "↑",
    1: "→",
    5: "↓",
    -1: "←",
}

INVALID_MOVES = {(5, 6), (6, 5), (10, 11), (11, 10), (15, 16), (16, 15), (20, 21), (21, 20)}

def is_valid_position(pos):
    return 1 <= pos <= 25

class InitialPositionButton(discord.ui.Button):
    def __init__(self, number: int, channel_id):
        super().__init__(label=str(number), style=discord.ButtonStyle.secondary, custom_id=f"{INITIAL_POS_PREFIX}{number}")
        self.number = number
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        channel_id = self.channel_id
        game_data = game_states.get(channel_id)
        if not game_data:
            await interaction.response.send_message("❌ このチャンネルでゲームは開始されていません。", ephemeral=True)
            return

        if game_data['game_started']:
            await interaction.response.send_message("❌ ゲームはすでに開始されています。", ephemeral=True)
            return

        user_id = interaction.user.id
        # 1ユーザー1回のみ
        if user_id in game_data['initial_positions']:
            await interaction.response.send_message("❌ あなたはすでに初期位置を選択済みです。", ephemeral=True)
            return

        game_data['initial_positions'][user_id] = self.number
        # 現在位置も初期位置と同じにする
        game_data['current_positions'][user_id] = self.number

        try:
            await interaction.user.send(f"あなたの現在位置は {self.number} です。")
            await interaction.response.send_message("初期位置をDMに送信しました。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ DMを送れませんでした。設定を確認してください。", ephemeral=True)
            return

        # 開始メッセージを更新（参加プレイヤーリスト表示）
        start_msg = game_data.get('start_message')
        start_view = game_data.get('start_view')
        if start_msg and start_view:
            user_mentions = [f"<@{uid}>" for uid in game_data['initial_positions'].keys()]
            new_content = f"WORLDENDゲーム開始！ \n [参加プレーヤー]\n" + "\n".join(user_mentions)
            try:
                await start_msg.edit(content=new_content, view=start_view)
            except Exception as e:
                print(f"メッセージ編集失敗: {e}")

class InitialPositionView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        for i in range(1, 26):
            self.add_item(InitialPositionButton(i, channel_id))

class InitialPositionSelectButton(discord.ui.Button):
    def __init__(self, channel_id):
        super().__init__(label="初期位置", style=discord.ButtonStyle.primary, custom_id=INITIAL_SELECT_ID)
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        view = InitialPositionView(self.channel_id)
        await interaction.response.send_message("初期位置を選んでください。", view=view, ephemeral=False)

        self.disabled = True
        await interaction.message.edit(view=self.view)

class GameStartButton(discord.ui.Button):
    def __init__(self, channel_id):
        super().__init__(label="ゲーム開始", style=discord.ButtonStyle.danger, custom_id=GAME_START_ID)
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        channel_id = self.channel_id
        game_data = game_states.get(channel_id)
        if not game_data:
            await interaction.response.send_message("❌ このチャンネルでゲームは開始されていません。", ephemeral=True)
            return
        if len(game_data['initial_positions']) < 2:
            await interaction.response.send_message("❌ 初期位置を少なくとも2人は選んでください。", ephemeral=True)
            return

        game_data['game_started'] = True

        # ターン順リストを作りシャッフル
        turn_order = list(game_data['initial_positions'].keys())
        random.shuffle(turn_order)
        game_data['turn_order'] = turn_order
        game_data['turn_index'] = 0
        game_data['destroyed_positions'] = set()
        game_data['eliminated_players'] = set()

        # 最初のプレイヤーを取得
        next_player = turn_order[0]
        game_data['current_turn_player'] = next_player

        # 初期位置選択を無効化（ビューを消すなど）
        start_msg = game_data.get('start_message')
        start_view = game_data.get('start_view')
        if start_msg and start_view:
            await start_msg.edit(content="ゲーム開始！初期位置選択は終了しました。", view=None)

        view = MoveButtonsView(self.channel_id, next_player)
        move_msg = await interaction.channel.send(
            f"{interaction.guild.get_member(next_player).mention} さんは移動してください。", view=view)
        game_data['move_message'] = move_msg

class StartGameView(discord.ui.View):
    def __init__(self, starter_id, channel_id):
        super().__init__(timeout=None)
        self.starter_id = starter_id
        self.channel_id = channel_id
        self.add_item(InitialPositionSelectButton(channel_id))
        self.add_item(GameStartButton(channel_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.starter_id:
            await interaction.response.send_message("❌ このボタンはコマンド実行者のみ操作可能です。", ephemeral=True)
            return False
        return True

class MoveButton(discord.ui.Button):
    def __init__(self, channel_id, user_id, move_value):
        label = MOVE_LABELS.get(move_value, str(move_value))
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=f"{MOVE_BUTTON_PREFIX}{move_value}")
        self.channel_id = channel_id
        self.user_id = user_id
        self.move_value = move_value

    async def callback(self, interaction: discord.Interaction):
        game_data = game_states.get(self.channel_id)
        if not game_data:
            await interaction.response.send_message("❌ ゲームが見つかりません。", ephemeral=True)
            return

        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ あなたのターンではありません。", ephemeral=True)
            return

        if self.user_id in game_data['eliminated_players']:
            # 脱落済みは移動フェーズスキップ
            await interaction.response.send_message("あなたは脱落済みのため移動できません。破壊フェーズに移ります。", ephemeral=True)
            # 破壊フェーズへ
            await send_destroy_phase(interaction, self.channel_id, self.user_id)
            return

        current_pos = game_data['current_positions'].get(self.user_id)
        previous_pos = game_data.get('previous_positions', {}).get(self.user_id)
        

        if current_pos is None:
            await interaction.response.send_message("❌ 現在の位置が設定されていません。", ephemeral=True)
            return

        new_pos = current_pos + self.move_value

        # 無効な移動チェック
        if (current_pos, new_pos) in INVALID_MOVES:
            await interaction.response.send_message("❌ その場所には移動できません。", ephemeral=True)
            return

        if not is_valid_position(new_pos) or new_pos in game_data['destroyed_positions']:
            await interaction.response.send_message("❌ その場所には移動できません。", ephemeral=True)
            return

        # 前の位置に戻る警告初回のみ
        warned = game_data.setdefault('warned_return', {}).get(self.user_id)

        if previous_pos == new_pos and not warned:
            await interaction.response.send_message("⚠️ 前の位置戻ろうとしています。 \n もう一度ボタンを押すと移動出来ますが、マイナス3点です", ephemeral=True)
            game_data['warned_return'][self.user_id] = True  # 警告済みにする
            return
        
        # 2度目以降の押下で実際に戻った場合、全体向けにメッセージを出す
        if previous_pos == new_pos and warned:
            embed = discord.Embed(
                description=f"⚠️ <@{self.user_id}> さんは前の位置に戻ったため **マイナス3点** です。",
                color=discord.Color.yellow()
            )
            await interaction.channel.send(embed=embed)

        game_data.setdefault('previous_positions', {})[self.user_id] = current_pos
        game_data['current_positions'][self.user_id] = new_pos

        try:
            await interaction.user.send(f"あなたの現在位置は {new_pos} です。")
        except discord.Forbidden:
            await interaction.response.send_message("❌ DMを送れませんでした。設定を確認してください。", ephemeral=True)
            return

        # 旧移動ボタン削除
        move_msg = game_data.get('move_message')
        if move_msg:
            await move_msg.edit(view=None)

        # 移動メッセージを送信し、破壊用ボタン表示
        destroy_view = DestroyPositionView(self.channel_id, self.user_id)
        direction = MOVE_LABELS.get(self.move_value, str(self.move_value))
        destroy_msg = await interaction.channel.send(f"{interaction.user.mention} さんが {direction} 方向に移動しました。破壊する位置を選んでください。", view=destroy_view)
        game_data['destroy_message'] = destroy_msg

class MoveButtonsView(discord.ui.View):
    def __init__(self, channel_id, user_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.user_id = user_id
        for val in MOVE_VALUES:
            self.add_item(MoveButton(channel_id, user_id, val))
        self.add_item(AreaDestroyButton(channel_id, user_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ あなたのターンではありません。", ephemeral=True)
            return False
        return True

class DestroyPositionButton(discord.ui.Button):
    def __init__(self, number, channel_id, user_id):
        super().__init__(label=str(number), style=discord.ButtonStyle.danger, custom_id=f"{DESTROY_BUTTON_PREFIX}{number}")
        self.number = number
        self.channel_id = channel_id
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        game_data = game_states.get(self.channel_id)
        if not game_data:
            await interaction.response.send_message("❌ ゲームが見つかりません。", ephemeral=True)
            return

        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ あなたのターンではありません。", ephemeral=True)
            return

        if self.number in game_data['destroyed_positions']:
            await interaction.response.send_message("❌ すでに破壊されています。選びなおしてください。", ephemeral=True)
            return

        # 破壊処理
        game_data['destroyed_positions'].add(self.number)

        # 破壊位置にプレイヤーがいるか判定
        eliminated_mentions = []
        eliminated_ids = []
        for uid, pos in game_data['current_positions'].items():
            if pos == self.number:
                # 脱落
                eliminated_mentions.append(f"<@{uid}>")
                eliminated_ids.append(uid)

        # 脱落者処理
        for uid in eliminated_ids:
            game_data['eliminated_players'].add(uid)
            game_data['current_positions'][uid] = None  # 位置リセット

        embed = discord.Embed(
            title=f"{self.number} が破壊されました。",
            color=discord.Color.red()
        )
        if eliminated_mentions:
            embed.description = f"{', '.join(eliminated_mentions)} がそこにいました。（1人につき3点）"
        await interaction.response.send_message(embed=embed, ephemeral=False)

        # 旧破壊ボタン削除
        destroy_msg = game_data.get('destroy_message')
        if destroy_msg:
            await destroy_msg.edit(view=None)

        # 生存者が1人なら終了
        alive_players = set(game_data['initial_positions'].keys()) - game_data['eliminated_players']
        if len(alive_players) == 1:
            winner_id = list(alive_players)[0]
            embed = discord.Embed(
                title="🎊 ゲーム終了 🎊",
                description=f"🎉 <@{winner_id}> さんが最後の生存者になりました！（10点）🎉 \n 得点計算をしてください。",
                color=discord.Color.gold()
            )
            await interaction.channel.send(embed=embed)

            move_msg = game_data.get('move_message')
            destroy_view_msg = game_data.get('destroy_message')
            for msg in [move_msg, destroy_view_msg]:
                if msg:
                    await msg.edit(view=None)

            game_states.pop(self.channel_id, None)
            return
        
        # 生存者なしで終了
        elif len(alive_players) == 0:
            embed = discord.Embed(
                title="😭 ゲーム終了 😭",
                description="すべてのプレイヤーが脱落しました。生存者得点はなし。 \n 得点計算をしてください。",
                color=discord.Color.red()
            )
            await interaction.channel.send(embed=embed)

            move_msg = game_data.get('move_message')
            destroy_view_msg = game_data.get('destroy_message')
            for msg in [move_msg, destroy_view_msg]:
                if msg:
                    await msg.edit(view=None)

            game_states.pop(self.channel_id, None)
            return

        # 次のプレイヤーを turn_order に沿って選ぶ
        turn_order = game_data['turn_order']
        turn_index = game_data['turn_index']

        # 次のインデックスに進める（脱落者も含める仕様）
        turn_index = (turn_index + 1) % len(turn_order)
        game_data['turn_index'] = turn_index

        next_player = turn_order[turn_index]
        game_data['current_turn_player'] = next_player

        # 警告状態などをリセット
        game_data.setdefault('warned_return', {}).pop(next_player, None)

        # ✅ 脱落者かどうかを確認
        if next_player in game_data['eliminated_players']:
            await interaction.channel.send(f"<@{next_player}> さんは脱落済みのため移動をスキップしました。")
            await send_destroy_phase(interaction, self.channel_id, next_player)
        else:
            view = MoveButtonsView(self.channel_id, next_player)
            move_msg = await interaction.channel.send(f"次のプレーヤーは <@{next_player}> さんです。移動してください。", view=view)
            game_data['move_message'] = move_msg


class DestroyPositionView(discord.ui.View):
    def __init__(self, channel_id, user_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.user_id = user_id

        game_data = game_states.get(channel_id)
        destroyed_positions = set()
        if game_data:
            destroyed_positions = game_data.get('destroyed_positions', set())

        for i in range(1, 26):
            disabled = i in destroyed_positions
            btn = DestroyPositionButton(i, channel_id, user_id)
            btn.disabled = disabled
            self.add_item(btn)

class AreaDestroyButton(discord.ui.Button):
    def __init__(self, channel_id, user_id):
        super().__init__(label="移動不可", style=discord.ButtonStyle.danger, custom_id=AREA_DESTROY_ID)
        self.channel_id = channel_id
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        game_data = game_states.get(self.channel_id)
        if not game_data:
            await interaction.response.send_message("❌ ゲームが見つかりません。", ephemeral=True)
            return

        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ あなたのターンではありません。", ephemeral=True)
            return
        
        current_pos = game_data['current_positions'].get(self.user_id)
        possible_moves = []

        for move_value in MOVE_VALUES:
            new_pos = current_pos + move_value
            if (current_pos, new_pos) in INVALID_MOVES:
                continue
            if not is_valid_position(new_pos):
                continue
            if new_pos in game_data['destroyed_positions']:
                continue
            possible_moves.append(MOVE_LABELS[move_value])

        if possible_moves:
            directions = " / ".join(possible_moves)
            await interaction.response.send_message(
                f"🔁 現在位置 {current_pos} から以下の方向に移動可能です: {directions}\n移動ボタンをご利用ください。",
                ephemeral=True
            )
            return
        
        # 旧移動ボタン削除
        move_msg = game_data.get('move_message')
        if move_msg:
            await move_msg.edit(view=None)

        # 破壊用ボタン表示
        view = DestroyPositionView(self.channel_id, self.user_id)
        destroy_msg = await interaction.channel.send(f"{interaction.user.mention} さんは移動することが出来ません。破壊する位置を選んでください。", view=view)
        game_data['destroy_message'] = destroy_msg

async def send_destroy_phase(interaction: discord.Interaction, channel_id: int, user_id: int):
    # 脱落者の破壊フェーズに遷移するヘルパー
    view = DestroyPositionView(channel_id, user_id)
    destroy_msg = await interaction.channel.send(f"破壊する位置を選んでください。", view=view)
    game_states[channel_id]['destroy_message'] = destroy_msg

class WorldEnd(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="worldend", description="WORLDENDゲームを開始します")
    async def worldend_command(self, interaction: discord.Interaction):
        channel_id = interaction.channel.id
        # チャンネルごとにゲーム状態を初期化
        game_states[channel_id] = {
            'starter_id': interaction.user.id,
            'initial_positions': {},        # プレイヤーの初期位置
            'current_positions': {},        # 現在位置 (Noneは脱落)
            'game_started': False,          
            'start_message': None,
            'start_view': None,
            'current_turn_player': None,    # 現在のターンプレイヤー
            'destroyed_positions': set(),   # 破壊済みのマス
            'eliminated_players': set(),    # 脱落プレイヤー
            'turn_order': [],               # ターン順
            'turn_index': 0,                # 現在のターンインデックス
        }
        view = StartGameView(starter_id=interaction.user.id, channel_id=channel_id)
        # メッセージ送信
        await interaction.response.send_message("WORLDENDゲーム開始！ \n [参加プレーヤー]", view=view)
        # メッセージオブジェクトを取得して保存
        start_msg = await interaction.original_response()
        game_states[channel_id]['start_message'] = start_msg
        game_states[channel_id]['start_view'] = view

async def setup(bot: commands.Bot):
    await bot.add_cog(WorldEnd(bot))
