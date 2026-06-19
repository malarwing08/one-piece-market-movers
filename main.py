import os
import requests
import discord
from discord.ext import commands

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
JUSTTCG_API_KEY = os.environ["JUSTTCG_API_KEY"]

BASE_URL = "https://api.justtcg.com/v1/cards"
GAME_NAME = "One Piece Card Game"
LIMIT = 20

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# -----------------------
# API HELPERS
# -----------------------

def fetch_cards(search=None):
    headers = {"x-api-key": JUSTTCG_API_KEY}

    params = {
        "game": GAME_NAME,
        "limit": LIMIT,
        "priceHistoryDuration": "30d"
    }

    if search:
        params["q"] = search

    r = requests.get(BASE_URL, headers=headers, params=params, timeout=30)
    r.raise_for_status()

    return r.json().get("data", [])


def get_price(card):
    for v in card.get("variants", []):
        price = v.get("marketPrice") or v.get("price") or v.get("latestPrice")
        if price:
            return float(price)
    return None


def get_image(card):
    return (
        card.get("image")
        or card.get("imageUrl")
        or card.get("image_url")
        or card.get("img")
        or None
    )


def get_set(card):
    return (
        card.get("set")
        or card.get("setName")
        or card.get("set_name")
        or "Unknown Set"
    )


def get_rarity(card):
    return (
        card.get("rarity")
        or card.get("cardType")
        or "Unknown Rarity"
    )


async def send_card_results(ctx, title, cards):
    if not cards:
        await ctx.send("No cards found.")
        return

    await ctx.send(f"**{title}**")

    for card in cards[:10]:
        price = get_price(card)
        image = get_image(card)

        embed = discord.Embed(
            title=card.get("name", "Unknown Card"),
            description=(
                f"**Set:** {get_set(card)}\n"
                f"**Rarity:** {get_rarity(card)}\n"
                f"**Market Price:** ${price:.2f}" if price else
                f"**Set:** {get_set(card)}\n"
                f"**Rarity:** {get_rarity(card)}\n"
                f"**Market Price:** Not found"
            )
        )

        if image:
            embed.set_image(url=image)

        await ctx.send(embed=embed)


async def search_and_send(ctx, search_term, title=None):
    try:
        cards = fetch_cards(search_term)
        await send_card_results(ctx, title or f"Search: {search_term}", cards)
    except Exception as e:
        await ctx.send(f"Bot error: {e}")


# -----------------------
# BASIC COMMANDS
# -----------------------

@bot.event
async def on_ready():
    print(f"nami is online as {bot.user}")


@bot.command()
async def helpme(ctx):
    await ctx.send(
        "**Nami Commands**\n\n"
        "**Sets:** `!op01` through `!op16`\n"
        "**Extra Boosters:** `!eb01` `!eb02` `!eb03`\n"
        "**PRB:** `!prb01` `!prb02`\n"
        "**Markets:** `!sp` `!manga` `!alt`\n"
        "**Search:** type any character like `!perona`, `!nami`, `!zoro`\n"
        "**Exact search:** `!card perona`"
    )


@bot.command()
async def card(ctx, *, name):
    await search_and_send(ctx, name, f"🏴‍☠️ Card Search: {name}")


# -----------------------
# MARKET COMMANDS
# -----------------------

@bot.command()
async def sp(ctx):
    await search_and_send(ctx, "SP", "✨ SP Market")


@bot.command()
async def manga(ctx):
    await search_and_send(ctx, "manga", "🔥 Manga Rare Market")


@bot.command()
async def alt(ctx):
    await search_and_send(ctx, "alternate art", "🎨 Alt Art Market")


# -----------------------
# SET COMMANDS
# -----------------------

async def set_command(ctx, set_code):
    await search_and_send(ctx, set_code.upper(), f"📦 {set_code.upper()} Market")


for i in range(1, 17):
    code = f"op{i:02d}"

    async def command_func(ctx, code=code):
        await set_command(ctx, code)

    bot.command(name=code)(command_func)


for code in ["eb01", "eb02", "eb03", "prb01", "prb02"]:
    async def command_func(ctx, code=code):
        await set_command(ctx, code)

    bot.command(name=code)(command_func)


# -----------------------
# CHARACTER SEARCH
# Allows !perona, !nami, !zoro, etc.
# -----------------------

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.content.startswith("!"):
        return

    command_text = message.content[1:].strip()

    known_commands = [
        "helpme", "card", "sp", "manga", "alt",
        *[f"op{i:02d}" for i in range(1, 17)],
        "eb01", "eb02", "eb03",
        "prb01", "prb02"
    ]

    first_word = command_text.split()[0].lower()

    if first_word in known_commands:
        await bot.process_commands(message)
        return

    ctx = await bot.get_context(message)
    await search_and_send(ctx, command_text, f"🔎 Character Search: {command_text}")


bot.run(DISCORD_BOT_TOKEN)
