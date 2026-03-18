from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import discord
from config import NOTICE_CHANNEL_ID, NOTICE_BEFORE_MINUTES

scheduler = AsyncIOScheduler()


def schedule_notifications(bot, user_name, date_str, time_str):
    interview_time = datetime.strptime(
        f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
    )

    before_time = interview_time - timedelta(minutes=NOTICE_BEFORE_MINUTES)

    async def notify_before():
        channel = bot.get_channel(NOTICE_CHANNEL_ID)
        await channel.send(
            f"🔔【面接予告】{user_name} さんの面接が {NOTICE_BEFORE_MINUTES} 分後に開始されます！"
        )

    async def notify_start():
        channel = bot.get_channel(NOTICE_CHANNEL_ID)
        await channel.send(
            f"🎮【面接開始】{user_name} さんの面接開始時刻です！"
        )

    scheduler.add_job(notify_before, "date", run_date=before_time)
    scheduler.add_job(notify_start, "date", run_date=interview_time)