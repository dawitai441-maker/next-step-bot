import os
import sqlite3

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "database.db"

# ---------------- MAIN KEYBOARDS ----------------

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🎯 Dream Survey", "📖 Business Presentation"],
        ["📚 ነፃ ስልጠናዎች", "🧠 የስልጠና ይዞታ"],
        ["ℹ️ ስለ እኛ", "❓ FAQ"],
        ["📞 ያግኙን", "👑 Premium"],
    ],
    resize_keyboard=True,
)

CONTACT_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("📱 ስልክ ቁጥር አጋራ", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

# ---------------- DREAM SURVEY ----------------

SURVEY_FIELDS = {
    1: "occupation",
    2: "dream",
    3: "obstacle",
    4: "desired_income",
    5: "current_income",
    6: "free_time",
    7: "teamwork",
    8: "timeframe",
    9: "family_life",
    10: "ready",
}

SURVEY_QUESTIONS = {
    1: """1️⃣ / 10

👨‍💼 አሁን ምን እየሰሩ ነው?

(ለምሳሌ፦ ተማሪ፣ ሰራተኛ፣ ነጋዴ፣
ስራ አጥ፣ ወዘተ)""",

    2: """2️⃣ / 10

🎯 በህይወትዎ ምን ማሳካት ይፈልጋሉ?

(ህልምዎን፣ ግቦችዎን በነፃነት ይጻፉ)""",

    3: """3️⃣ / 10

🚧 ያንን እንዳያሳኩ ምን እንቅፋት ወይም
ፈተና ሆኖብዎታል?

(ለምሳሌ፦ ገንዘብ፣ ጊዜ፣ እውቀት፣
ድጋፍ፣ ወዘተ)""",

    4: """4️⃣ / 10

💰 በወር ስንት ገቢ ማግኘት ይፈልጋሉ?

(በብር ያስገቡ፦ ለምሳሌ 50000)""",

    5: """5️⃣ / 10

💵 አሁን ያለው ወርሃዊ ገቢዎ ስንት
ያህል ነው?

(በብር ያስገቡ፦ ለምሳሌ 15000
ወይም 0 ከሌለ)""",

    6: """6️⃣ / 10

🕒 በቀን ስንት ሰዓት ነፃ ጊዜ አለዎት?

(ለምሳሌ፦ 2 ሰዓት፣ 4 ሰዓት፣ ወዘተ)""",

    7: """7️⃣ / 10

👥 ከሰዎች ጋር በቡድን መስራት ይወዳሉ?""",

    8: """8️⃣ / 10

⏳ በስንት ወር ውስጥ ውጤት ማየት
ይፈልጋሉ?

(ለምሳሌ፦ 3 ወር፣ 6 ወር፣ 1 ዓመት)""",

    9: """9️⃣ / 10

❤️ ለቤተሰብዎ ምን አይነት ህይወት
መስጠት ይፈልጋሉ?

(ለምሳሌ፦ የራሳቸው ቤት፣ ጥሩ ትምህርት፣
የተረጋጋ ገቢ፣ ወዘተ)""",

    10: """🔟 / 10

ህልምዎን በእርግጠኝነት የሚያሳኩበት
እና የኢኮኖሚ ነፃነት የሚያገኙበት
ትክክለኛ ዕድል ቢያገኙ ሊቀበሉት
ዝግጁ ነዎት?

If you found a real opportunity to achieve your
dreams and gain financial freedom, would you
be ready to accept it?""",
}


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Existing database ላይ አዲስ columns ለመጨመር
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)")]

    if "phone" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")

    if "referrer_id" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            user_id INTEGER PRIMARY KEY,
            state TEXT DEFAULT '',
            survey_step INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS dream_survey (
            user_id INTEGER PRIMARY KEY,
            occupation TEXT,
            dream TEXT,
            obstacle TEXT,
            desired_income TEXT,
            current_income TEXT,
            free_time TEXT,
            teamwork TEXT,
            timeframe TEXT,
            family_life TEXT,
            ready TEXT,
            completed INTEGER DEFAULT 0,
            completed_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def ensure_user(user, referrer_id=None):
    conn = get_db()

    conn.execute("""
        INSERT OR IGNORE INTO users (user_id, full_name, username)
        VALUES (?, ?, ?)
    """, (user.id, user.full_name, user.username))

    conn.execute("""
        UPDATE users
        SET full_name = ?, username = ?
        WHERE user_id = ?
    """, (user.full_name, user.username, user.id))

    # Referral አንዴ ብቻ ይመዘገባል
    if referrer_id and referrer_id != user.id:
        row = conn.execute(
            "SELECT referrer_id FROM users WHERE user_id = ?",
            (user.id,)
        ).fetchone()

        if row and row["referrer_id"] is None:
            conn.execute(
                "UPDATE users SET referrer_id = ? WHERE user_id = ?",
                (referrer_id, user.id)
            )

    conn.commit()
    conn.close()


def get_phone(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT phone FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    return row["phone"] if row else None


def save_phone(user_id, phone):
    conn = get_db()
    conn.execute(
        "UPDATE users SET phone = ? WHERE user_id = ?",
        (phone, user_id)
    )
    conn.commit()
    conn.close()


def set_state(user_id, state="", step=0):
    conn = get_db()
    conn.execute("""
        INSERT INTO user_state (user_id, state, survey_step)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            state = excluded.state,
            survey_step = excluded.survey_step
    """, (user_id, state, step))
    conn.commit()
    conn.close()


def get_state(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT state, survey_step FROM user_state WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    if not row:
        return "", 0

    return row["state"], row["survey_step"]


def reset_survey(user_id):
    conn = get_db()
    conn.execute("DELETE FROM dream_survey WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def save_survey_answer(user_id, step, answer):
    field = SURVEY_FIELDS[step]

    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO dream_survey (user_id) VALUES (?)",
        (user_id,)
    )
    conn.execute(
        f"UPDATE dream_survey SET {field} = ? WHERE user_id = ?",
        (answer, user_id)
    )
    conn.commit()
    conn.close()


def complete_survey(user_id):
    conn = get_db()
    conn.execute("""
        UPDATE dream_survey
        SET completed = 1,
            completed_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()


# ---------------- HELPERS ----------------

def get_referrer_from_start(args):
    if not args:
        return None

    value = args[0].lower()

    if value.startswith("ref_"):
        value = value[4:]
    elif value.startswith("ref"):
        value = value[3:]

    return int(value) if value.isdigit() else None


async def show_main_menu(message, first_time=False):
    if first_time:
        text = """✅ እንኳን ደስ አሎት!

ምዝገባዎ ተጠናቋል።

🎯 Dream Survey — ግብዎን እና ፍላጎትዎን ይለዩ
📖 Business Presentation — የቢዝነስ ገለጻ ይመልከቱ
📚 ነፃ ስልጠናዎች — በነፃ ይማሩ
👑 Premium — ተጨማሪ የቢዝነስ መሳሪያዎች

ከዚህ በታች ይምረጡ 👇"""
    else:
        text = """🏠 ዋና ምናሌ

ከዚህ በታች የሚፈልጉትን ይምረጡ 👇"""

    await message.reply_text(text, reply_markup=MAIN_MENU)


async def send_presentation_language(chat_id, context):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ],
        [
            InlineKeyboardButton("🇪🇷 ትግርኛ", callback_data="lang_ti"),
            InlineKeyboardButton("🇪🇹 Afaan Oromo", callback_data="lang_om"),
        ],
    ])

    await context.bot.send_message(
        chat_id=chat_id,
        text="""🎉 እንኳን ደስ አሎት!

ህልምዎን እውን የሚያደርግ ጉዞ
እየጀመሩ ነው! 🚀

በምን ቋንቋ መከታተል ይፈልጋሉ? 👇""",
        reply_markup=keyboard,
    )


async def send_survey_question(chat_id, user_id, context, step):
    set_state(user_id, "survey", step)

    if step == 7:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ አዎ", callback_data="survey_7_yes"),
                InlineKeyboardButton("❌ አይ", callback_data="survey_7_no"),
            ]
        ])
        await context.bot.send_message(
            chat_id=chat_id,
            text=SURVEY_QUESTIONS[step],
            reply_markup=keyboard,
        )
        return

    if step == 10:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ አዎ / Yes", callback_data="survey_10_yes")],
            [InlineKeyboardButton("❌ ኖ / No", callback_data="survey_10_no")],
        ])
        await context.bot.send_message(
            chat_id=chat_id,
            text=SURVEY_QUESTIONS[step],
            reply_markup=keyboard,
        )
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text=SURVEY_QUESTIONS[step],
    )


# ---------------- COMMANDS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referrer_id = get_referrer_from_start(context.args)

    ensure_user(user, referrer_id)

    if not get_phone(user.id):
        set_state(user.id, "await_phone", 0)

        await update.message.reply_text(
            """🌟 እንኳን ደህና መጡ ወደ NEXT STEP! 🌟

ይህ ቦት የቢዝነስ መረጃ፣ ነፃ ስልጠናዎች፣
Dream Survey እና የPremium የቢዝነስ
መሳሪያዎችን የሚያገኙበት መድረክ ነው።

ለመቀጠል እባክዎ ስልክ ቁጥርዎን
ያጋሩ 👇""",
            reply_markup=CONTACT_MENU,
        )
        return

    set_state(user.id, "", 0)
    await show_main_menu(update.message)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)
    set_state(update.effective_user.id, "", 0)
    await show_main_menu(update.message)


# ---------------- CONTACT ----------------

async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = update.message.contact

    ensure_user(user)

    # የራሱን ስልክ ብቻ እንዲያጋራ
    if contact.user_id and contact.user_id != user.id:
        await update.message.reply_text(
            "እባክዎ የራስዎን ስልክ ቁጥር ያጋሩ።",
            reply_markup=CONTACT_MENU,
        )
        return

    save_phone(user.id, contact.phone_number)
    set_state(user.id, "", 0)

    await show_main_menu(update.message, first_time=True)


# ---------------- TEXT HANDLER ----------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    ensure_user(user)

    # Main Menu buttons
    if text == "🎯 Dream Survey":
        set_state(user.id, "", 0)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ጀምር", callback_data="survey_start")]
        ])

        await update.message.reply_text(
            """🎯 Dream Survey

3 ደቂቃ ብቻ የሚፈጅ አጭር ጥያቄ ነው።

ግልጽ የሆነ ምስል እንዲኖርዎት እና
ትክክለኛውን መንገድ እንዲያገኙ
ይረዳዎታል።

📌 መልስዎ በምስጢር የተያዘ ነው።

ዝግጁ ሲሆኑ ይጫኑ 👇""",
            reply_markup=keyboard,
        )
        return

    if text == "📖 Business Presentation":
        set_state(user.id, "", 0)
        await send_presentation_language(update.effective_chat.id, context)
        return

    # ሌሎቹ menu ቀጣይ ላይ እንጨምራቸዋለን
    if text in [
        "📚 ነፃ ስልጠናዎች",
        "🧠 የስልጠና ይዞታ",
        "ℹ️ ስለ እኛ",
        "❓ FAQ",
        "📞 ያግኙን",
        "👑 Premium",
    ]:
        set_state(user.id, "", 0)
        await update.message.reply_text(
            "✅ ይህ ክፍል በቀጣዩ ደረጃ ይጨመራል።",
            reply_markup=MAIN_MENU,
        )
        return

    state, step = get_state(user.id)

    if state == "await_phone":
        await update.message.reply_text(
            "እባክዎ ከታች ያለውን «📱 ስልክ ቁጥር አጋራ» ይጫኑ።",
            reply_markup=CONTACT_MENU,
        )
        return

    # የSurvey ጽሑፍ መልሶች
    if state == "survey":
        if step in [7, 10]:
            await update.message.reply_text(
                "እባክዎ ከጥያቄው በታች ያለውን አማራጭ ይምረጡ።"
            )
            return

        save_survey_answer(user.id, step, text)
        await send_survey_question(
            update.effective_chat.id,
            user.id,
            context,
            step + 1,
        )
        return

    await update.message.reply_text(
        "እባክዎ ከዋናው ምናሌ ውስጥ አንድ አማራጭ ይምረጡ።",
        reply_markup=MAIN_MENU,
    )


# ---------------- INLINE BUTTONS ----------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    await query.answer()
    ensure_user(user)

    if data == "survey_start":
        reset_survey(user.id)
        await send_survey_question(
            query.message.chat.id,
            user.id,
            context,
            1,
        )
        return

    if data in ["survey_7_yes", "survey_7_no"]:
        answer = "አዎ" if data == "survey_7_yes" else "አይ"
        save_survey_answer(user.id, 7, answer)

        await send_survey_question(
            query.message.chat.id,
            user.id,
            context,
            8,
        )
        return

    if data in ["survey_10_yes", "survey_10_no"]:
        answer = "አዎ / Yes" if data == "survey_10_yes" else "ኖ / No"

        save_survey_answer(user.id, 10, answer)
        complete_survey(user.id)
        set_state(user.id, "", 0)

        # Yes = ወዲያውኑ ወደ Business Presentation
        if data == "survey_10_yes":
            await send_presentation_language(query.message.chat.id, context)
            return

        # No = መጨረሻ መልዕክት ከPresentation button ጋር
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📖 Business Presentation ይመልከቱ",
                    callback_data="presentation_start",
                )
            ]
        ])

        await query.message.reply_text(
            """✅ የህልም ጥናትዎ በሚገባ ሞልተው
ጨርሰዋል፤ እንኳን ደስ አሎት!

አሁን ወደ ቀጣይ ለመሄድ ከታች ይንኩ 👇""",
            reply_markup=keyboard,
        )
        return

    if data == "presentation_start":
        await send_presentation_language(query.message.chat.id, context)
        return

    if data.startswith("lang_"):
        selected = {
            "lang_am": "አማርኛ",
            "lang_en": "English",
            "lang_ti": "ትግርኛ",
            "lang_om": "Afaan Oromo",
        }.get(data, "አማርኛ")

        await query.message.reply_text(
            f"""✅ {selected} ተመርጧል።

📖 Business Presentation የ8ቱ ገጾች
በቀጣዩ የCode ክፍል ውስጥ ይጨመራሉ።""",
            reply_markup=MAIN_MENU,
        )
        return


# ---------------- RUN BOT ----------------

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN በ Railway Variables ውስጥ አልተገኘም።")

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(MessageHandler(filters.CONTACT, receive_contact))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ NEXT STEP BOT is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
