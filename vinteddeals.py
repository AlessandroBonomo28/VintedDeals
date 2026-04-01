import time
import json
import telepot
import threading
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup
from vinted_scraper import VintedScraper
import os
from dotenv import load_dotenv

load_dotenv()
data_lock = threading.Lock()
ENFORCE_WHITELIST = False

TOKEN = os.getenv('TOKEN')
if not TOKEN:
    print("ERROR: Token not found in environment or .env file!")
    exit(1)

whitelist_file = "whitelist.json"

whitelist = []

if not os.path.exists(whitelist_file):
    with open(whitelist_file, 'w') as f:
        json.dump([], f)
    print(f"Created {whitelist_file} with empty array")
else:
    print(f"{whitelist_file} already exists")

with open(whitelist_file, "r") as f:
    whitelist = json.load(f)

DATA_FILE = "vinted_users.json"
CHECK_DELAY = 180

bot = telepot.Bot(TOKEN)

scraper = VintedScraper("https://www.vinted.it")

try:
    with open(DATA_FILE, "r") as f:
        user_data = json.load(f)
except:
    user_data = {}

def save_data():
    with data_lock:
        with open(DATA_FILE, "w") as f:
            json.dump(user_data, f)

def parse_price(text):
    """Parse price accepting both '.' and ',' as decimal separator."""
    text = text.strip().replace(",", ".")
    try:
        price = float(text)
        return round(price, 2)
    except ValueError:
        return None

def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    chat_id = str(chat_id)
    text = msg.get('text', '').strip()

    with data_lock:
        if chat_id not in user_data:
            user_data[chat_id] = {"keywords": {}, "state": None, "temp": {}}
        if "temp" not in user_data[chat_id]:
            user_data[chat_id]["temp"] = {}

    keyboard = ReplyKeyboardMarkup(keyboard=[
        ['/add', '/remove'],
        ['/list', '/edit']
    ], resize_keyboard=True)

    state = user_data[chat_id].get('state')

    # ── /start ──────────────────────────────────────────────────────────────
    if text == '/start':
        bot.sendMessage(chat_id, "Welcome! Manage your Vinted alerts here.", reply_markup=keyboard)

    # ── /add ─────────────────────────────────────────────────────────────────
    elif text == '/add':
        with data_lock:
            user_data[chat_id]['state'] = 'adding_keyword'
            user_data[chat_id]['temp'] = {}
        save_data()
        bot.sendMessage(chat_id, "✏️ Enter the keyword to monitor:")

    # ── /remove ──────────────────────────────────────────────────────────────
    elif text == '/remove':
        keywords = user_data[chat_id].get('keywords', {})
        if not keywords:
            bot.sendMessage(chat_id, "No keywords to remove.")
            return
        with data_lock:
            user_data[chat_id]['state'] = 'removing'
            user_data[chat_id]['temp'] = {}
        save_data()
        kw_list = "\n".join(f"• {kw}" for kw in keywords.keys())
        bot.sendMessage(chat_id, f"🗑️ Enter the keyword to remove:\n\n{kw_list}")

    # ── /list ────────────────────────────────────────────────────────────────
    elif text == '/list':
        keywords = user_data[chat_id].get('keywords', {})
        if not keywords:
            bot.sendMessage(chat_id, "No active keywords.")
        else:
            lines = []
            for kw, info in keywords.items():
                max_price = info.get('max_price') if isinstance(info, dict) else None
                if max_price is not None:
                    lines.append(f"🔍 *{kw}* — max €{max_price:.2f}")
                else:
                    lines.append(f"🔍 *{kw}* — no price limit")
            bot.sendMessage(chat_id, "\n".join(lines), parse_mode='Markdown')

    # ── /edit ────────────────────────────────────────────────────────────────
    elif text == '/edit':
        keywords = user_data[chat_id].get('keywords', {})
        if not keywords:
            bot.sendMessage(chat_id, "No keywords to edit.")
        else:
            with data_lock:
                user_data[chat_id]['state'] = 'editing_keyword'
                user_data[chat_id]['temp'] = {}
            save_data()
            kw_list = "\n".join(f"• {kw}" for kw in keywords.keys())
            bot.sendMessage(chat_id, f"Which keyword do you want to edit?\n\n{kw_list}")

    # ── State handling ───────────────────────────────────────────────────────
    else:
        if state == 'adding_keyword':
            kw = text.lower()
            with data_lock:
                user_data[chat_id]['temp']['keyword'] = kw
                user_data[chat_id]['state'] = 'adding_price'
            save_data()
            bot.sendMessage(chat_id, f"💰 Set a maximum price for *{kw}* (e.g. 25 or 19.99)\nOr type *skip* to set no limit.", parse_mode='Markdown')

        elif state == 'adding_price':
            kw = user_data[chat_id]['temp'].get('keyword')
            if text.lower() == 'skip':
                max_price = None
            else:
                max_price = parse_price(text)
                if max_price is None:
                    bot.sendMessage(chat_id, "⚠️ Invalid price. Enter a number (e.g. 25 or 19.99) or type *skip*.", parse_mode='Markdown')
                    return
            with data_lock:
                user_data[chat_id]['keywords'][kw] = {
                    "last_id": None,
                    "max_price": max_price
                }
                user_data[chat_id]['state'] = None
                user_data[chat_id]['temp'] = {}
            save_data()
            price_msg = f"€{max_price:.2f}" if max_price is not None else "no limit"
            bot.sendMessage(chat_id, f"✅ Monitoring started for: *{kw}*\n💰 Max price: {price_msg}", parse_mode='Markdown', reply_markup=keyboard)

        elif state == 'removing':
            kw = text.lower()
            if kw in user_data[chat_id].get('keywords', {}):
                with data_lock:
                    del user_data[chat_id]['keywords'][kw]
                    user_data[chat_id]['state'] = None
                save_data()
                bot.sendMessage(chat_id, f"🗑️ Removed: *{kw}*", parse_mode='Markdown', reply_markup=keyboard)
            else:
                bot.sendMessage(chat_id, "❌ Keyword not found in list.")
                with data_lock:
                    user_data[chat_id]['state'] = None
                save_data()

        elif state == 'editing_keyword':
            kw = text.lower()
            if kw in user_data[chat_id].get('keywords', {}):
                with data_lock:
                    user_data[chat_id]['temp']['keyword'] = kw
                    user_data[chat_id]['state'] = 'editing_price'
                save_data()
                bot.sendMessage(chat_id, f"💰 Enter the new maximum price for *{kw}*\nOr type *skip* to remove the limit.", parse_mode='Markdown')
            else:
                bot.sendMessage(chat_id, "❌ Keyword not found. Try again with /edit.")
                with data_lock:
                    user_data[chat_id]['state'] = None
                save_data()

        elif state == 'editing_price':
            kw = user_data[chat_id]['temp'].get('keyword')
            if text.lower() == 'skip':
                max_price = None
            else:
                max_price = parse_price(text)
                if max_price is None:
                    bot.sendMessage(chat_id, "⚠️ Invalid price. Enter a number (e.g. 25 or 19.99) or type *skip*.", parse_mode='Markdown')
                    return
            with data_lock:
                if kw in user_data[chat_id]['keywords']:
                    info = user_data[chat_id]['keywords'][kw]
                    if isinstance(info, dict):
                        info['max_price'] = max_price
                    else:
                        user_data[chat_id]['keywords'][kw] = {"last_id": info, "max_price": max_price}
                user_data[chat_id]['state'] = None
                user_data[chat_id]['temp'] = {}
            save_data()
            price_msg = f"€{max_price:.2f}" if max_price is not None else "no limit"
            bot.sendMessage(chat_id, f"✅ Price updated for *{kw}*: {price_msg}", parse_mode='Markdown', reply_markup=keyboard)


