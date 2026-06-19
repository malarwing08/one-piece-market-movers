import time
import requests

# ==========================
# CONFIG
# ==========================

JUSTTCG_API_KEY = "tcg_f218951a1d8b41019507ba51da36707d"

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1517547992612081754/eOzZJbNS5Vyxs3o1uK2bEqD7nDncXYNfE2_UaUqqLu2Gf38cemLOTi6TncOnIQdY5V_m"

MIN_PRICE = 1.00
TOP_LIMIT = 50

# ==========================
# API
# ==========================

BASE_URL = "https://api.justtcg.com/v1/cards"

# ==========================
# HELPERS
# ==========================

def send_discord(message):
    try:
        requests.post(
            DISCORD_WEBHOOK,
            json={"content": message},
            timeout=20
        )
    except Exception as e:
        print("Discord Error:", e)

def percent_change(old_price, new_price):
    if old_price <= 0:
        return 0

    return ((new_price - old_price) / old_price) * 100

def get_cards():
    headers = {
        "x-api-key": JUSTTCG_API_KEY
    }

    params = {
        "game": "One Piece Card Game",
        "limit": 500,
        "include_price_history": "true"
    }

    response = requests.get(
        BASE_URL,
        headers=headers,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    if "data" in data:
        return data["data"]

    return []

def get_current_price(card):
    variants = card.get("variants", [])

    for variant in variants:

        price = (
            variant.get("marketPrice")
            or variant.get("price")
            or variant.get("latestPrice")
        )

        if price:
            return float(price)

    return None

def get_previous_price(card):
    variants = card.get("variants", [])

    for variant in variants:

        history = (
            variant.get("price_history")
            or variant.get("priceHistory")
            or []
        )

        if len(history) >= 2:

            old_price = (
                history[-2].get("marketPrice")
                or history[-2].get("price")
            )

            if old_price:
                return float(old_price)

    return None

# ==========================
# REPORT
# ==========================

def build_report(title, cards):

    lines = [title, ""]

    for index, card in enumerate(cards, start=1):

        lines.append(
            f"{index}. {card['name']} | "
            f"${card['old']:.2f} → "
            f"${card['new']:.2f} | "
            f"{card['change']:+.2f}%"
        )

    return "\n".join(lines)

# ==========================
# MAIN
# ==========================

print("Starting One Piece Market Movers Bot...")

send_discord("✅ One Piece Market Movers Bot Started")

while True:

    try:

        print("Downloading card data...")

        cards = get_cards()

        movers = []

        for card in cards:

            current_price = get_current_price(card)
            previous_price = get_previous_price(card)

            if current_price is None:
                continue

            if previous_price is None:
                continue

            if current_price < MIN_PRICE:
                continue

            change = percent_change(
                previous_price,
                current_price
            )

            movers.append({
                "name": card.get("name", "Unknown"),
                "old": previous_price,
                "new": current_price,
                "change": change
            })

        print(f"Found {len(movers)} cards")

        gainers = sorted(
            movers,
            key=lambda x: x["change"],
            reverse=True
        )[:TOP_LIMIT]

        losers = sorted(
            movers,
            key=lambda x: x["change"]
        )[:TOP_LIMIT]

        gainers_report = build_report(
            "📈 TOP 50 ONE PIECE GAINERS",
            gainers
        )

        losers_report = build_report(
            "📉 TOP 50 ONE PIECE LOSERS",
            losers
        )

        send_discord(gainers_report)

        time.sleep(5)

        send_discord(losers_report)

        print("Reports sent")

        # Run once every 24 hours
        time.sleep(86400)

    except Exception as e:

        error_message = f"❌ Bot Error:\n{str(e)}"

        print(error_message)

        send_discord(error_message)

        time.sleep(300)
