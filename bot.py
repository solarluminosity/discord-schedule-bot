import os
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
MESSAGE_ID = int(os.getenv("MESSAGE_ID", "0"))

MSK = ZoneInfo("Europe/Moscow")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def to_unix(dt: datetime) -> int:
    return int(dt.timestamp())


def next_daily_occurrence(now_msk: datetime, hour: int, minute: int) -> datetime:
    candidate = datetime.combine(now_msk.date(), time(hour, minute), tzinfo=MSK)
    if candidate <= now_msk:
        candidate += timedelta(days=1)
    return candidate


def next_weekday_occurrence(now_msk: datetime, weekday: int, hour: int, minute: int) -> datetime:
    days_ahead = (weekday - now_msk.weekday()) % 7
    candidate_date = now_msk.date() + timedelta(days=days_ahead)
    candidate = datetime.combine(candidate_date, time(hour, minute), tzinfo=MSK)

    if candidate <= now_msk:
        candidate += timedelta(days=7)

    return candidate


def build_schedule_text() -> str:
    now_msk = datetime.now(MSK)

    guild_party_start = next_daily_occurrence(now_msk, 21, 0)
    guild_party_end = guild_party_start + timedelta(minutes=30)

    arena_mon_start = next_weekday_occurrence(now_msk, 0, 21, 0)
    arena_mon_end = arena_mon_start + timedelta(hours=1)

    arena_tue_start = next_weekday_occurrence(now_msk, 1, 21, 0)
    arena_tue_end = arena_tue_start + timedelta(hours=1)

    ba_wed_start = next_weekday_occurrence(now_msk, 2, 20, 0)
    ba_wed_end = ba_wed_start + timedelta(hours=2)

    ba_fri_start = next_weekday_occurrence(now_msk, 4, 20, 0)
    ba_fri_end = ba_fri_start + timedelta(hours=2)

    text = (
        "## ✦ Расписание\n\n"
        "✧ **Гильд пати**\n"
        f"ежедневно • 21:00–21:30 МСК\n"
        f"(<t:{to_unix(guild_party_start)}:t>–<t:{to_unix(guild_party_end)}:t>)\n\n"

        "✧ **Арена**\n"
        f"понедельник • 21:00–22:00 МСК\n"
        f"(<t:{to_unix(arena_mon_start)}:t>–<t:{to_unix(arena_mon_end)}:t>)\n"
        f"вторник • 21:00–22:00 МСК\n"
        f"(<t:{to_unix(arena_tue_start)}:t>–<t:{to_unix(arena_tue_end)}:t>)\n\n"

        "✧ **Брейкинг арми**\n"
        f"среда • 20:00–22:00 МСК\n"
        f"(<t:{to_unix(ba_wed_start)}:t>–<t:{to_unix(ba_wed_end)}:t>)\n"
        f"пятница • 20:00–22:00 МСК\n"
        f"(<t:{to_unix(ba_fri_start)}:t>–<t:{to_unix(ba_fri_end)}:t>)\n\n"

        "_Время автоматически отображается в вашем часовом поясе_"
    )

    return text


async def get_or_create_message(channel: discord.TextChannel) -> discord.Message:
    global MESSAGE_ID

    if MESSAGE_ID != 0:
        try:
            return await channel.fetch_message(MESSAGE_ID)
        except discord.NotFound:
            pass

    msg = await channel.send(build_schedule_text())
    MESSAGE_ID = msg.id
    print(f"NEW_MESSAGE_ID={MESSAGE_ID}")
    return msg


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    if not update_schedule.is_running():
        update_schedule.start()


@tasks.loop(minutes=10)
async def update_schedule():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await bot.fetch_channel(CHANNEL_ID)

    if not isinstance(channel, discord.TextChannel):
        print("CHANNEL_ID does not point to a text channel.")
        return

    msg = await get_or_create_message(channel)
    new_text = build_schedule_text()

    if msg.content != new_text:
        await msg.edit(content=new_text)
        print("Schedule updated.")


@update_schedule.before_loop
async def before_update():
    await bot.wait_until_ready()


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

if CHANNEL_ID == 0:
    raise RuntimeError("CHANNEL_ID is not set")

bot.run(TOKEN)
