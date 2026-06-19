import os
import requests
import discord
from discord.ext import commands

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
JUSTTCG_API_KEY = os.environ["JUSTTCG_API_KEY"]

BASE_URL = "https://api.justtcg.com/v1/cards"
LIMIT = 20

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

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
    for v in card.get("variants", []):
        price = v.get("marketPrice") or v.get("price") or v.get("latestPrice")
        if price:
            return float(price)
    return None

def get_old_price(card):
    for v in card.get("variants", []):
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

def make_movers(cards):
    movers = []

    for card in cards:
        new = get_price(card)
        old = get_old_price(card)

        if not new or not old:
            continue

        movers.append({
            "name": card.get("name", "Unknown Card"),
            "old": old,
            "new": new,
            "change": percent(old, new)
        })

    return movers

async def send_list(ctx, title, movers):
    if not movers:
        await ctx.send("No movement data found.")
        return

    msg = f"**{title}**\n\n"

    for i, c in enumerate(movers[:20], 1):
        msg += f"{i}. **{c['name']}**\n${c['old']:.2f} → ${c['new']:.2f} ({c['change']:+.2f}%)\n\n"

    await ctx.send(msg[:1900])

@bot.event
async def on_ready():
    print(f"nami is online as {bot.user}")

@bot.command(name="helpme")
async def helpme(ctx):
    await ctx.send(
        "**Nami Commands**\n"
        "`!gainers` - top gainers\n"
        "`!losers` - top losers\n"
        "`!leaderboard` - biggest movers\n"
        "`!card nami` - search a card\n"
        "`!manga` - manga movers\n"
        "`!sp` - SP movers\n"
        "`!eb02` - EB02 movers\n"
        "`!op11` - OP11 movers"
    )

@bot.command()
async def gainers(ctx):
    cards = fetch_cards()
    movers = sorted(make_movers(cards), key=lambda x: x["change"], reverse=True)
    await send_list(ctx, "📈 One Piece Gainers", movers)

@bot.command()
async def losers(ctx):
    cards = fetch_cards()
    movers = sorted(make_movers(cards), key=lambda x: x["change"])
    await send_list(ctx, "📉 One Piece Losers", movers)

@bot.command()
async def leaderboard(ctx):
    cards = fetch_cards()
    movers = sorted(make_movers(cards), key=lambda x: abs(x["change"]), reverse=True)
    await send_list(ctx, "🏆 Biggest Market Movers", movers)

@bot.command()
async def card(ctx, *, name):
    cards = fetch_cards(name)

    if not cards:
        await ctx.send("No card found.")
        return

    c = cards[0]
    price = get_price(c)

    await ctx.send(
        f"**{c.get('name', 'Unknown Card')}**\n"
        f"Market Price: ${price:.2f}" if price else "No price found."
    )

@bot.command()
async def manga(ctx):
    cards = fetch_cards("manga")
    movers = sorted(make_movers(cards), key=lambda x: x["change"], reverse=True)
    await send_list(ctx, "🔥 Manga Rare Movers", movers)

@bot.command()
async def sp(ctx):
    cards = fetch_cards("SP")
    movers = sorted(make_movers(cards), key=lambda x: x["change"], reverse=True)
    await send_list(ctx, "✨ SP Card Movers", movers)

@bot.command()
async def eb02(ctx):
    cards = fetch_cards("EB02")
    movers = sorted(make_movers(cards), key=lambda x: x["change"], reverse=True)
    await send_list(ctx, "🥇 EB02 Movers", movers)

@bot.command()
async def op11(ctx):
    cards = fetch_cards("OP11")
    movers = sorted(make_movers(cards), key=lambda x: x["change"], reverse=True)
    await send_list(ctx, "⚔️ OP11 Movers", movers)

bot.run(DISCORD_BOT_TOKEN)
