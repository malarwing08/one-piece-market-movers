import os
import time
import requests
import discord
from discord.ext import commands

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
JUSTTCG_API_KEY = os.environ["JUSTTCG_API_KEY"]

BASE_URL = "https://api.justtcg.com/v1/cards"
GAME_NAME = "One Piece Card Game"

LIMIT = 20
MAX_PAGES_TO_SCAN = 3
API_DELAY = 1.2
CACHE_SECONDS = 600

cache = {}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

SET_SEARCHES = {
    "op01": "Romance Dawn",
    "op02": "Paramount War",
    "op03": "Pillars of Strength",
    "op04": "Kingdoms of Intrigue",
    "op05": "Awakening of the New Era",
    "op06": "Wings of the Captain",
    "op07": "500 Years in the Future",
    "op08": "Two Legends",
    "op09": "Emperors in the New World",
    "op10": "Royal Blood",
    "op11": "A Fist of Divine Speed",
    "eb01": "Memorial Collection",
    "eb02": "Anime 25th Collection",
    "prb01": "One Piece Card The Best",
}

def fetch_page(search=None, page=1):
    headers = {"x-api-key": JUSTTCG_API_KEY}

    params = {
        "game": GAME_NAME,
        "limit": LIMIT,
        "page": page,
        "orderBy": "price",
        "order": "desc",
    }

    if search:
        params["q"] = search

    r = requests.get(BASE_URL, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])

def get_price(card):
    prices = []
    keys = [
        "marketPrice",
        "tcgplayerMarketPrice",
        "price",
        "latestPrice",
        "lowPrice",
        "midPrice",
        "highPrice",
    ]

    for key in keys:
        try:
            if card.get(key):
                prices.append(float(card.get(key)))
        except:
            pass

    for variant in card.get("variants", []):
        for key in keys:
            try:
                if variant.get(key):
                    prices.append(float(variant.get(key)))
            except:
                pass

    return max(prices) if prices else None

def get_image(card):
    keys = [
        "image",
        "imageUrl",
        "image_url",
        "imageSmall",
        "imageLarge",
        "cardImage",
        "cardImageUrl",
        "tcgplayerImageUrl",
        "img",
        "photo",
        "picture",
    ]

    for key in keys:
        if card.get(key):
            return card.get(key)

    for variant in card.get("variants", []):
        for key in keys:
            if variant.get(key):
                return variant.get(key)

    def deep_find(obj):
        if isinstance(obj, dict):
            for _, value in obj.items():
                if isinstance(value, str):
                    lower = value.lower()
                    if value.startswith("http") and (
                        ".jpg" in lower
                        or ".jpeg" in lower
                        or ".png" in lower
                        or ".webp" in lower
                    ):
                        return value

                found = deep_find(value)
                if found:
                    return found

        if isinstance(obj, list):
            for item in obj:
                found = deep_find(item)
                if found:
                    return found

        return None

    return deep_find(card)

def get_set(card):
    return str(
        card.get("set")
        or card.get("setName")
        or card.get("set_name")
        or card.get("setCode")
        or ""
    )

def get_number(card):
    return str(
        card.get("number")
        or card.get("cardNumber")
        or card.get("collectorNumber")
        or ""
    )

def get_rarity(card):
    return str(
        card.get("rarity")
        or card.get("type")
        or card.get("cardType")
        or ""
    )

def card_key(card):
    return str(
        card.get("id")
        or card.get("tcgplayerProductId")
        or card.get("productId")
        or f"{card.get('name')}-{get_set(card)}-{get_number(card)}"
    )

def is_set_match(card, set_name):
    return set_name.lower() in get_set(card).lower()

