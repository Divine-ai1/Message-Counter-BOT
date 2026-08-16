import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os

# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("TOKEN") or "PASTE_YOUR_BOT_TOKEN_HERE"

# PUT YOUR #GENERAL CHANNEL ID HERE
GENERAL_CHANNEL_ID = 1485624474278690826

ARROW = "<a:vistoarrow:1537111766989799604>"

DB_FILE = "messages.db"


# =========================================================
# DATABASE
# =========================================================

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
        """
        SELECT count
        FROM messages
        WHERE guild_id = ? AND user_id = ?
        """,
        (str(guild_id), str(user_id))
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    return 0


def set_count(guild_id, user_id, amount):
    amount = max(0, int(amount))

    cursor.execute(
        """
        INSERT INTO messages (guild_id, user_id, count)
        VALUES (?, ?, ?)
        ON CONFLICT(guild_id, user_id)
        DO UPDATE SET count = excluded.count
        """,
        (str(guild_id), str(user_id), amount)
    )

    db.commit()


def add_message(guild_id, user_id):
    cursor.execute(
        """
        INSERT INTO messages (guild_id, user_id, count)
        VALUES (?, ?, 1)
        ON CONFLICT(guild_id, user_id)
        DO UPDATE SET count = count + 1
        """,
        (str(guild_id), str(user_id))
    )

    db.commit()


def add_count(guild_id, user_id, amount):
    current = get_count(guild_id, user_id)
    set_count(guild_id, user_id, current + amount)


def remove_count(guild_id, user_id, amount):
    current = get_count(guild_id, user_id)
    set_count(guild_id, user_id, max(0, current - amount))


# =========================================================
# BOT SETUP
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="-",
    intents=intents
)


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Slash sync error: {e}")

    print(f"Logged in as {bot.user}")
    print("Message Counter Bot is online!")


# =========================================================
# MESSAGE COUNTER
# =========================================================

@bot.event
async def on_message(message):

    # Ignore bots
    if message.author.bot:
        return

    # Count ONLY messages in the configured General channel
    if (
        message.guild is not None
        and message.channel.id == GENERAL_CHANNEL_ID
    ):
        add_message(
            message.guild.id,
            message.author.id
        )

    # Process prefix commands once
    await bot.process_commands(message)


# =========================================================
# EMBED HELPER
# =========================================================

def counter_embed(user, count, title="Message Counter"):

    embed = discord.Embed(
        title=title,
        description=(
            f"{ARROW} **User:** {user.mention}\n"
            f"{ARROW} **Messages:** `{count}`"
        ),
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=user.display_avatar.url
    )

    return embed


# =========================================================
# -m
# =========================================================

@bot.command(name="m")
async def m_command(ctx):

    if ctx.guild is None:
        return

    count = get_count(
        ctx.guild.id,
        ctx.author.id
    )

    await ctx.send(
        embed=counter_embed(
            ctx.author,
            count
        )
    )


# =========================================================
# -reset @user
# =========================================================

@bot.command(name="reset")
@commands.has_permissions(manage_guild=True)
async def reset_command(ctx, member: discord.Member):

    set_count(
        ctx.guild.id,
        member.id,
        0
    )

    embed = discord.Embed(
        title="Messages Reset",
        description=(
            f"{ARROW} {member.mention}'s message count has been reset to `0`."
        ),
        color=discord.Color.red()
    )

    await ctx.send(embed=embed)


# =========================================================
# -add @user amount
# =========================================================

@bot.command(name="add")
@commands.has_permissions(manage_guild=True)
async def add_command(ctx, member: discord.Member, amount: int):

    if amount <= 0:
        await ctx.send("Amount must be greater than `0`.")
        return

    add_count(
        ctx.guild.id,
        member.id,
        amount
    )

    new_count = get_count(
        ctx.guild.id,
        member.id
    )

    embed = discord.Embed(
        title="Messages Added",
        description=(
            f"{ARROW} Added `{amount}` messages to {member.mention}.\n"
            f"{ARROW} **New Count:** `{new_count}`"
        ),
        color=discord.Color.green()
    )

    await ctx.send(embed=embed)


# =========================================================
# -remove @user amount
# =========================================================

@bot.command(name="remove")
@commands.has_permissions(manage_guild=True)
async def remove_command(ctx, member: discord.Member, amount: int):

    if amount <= 0:
        await ctx.send("Amount must be greater than `0`.")
        return

    remove_count(
        ctx.guild.id,
        member.id,
        amount
    )

    new_count = get_count(
        ctx.guild.id,
        member.id
    )

    embed = discord.Embed(
        title="Messages Removed",
        description=(
            f"{ARROW} Removed `{amount}` messages from {member.mention}.\n"
            f"{ARROW} **New Count:** `{new_count}`"
        ),
        color=discord.Color.orange()
    )

    await ctx.send(embed=embed)


# =========================================================
# /messages
# =========================================================

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

    await interaction.response.send_message(
        embed=counter_embed(
            interaction.user,
            count
        )
    )


# =========================================================
# /dm @user
# =========================================================

@bot.tree.command(
    name="dm",
    description="DM a user's current message count"
)
@app_commands.describe(
    user="The user to DM"
)
async def dm_command(
    interaction: discord.Interaction,
    user: discord.Member
):

    if interaction.guild is None:
        await interaction.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True
        )
        return

    # Get count
    count = get_count(
        interaction.guild.id,
        user.id
    )

    embed = counter_embed(
        user,
        count,
        title="Your Message Count"
    )

    try:

        await user.send(embed=embed)

        await interaction.response.send_message(
            f"{ARROW} Successfully DMed {user.mention} their message count.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            f"{ARROW} I couldn't DM {user.mention}. Their DMs may be closed.",
            ephemeral=True
        )

    except discord.HTTPException:

        await interaction.response.send_message(
            f"{ARROW} Discord couldn't deliver the DM.",
            ephemeral=True
        )


# =========================================================
# ERROR HANDLING
# =========================================================

@reset_command.error
async def reset_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            f"{ARROW} You need **Manage Server** permission to use this."
        )

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"{ARROW} Usage: `-reset @user`"
        )

    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(
            f"{ARROW} I couldn't find that member."
        )


@add_command.error
async def add_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            f"{ARROW} You need **Manage Server** permission to use this."
        )

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"{ARROW} Usage: `-add @user amount`"
        )

    elif isinstance(error, commands.BadArgument):
        await ctx.send(
            f"{ARROW} Usage: `-add @user amount`"
        )


@remove_command.error
async def remove_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            f"{ARROW} You need **Manage Server** permission to use this."
        )

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"{ARROW} Usage: `-remove @user amount`"
        )

    elif isinstance(error, commands.BadArgument):
        await ctx.send(
            f"{ARROW} Usage: `-remove @user amount`"
        )


# =========================================================
# START
# =========================================================

bot.run(TOKEN)
