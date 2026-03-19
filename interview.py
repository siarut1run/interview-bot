import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput
from datetime import datetime, timedelta

from config import DISCORD_TOKEN, ADMIN_ROLE_NAME, REMIND_BEFORE_MINUTES
from sheets import (
    save_interview,
    cancel_interview,
    list_interviews,
    is_time_conflict,
    set_notify_channel,
    get_notify_channel,
    # ↓ 追加
    set_channel,
    get_channel_id,
)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= 通知チャンネル =================

def get_notify_channel_obj(guild):
    cid = get_notify_channel(guild.id)
    if cid:
        ch = guild.get_channel(int(cid))
        if ch:
            return ch
    return guild.system_channel

# ================= 🔥 追加：チャンネル分離 =================

def get_log_channel(guild):
    cid = get_channel_id(guild.id, "log_channel")
    if cid:
        ch = guild.get_channel(int(cid))
        if ch:
            return ch
    return None

def get_interview_channel(guild):
    cid = get_channel_id(guild.id, "interview_channel")
    if cid:
        ch = guild.get_channel(int(cid))
        if ch:
            return ch
    return None

# ================= 日付入力 =================

class DateInputModal(Modal, title="日付入力"):
    year = TextInput(label="年 (例: 2026)")
    month = TextInput(label="月 (例: 1)")
    day = TextInput(label="日 (例: 1)")

    async def on_submit(self, interaction: discord.Interaction):
        date_str = f"{self.year.value}-{int(self.month.value):02}-{int(self.day.value):02}"
        await interaction.response.send_message(
            f"📅 日付: {date_str}\n午前か午後を選択してください",
            view=PeriodView(interaction.guild, date_str),
            ephemeral=True
        )

# ================= 午前午後 =================

class PeriodView(View):
    def __init__(self, guild, date_str):
        super().__init__(timeout=180)
        self.guild = guild
        self.date_str = date_str

    @discord.ui.button(label="🌅 午前", style=discord.ButtonStyle.primary)
    async def am(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "午前の時間を選択",
            view=TimeView(self.guild, self.date_str, "am"),
            ephemeral=True
        )

    @discord.ui.button(label="🌇 午後", style=discord.ButtonStyle.success)
    async def pm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "午後の時間を選択",
            view=TimeView(self.guild, self.date_str, "pm"),
            ephemeral=True
        )

# ================= 時間選択 =================

class TimeSelect(discord.ui.Select):
    def __init__(self, period, guild, date_str):
        self.guild = guild
        self.date_str = date_str

        if period == "am":
            hours = range(0, 12)
            placeholder = "午前の時間"
        else:
            hours = range(12, 24)
            placeholder = "午後の時間"

        times = []
        for h in hours:
            times.append(f"{h:02}:00")
            times.append(f"{h:02}:30")

        options = [discord.SelectOption(label=t, value=t) for t in times]

        super().__init__(placeholder=placeholder, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        time_str = self.values[0]

        await interaction.followup.send(
            "👤 面接者を選択してください",
            view=MemberView(self.guild, self.date_str, time_str),
            ephemeral=True
        )

class TimeView(View):
    def __init__(self, guild, date_str, period):
        super().__init__(timeout=180)
        self.add_item(TimeSelect(period, guild, date_str))

# ================= 面接者選択 =================

class MemberSelect(discord.ui.Select):
    def __init__(self, guild, date_str, time_str):
        self.guild = guild
        self.date_str = date_str
        self.time_str = time_str

        options = [
            discord.SelectOption(label=m.display_name, value=str(m.id))
            for m in guild.members if not m.bot
        ][:25]

        super().__init__(placeholder="面接者選択", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        uid = self.values[0]
        member = interaction.guild.get_member(int(uid))

        # 予約重複チェック
        if is_time_conflict(interaction.guild.id, self.date_str, self.time_str):
            await interaction.followup.send("❌ その時間は予約済み")
            return

        # 予約保存
        save_interview(
            interaction.guild.id,
            uid,
            member.display_name,
            self.date_str,
            self.time_str
        )

        # ================= 🔥 運営ログ送信 =================
        cid = get_channel_id(interaction.guild.id, "log_channel")

        if cid:
            log_ch = bot.get_channel(int(cid))
            if log_ch:
                await log_ch.send(
                    f"📢 **予約完了ログ**\n"
                    f"👤 {member.mention}\n"
                    f"📅 {self.date_str}\n"
                    f"🕒 {self.time_str}"
                )
            else:
                print("チャンネル取得失敗")
        else:
            print("ログチャンネル未設定")

        # ================= ユーザー通知 =================
        await interaction.followup.send(
            f"✅ 予約完了\n📅 {self.date_str}\n🕒 {self.time_str}\n👤 {member.mention}"
        )

# ================= キャンセル =================

class CancelModal(Modal, title="面接キャンセル"):
    user_id = TextInput(label="面接者Discord ID")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        ok = cancel_interview(interaction.guild.id, str(self.user_id.value))

        if ok:
            await interaction.followup.send("✅ キャンセル完了")
        else:
            await interaction.followup.send("❌ 予約が見つかりません")

# ================= メインパネル =================

class MainPanel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="予約", style=discord.ButtonStyle.green, custom_id="reserve_btn")
    async def reserve(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DateInputModal())

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.red, custom_id="cancel_btn")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(CancelModal())

    @discord.ui.button(label="一覧", style=discord.ButtonStyle.blurple, custom_id="list_btn")
    async def show_list(self, interaction: discord.Interaction, button: Button):
        data = list_interviews(interaction.guild.id)
        if not data:
            msg = "予約はありません"
        else:
            msg = "\n".join([f"{r[1]}｜{r[2]} {r[3]}" for r in data])
        await interaction.response.send_message(msg, ephemeral=True)

