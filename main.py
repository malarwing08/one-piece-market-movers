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
    "op12": "Legacy of the Master",
    "op13": "Carrying on His Will",
    "op14": "The Azure Sea's Seven",
    "op15": "Adventure on Kami's Island",
    "op16": "The Time of Battle",
    "eb01": "Memorial Collection",
    "eb02": "Anime 25th Collection",
    "eb03": "One Piece Heroines Edition",
    "prb01": "One Piece Card The Best",
    "prb02": "One Piece Card The Best Vol.2",
}

def fetch_cards(search=None, page=1, set_name=None):
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

    if set_name:
        params["set"] = set_name

    r = requests.get(BASE_URL, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])

def get_price(card):
    prices = []

    for key in ["marketPrice", "tcgplayerMarketPrice", "price", "latestPrice"]:
        if card.get(key):
            try:
                prices.append(float(card[key]))
            except:
                pass

    for v in card.get("variants", []):
        for key in ["marketPrice", "tcgplayerMarketPrice", "price", "latestPrice"]:
            if v.get(key):
                try:
                    prices.append(float(v[key]))
                except:
                    pass

    return max(prices) if prices else None

def find_image_url(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str):
                lower = value.lower()
                if value.startswith("http") and (
                    "image" in key.lower()
                    or "img" in key.lower()
                    or ".jpg" in lower
                    or ".png" in lower
                    or ".webp" in lower
                ):
                    return value

            found = find_image_url(value)
            if found:
                return found

    if isinstance(obj, list):
        for item in obj:
            found = find_image_url(item)
            if found:
                return found

    return None

def get_image(card):
    return find_image_url(card)

def get_set(card):
    return card.get("set") or card.get("setName") or "Unknown Set"

def get_rarity(card):
    return card.get("rarity") or card.get("type") or "Unknown Rarity"

def get_number(card):
    return card.get("number") or card.get("cardNumber") or "Unknown Number"

def sort_by_price(cards):
    return sorted(cards, key=lambda c: get_price(c) or 0, reverse=True)

class CardPaginator(discord.ui.View):
    def __init__(self, search_term, title, cards, page=1, set_name=None):
        super().__init__(timeout=300)
        self.search_term = search_term
        self.title = title
        self.cards = sort_by_price(cards)
        self.page = page
        self.index = 0
        self.set_name = set_name

    def build_embed(self):
        card = self.cards[self.index]
        price = get_price(card)
        image = get_image(card)

        embed = discord.Embed(
            title=card.get("name", "Unknown Card"),
            description=(
                f"**Market:** {self.title}\n"
                f"**Set:** {get_set(card)}\n"
                f"**Number:** {get_number(card)}\n"
                f"**Rarity:** {get_rarity(card)}\n"
                f"**Price:** ${price:.2f}" if price else
                f"**Market:** {self.title}\n"
                f"**Set:** {get_set(card)}\n"
                f"**Number:** {get_number(card)}\n"
                f"**Rarity:** {get_rarity(card)}\n"
                f"**Price:** Not found"
            ),
            color=discord.Color.orange()
        )

        if image:
            embed.set_image(url=image)

        embed.set_footer(
            text=f"Card {self.index + 1}/{len(self.cards)} • Page {self.page} • Highest price first"
        )

        return embed

    async def update_msg(self, interaction):
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction, button):
        self.index = (self.index - 1) % len(self.cards)
        await self.update_msg(interaction)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction, button):
        self.index = (self.index + 1) % len(self.cards)
        await self.update_msg(interaction)

    @discord.ui.button(label="⏭️ Next 20", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction, button):
        self.page += 1

        cards = fetch_cards(
            search=self.search_term,
            page=self.page,
            set_name=self.set_name
        )

        if not cards:
            self.page -= 1
            await interaction.response.send_message("No more cards found.", ephemeral=True)
            return

        self.cards = sort_by_price(cards)
        self.index = 0
        await self.update_msg(interaction)

async def send_cards(ctx, title, search=None, set_name=None):
    try:
        cards = fetch_cards(search=search, page=1, set_name=set_name)

        if not cards:
            await ctx.send("No cards found.")
            return

        view = CardPaginator(search, title, cards, page=1, set_name=set_name)
        await ctx.send(embed=view.build_embed(), view=view)

    except Exception as e:
        await ctx.send(f"Bot error: {e}")

@bot.event
async def on_ready():
    print(f"nami is online as {bot.user}")

@bot.command()
async def helpme(ctx):
    await ctx.send(
        "**Nami Commands**\n\n"
        "`!op01` through `!op16`\n"
        "`!eb01` `!eb02` `!eb03`\n"
        "`!prb01` `!prb02`\n"
        "`!sp` `!manga` `!alt`\n"
        "`!perona` `!nami` `!zoro`\n"
        "`!card perona`\n\n"
        "Set commands now use the actual set filter, not random OP text."
    )

@bot.command()
async def card(ctx, *, name):
    await send_cards(ctx, f"Character/Card Search: {name}", search=name)

@bot.command()
async def sp(ctx):
    await send_cards(ctx, "SP Market", search="SP")

@bot.command()
async def manga(ctx):
    await send_cards(ctx, "Manga Rare Market", search="Manga")

@bot.command()
async def alt(ctx):
    await send_cards(ctx, "Alternate Art Market", search="Alternate Art")

async def set_command(ctx, code):
    set_name = SET_SEARCHES[code.lower()]
    await send_cards(ctx, f"{code.upper()} - {set_name}", set_name=set_name)

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

    command_text = message.content[1:].strip()
    if not command_text:
        return

    first_word = command_text.split()[0].lower()

    known = ["helpme", "card", "sp", "manga", "alt", *SET_SEARCHES.keys()]

    if first_word in known:
        await bot.process_commands(message)
    else:
        ctx = await bot.get_context(message)
        await send_cards(ctx, f"Character Search: {command_text}", search=command_text)

bot.run(DISCORD_BOT_TOKEN)
