import discord
from discord import app_commands
from discord.ext import commands


class SpacerButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="\u200b", style=discord.ButtonStyle.secondary, disabled=True)


class AnswerFlip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}  # message_id -> session_data

    @app_commands.command(name="回答フリップ", description="集めた回答を各自で発表できる")
    async def start_flip(self, interaction: discord.Interaction):
        await interaction.response.defer()

        view = AnswerFlipView(self, None)
        msg = await interaction.followup.send(
            "回答フリップ開始！\n「回答入力」ボタンで回答を入力してください。",
            view=view,
            ephemeral=False
        )

        session_id = msg.id
        self.sessions[session_id] = {
            "answers": {},
            "is_closed": False,
            "owner_id": interaction.user.id,
            "message": msg,
            "view": view,
            "revealed_users": set()
        }

        view.session_id = session_id
        await msg.edit(view=view)


class AnswerFlipView(discord.ui.View):
    def __init__(self, cog: AnswerFlip, session_id: int | None):
        super().__init__(timeout=None)
        self.cog = cog
        self.session_id = session_id

        input_btn = discord.ui.Button(label="回答入力", style=discord.ButtonStyle.primary, custom_id="answer_input")
        input_btn.callback = self.answer_input_button
        self.add_item(input_btn)

        self.add_item(SpacerButton())
        self.add_item(SpacerButton())

        close_btn = discord.ui.Button(label="回答締切", style=discord.ButtonStyle.danger, custom_id="answer_close")
        close_btn.callback = self.answer_close_button
        self.add_item(close_btn)

    def get_session(self):
        return self.cog.sessions.get(self.session_id)

    async def answer_input_button(self, interaction: discord.Interaction):
        session = self.get_session()
        if not session:
            await interaction.response.send_message("セッションが見つかりません。", ephemeral=True)
            return
        if session["is_closed"]:
            await interaction.response.send_message("回答締切済みです。", ephemeral=True)
            return
        await interaction.response.send_modal(AnswerInputModal(self.cog, self.session_id))

    async def answer_close_button(self, interaction: discord.Interaction):
        session = self.get_session()
        if not session:
            await interaction.response.send_message("セッションが見つかりません。", ephemeral=True)
            return
        if interaction.user.id != session["owner_id"]:
            await interaction.response.send_message("このボタンはコマンド実行者のみ使えます。", ephemeral=True)
            return
        if session["is_closed"]:
            await interaction.response.send_message("すでに回答は締切られています。", ephemeral=True)
            return

        session["is_closed"] = True

        reveal_view = AnswerRevealView(self.cog, self.session_id)
        await interaction.response.edit_message(
            content="回答は締切られました。各自「回答発表」ボタンで自分の回答を表示できます。",
            view=reveal_view
        )


class AnswerInputModal(discord.ui.Modal, title="回答を入力してください"):
    answer = discord.ui.TextInput(label="回答", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, cog: AnswerFlip, session_id: int | None):
        super().__init__()
        self.cog = cog
        self.session_id = session_id

    async def on_submit(self, interaction: discord.Interaction):
        session = self.cog.sessions.get(self.session_id)
        if not session:
            await interaction.response.send_message("セッションが見つかりません。", ephemeral=True)
            return

        user_id = interaction.user.id
        user_name = interaction.user.display_name
        session["answers"][user_id] = self.answer.value

        guild = interaction.guild
        names = []
        for uid in session["answers"].keys():
            member = guild.get_member(uid) if guild else None
            names.append(member.display_name if member else f"ユーザーID:{uid}")

        total_count = len(names)
        names_text = "\n".join(f"- {name}" for name in names)

        content = (
            f"回答フリップ開始！\n"
            f"「回答入力」ボタンで回答を入力してください。\n\n"
            f"現在の回答者数: {total_count} 人\n"
            f"[回答者一覧]\n{names_text}"
        )

        await session["message"].edit(content=content, view=session["view"])
        await interaction.response.send_message(f"回答『{self.answer.value}』を受け付けました。", ephemeral=True)


class AnswerRevealView(discord.ui.View):
    def __init__(self, cog: AnswerFlip, session_id: int | None):
        super().__init__(timeout=None)
        self.cog = cog
        self.session_id = session_id

        reveal_btn = discord.ui.Button(label="回答発表", style=discord.ButtonStyle.success, custom_id="answer_reveal")
        reveal_btn.callback = self.reveal_button
        self.add_item(reveal_btn)

    def get_session(self):
        return self.cog.sessions.get(self.session_id)

    async def reveal_button(self, interaction: discord.Interaction):
        session = self.get_session()
        if not session:
            await interaction.response.send_message("セッションが見つかりません。", ephemeral=True)
            return

        user_id = interaction.user.id
        user_name = interaction.user.display_name

        if user_id not in session["answers"]:
            await interaction.response.send_message(f"{user_name} さんは回答していません。", ephemeral=True)
            return

        if user_id in session["revealed_users"]:
            await interaction.response.send_message("回答はすでに発表済みです。", ephemeral=True)
            return

        session["revealed_users"].add(user_id)
        answer = session["answers"][user_id]
        await interaction.response.send_message(f"**{user_name}** さんの回答\n『{answer}』", ephemeral=False)


async def setup(bot):
    await bot.add_cog(AnswerFlip(bot))
