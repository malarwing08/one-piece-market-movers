import requests
import discord
from discord import app_commands

import os

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
JUSTTCG_API_KEY = os.environ["JUSTTCG_API_KEY"]

BASE_URL = "https://api.justtcg.com/v1/cards"
LIMIT = 20

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def fetch_cards(search=None):
    headers = {"x-api-key": JUSTTCG_API_KEY}
    params = {
        "game": "One Piece Card Game",
        "limit": LIMIT,
        "priceHistoryDuration": "30d"
    }

    if search:
        params["q"] = search

    r = requests.get(BASE_URL, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])

def get_price(card):
    variants = card.get("variants", [])
    for v in variants:
        price = v.get("marketPrice") or v.get("price") or v.get("latestPrice")
        if price:
            return float(price)
    return None

def get_old_price(card):
    variants = card.get("variants", [])
    for v in variants:
        history = v.get("priceHistory") or v.get("price_history") or []
        if len(history) >= 2:
            old = history[-2].get("marketPrice") or history[-2].get("price")
            if old:
                return float(old)
    return None

def percent(old, new):
    if not old or old <= 0:
        return 0
    return ((new - old) / old) * 100

def get_image(card):
    return card.get("image") or card.get("imageUrl") or card.get("image_url")

def make_movers(cards):
    movers = []

    for card in cards:
        new = get_price(card)
        old = get_old_price(card)

        if not new or not old:
            continue

        movers.append({
            "name": card.get("name", "Unknown Card"),
            "new": new,
            "old": old,
            "change": percent(old, new),
            "image": get_image(card)
        })

    return movers

async def send_mover_list(interaction, title, movers):
    if not movers:
        await interaction.response.send_message("No price movement data found.")
        return

    text = f"**{title}**\n\n"

    for i, card in enumerate(movers[:20], 1):
        text += (
            f"{i}. **{card['name']}**\n"
            f"${card['old']:.2f} → ${card['new']:.2f} "
            f"({card['change']:+.2f}%)\n\n"
        )

    await interaction.response.send_message(text)

@client.event
async def on_ready():
    await tree.sync()
    print(f"nami is online as {client.user}")

@tree.command(name="help", description="Show nami commands")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**nami commands**\n"
        "/gainers - top One Piece gainers\n"
        "/losers - top One Piece losers\n"
        "/card - search a card\n"
        "/manga - search manga cards\n"
        "/sp - search SP cards\n"
        "/eb02 - search EB02 cards\n"
        "/op11 - search OP11 cards\n"
        "/leaderboard - biggest movers"
    )

@tree.command(name="gainers", description="Show One Piece price gainers")
async def gainers(interaction: discord.Interaction):
    cards = fetch_cards()
    movers = make_movers(cards)
    movers = sorted(movers, key=lambda x: x["change"], reverse=True)
    await send_mover_list(interaction, "📈 One Piece Gainers", movers)

@tree.command(name="losers", description="Show One Piece price losers")
async def losers(interaction: discord.Interaction):
    cards = fetch_cards()
    movers = make_movers(cards)
    movers = sorted(movers, key=lambda x: x["change"])
    await send_mover_list(interaction, "📉 One Piece Losers", movers)

@tree.command(name="leaderboard", description="Show biggest movers")
async def leaderboard(interaction: discord.Interaction):
    cards = fetch_cards()
    movers = make_movers(cards)
    movers = sorted(movers, key=lambda x: abs(x["change"]), reverse=True)
    await send_mover_list(interaction, "🏆 Biggest Market Movers", movers)

@tree.command(name="card", description="Search a One Piece card")
async def card(interaction: discord.Interaction, name: str):
    cards = fetch_cards(name)

    if not cards:
        await interaction.response.send_message("No card found.")
        return

    c = cards[0]
    price = get_price(c)
    image = get_image(c)

    embed = discord.Embed(
        title=c.get("name", "Unknown Card"),
        description=f"Market Price: ${price:.2f}" if price else "No price found"
    )

    if image:
        embed.set_image(url=image)

    await interaction.response.send_message(embed=embed)

@tree.command(name="manga", description="Search manga rare cards")
async def manga(interaction: discord.Interaction):
    cards = fetch_cards("manga")
    movers = make_movers(cards)
    movers = sorted(movers, key=lambda x: x["change"], reverse=True)
    await send_mover_list(interaction, "🔥 Manga Rare Movers", movers)

@tree.command(name="sp", description="Search SP cards")
async def sp(interaction: discord.Interaction):
    cards = fetch_cards("SP")
    movers = make_movers(cards)
    movers = sorted(movers, key=lambda x: x["change"], reverse=True)
    await send_mover_list(interaction, "✨ SP Card Movers", movers)

@tree.command(name="eb02", description="Search EB02 cards")
async def eb02(interaction: discord.Interaction):
    cards = fetch_cards("EB02")
    movers = make_movers(cards)
    movers = sorted(movers, key=lambda x: x["change"], reverse=True)
    await send_mover_list(interaction, "🥇 EB02 Movers", movers)

@tree.command(name="op11", description="Search OP11 cards")
async def op11(interaction: discord.Interaction):
    cards = fetch_cards("OP11")
    movers = make_movers(cards)
    movers = sorted(movers, key=lambda x: x["change"], reverse=True)
    await send_mover_list(interaction, "⚔️ OP11 Movers", movers)

client.run(DISCORD_BOT_TOKEN)
