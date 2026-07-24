import os
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# Database setup
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    username TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
        (user.id, user.full_name, user.username),
    )
    conn.commit()

    await update.message.reply_text(
        f"👋 ሰላም {user.first_name}!\n\n"
        "✅ Bot በትክክል ተጀምሯል!\n\n"
        "🚀 አሁን እኛ ቀጣይ ደረጃ እንሄዳለን."
    )


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("✅ Bot is running...")
    app.run_polling()
