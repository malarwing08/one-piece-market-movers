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
# API
# -----------------------

def fetch_cards(search=None, page=1):
    headers = {"x-api-key": JUSTTCG_API_KEY}

    params = {
        "game": GAME_NAME,
        "limit": LIMIT,
        "page": page,
        "priceHistoryDuration": "30d"
    }

    if search:
        params["q"] = search

    response = requests.get(
        BASE_URL,
        headers=headers,
        params=params,
        timeout=30
    )

    response.raise_for_status()
    data = response.json()

    return data.get("data", [])


def get_price(card):
    prices = []

    for v in card.get("variants", []):
        price = (
            v.get("marketPrice")
            or v.get("price")
            or v.get("latestPrice")
            or v.get("tcgplayerMarketPrice")
        )

        try:
            if price:
                prices.append(float(price))
        except:
            pass

    if prices:
        return max(prices)

    return None


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
        "img"
    ]

    for key in keys:
        if card.get(key):
            return card.get(key)

    for v in card.get("variants", []):
        for key in keys:
            if v.get(key):
                return v.get(key)

    return None


def get_set(card):
    return (
        card.get("set")
        or card.get("setName")
        or card.get("set_name")
        or card.get("setCode")
        or "Unknown Set"
    )


def get_rarity(card):
    return (
        card.get("rarity")
        or card.get("cardType")
        or card.get("type")
        or "Unknown Rarity"
    )


def get_card_number(card):
    return (
        card.get("number")
        or card.get("cardNumber")
        or card.get("collectorNumber")
        or "Unknown Number"
    )


def sort_by_price(cards):
    return sorted(
        cards,
        key=lambda c: get_price(c) or 0,
        reverse=True
    )


# -----------------------
# PAGINATOR
# -----------------------

class CardPaginator(discord.ui.View):
    def __init__(self, ctx, search_term, title, cards, page=1):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.search_term = search_term
        self.title = title
        self.cards = sort_by_price(cards)
        self.index = 0
        self.page = page

    def build_embed(self):
        card = self.cards[self.index]
        price = get_price(card)
        image = get_image(card)

        embed = discord.Embed(
            title=card.get("name", "Unknown Card"),
            description=(
                f"**Market:** {self.title}\n"
                f"**Set:** {get_set(card)}\n"
                f"**Number:** {get_card_number(card)}\n"
                f"**Rarity:** {get_rarity(card)}\n"
                f"**Price:** ${price:.2f}" if price else
                f"**Market:** {self.title}\n"
                f"**Set:** {get_set(card)}\n"
                f"**Number:** {get_card_number(card)}\n"
                f"**Rarity:** {get_rarity(card)}\n"
                f"**Price:** Not found"
            ),
            color=discord.Color.orange()
        )

        embed.set_footer(
            text=f"Card {self.index + 1}/{len(self.cards)} • Page {self.page}"
        )

        if image:
            embed.set_image(url=image)

        return embed

    async def update_message(self, interaction):
        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self
        )

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
        else:
            self.index = len(self.cards) - 1

        await self.update_message(interaction)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.cards) - 1:
            self.index += 1
        else:
            self.index = 0

        await self.update_message(interaction)

    @discord.ui.button(label="⏭️ Next 20", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1

        try:
            new_cards = fetch_cards(self.search_term, self.page)
            new_cards = sort_by_price(new_cards)

            if not new_cards:
                self.page -= 1
                await interaction.response.send_message(
                    "No more cards found.",
                    ephemeral=True
                )
                return

            self.cards = new_cards
            self.index = 0

            await interaction.response.edit_message(
                embed=self.build_embed(),
                view=self
            )

        except Exception as e:
            await interaction.response.send_message(
                f"Bot error: {e}",
                ephemeral=True
            )


# -----------------------
# COMMAND HELPERS
# -----------------------

async def send_paginated_cards(ctx, search_term, title):
    try:
        cards = fetch_cards(search_term, page=1)

        if not cards:
            await ctx.send("No cards found.")
            return

        view = CardPaginator(
            ctx=ctx,
            search_term=search_term,
            title=title,
            cards=cards,
            page=1
        )

        await ctx.send(embed=view.build_embed(), view=view)

    except Exception as e:
        await ctx.send(f"Bot error: {e}")


async def set_command(ctx, set_code):
    await send_paginated_cards(
        ctx,
        set_code.upper(),
        f"{set_code.upper()} Market"
    )


# -----------------------
# EVENTS
# -----------------------

@bot.event
async def on_ready():
    print(f"nami is online as {bot.user}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.content.startswith("!"):
        return

    command_text = message.content[1:].strip()

    if not command_text:
        return

    known_commands = [
        "helpme",
        "card",
        "sp",
        "manga",
        "alt",
        *[f"op{i:02d}" for i in range(1, 17)],
        "eb01",
        "eb02",
        "eb03",
        "prb01",
        "prb02"
    ]

    first_word = command_text.split()[0].lower()

    if first_word in known_commands:
        await bot.process_commands(message)
        return

    ctx = await bot.get_context(message)

    await send_paginated_cards(
        ctx,
        command_text,
        f"Character Search: {command_text}"
    )


# -----------------------
# COMMANDS
# -----------------------

@bot.command()
async def helpme(ctx):
    await ctx.send(
        "**Nami Commands**\n\n"
        "**Sets:** `!op01` through `!op16`\n"
        "**Extra Boosters:** `!eb01` `!eb02` `!eb03`\n"
        "**PRB:** `!prb01` `!prb02`\n"
        "**Markets:** `!sp` `!manga` `!alt`\n"
        "**Search:** `!perona`, `!nami`, `!zoro`, etc.\n"
        "**Exact Search:** `!card perona`\n\n"
        "Use the buttons under each result to scroll cards."
    )


@bot.command()
async def card(ctx, *, name):
    await send_paginated_cards(
        ctx,
        name,
        f"Card Search: {name}"
    )


@bot.command()
async def sp(ctx):
    await send_paginated_cards(ctx, "SP", "SP Market")


@bot.command()
async def manga(ctx):
    await send_paginated_cards(ctx, "manga", "Manga Rare Market")


@bot.command()
async def alt(ctx):
    await send_paginated_cards(ctx, "alternate art", "Alt Art Market")


for i in range(1, 17):
    code = f"op{i:02d}"

    async def command_func(ctx, code=code):
        await set_command(ctx, code)

    bot.command(name=code)(command_func)


for code in ["eb01", "eb02", "eb03", "prb01", "prb02"]:
    async def command_func(ctx, code=code):
        await set_command(ctx, code)

    bot.command(name=code)(command_func)


bot.run(DISCORD_BOT_TOKEN)