# --- VINTED MONITORING LOOP ---
def run_monitor():
    print("Bot started and listening on Vinted...")
    MessageLoop(bot, handle).run_as_thread()

    while True:
        try:
            print("🔄 Refreshing Vinted session...")
            scraper = VintedScraper("https://www.vinted.it")
        except Exception as e:
            print(f"❌ Error while refreshing session: {e}")
            time.sleep(60)
            continue

        for chat_id, data in list(user_data.items()):
            keywords = data.get("keywords", {})

            for kw, info in list(keywords.items()):
                try:
                    if isinstance(info, dict):
                        last_id = info.get("last_id")
                        max_price = info.get("max_price")
                    else:
                        last_id = info
                        max_price = None

                    params = {"search_text": kw, "order": "newest_first", "per_page": 5}
                    items = scraper.search(params)

                    if items:
                        if max_price is not None:
                            items = [i for i in items if float(i.price) <= max_price]

                        if not items:
                            time.sleep(60)
                            continue

                        newest_item = items[0]

                        if str(newest_item.id) != str(last_id):
                            msg_text = (
                                f"🔔 *NEW ITEM FOUND*\n"
                                f"Keyword: {kw.upper()}\n\n"
                                f"📦 {newest_item.title}\n"
                                f"💰 {newest_item.price} {newest_item.currency}\n"
                                f"🔗 {newest_item.url}"
                            )
                            if max_price is not None:
                                msg_text += f"\n_Price filter: ≤ €{max_price:.2f}_"

                            bot.sendMessage(chat_id, msg_text, parse_mode='Markdown')

                            with data_lock:
                                if chat_id in user_data and kw in user_data[chat_id]["keywords"]:
                                    if isinstance(user_data[chat_id]["keywords"][kw], dict):
                                        user_data[chat_id]["keywords"][kw]["last_id"] = str(newest_item.id)
                                    else:
                                        user_data[chat_id]["keywords"][kw] = {
                                            "last_id": str(newest_item.id),
                                            "max_price": None
                                        }
                            save_data()

                    time.sleep(60)
                except Exception as e:
                    print(f"Scraping error for '{kw}': {e}")

        time.sleep(CHECK_DELAY)


if __name__ == "__main__":
    run_monitor()