# ================= 通知 =================

notified_reserves = set()

@tasks.loop(minutes=1)
async def reminder_loop():
    now = datetime.now()

    for guild in bot.guilds:
        ch = get_interview_channel(guild)  # 🔥 変更

        if not ch:
            continue

        data = list_interviews(guild.id)

        for r in data:
            reserve_id = f"{guild.id}_{r[0]}_{r[2]}_{r[3]}"
            dt = datetime.strptime(r[2] + " " + r[3], "%Y-%m-%d %H:%M")

            if dt - timedelta(minutes=REMIND_BEFORE_MINUTES) <= now < dt:
                if reserve_id + "_before" not in notified_reserves:
                    await ch.send(f"🔔 面接{REMIND_BEFORE_MINUTES}分前 <@{r[0]}>")
                    notified_reserves.add(reserve_id + "_before")

            if dt <= now < dt + timedelta(minutes=1):
                if reserve_id + "_start" not in notified_reserves:
                    await ch.send(f"⏰ 面接開始 <@{r[0]}>")
                    notified_reserves.add(reserve_id + "_start")

# ================= 起動 =================

@bot.event
async def on_ready():
    print(f"起動完了: {bot.user}")
    await bot.change_presence(activity=discord.Game(name="面接管理中"))
    reminder_loop.start()  # ← 忘れがち🔥

# ================= コマンド =================

@bot.command()
@commands.has_role(ADMIN_ROLE_NAME)
async def panel(ctx):
    await ctx.send("面接管理パネル", view=MainPanel())

@bot.command()
@commands.has_role(ADMIN_ROLE_NAME)
async def setnotify(ctx, channel: discord.TextChannel):
    set_notify_channel(ctx.guild.id, str(channel.id))
    await ctx.send(f"✅ 通知チャンネルを {channel.mention} に設定しました")

# 🔥 追加コマンド

@bot.command()
@commands.has_role(ADMIN_ROLE_NAME)
async def ログ設定(ctx):
    set_channel(ctx.guild.id, "log_channel", ctx.channel.id)
    await ctx.send("✅ このチャンネルを【運営ログ用】に設定しました")

@bot.command()
@commands.has_role(ADMIN_ROLE_NAME)
async def 面接通知設定(ctx):
    set_channel(ctx.guild.id, "interview_channel", ctx.channel.id)
    await ctx.send("✅ このチャンネルを【面接通知用】に設定しました")

# ================= 起動 =================

import os
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)