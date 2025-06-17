import discord
from discord.ext import commands

# Cog本体
class HayaOshi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session_data = {}

    class FastestButtonView(discord.ui.View):
        def __init__(self, parent, message_id: int, author_id: int):
            super().__init__(timeout=None)
            self.parent = parent
            self.message_id = message_id
            self.author_id = author_id
            self.parent.session_data[self.message_id] = {"pressed_users": []}

            # ボタンを手動で追加して順序制御
            self.add_item(self.PressButton(self))
            self.add_item(self.SpacerButton1())  # 空白ボタン①
            self.add_item(self.SpacerButton2())  # 空白ボタン②
            self.add_item(self.ResetButton(self))

        class PressButton(discord.ui.Button):
            def __init__(self, view):
                super().__init__(label="早押し", style=discord.ButtonStyle.primary, custom_id="fast_button", row=0)
                self.view_ref = view

            async def callback(self, interaction: discord.Interaction):
                session = self.view_ref.parent.session_data.get(self.view_ref.message_id)
                if not session:
                    await interaction.response.send_message("❌ セッションが存在しません。", ephemeral=True)
                    return

                if interaction.user.id in [u.id for u in session["pressed_users"]]:
                    await interaction.response.send_message("❌ 一度押したらリセットまで押せません。", ephemeral=True)
                    return

                session["pressed_users"].append(interaction.user)
                pressed_list_text = "\n".join(f"{i+1}. {user.display_name}" for i, user in enumerate(session["pressed_users"]))
                await interaction.response.defer()
                await interaction.message.edit(content=f"🕹️ 早押し順:\n{pressed_list_text}", view=self.view_ref)

        class ResetButton(discord.ui.Button):
            def __init__(self, view):
                super().__init__(label="リセット", style=discord.ButtonStyle.danger, custom_id="reset_button", row=0)
                self.view_ref = view

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != self.view_ref.author_id:
                    await interaction.response.send_message("❌ リセットはコマンド実行者のみ可能です。", ephemeral=True)
                    return

                session = self.view_ref.parent.session_data.get(self.view_ref.message_id)
                if session:
                    session["pressed_users"] = []
                    await interaction.message.edit(content="🕹️ 早押し順:", view=self.view_ref)
                    await interaction.response.send_message("🔁 押した記録をリセットしました！", ephemeral=True)

        class SpacerButton1(discord.ui.Button):
            def __init__(self):
                super().__init__(label="\u200b", style=discord.ButtonStyle.secondary, disabled=True, row=0)  # ゼロ幅スペース

        class SpacerButton2(discord.ui.Button):
            def __init__(self):
                super().__init__(label="\u200b", style=discord.ButtonStyle.secondary, disabled=True, row=0)

    def has_any_allowed_role(self, user: discord.Member):
        return any(role.name in self.ALLOWED_ROLES for role in user.roles)

    @commands.hybrid_command(name="早押しボタン", with_app_command=True, description="早押しボタンを設置する")
    async def fast_button_command(self, ctx: commands.Context):
        dummy_message = await ctx.send("準備中...")
        view = self.FastestButtonView(self, message_id=dummy_message.id, author_id=ctx.author.id)
        await dummy_message.edit(content="🕹️ 早押しスタート！", view=view)

# setup関数は必須
async def setup(bot: commands.Bot):
    await bot.add_cog(HayaOshi(bot))
