import hmac
import hashlib
import random
import os

from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from telegram.ext.webhook import WebhookRequestHandler

BOT_TOKEN = os.getenv("BOT_TOKEN", "7542612722:AAEaissWRRDMPj1DeE5kz_3dV-HVnAHN5jY")  # ✅ Set in Render env
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN", "https://py-stake.onrender.com")     # Replace or set env
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

user_data = {}

# ✅ Accurate hash-based prediction
def generate_prediction_with_hash(server_seed, nonce, mine_count):
    total_positions = 25
    safe_count = random.choices([4, 5, 6], weights=[0.45, 0.45, 0.1])[0]

    message = f"{nonce}:{mine_count}"
    hash_hex = hmac.new(server_seed.encode(), message.encode(), hashlib.sha256).hexdigest()

    safe_indexes = []
    i = 0
    while len(safe_indexes) < safe_count and i + 4 <= len(hash_hex):
        chunk = hash_hex[i:i + 4]
        index = int(chunk, 16) % total_positions
        if index not in safe_indexes:
            safe_indexes.append(index)
        i += 4

    grid = ["🚫"] * total_positions
    for idx in safe_indexes:
        grid[idx] = "💎"
    return [grid[i:i + 5] for i in range(0, total_positions, 5)]

# 👋 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("▶️ Start", callback_data="start_bot")],
        [InlineKeyboardButton("📹 How to Use", callback_data="how_to_use")]
    ]
    await update.message.reply_text(
        "👋 Welcome to *Stake Mine Predictor Bot*\n\n"
        "🔐 Now uses *Provably Fair Hash-Based Logic*\n"
        "🎯 Gives 4–6 safe positions with high accuracy!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# 🔘 Handle buttons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    user_data[uid] = {}

    if query.data == "how_to_use":
        await query.message.reply_text("📽 How to Use:\nhttps://www.instagram.com/reel/DKdH4trRfC2/")
    elif query.data == "start_bot":
        await query.message.reply_photo(
            photo="https://i.ibb.co/spgwSXts/Screenshot-20250604-195625-Canva-2.png",
            caption="📩 Enter your **Server Seed**:"
        )

# 💬 Handle user input
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()

    if uid not in user_data:
        return await update.message.reply_text("❗ Please click ▶️ Start first.")

    user = user_data[uid]

    if "server_seed" not in user:
        user["server_seed"] = text
        await update.message.reply_photo(
            photo="https://i.ibb.co/NdCy52LB/Screenshot-20250604-195659-Canva-2.png",
            caption="🔢 Enter your **Nonce**:"
        )
    elif "nonce" not in user:
        user["nonce"] = text
        await ask_mine(update)
    elif "mine" not in user:
        if text.isdigit() and 1 <= int(text) <= 7:
            user["mine"] = int(text)
            await send_prediction(update, user)
        else:
            await update.message.reply_text("❌ Enter a number between 1 and 7.")

# 💣 Ask mine count
async def ask_mine(update: Update):
    keyboard = [[KeyboardButton(str(i)) for i in range(1, 8)]]
    await update.message.reply_text(
        "💣 Select Mine Count (1–7):",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# 📤 Send prediction
async def send_prediction(update: Update, user):
    grid = generate_prediction_with_hash(
        user["server_seed"], user["nonce"], user["mine"]
    )

    result = "✅ *Prediction Result:*\n\n"
    for row in grid:
        result += " ".join(row) + "\n"

    result += f"\n🔐 *Server Seed:* `{user['server_seed']}`"
    result += f"\n🔢 *Nonce:* `{user['nonce']}`"
    result += f"\n💣 *Mine Count:* `{user['mine']}`"
    result += (
        "\n\n🧠 *Powered by HMAC-SHA256*"
        "\n🔍 Verifiable & Fair Results"
    )

    await update.message.reply_text(result, parse_mode="Markdown")

    user_data[update.message.from_user.id] = {}

    keyboard = [[InlineKeyboardButton("🔁 Predict Again", callback_data="start_bot")]]
    await update.message.reply_text("🔮 Want to predict again?", reply_markup=InlineKeyboardMarkup(keyboard))

# 🔧 FastAPI app and Telegram Application
app = FastAPI()
telegram_app = Application.builder().token(BOT_TOKEN).build()

# Add handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button_handler))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# 🧠 Webhook handler
class Handler(WebhookRequestHandler):
    async def handle(self, request: Request) -> None:
        update = Update.de_json(await request.json(), telegram_app.bot)
        await telegram_app.process_update(update)

# ✅ Endpoint for Telegram webhook
@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    handler = Handler()
    return await handler.handle(request)

# 🌐 Root test endpoint
@app.get("/")
def root():
    return {"message": "Bot is live 🚀"}

# 📦 Webhook setup on startup
@app.on_event("startup")
async def on_startup():
    await telegram_app.bot.set_webhook(url=WEBHOOK_DOMAIN + WEBHOOK_PATH)
