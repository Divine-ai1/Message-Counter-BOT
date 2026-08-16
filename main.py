import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("TOKEN") or "PASTE_YOUR_BOT_TOKEN_HERE"

# PUT YOUR #GENERAL CHANNEL ID HERE
GENERAL_CHANNEL_ID = 1485624474278690826

ARROW = "<a:vistoarrow:1537111766989799604>"

DB_FILE = "messages.db"


# =========================
# DATABASE
# =========================

db = sqlite3.connect(DB_FILE)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
)
""")

db.commit()


def get_count(guild_id, user_id):
    cursor.execute(
        "SELECT count FROM messages WHERE guild_id = ? AND user_id = ?",
        (str(guild_id), str(user_id))
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return 0


def add_message(guild_id, user_id):
    cursor.execute("""
        INSERT INTO messages (guild_id, user_id, count)
        VALUES (?, ?, 1)
        ON CONFLICT(guild_id, user_id)
        DO UPDATE SET count = count + 1
    """, (str(guild_id), str(user_id)))

    db.commit()


# =========================
# BOT
# =========================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="-",
    intents=intents
)


# =========================
# READY
# =========================

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Slash sync error: {e}")

    print(f"Logged in as {bot.user}")
    print("Message Counter Bot is online!")


# =========================
# MESSAGE COUNTER
# =========================

@bot.event
async def on_message(message):

    # Ignore bots
    if message.author.bot:
        return

    # Only count messages in the specified channel
    if (
        message.guild is not None
        and message.channel.id == GENERAL_CHANNEL_ID
    ):
        add_message(
            message.guild.id,
            message.author.id
        )

    # Process prefix commands ONCE
    await bot.process_commands(message)


# =========================
# -m
# =========================

@bot.command(name="m")
async def m_command(ctx):

    if ctx.guild is None:
        return

    count = get_count(
        ctx.guild.id,
        ctx.author.id
    )

    embed = discord.Embed(
        title="Message Counter",
        description=(
            f"{ARROW} **User:** {ctx.author.mention}\n"
            f"{ARROW} **Messages:** `{count}`"
        ),
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=ctx.author.display_avatar.url
    )

    await ctx.send(embed=embed)


# =========================
# /messages
# =========================

@bot.tree.command(
    name="messages",
    description="Check your messages in General"
)
async def messages(interaction: discord.Interaction):

    if interaction.guild is None:
        await interaction.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True
        )
        return

    count = get_count(
        interaction.guild.id,
        interaction.user.id
    )

    embed = discord.Embed(
        title="Message Counter",
        description=(
            f"{ARROW} **User:** {interaction.user.mention}\n"
            f"{ARROW} **Messages:** `{count}`"
        ),
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=interaction.user.display_avatar.url
    )

    await interaction.response.send_message(embed=embed)


# =========================
# START
# =========================

bot.run(TOKEN)
