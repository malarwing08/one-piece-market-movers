import os
import re
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


def fetch_cards(search=None, page=1):
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

    for v in card.get("variants", []):
        for key in [
            "marketPrice",
            "tcgplayerMarketPrice",
            "price",
            "latestPrice",
            "lowPrice",
            "midPrice",
        ]:
            price = v.get(key)
            if price:
                try:
                    prices.append(float(price))
                except:
                    pass

    for key in [
        "marketPrice",
        "tcgplayerMarketPrice",
        "price",
        "latestPrice",
        "lowPrice",
        "midPrice",
    ]:
        price = card.get(key)
        if price:
            try:
                prices.append(float(price))
            except:
                pass

    return max(prices) if prices else None


def find_image_url(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = str(key).lower()

            if isinstance(value, str):
                if (
                    "image" in key_lower
                    or "img" in key_lower
                    or "photo" in key_lower
                    or "picture" in key_lower
                ):
                    if value.startswith("http"):
                        return value

                if value.startswith("http") and any(
                    ext in value.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]
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


def find_tcgplayer_id(card):
    possible_keys = [
        "tcgplayerProductId",
        "tcgplayerId",
        "productId",
        "tcgProductId",
        "tcgplayer_product_id",
    ]

    for key in possible_keys:
        if card.get(key):
            return card.get(key)

    for v in card.get("variants", []):
        for key in possible_keys:
            if v.get(key):
                return v.get(key)

    return None


def get_image(card):
    image = find_image_url(card)

    if image:
        return image

    product_id = find_tcgplayer_id(card)

    if product_id:
        return f"https://tcgplayer-cdn.tcgplayer.com/product/{product_id}_in_1000x1000.jpg"

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


def get_number(card):
    return (
        card.get("number")
        or card.get("cardNumber")
        or card.get("collectorNumber")
        or "Unknown Number"
    )


def sort_by_price(cards):
    return sorted(cards, key=lambda c: get_price(c) or 0, reverse=True)


class CardPaginator(discord.ui.View):
    def __init__(self, search_term, title, cards, page=1):
        super().__init__(timeout=300)
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

        embed.set_footer(
            text=f"Card {self.index + 1}/{len(self.cards)} • Page {self.page} • Sorted high to low"
        )

        if image:
            embed.set_image(url=image)

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
        try:
            self.page += 1
            new_cards = fetch_cards(self.search_term, self.page)

            if not new_cards:
                self.page -= 1
                await interaction.response.send_message("No more cards found.", ephemeral=True)
                return

            self.cards = sort_by_price(new_cards)
            self.index = 0
            await self.update_msg(interaction)

        except Exception as e:
            await interaction.response.send_message(f"Bot error: {e}", ephemeral=True)


async def send_cards(ctx, search_term, title):
    try:
        cards = fetch_cards(search_term, 1)

        if not cards:
            await ctx.send("No cards found.")
            return

        view = CardPaginator(search_term, title, cards, 1)
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
        "Results are sorted by highest market price first."
    )


@bot.command()
async def card(ctx, *, name):
    await send_cards(ctx, name, f"Card Search: {name}")


@bot.command()
async def sp(ctx):
    await send_cards(ctx, "(SP)", "SP Market")


@bot.command()
async def manga(ctx):
    await send_cards(ctx, "Manga", "Manga Rare Market")


@bot.command()
async def alt(ctx):
    await send_cards(ctx, "Alternate Art", "Alt Art Market")


async def set_command(ctx, code):
    await send_cards(ctx, code.upper(), f"{code.upper()} Market")


for i in range(1, 17):
    code = f"op{i:02d}"

    async def command_func(ctx, code=code):
        await set_command(ctx, code)

    bot.command(name=code)(command_func)


for code in ["eb01", "eb02", "eb03", "prb01", "prb02"]:
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

    known = [
        "helpme", "card", "sp", "manga", "alt",
        *[f"op{i:02d}" for i in range(1, 17)],
        "eb01", "eb02", "eb03", "prb01", "prb02"
    ]

    if first_word in known:
        await bot.process_commands(message)
    else:
        ctx = await bot.get_context(message)
        await send_cards(ctx, command_text, f"Character Search: {command_text}")


bot.run(DISCORD_BOT_TOKEN)
