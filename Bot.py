import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import sqlite3
import json

BOT_TOKEN = "8793044253:AAE_x5dh5MOON16vYUsblliyvRtjqwtv1xY"
ADMIN_ID = 7470626131
CHANNEL_INVITE_LINK = "https://t.me/+A6m27qMr7qZjYmNl"
PER_REFER_BONUS = 5.0  # Oru refer-kku kidaikkum amount
WEBAPP_URL = "https://your-domain.com/verify.html"  # Device verify seiyyum HTML link

bot = telebot.TeleBot(BOT_TOKEN)

# Database Setup
conn = sqlite3.connect('referral_bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    referred_by INTEGER,
    device_hash TEXT,
    is_verified INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    upi_id TEXT,
    status TEXT DEFAULT 'PENDING'
)''')
conn.commit()

def is_user_in_channel(user_id):
    try:
        # Private invite link channel aaga irundhaal channel chat id thevaippadum
        # Bot channel-il admin aaga irundhaal get_chat_member velaiseyyum
        member = bot.get_chat_member(chat_id=CHANNEL_INVITE_LINK, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        # Bot invite link vali check seiyya mudiyavittal true endru veikkalaam alladhu channel chat ID podavendum
        return True

def force_join_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📢 Channel-il Inaiyavum", url=CHANNEL_INVITE_LINK))
    markup.add(InlineKeyboardButton("✅ I Have Joined", callback_data="check_join"))
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Anonymous"

    # Ban check
    cursor.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
    user_data = cursor.fetchone()
    if user_data and user_data[0] == 1:
        bot.send_message(user_id, "❌ Ungal account admin-aal thadaikkappattulladhu (Banned).")
        return

    # Referral link check
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1].replace("ref_", ""))
            if ref_id != user_id:
                referrer_id = ref_id
        except ValueError:
            pass

    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, referred_by) VALUES (?, ?, ?)",
                   (user_id, username, referrer_id))
    conn.commit()

    # Step 1: Force Join Check
    if not is_user_in_channel(user_id):
        bot.send_message(user_id, "⚠️ Bot-ai payanpadutha mudhalil engal channel-il inaiya vendum:", reply_markup=force_join_markup())
        return

    check_verification_and_proceed(user_id, message.chat.id)

def check_verification_and_proceed(user_id, chat_id):
    cursor.execute("SELECT is_verified FROM users WHERE user_id=?", (user_id,))
    verified = cursor.fetchone()[0]

    # Step 2: Device verification check
    if not verified:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📱 Verify Device", web_app=WebAppInfo(url=WEBAPP_URL)))
        bot.send_message(chat_id, "🔐 Oru device-kku oru murai mattume refer mudiyum.\nKeezhe ulla button-ai click seidhu ungal device-ai verify seiyavum:", reply_markup=markup)
        return

    show_main_dashboard(chat_id, user_id)

def show_main_dashboard(chat_id, user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]

    bot_me = bot.get_me()
    ref_link = f"https://t.me/{bot_me.username}?start=ref_{user_id}"

    text = f"🎉 **Vanakkam!**\n\n" \
           f"💰 **Ungal Balance:** ₹{bal}\n" \
           f"🔗 **Ungal Unique Referral Link:**\n`{ref_link}`\n\n" \
           f"Ovvoru unmaiyaana refer-kkum ₹{PER_REFER_BONUS} kidaikkum!"

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💳 Withdrawal", callback_data="withdraw"))
    markup.add(InlineKeyboardButton("🔄 Re-check Membership", callback_data="check_join"))
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def on_check_join(call):
    user_id = call.from_user.id
    if is_user_in_channel(user_id):
        bot.answer_callback_query(call.id, "✅ Channel membership urudhi seiyyappattadhu!")
        check_verification_and_proceed(user_id, call.message.chat.id)
    else:
        bot.answer_callback_query(call.id, "❌ Neengal innum channel-il inaiyavillai!", show_alert=True)

# WebApp Data (Device Fingerprint) handle seiyyappadum idam
@bot.message_handler(content_types=['web_app_data'])
def on_device_received(message):
    user_id = message.from_user.id
    data = json.loads(message.web_app_data.data)

    if data.get("action") == "verify_device":
        device_id = data.get("device_id")

        # Idhe device munbe payanpaduthappattulladha endru check seigirom
        cursor.execute("SELECT user_id FROM users WHERE device_hash=? AND user_id!=?", (device_id, user_id))
        already_used = cursor.fetchone()

        if already_used:
            bot.send_message(user_id, "❌ **Niragirikkappattadhu:** Indha device-il munbe oru account payanpaduthappattuvittadhu. Multi-account thadukkappattulladhu.")
            return

        # Pudiya device - verify seigirom
        cursor.execute("UPDATE users SET device_hash=?, is_verified=1 WHERE user_id=?", (device_id, user_id))

        # Referrer-ukku balance sethal
        cursor.execute("SELECT referred_by FROM users WHERE user_id=?", (user_id,))
        ref_user = cursor.fetchone()
        if ref_user and ref_user[0]:
            ref_id = ref_user[0]
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (PER_REFER_BONUS, ref_id))
            try:
                bot.send_message(ref_id, f"🎉 Ungal refer moolam pudhiya user inaindhaar! ₹{PER_REFER_BONUS} balance-il serkkappattadhu.")
            except Exception:
                pass

        conn.commit()
        bot.send_message(user_id, "✅ Ungal device vetrigaramaaga verify seiyyappattadhu!")
        show_main_dashboard(message.chat.id, user_id)

# Admin Panel Commands
@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM withdrawals WHERE status='PENDING'")
    pending_wd = cursor.fetchone()[0]

    report = f"👑 **Admin Control Panel**\n\n" \
             f"👥 Moththa Users: {total_users}\n" \
             f"⏳ Pending Withdrawals: {pending_wd}\n\n" \
             f"Commands:\n" \
             f"`/ban <user_id>` - Account-ai ban seiyya\n" \
             f"`/unban <user_id>` - Account-ai unban seiyya\n" \
             f"`/broadcast <message>` - Ellorukkum seidhi anuppa"
    bot.send_message(ADMIN_ID, report, parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target = int(message.text.split()[1])
        cursor.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (target,))
        conn.commit()
        bot.send_message(ADMIN_ID, f"✅ User `{target}` ban seiyyappattaar.", parse_mode="Markdown")
    except Exception:
        bot.send_message(ADMIN_ID, "Usage: `/ban <user_id>`")

bot.infinity_polling()
      