def scan_cards(search=None, exact_set=None):
    cache_key = f"{search}|{exact_set}"

    now = time.time()

    if cache_key in cache:
        cached_time, cached_cards = cache[cache_key]
        if now - cached_time < CACHE_SECONDS:
            return cached_cards

    found = {}

    for page in range(1, MAX_PAGES_TO_SCAN + 1):
        cards = fetch_page(search=search, page=page)

        if not cards:
            break

        for card in cards:
            if exact_set and not is_set_match(card, exact_set):
                continue

            if get_price(card) is None:
                continue

            found[card_key(card)] = card

        time.sleep(API_DELAY)

    sorted_cards = sorted(
        found.values(),
        key=lambda c: get_price(c) or 0,
        reverse=True
    )

    cache[cache_key] = (now, sorted_cards)

    return sorted_cards

class CardPaginator(discord.ui.View):
    def __init__(self, title, cards):
        super().__init__(timeout=300)
        self.title = title
        self.cards = cards
        self.index = 0

    def build_embed(self):
        card = self.cards[self.index]
        price = get_price(card)
        image = get_image(card)

        embed = discord.Embed(
            title=card.get("name", "Unknown Card"),
            description=(
                f"**Market:** {self.title}\n"
                f"**Set:** {get_set(card) or 'Unknown Set'}\n"
                f"**Number:** {get_number(card) or 'Unknown Number'}\n"
                f"**Rarity:** {get_rarity(card) or 'Unknown Rarity'}\n"
                f"**Price:** ${price:.2f}"
            ),
            color=discord.Color.orange()
        )

        if image:
            embed.set_image(url=image)

        embed.set_footer(
            text=f"Card {self.index + 1}/{len(self.cards)} • Highest price first"
        )

        return embed

    async def update_msg(self, interaction):
        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction, button):
        self.index = (self.index - 1) % len(self.cards)
        await self.update_msg(interaction)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction, button):
        self.index = (self.index + 1) % len(self.cards)
        await self.update_msg(interaction)

async def send_cards(ctx, title, search=None, exact_set=None):
    try:
        loading = await ctx.send("🔎 Scanning cards and sorting by price...")

        cards = scan_cards(search=search, exact_set=exact_set)

        if not cards:
            await loading.edit(content="No cards found.")
            return

        view = CardPaginator(title, cards)

        await loading.edit(
            content="",
            embed=view.build_embed(),
            view=view
        )

    except Exception as e:
        await ctx.send(f"Bot error: {e}")

@bot.event
async def on_ready():
    print(f"nami is online as {bot.user}")

@bot.command()
async def helpme(ctx):
    await ctx.send(
        "**Nami Commands**\n\n"
        "`!op01` through `!op11`\n"
        "`!eb01` `!eb02` `!prb01`\n"
        "`!sp` `!manga` `!alt`\n"
        "`!zoro` `!nami` `!perona`\n"
        "`!card zoro`\n\n"
        "Nami scans multiple pages, avoids rate limits, and sorts highest price first."
    )

@bot.command()
async def card(ctx, *, name):
    await send_cards(ctx, f"Search: {name}", search=name)

@bot.command()
async def sp(ctx):
    await send_cards(ctx, "SP Market", search="SP")

@bot.command()
async def manga(ctx):
    await send_cards(ctx, "Manga Market", search="Manga")

@bot.command()
async def alt(ctx):
    await send_cards(ctx, "Alt Art Market", search="Alternate Art")

async def set_command(ctx, code):
    set_name = SET_SEARCHES[code.lower()]
    await send_cards(
        ctx,
        f"{code.upper()} - {set_name}",
        search=set_name,
        exact_set=set_name
    )

for code in SET_SEARCHES:
    async def command_func(ctx, code=code):
        await set_command(ctx, code)

    bot.command(name=code)(command_func)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.content.startswith("!"):
        return

    text = message.content[1:].strip()

    if not text:
        return

    first_word = text.split()[0].lower()

    known = [
        "helpme",
        "card",
        "sp",
        "manga",
        "alt",
        *SET_SEARCHES.keys()
    ]

    if first_word in known:
        await bot.process_commands(message)
    else:
        ctx = await bot.get_context(message)
        await send_cards(ctx, f"Character Search: {text}", search=text)

bot.run(DISCORD_BOT_TOKEN)
