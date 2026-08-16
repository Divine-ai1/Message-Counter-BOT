import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# =========================
# CONFIG
# =========================

TOKEN = os.getenv("TOKEN") or "PASTE_YOUR_BOT_TOKEN_HERE"

# Change this if your channel is named something other than "general"
GENERAL_CHANNEL_ID = 1485624474278690826

PREFIX = "-"

ARROW = "<a:vistoarrow:1537111766989799604>"

DATA_FILE = "messages.json"


# =========================
# BOT SETUP
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents
)


# =========================
# DATABASE
# =========================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


message_counts = load_data()


def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(message_counts, f, indent=4)


def get_count(guild_id, user_id):
    guild_id = str(guild_id)
    user_id = str(user_id)

    if guild_id not in message_counts:
        message_counts[guild_id] = {}

    return message_counts[guild_id].get(user_id, 0)


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

    # Only count messages in #general
    if message.guild and message.channel.id == GENERAL_CHANNEL_ID:

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)

        if guild_id not in message_counts:
            message_counts[guild_id] = {}

        if user_id not in message_counts[guild_id]:
            message_counts[guild_id][user_id] = 0

        message_counts[guild_id][user_id] += 1

        save_data()

    # Make sure prefix commands still work
    await bot.process_commands(message)


# =========================
# -m COMMAND
# =========================

@bot.command(name="m")
async def message_count(ctx):

    # Only allow command in a server
    if not ctx.guild:
        return

    count = get_count(ctx.guild.id, ctx.author.id)

    embed = discord.Embed(
        title="Message Counter",
        description=(
            f"{ARROW} **User:** {ctx.author.mention}\n"
            f"{ARROW} **Messages in #general:** `{count}`"
        ),
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)


# =========================
# /messages COMMAND
# =========================

@bot.tree.command(
    name="messages",
    description="Check your messages sent in #general"
)
async def messages(interaction: discord.Interaction):

    if not interaction.guild:
        await interaction.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True
        )
        return

    count = get_count(interaction.guild.id, interaction.user.id)

    embed = discord.Embed(
        title="Message Counter",
        description=(
            f"{ARROW} **User:** {interaction.user.mention}\n"
            f"{ARROW} **Messages in #general:** `{count}`"
        ),
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)


# =========================
# START BOT
# =========================

if __name__ == "__main__":
    bot.run(TOKEN)
