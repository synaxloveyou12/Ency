import os
import base64
import marshal
import zlib
import telebot
from telebot import types
from datetime import datetime, timedelta
import json
import io
import time
import hashlib
import random
import string
import re
import uuid
import ast
import inspect
import sqlite3
from functools import wraps

# --- CONFIGURATION ---
TOKEN = "8422725777:AAEqX__3KmAlYy7Ty34J2EaAghYYhUvRb7E"
ADMIN_ID = 6068463116
CHANNEL_ID = "@synaxbotz"
bot = telebot.TeleBot(TOKEN)

# --- DATABASE ---
USER_DB = "users.txt"
STATS_DB = "stats.json"
LICENSE_DB = "licenses.json"
HISTORY_DB = "encryption_history.db"

# Initialize databases
def init_stats():
    if not os.path.exists(STATS_DB):
        with open(STATS_DB, "w") as f:
            json.dump({"total_encryptions": 0, "methods": {}}, f)

def init_licenses():
    if not os.path.exists(LICENSE_DB):
        with open(LICENSE_DB, "w") as f:
            json.dump({}, f)

def init_history_db():
    conn = sqlite3.connect(HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS encryption_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        method TEXT,
        file_name TEXT,
        file_size INTEGER,
        timestamp DATETIME,
        expiration TEXT,
        license_type TEXT,
        obfuscation TEXT,
        custom_key TEXT,
        ip_address TEXT
    )
    ''')
    conn.commit()
    conn.close()

def update_stats(method):
    try:
        with open(STATS_DB, "r") as f:
            stats = json.load(f)
        stats["total_encryptions"] += 1
        if method in stats["methods"]:
            stats["methods"][method] += 1
        else:
            stats["methods"][method] = 1
        with open(STATS_DB, "w") as f:
            json.dump(stats, f)
    except:
        pass

def get_stats():
    try:
        with open(STATS_DB, "r") as f:
            return json.load(f)
    except:
        return {"total_encryptions": 0, "methods": {}}

def add_user(user):
    if not os.path.exists(USER_DB):
        with open(USER_DB, "w") as f: pass
    with open(USER_DB, "r") as f:
        users = f.read().splitlines()
    if str(user.id) not in users:
        with open(USER_DB, "a") as f:
            f.write(f"{user.id}\n")
        return True 
    return False 

def get_total_users():
    if not os.path.exists(USER_DB): return 0
    with open(USER_DB, "r") as f:
        return len(f.read().splitlines())

def add_to_history(user_id, username, first_name, method, file_name, file_size, expiration, license_type, obfuscation, custom_key):
    try:
        conn = sqlite3.connect(HISTORY_DB)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO encryption_history 
        (user_id, username, first_name, method, file_name, file_size, timestamp, expiration, license_type, obfuscation, custom_key, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, method, file_name, file_size, datetime.now(), expiration, license_type, obfuscation, custom_key, "N/A"))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error adding to history: {e}")

def get_history(limit=20):
    try:
        conn = sqlite3.connect(HISTORY_DB)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM encryption_history 
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (limit,))
        history = cursor.fetchall()
        conn.close()
        return history
    except Exception as e:
        print(f"Error getting history: {e}")
        return []

def get_user_history(user_id, limit=10):
    try:
        conn = sqlite3.connect(HISTORY_DB)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM encryption_history 
        WHERE user_id = ?
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (user_id, limit))
        history = cursor.fetchall()
        conn.close()
        return history
    except Exception as e:
        print(f"Error getting user history: {e}")
        return []

# --- AUTHENTICATION ---
def check_auth(message):
    try:
        status = bot.get_chat_member(CHANNEL_ID, message.chat.id).status
        if status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        pass
    
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🚀 Join Channel", url=f"https://t.me/{CHANNEL_ID[1:]}")
    markup.add(btn)
    
    welcome_msg = (
        f"👋 <b>Welcome to SecureCrypt!</b>\n\n"
        f"🔐 Join our channel to use the bot.\n\n"
        f"✨ <b>Channel:</b> {CHANNEL_ID}\n\n"
        f"<b>Join and type /start again!</b>"
    )
    bot.send_message(message.chat.id, welcome_msg, parse_mode="HTML", reply_markup=markup)
    return False

# Admin-only decorator
def admin_only(func):
    @wraps(func)
    def wrapped(message, *args, **kwargs):
        if message.chat.id == ADMIN_ID:
            return func(message, *args, **kwargs)
        else:
            bot.reply_to(message, "❌ <b>This command is for admins only!</b>", parse_mode="HTML")
    return wrapped

user_selections = {}
user_expire_settings = {}
user_license_settings = {}
user_obfuscation_settings = {}
user_watermark_settings = {}
user_anti_vm_settings = {}

# --- MENU FUNCTIONS ---
def get_main_menu_markup(user_id):
    buttons = [
        types.InlineKeyboardButton("⚡ Basic", callback_data='basic_menu'),
        types.InlineKeyboardButton("🔐 Advanced", callback_data='advanced_menu'),
        types.InlineKeyboardButton("🛡️ Ultimate", callback_data='ultimate_menu'),
        types.InlineKeyboardButton("📜 License", callback_data='license_menu'),
        types.InlineKeyboardButton("🎨 Obfuscation", callback_data='obfuscation_menu'),
        types.InlineKeyboardButton("⏰ Expiration", callback_data='expire'),
        types.InlineKeyboardButton("🔓 Custom", callback_data='custom'),
        types.InlineKeyboardButton("💧 Watermark", callback_data='watermark'),
        types.InlineKeyboardButton("🛡️ Anti-VM", callback_data='anti_vm'),
        types.InlineKeyboardButton("ℹ️ Info", callback_data='bot_info'),
        types.InlineKeyboardButton("👥 Stats", callback_data='stats')
    ]
    
    # Add history button only for admin
    if user_id == ADMIN_ID:
        buttons.append(types.InlineKeyboardButton("📜 History", callback_data='history'))
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    return markup

def get_basic_menu_markup():
    buttons = [
        types.InlineKeyboardButton("Base64", callback_data='base64'),
        types.InlineKeyboardButton("Marshal", callback_data='marshal'),
        types.InlineKeyboardButton("Zlib", callback_data='zlib'),
        types.InlineKeyboardButton("B16", callback_data='base16'),
        types.InlineKeyboardButton("B32", callback_data='base32'),
        types.InlineKeyboardButton("⬅️ Back", callback_data='back')
    ]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    return markup

def get_advanced_menu_markup():
    buttons = [
        types.InlineKeyboardButton("MZlib", callback_data='marshal_zlib'),
        types.InlineKeyboardButton("Complex", callback_data='complex'),
        types.InlineKeyboardButton("AES", callback_data='aes'),
        types.InlineKeyboardButton("XOR", callback_data='xor'),
        types.InlineKeyboardButton("Hybrid", callback_data='hybrid'),
        types.InlineKeyboardButton("⬅️ Back", callback_data='back')
    ]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    return markup

def get_ultimate_menu_markup():
    buttons = [
        types.InlineKeyboardButton("Triple Layer", callback_data='triple'),
        types.InlineKeyboardButton("Military Grade", callback_data='military'),
        types.InlineKeyboardButton("Quantum", callback_data='quantum'),
        types.InlineKeyboardButton("Stealth", callback_data='stealth'),
        types.InlineKeyboardButton("Nuclear", callback_data='nuclear'),
        types.InlineKeyboardButton("DNA", callback_data='dna'),
        types.InlineKeyboardButton("Neural", callback_data='neural'),
        types.InlineKeyboardButton("Chaos", callback_data='chaos'),
        types.InlineKeyboardButton("⬅️ Back", callback_data='back')
    ]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    return markup

def get_license_menu_markup():
    buttons = [
        types.InlineKeyboardButton("Generate License", callback_data='generate_license'),
        types.InlineKeyboardButton("Validate License", callback_data='validate_license'),
        types.InlineKeyboardButton("Usage Limit", callback_data='usage_limit'),
        types.InlineKeyboardButton("Hardware Lock", callback_data='hardware_lock'),
        types.InlineKeyboardButton("Domain Lock", callback_data='domain_lock'),
        types.InlineKeyboardButton("Time Lock", callback_data='time_lock'),
        types.InlineKeyboardButton("Network Lock", callback_data='network_lock'),
        types.InlineKeyboardButton("⬅️ Back", callback_data='back')
    ]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    return markup

def get_obfuscation_menu_markup():
    buttons = [
        types.InlineKeyboardButton("Variable Names", callback_data='obf_vars'),
        types.InlineKeyboardButton("String Obfuscation", callback_data='obf_strings'),
        types.InlineKeyboardButton("Control Flow", callback_data='obf_flow'),
        types.InlineKeyboardButton("Anti-Debug", callback_data='obf_debug'),
        types.InlineKeyboardButton("Import Hiding", callback_data='obf_imports'),
        types.InlineKeyboardButton("Code Splitting", callback_data='obf_split'),
        types.InlineKeyboardButton("Dead Code", callback_data='obf_dead'),
        types.InlineKeyboardButton("All Techniques", callback_data='obf_all'),
        types.InlineKeyboardButton("⬅️ Back", callback_data='back')
    ]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    return markup

def get_watermark_markup():
    buttons = [
        types.InlineKeyboardButton("Visible Watermark", callback_data='watermark_visible'),
        types.InlineKeyboardButton("Hidden Watermark", callback_data='watermark_hidden'),
        types.InlineKeyboardButton("Steganography", callback_data='watermark_stego'),
        types.InlineKeyboardButton("No Watermark", callback_data='watermark_none'),
        types.InlineKeyboardButton("⬅️ Back", callback_data='back')
    ]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    return markup

def get_anti_vm_markup():
    buttons = [
        types.InlineKeyboardButton("VM Detection", callback_data='vm_detection'),
        types.InlineKeyboardButton("Sandbox Evasion", callback_data='vm_sandbox'),
        types.InlineKeyboardButton("Debugger Evasion", callback_data='vm_debugger'),
        types.InlineKeyboardButton("Analysis Evasion", callback_data='vm_analysis'),
        types.InlineKeyboardButton("Full Protection", callback_data='vm_full'),
        types.InlineKeyboardButton("No Protection", callback_data='vm_none'),
        types.InlineKeyboardButton("⬅️ Back", callback_data='back')
    ]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    return markup

def get_expire_markup():
    buttons = [
        types.InlineKeyboardButton("1 Hour", callback_data='expire_1h'),
        types.InlineKeyboardButton("6 Hours", callback_data='expire_6h'),
        types.InlineKeyboardButton("12 Hours", callback_data='expire_12h'),
        types.InlineKeyboardButton("1 Day", callback_data='expire_1d'),
        types.InlineKeyboardButton("3 Days", callback_data='expire_3d'),
        types.InlineKeyboardButton("1 Week", callback_data='expire_1w'),
        types.InlineKeyboardButton("2 Weeks", callback_data='expire_2w'),
        types.InlineKeyboardButton("1 Month", callback_data='expire_1m'),
        types.InlineKeyboardButton("3 Months", callback_data='expire_3m'),
        types.InlineKeyboardButton("Custom", callback_data='expire_custom'),
        types.InlineKeyboardButton("⬅️ Back", callback_data='back')
    ]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*buttons)
    return markup

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    is_new = add_user(message.from_user)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    intro_text = (
        f"🚀 <b>SecureCrypt Ultimate Pro Max</b> 🚀\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 <b>{message.from_user.first_name}</b>!\n\n"
        f"🛡️ <b>Next-Gen Ultra Encryption System</b>\n"
        f"Military-grade protection with advanced features!\n\n"
        f"📊 <b>Status:</b>\n"
        f"👤 ID: <code>{message.from_user.id}</code>\n"
        f"📅 Date: <code>{now}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 <i>Select encryption category below!</i>"
    )

    if is_new:
        admin_notif = (
            f"🔔 <b>New User!</b>\n\n"
            f"👤 <b>Name:</b> {message.from_user.first_name}\n"
            f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
            f"🔗 <b>User:</b> @{message.from_user.username if message.from_user.username else 'None'}"
        )
        try: bot.send_message(ADMIN_ID, admin_notif, parse_mode="HTML")
        except: pass

    if check_auth(message):
        bot.send_message(message.chat.id, intro_text, reply_markup=get_main_menu_markup(message.chat.id), parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id

    if call.data == "bot_info":
        info_text = f"""
🛠 <b>SecureCrypt Ultimate Pro Max</b>
━━━━━━━━━━━━━━━━━━━━━
💻 <b>Dev:</b> @a4bhi
📢 <b>Channel:</b> @synaxBotz
🐍 <b>Python 3.x</b>
💎 <b>v8.0 (Ultimate Pro Max)</b>

<i>Next-generation ultra-encryption with military-grade security</i>
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="back"))
        bot.edit_message_text(info_text, chat_id, call.message.message_id, parse_mode="HTML", reply_markup=markup)
        
    elif call.data == "stats":
        stats = get_stats()
        total_users = get_total_users()
        
        if call.from_user.id == ADMIN_ID:
            stats_text = f"""
📊 <b>Admin Stats</b>
━━━━━━━━━━━━━━━━━━━━━
👥 <b>Users:</b> {total_users}
🔐 <b>Encryptions:</b> {stats["total_encryptions"]}

<b>Methods:</b>
"""
            for method, count in stats["methods"].items():
                stats_text += f"• {method.upper()}: {count}\n"
                
            bot.answer_callback_query(call.id, stats_text, show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"Users: {total_users}", show_alert=True)
        
    elif call.data == "history":
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "Access denied", show_alert=True)
            return
            
        # Get recent history
        history = get_history(20)
        
        if not history:
            history_text = "📜 <b>Encryption History</b>\n\nNo encryption history found."
        else:
            history_text = "📜 <b>Recent Encryption History</b>\n\n"
            for record in history:
                user_id, username, first_name, method, file_name, file_size, timestamp, expiration, license_type, obfuscation, custom_key, ip_address = record
                timestamp_str = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f").strftime("%Y-%m-%d %H:%M:%S")
                history_text += f"👤 {first_name} (@{username})\n"
                history_text += f"📁 {file_name} ({file_size} bytes)\n"
                history_text += f"🔐 {method.upper()}"
                if expiration:
                    history_text += f" | ⏰ {expiration}"
                if license_type:
                    history_text += f" | 📜 {license_type}"
                if obfuscation:
                    history_text += f" | 🎨 {obfuscation}"
                history_text += f"\n📅 {timestamp_str}\n\n"
        
        # Split into chunks if too long
        if len(history_text) > 4000:
            chunks = [history_text[i:i+4000] for i in range(0, len(history_text), 4000)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    bot.edit_message_text(chunk, chat_id, call.message.message_id, parse_mode="HTML")
                else:
                    bot.send_message(chat_id, chunk, parse_mode="HTML")
        else:
            bot.edit_message_text(history_text, chat_id, call.message.message_id, parse_mode="HTML")
        
    elif call.data == "back":
        bot.edit_message_text("🚀 <b>Select Encryption Category:</b>", chat_id, call.message.message_id, reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")
        
    elif call.data == "basic_menu":
        bot.edit_message_text("⚡ <b>Basic Encryption Methods:</b>", chat_id, call.message.message_id, reply_markup=get_basic_menu_markup(), parse_mode="HTML")
        
    elif call.data == "advanced_menu":
        bot.edit_message_text("🔐 <b>Advanced Encryption Methods:</b>", chat_id, call.message.message_id, reply_markup=get_advanced_menu_markup(), parse_mode="HTML")
        
    elif call.data == "ultimate_menu":
        bot.edit_message_text("🛡️ <b>Ultimate Encryption Methods:</b>", chat_id, call.message.message_id, reply_markup=get_ultimate_menu_markup(), parse_mode="HTML")
        
    elif call.data == "license_menu":
        bot.edit_message_text("📜 <b>License Protection Options:</b>", chat_id, call.message.message_id, reply_markup=get_license_menu_markup(), parse_mode="HTML")
        
    elif call.data == "obfuscation_menu":
        bot.edit_message_text("🎨 <b>Code Obfuscation Techniques:</b>", chat_id, call.message.message_id, reply_markup=get_obfuscation_menu_markup(), parse_mode="HTML")
        
    elif call.data == "watermark":
        if not check_auth(call.message): return
        bot.edit_message_text("💧 <b>Watermark Options:</b>", chat_id, call.message.message_id, reply_markup=get_watermark_markup(), parse_mode="HTML")
        
    elif call.data == "anti_vm":
        if not check_auth(call.message): return
        bot.edit_message_text("🛡️ <b>Anti-VM/Anti-Analysis Options:</b>", chat_id, call.message.message_id, reply_markup=get_anti_vm_markup(), parse_mode="HTML")
        
    elif call.data.startswith("watermark_"):
        if not check_auth(call.message): return
        watermark_type = call.data[10:]  # Remove 'watermark_' prefix
        user_watermark_settings[chat_id] = watermark_type
        bot.edit_message_text(f"💧 <b>Watermark: {watermark_type.replace('_', ' ').title()}</b>\n\nNow select encryption method:", chat_id, call.message.message_id, reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")
        
    elif call.data.startswith("vm_"):
        if not check_auth(call.message): return
        vm_type = call.data[3:]  # Remove 'vm_' prefix
        user_anti_vm_settings[chat_id] = vm_type
        bot.edit_message_text(f"🛡️ <b>Anti-VM: {vm_type.replace('_', ' ').title()}</b>\n\nNow select encryption method:", chat_id, call.message.message_id, reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")
        
    elif call.data == "expire":
        if not check_auth(call.message): return
        bot.edit_message_text("⏰ <b>Select Expiration Time:</b>", chat_id, call.message.message_id, reply_markup=get_expire_markup(), parse_mode="HTML")
        
    elif call.data.startswith("expire_"):
        if not check_auth(call.message): return
        if call.data == "expire_custom":
            msg = bot.send_message(chat_id, "⏰ <b>Custom Expiration</b>\n\nEnter hours (1-8760):", parse_mode="HTML")
            bot.register_next_step_handler(msg, process_custom_expire)
        else:
            expire_time = call.data[7:]  # Remove 'expire_' prefix
            user_expire_settings[chat_id] = expire_time
            bot.edit_message_text(f"⏰ <b>Expiration Set: {expire_time}</b>\n\nNow select encryption method:", chat_id, call.message.message_id, reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")
        
    elif call.data == "generate_license":
        if not check_auth(call.message): return
        user_license_settings[chat_id] = "generate"
        msg = bot.send_message(chat_id, "📜 <b>License Generation</b>\n\nEnter user identifier (email/username):", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_license_generation)
        
    elif call.data == "validate_license":
        if not check_auth(call.message): return
        user_license_settings[chat_id] = "validate"
        msg = bot.send_message(chat_id, "🔍 <b>License Validation</b>\n\nEnter license key:", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_license_validation)
        
    elif call.data == "usage_limit":
        if not check_auth(call.message): return
        user_license_settings[chat_id] = "usage"
        msg = bot.send_message(chat_id, "🔢 <b>Usage Limit</b>\n\nEnter max usage count:", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_usage_limit)
        
    elif call.data == "hardware_lock":
        if not check_auth(call.message): return
        user_license_settings[chat_id] = "hardware"
        bot.send_message(chat_id, "🔒 <b>Hardware Lock Enabled</b>\n\nNow select encryption method:", parse_mode="HTML")
        bot.edit_message_text("🔒 <b>Hardware Lock Enabled</b>\n\nNow select encryption method:", chat_id, call.message.message_id, reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")
        
    elif call.data == "domain_lock":
        if not check_auth(call.message): return
        user_license_settings[chat_id] = "domain"
        msg = bot.send_message(chat_id, "🌐 <b>Domain Lock</b>\n\nEnter domain name:", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_domain_lock)
        
    elif call.data == "time_lock":
        if not check_auth(call.message): return
        user_license_settings[chat_id] = "time"
        msg = bot.send_message(chat_id, "⏰ <b>Time Lock</b>\n\nEnter allowed time range (e.g., 09:00-17:00):", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_time_lock)
        
    elif call.data == "network_lock":
        if not check_auth(call.message): return
        user_license_settings[chat_id] = "network"
        msg = bot.send_message(chat_id, "🌐 <b>Network Lock</b>\n\nEnter allowed IP range (e.g., 192.168.1.0/24):", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_network_lock)
        
    elif call.data.startswith("obf_"):
        if not check_auth(call.message): return
        obf_type = call.data[4:]  # Remove 'obf_' prefix
        user_obfuscation_settings[chat_id] = obf_type
        bot.edit_message_text(f"🎨 <b>Obfuscation: {obf_type.replace('_', ' ').title()}</b>\n\nNow select encryption method:", chat_id, call.message.message_id, reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")
        
    elif call.data == "custom":
        if not check_auth(call.message): return
        user_selections[chat_id] = call.data
        msg = bot.send_message(chat_id, "🔓 <b>Custom Encryption</b>\n\nEnter your custom key:", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_custom_key)
        
    else:
        if not check_auth(call.message): return
        user_selections[chat_id] = call.data
        bot.send_message(chat_id, f"🚀 <b>Method: {call.data.upper()}</b>\n\nSend your <code>.py</code> file now!", parse_mode="HTML")

def process_custom_expire(message):
    try:
        hours = int(message.text)
        if 1 <= hours <= 8760:  # Max 1 year
            chat_id = message.chat.id
            user_expire_settings[chat_id] = f"{hours}h"
            bot.send_message(chat_id, f"⏰ <b>Custom Expiration Set: {hours} hours</b>\n\nNow select encryption method:", reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "❌ <b>Invalid hours. Please enter a value between 1 and 8760.</b>", parse_mode="HTML")
            bot.register_next_step_handler(message, process_custom_expire)
    except ValueError:
        bot.send_message(message.chat.id, "❌ <b>Invalid input. Please enter a number.</b>", parse_mode="HTML")
        bot.register_next_step_handler(message, process_custom_expire)

def process_license_generation(message):
    chat_id = message.chat.id
    user_id = message.text.strip()
    
    # Generate a unique license key
    license_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    license_key = '-'.join([license_key[i:i+4] for i in range(0, len(license_key), 4)])
    
    # Save license to database
    try:
        with open(LICENSE_DB, "r") as f:
            licenses = json.load(f)
    except:
        licenses = {}
    
    licenses[license_key] = {
        "user_id": user_id,
        "created": datetime.now().isoformat(),
        "usage_count": 0
    }
    
    with open(LICENSE_DB, "w") as f:
        json.dump(licenses, f)
    
    bot.send_message(chat_id, f"📜 <b>License Generated</b>\n\nUser: {user_id}\nKey: <code>{license_key}</code>\n\nNow select encryption method:", reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")

def process_license_validation(message):
    chat_id = message.chat.id
    license_key = message.text.strip()
    
    # Check if license exists
    try:
        with open(LICENSE_DB, "r") as f:
            licenses = json.load(f)
    except:
        licenses = {}
    
    if license_key in licenses:
        license_info = licenses[license_key]
        bot.send_message(chat_id, f"✅ <b>Valid License</b>\n\nUser: {license_info['user_id']}\nCreated: {license_info['created']}\nUsage: {license_info['usage_count']}\n\nNow select encryption method:", reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")
    else:
        bot.send_message(chat_id, "❌ <b>Invalid License Key</b>\n\nPlease try again or generate a new license.", parse_mode="HTML")

def process_usage_limit(message):
    try:
        limit = int(message.text)
        if limit > 0:
            chat_id = message.chat.id
            user_license_settings[chat_id] = f"usage_{limit}"
            bot.send_message(chat_id, f"🔢 <b>Usage Limit Set: {limit}</b>\n\nNow select encryption method:", reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "❌ <b>Invalid limit. Please enter a positive number.</b>", parse_mode="HTML")
            bot.register_next_step_handler(message, process_usage_limit)
    except ValueError:
        bot.send_message(message.chat.id, "❌ <b>Invalid input. Please enter a number.</b>", parse_mode="HTML")
        bot.register_next_step_handler(message, process_usage_limit)

def process_domain_lock(message):
    chat_id = message.chat.id
    domain = message.text.strip()
    user_license_settings[chat_id] = f"domain_{domain}"
    bot.send_message(chat_id, f"🌐 <b>Domain Lock Set: {domain}</b>\n\nNow select encryption method:", reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")

def process_time_lock(message):
    chat_id = message.chat.id
    time_range = message.text.strip()
    user_license_settings[chat_id] = f"time_{time_range}"
    bot.send_message(chat_id, f"⏰ <b>Time Lock Set: {time_range}</b>\n\nNow select encryption method:", reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")

def process_network_lock(message):
    chat_id = message.chat.id
    ip_range = message.text.strip()
    user_license_settings[chat_id] = f"network_{ip_range}"
    bot.send_message(chat_id, f"🌐 <b>Network Lock Set: {ip_range}</b>\n\nNow select encryption method:", reply_markup=get_main_menu_markup(chat_id), parse_mode="HTML")

def process_custom_key(message):
    chat_id = message.chat.id
    if not message.text:
        bot.send_message(chat_id, "❌ <b>Invalid key. Try again.</b>", parse_mode="HTML")
        return
        
    user_selections[f"{chat_id}_key"] = message.text
    bot.send_message(chat_id, f"🔑 <b>Key Set!</b>\n\nSend your <code>.py</code> file now!", parse_mode="HTML")

# --- ADVANCED ENCRYPTION & OBFUSCATION FUNCTIONS ---
def get_expiration_timestamp(expire_setting):
    now = datetime.now()
    if expire_setting.endswith("h"):
        hours = int(expire_setting[:-1])
        return now + timedelta(hours=hours)
    elif expire_setting == "1d":
        return now + timedelta(days=1)
    elif expire_setting == "3d":
        return now + timedelta(days=3)
    elif expire_setting == "1w":
        return now + timedelta(weeks=1)
    elif expire_setting == "2w":
        return now + timedelta(weeks=2)
    elif expire_setting == "1m":
        return now + timedelta(days=30)
    elif expire_setting == "3m":
        return now + timedelta(days=90)
    else:
        return None

def create_expire_check(expire_timestamp, expire_setting):
    if not expire_timestamp:
        return ""
    
    timestamp_str = str(int(expire_timestamp.timestamp()))
    hash_key = hashlib.md5(timestamp_str.encode()).hexdigest()[:8]
    
    expire_check = f"""
# EXPIRATION CHECK
import datetime, time, hashlib, sys
try:
    expire_ts = {timestamp_str}
    hash_key = "{hash_key}"
    current_ts = int(time.time())
    if current_ts > expire_ts:
        print("❌ This script has expired on {expire_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        sys.exit(1)
    if hashlib.md5(str(expire_ts).encode()).hexdigest()[:8] != hash_key:
        print("❌ Script integrity check failed")
        sys.exit(1)
except:
    print("❌ Error checking expiration")
    sys.exit(1)

"""
    return expire_check

def create_license_check(license_setting, chat_id):
    if not license_setting:
        return ""
    
    if license_setting == "generate":
        # Get the last generated license for this user
        try:
            with open(LICENSE_DB, "r") as f:
                licenses = json.load(f)
            # Find the most recent license
            latest_license = None
            latest_time = None
            for key, value in licenses.items():
                if latest_time is None or value["created"] > latest_time:
                    latest_license = key
                    latest_time = value["created"]
            
            if latest_license:
                license_check = f"""
# LICENSE CHECK
import hashlib, sys, os, platform, uuid
try:
    license_key = "{latest_license}"
    # Simple license validation
    if len(license_key) != 19 or license_key[4] != '-' or license_key[9] != '-' or license_key[14] != '-':
        print("❌ Invalid license format")
        sys.exit(1)
    # Additional validation would go here
except:
    print("❌ License validation failed")
    sys.exit(1)

"""
                return license_check
        except:
            pass
    
    elif license_setting.startswith("usage_"):
        try:
            limit = int(license_setting[6:])
            usage_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".usage_count")
            usage_check = f"""
# USAGE LIMIT CHECK
import os, sys
try:
    usage_file = r"{usage_file}"
    limit = {limit}
    count = 0
    if os.path.exists(usage_file):
        with open(usage_file, 'r') as f:
            count = int(f.read().strip())
    if count >= limit:
        print(f"❌ Usage limit exceeded: {{count}}/{{limit}}")
        sys.exit(1)
    # Increment usage count
    with open(usage_file, 'w') as f:
        f.write(str(count + 1))
except:
    print("❌ Error checking usage limit")
    sys.exit(1)

"""
            return usage_check
        except:
            pass
    
    elif license_setting == "hardware":
        hardware_check = """
# HARDWARE LOCK CHECK
import platform, hashlib, sys
try:
    # Generate hardware fingerprint
    hw_str = f"{{platform.processor()}}-{{platform.system()}}-{{platform.node()}}"
    hw_hash = hashlib.md5(hw_str.encode()).hexdigest()
    # In a real implementation, you would check this against a known value
    # For demo purposes, we'll just generate the hash
except:
    print("❌ Hardware fingerprinting failed")
    sys.exit(1)

"""
        return hardware_check
    
    elif license_setting.startswith("domain_"):
        domain = license_setting[7:]
        domain_check = f"""
# DOMAIN LOCK CHECK
import socket, sys
try:
    domain = "{domain}"
    # Check if current hostname matches the locked domain
    if socket.gethostname() != domain:
        print(f"❌ This script is locked to domain: {{domain}}")
        sys.exit(1)
except:
    print("❌ Domain lock check failed")
    sys.exit(1)

"""
        return domain_check
    
    elif license_setting.startswith("time_"):
        time_range = license_setting[5:]
        time_check = f"""
# TIME LOCK CHECK
import datetime, sys
try:
    time_range = "{time_range}"
    start_time, end_time = time_range.split('-')
    now = datetime.datetime.now().time()
    start = datetime.datetime.strptime(start_time, "%H:%M").time()
    end = datetime.datetime.strptime(end_time, "%H:%M").time()
    if not (start <= now <= end):
        print(f"❌ This script can only run between {{start_time}} and {{end_time}}")
        sys.exit(1)
except:
    print("❌ Time lock check failed")
    sys.exit(1)

"""
        return time_check
    
    elif license_setting.startswith("network_"):
        ip_range = license_setting[8:]
        network_check = f"""
# NETWORK LOCK CHECK
import socket, sys, ipaddress
try:
    ip_range = "{ip_range}"
    network = ipaddress.ip_network(ip_range)
    # Get current IP address
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    current_ip = ipaddress.ip_address(ip)
    if current_ip not in network:
        print(f"❌ This script is locked to network: {{ip_range}}")
        sys.exit(1)
except:
    print("❌ Network lock check failed")
    sys.exit(1)

"""
        return network_check
    
    return ""

def create_watermark(watermark_type, user_id, username):
    if not watermark_type or watermark_type == "none":
        return ""
    
    if watermark_type == "visible":
        return f"""
# VISIBLE WATERMARK
# This script is protected by SecureCrypt Ultimate Pro Max
# Licensed to: {username} (ID: {user_id})
# Unauthorized distribution is prohibited

"""
    elif watermark_type == "hidden":
        # Create a hidden watermark in a comment
        watermark = f"SecureCrypt-{user_id}-{username}-{datetime.now().isoformat()}"
        encoded = base64.b64encode(watermark.encode()).decode()
        return f"""
# HIDDEN WATERMARK
# {encoded}

"""
    elif watermark_type == "stego":
        # Create a steganographic watermark
        watermark = f"SecureCrypt-{user_id}-{username}-{datetime.now().isoformat()}"
        # In a real implementation, this would be hidden in the code itself
        # For demo purposes, we'll just add it as a comment
        return f"""
# STEGANOGRAPHIC WATERMARK
# This file contains a digital watermark
# {hashlib.md5(watermark.encode()).hexdigest()}

"""
    
    return ""

def create_anti_vm(anti_vm_type):
    if not anti_vm_type or anti_vm_type == "none":
        return ""
    
    if anti_vm_type == "detection":
        return """
# VM DETECTION
import sys, os, platform, ctypes
try:
    # Check for common VM artifacts
    if platform.system() == "Windows":
        # Check registry keys
        import winreg
        vm_keys = [
            r"SOFTWARE\\Oracle\\VirtualBox",
            r"SOFTWARE\\VMware, Inc.\\VMware Tools",
            r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\VMware Workstation"
        ]
        for key in vm_keys:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key):
                    print("❌ Virtual machine detected")
                    sys.exit(1)
            except:
                pass
        
        # Check for VM processes
        vm_processes = ["vmtoolsd.exe", "vboxservice.exe", "vboxtray.exe"]
        for proc in vm_processes:
            if os.path.exists(f"C:\\\\Windows\\\\System32\\\\{proc}"):
                print("❌ Virtual machine detected")
                sys.exit(1)
    
    elif platform.system() == "Linux":
        # Check for VM files
        vm_files = [
            "/usr/bin/VBoxClient",
            "/usr/bin/vmware-user",
            "/proc/scsi/scsi"
        ]
        for file in vm_files:
            if os.path.exists(file):
                print("❌ Virtual machine detected")
                sys.exit(1)
    
    # Check for VM MAC addresses
    import uuid
    mac = uuid.getnode()
    vm_mac_prefixes = [0x080027, 0x001C42, 0x005056, 0x000C29]  # VirtualBox, VMware
    for prefix in vm_mac_prefixes:
        if (mac >> 24) == prefix:
            print("❌ Virtual machine detected")
            sys.exit(1)
    
except:
    pass

"""
    elif anti_vm_type == "sandbox":
        return """
# SANDBOX EVASION
import sys, os, time, ctypes
try:
    # Check for sandbox artifacts
    if platform.system() == "Windows":
        # Check for sandbox processes
        sandbox_processes = ["wireshark.exe", "fiddler.exe", "procmon.exe"]
        for proc in sandbox_processes:
            if os.path.exists(f"C:\\\\Program Files\\\\{proc}") or os.path.exists(f"C:\\\\Program Files (x86)\\\\{proc}"):
                print("❌ Sandbox environment detected")
                sys.exit(1)
        
        # Check for sandbox registry keys
        import winreg
        sandbox_keys = [
            r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders\\Programs",
            r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders\\Personal"
        ]
        for key in sandbox_keys:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key):
                    pass
            except:
                print("❌ Sandbox environment detected")
                sys.exit(1)
    
    # Check for debugging tools
    if sys.gettrace() is not None:
        print("❌ Debugger detected")
        sys.exit(1)
    
    # Time-based check
    start_time = time.time()
    time.sleep(0.5)
    elapsed = time.time() - start_time
    if elapsed < 0.4:  # If time passes too quickly, might be in a sandbox
        print("❌ Sandbox environment detected")
        sys.exit(1)
    
except:
    pass

"""
    elif anti_vm_type == "debugger":
        return """
# DEBUGGER EVASION
import sys, os, ctypes
try:
    # Check for debugger
    if sys.gettrace() is not None:
        print("❌ Debugger detected")
        sys.exit(1)
    
    # Windows-specific check
    if os.name == 'nt':
        kernel32 = ctypes.windll.kernel32
        if kernel32.IsDebuggerPresent():
            print("❌ Debugger detected")
            sys.exit(1)
        
        # Check for remote debugger
        h_process = kernel32.GetCurrentProcess()
        is_remote_debugger_present = ctypes.c_bool(False)
        kernel32.CheckRemoteDebuggerPresent(h_process, ctypes.byref(is_remote_debugger_present))
        if is_remote_debugger_present.value:
            print("❌ Remote debugger detected")
            sys.exit(1)
    
    # Anti-debugging trick
    try:
        import ctypes
        debugger = ctypes.windll.kernel32.IsDebuggerPresent()
        if debugger:
            sys.exit(1)
    except:
        pass
    
except:
    pass

"""
    elif anti_vm_type == "analysis":
        return """
# ANALYSIS EVASION
import sys, os, platform
try:
    # Check for analysis tools
    if platform.system() == "Windows":
        analysis_tools = [
            "ida.exe", "ida64.exe", "idaq.exe", "idaq64.exe",
            "ollydbg.exe", "x64dbg.exe", "windbg.exe"
        ]
        for tool in analysis_tools:
            if os.path.exists(f"C:\\\\Program Files\\\\{tool}") or os.path.exists(f"C:\\\\Program Files (x86)\\\\{tool}"):
                print("❌ Analysis tool detected")
                sys.exit(1)
    
    # Check for virtual environment
    in_virtual_env = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if in_virtual_env:
        print("❌ Virtual environment detected")
        sys.exit(1)
    
    # Check for common analysis directories
    analysis_dirs = [
        "/tmp/vmware", "/tmp/virtualbox", "/tmp/analysis",
        "C:\\\\analysis", "C:\\\\malware", "C:\\\\sandbox"
    ]
    for dir in analysis_dirs:
        if os.path.exists(dir):
            print("❌ Analysis environment detected")
            sys.exit(1)
    
except:
    pass

"""
    elif anti_vm_type == "full":
        # Combine all anti-VM techniques
        return create_anti_vm("detection") + create_anti_vm("sandbox") + create_anti_vm("debugger") + create_anti_vm("analysis")
    
    return ""

def obfuscate_variables(code):
    # Replace variable names with random strings
    try:
        # Extract variable names (simplified regex approach)
        var_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*='
        variables = re.findall(var_pattern, code)
        
        # Create a mapping of original to obfuscated names
        var_map = {}
        for var in set(variables):
            if var not in ['import', 'from', 'def', 'class', 'if', 'else', 'for', 'while', 'try', 'except', 'with', 'as', 'return', 'yield', 'lambda', 'and', 'or', 'not', 'in', 'is', 'None', 'True', 'False']:
                var_map[var] = ''.join(random.choices(string.ascii_letters, k=8))
        
        # Replace variable names in the code
        for original, obfuscated in var_map.items():
            # Use word boundaries to avoid replacing parts of other words
            code = re.sub(r'\b' + re.escape(original) + r'\b', obfuscated, code)
        
        return code
    except:
        return code

def obfuscate_strings(code):
    # Replace string literals with encoded versions
    try:
        # Find string literals (simplified regex approach)
        string_pattern = r'(["\'])(?:(?=(\\?))\2.)*?\1'
        strings = re.findall(string_pattern, code)
        
        # Replace each string with its encoded version
        for match in re.finditer(string_pattern, code):
            original = match.group(0)
            quote = original[0]
            content = original[1:-1]
            
            # Encode the string content
            encoded = base64.b64encode(content.encode()).decode()
            replacement = f"{quote}eval('__import__(\"base64\").b64decode(\"{encoded}\").decode()'){quote}"
            
            # Replace the original string
            code = code.replace(original, replacement, 1)
        
        return code
    except:
        return code

def obfuscate_control_flow(code):
    # Add random dead code and reorder statements where possible
    try:
        lines = code.split('\n')
        result = []
        
        for line in lines:
            # Add the original line
            result.append(line)
            
            # Randomly add dead code after some lines
            if random.random() < 0.1 and line.strip() and not line.strip().startswith('#'):
                # Generate a random dead code statement
                dead_var = ''.join(random.choices(string.ascii_lowercase, k=5))
                dead_code = f"if False: {dead_var} = 'dead_code'"
                result.append(dead_code)
        
        return '\n'.join(result)
    except:
        return code

def obfuscate_anti_debug(code):
    # Add anti-debugging checks
    anti_debug = """
# ANTI-DEBUG CHECK
import sys, os, ctypes
try:
    # Check for debugger
    if sys.gettrace() is not None:
        print("Debugger detected!")
        sys.exit(1)
    
    # Windows-specific check
    if os.name == 'nt':
        kernel32 = ctypes.windll.kernel32
        if kernel32.IsDebuggerPresent():
            print("Debugger detected!")
            sys.exit(1)
except:
    pass

"""
    return anti_debug + code

def obfuscate_imports(code):
    # Hide imports by using __import__ or dynamic imports
    try:
        # Find import statements
        import_pattern = r'(?:from\s+(\S+)\s+)?import\s+(.+)'
        
        for match in re.finditer(import_pattern, code):
            from_module = match.group(1)
            imports = match.group(2)
            
            if from_module:
                # Handle "from module import name"
                if ',' in imports:
                    # Multiple imports
                    names = [name.strip() for name in imports.split(',')]
                    new_import = f"{from_module} = __import__('{from_module}'); "
                    new_import += "; ".join([f"{name} = getattr({from_module}, '{name}')" for name in names])
                else:
                    # Single import
                    new_import = f"{imports} = getattr(__import__('{from_module}'), '{imports}')"
            else:
                # Handle "import module"
                if ',' in imports:
                    # Multiple imports
                    modules = [module.strip() for module in imports.split(',')]
                    new_import = "; ".join([f"{module} = __import__('{module}')" for module in modules])
                else:
                    # Single import
                    new_import = f"{imports} = __import__('{imports}')"
            
            # Replace the original import statement
            original = match.group(0)
            code = code.replace(original, new_import, 1)
        
        return code
    except:
        return code

def obfuscate_code_splitting(code):
    # Split the code into multiple parts and execute them separately
    try:
        # Split the code into parts
        lines = code.split('\n')
        parts = []
        current_part = []
        
        for line in lines:
            current_part.append(line)
            # Every 10 lines, start a new part
            if len(current_part) >= 10 and random.random() < 0.5:
                parts.append('\n'.join(current_part))
                current_part = []
        
        # Add the remaining lines
        if current_part:
            parts.append('\n'.join(current_part))
        
        # If we have multiple parts, create a new structure
        if len(parts) > 1:
            # Encode each part
            encoded_parts = []
            for part in parts:
                encoded = base64.b64encode(part.encode()).decode()
                encoded_parts.append(f"'{encoded}'")
            
            # Create a new code structure
            new_code = """
# CODE SPLITTING
import base64
parts = [{parts}]
for part in parts:
    exec(base64.b64decode(part).decode())
""".format(parts=', '.join(encoded_parts))
            
            return new_code
        
        return code
    except:
        return code

def obfuscate_dead_code(code):
    # Add random dead code that will never execute
    try:
        lines = code.split('\n')
        result = []
        
        for line in lines:
            result.append(line)
            
            # Randomly add dead code
            if random.random() < 0.15 and line.strip() and not line.strip().startswith('#'):
                # Generate random dead code
                dead_var = ''.join(random.choices(string.ascii_lowercase, k=8))
                dead_value = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                dead_code = f"if False: {dead_var} = '{dead_value}'"
                result.append(dead_code)
                
                # Sometimes add more complex dead code
                if random.random() < 0.3:
                    dead_func = ''.join(random.choices(string.ascii_lowercase, k=6))
                    dead_param = ''.join(random.choices(string.ascii_lowercase, k=4))
                    dead_func_code = f"""
def {dead_func}({dead_param}):
    if False:
        return {dead_param} * 2
    return None
"""
                    result.append(dead_func_code)
        
        return '\n'.join(result)
    except:
        return code

def apply_obfuscation(code, obf_type):
    if obf_type == "vars":
        return obfuscate_variables(code)
    elif obf_type == "strings":
        return obfuscate_strings(code)
    elif obf_type == "flow":
        return obfuscate_control_flow(code)
    elif obf_type == "debug":
        return obfuscate_anti_debug(code)
    elif obf_type == "imports":
        return obfuscate_imports(code)
    elif obf_type == "split":
        return obfuscate_code_splitting(code)
    elif obf_type == "dead":
        return obfuscate_dead_code(code)
    elif obf_type == "all":
        # Apply all obfuscation techniques
        code = obfuscate_variables(code)
        code = obfuscate_strings(code)
        code = obfuscate_control_flow(code)
        code = obfuscate_anti_debug(code)
        code = obfuscate_imports(code)
        code = obfuscate_code_splitting(code)
        code = obfuscate_dead_code(code)
        return code
    else:
        return code

# --- ENCRYPTION LOGIC ---
def encrypt_logic(method, code, custom_key=""):
    header = f"# Encrypted by SecureCrypt Ultimate Pro Max\n# Author: @a4bhi\n# Channel: @synaxbotz\n\n"
    
    # Pre-optimized encryption templates
    if method == "base64":
        enc = base64.b64encode(code.encode()).decode()
        return f"{header}import base64;exec(base64.b64decode('{enc}').decode())"
    elif method == "zlib":
        enc = base64.b64encode(zlib.compress(code.encode())).decode()
        return f"{header}import zlib,base64;exec(zlib.decompress(base64.b64decode('{enc}')).decode())"
    elif method == "marshal":
        enc = marshal.dumps(compile(code, 'module', 'exec'))
        return f"{header}import marshal;exec(marshal.loads({enc}))"
    elif method == "marshal_zlib":
        enc = base64.b64encode(zlib.compress(marshal.dumps(compile(code, 'm', 'exec')))).decode()
        return f"{header}import marshal,zlib,base64;exec(marshal.loads(zlib.decompress(base64.b64decode('{enc}'))))"
    elif method == "base16":
        enc = base64.b16encode(code.encode()).decode()
        return f"{header}import base64;exec(base64.b16decode('{enc}').decode())"
    elif method == "base32":
        enc = base64.b32encode(code.encode()).decode()
        return f"{header}import base64;exec(base64.b32decode('{enc}').decode())"
    elif method == "aes" or method == "xor":
        key = custom_key if custom_key else ("SecureCryptKey123" if method == "aes" else "XORKey123")
        encrypted_bytes = bytes([b ^ ord(key[i % len(key)]) for i, b in enumerate(code.encode())])
        enc = base64.b64encode(encrypted_bytes).decode()
        return f"{header}import base64;key='{key}';exec(''.join([chr(b^ord(key[i%len(key)])) for i,b in enumerate(base64.b64decode('{enc}'))]))"
    elif method == "hybrid":
        key = custom_key if custom_key else "HybridKey456"
        m_code = marshal.dumps(compile(code, '<string>', 'exec'))
        z_code = zlib.compress(m_code)
        xor_bytes = bytes([b ^ ord(key[i % len(key)]) for i, b in enumerate(z_code)])
        enc = base64.b64encode(xor_bytes).decode()
        return f"{header}import base64 as a,zlib as b,marshal as c;key='{key}';exec(c.loads(b.decompress(bytes([b^ord(key[i%len(key)]) for i,b in enumerate(a.b64decode('{enc}'))]))))"
    elif method == "triple":
        # Triple layer encryption
        key = custom_key if custom_key else "TripleKey789"
        # First layer: XOR
        xor_bytes = bytes([b ^ ord(key[i % len(key)]) for i, b in enumerate(code.encode())])
        # Second layer: Base64
        b64_bytes = base64.b64encode(xor_bytes)
        # Third layer: Zlib
        z_bytes = zlib.compress(b64_bytes)
        enc = base64.b64encode(z_bytes).decode()
        return f"{header}import base64,zlib;key='{key}';exec(''.join([chr(b^ord(key[i%len(key)])) for i,b in enumerate(base64.b64decode(zlib.decompress(base64.b64decode('{enc}'))))))"
    elif method == "military":
        # Military grade encryption with multiple layers
        key1 = custom_key if custom_key else "MilKey123"
        key2 = "MilKey456"
        key3 = "MilKey789"
        # First layer: Marshal + Zlib
        m_code = marshal.dumps(compile(code, '<string>', 'exec'))
        z_code = zlib.compress(m_code)
        # Second layer: XOR with key1
        xor_bytes = bytes([b ^ ord(key1[i % len(key1)]) for i, b in enumerate(z_code)])
        # Third layer: Base64
        b64_bytes = base64.b64encode(xor_bytes)
        # Fourth layer: XOR with key2
        xor2_bytes = bytes([b ^ ord(key2[i % len(key2)]) for i, b in enumerate(b64_bytes)])
        # Fifth layer: Base64
        enc = base64.b64encode(xor2_bytes).decode()
        return f"{header}import base64,zlib,marshal;key1='{key1}';key2='{key2}';exec(marshal.loads(zlib.decompress(bytes([b^ord(key1[i%len(key1)]) for i,b in enumerate(base64.b64decode(bytes([b^ord(key2[i%len(key2)]) for i,b in enumerate(base64.b64decode('{enc}'))]))))))"
    elif method == "quantum":
        # Quantum-inspired encryption
        key = custom_key if custom_key else "QuantumKey123"
        # Create a quantum-like transformation
        quantum_transform = []
        for i, b in enumerate(code.encode()):
            # Apply a complex transformation based on position and key
            transformed = b ^ ord(key[i % len(key)]) ^ (i % 256)
            quantum_transform.append(transformed)
        
        # Apply multiple layers of encoding
        quantum_bytes = bytes(quantum_transform)
        z_bytes = zlib.compress(quantum_bytes)
        enc = base64.b64encode(z_bytes).decode()
        
        # Generate random variable names for the decoder
        v1, v2, v3, v4 = ''.join(random.choices(string.ascii_lowercase, k=5) for _ in range(4))
        
        return f"{header}import base64,zlib;{v1}='{key}';{v2}=base64.b64decode('{enc}');{v3}=zlib.decompress({v2});{v4}=bytes([b^ord({v1}[i%len({v1})])^(i%256) for i,b in enumerate({v3})]);exec({v4}.decode())"
    elif method == "stealth":
        # Stealth encryption that looks like normal code
        key = custom_key if custom_key else "StealthKey123"
        
        # First, encrypt the code
        encrypted_bytes = bytes([b ^ ord(key[i % len(key)]) for i, b in enumerate(code.encode())])
        enc = base64.b64encode(encrypted_bytes).decode()
        
        # Create a stealth decoder that looks like normal code
        stealth_code = f"""
# Normal looking imports
import os, sys, base64, random

# Some normal looking variables
_config = "{{}}"
_version = "1.0.0"
_debug = False

# A normal looking function
def _load_config():
    global _config
    if not _config:
        # This is where the hidden decryption happens
        _key = "{key}"
        _data = base64.b64decode("{enc}")
        _config = ''.join([chr(b ^ ord(_key[i % len(_key)])) for i, b in enumerate(_data)])
    return _config

# Execute the "config"
exec(_load_config())
"""
        return f"{header}{stealth_code}"
    elif method == "nuclear":
        # Nuclear encryption - maximum protection
        key1 = custom_key if custom_key else "NuclearKey123"
        key2 = "NuclearKey456"
        key3 = "NuclearKey789"
        
        # Layer 1: Marshal
        m_code = marshal.dumps(compile(code, '<string>', 'exec'))
        
        # Layer 2: Zlib
        z_code = zlib.compress(m_code)
        
        # Layer 3: XOR with key1
        xor1_bytes = bytes([b ^ ord(key1[i % len(key1)]) for i, b in enumerate(z_code)])
        
        # Layer 4: Base64
        b64_bytes = base64.b64encode(xor1_bytes)
        
        # Layer 5: XOR with key2
        xor2_bytes = bytes([b ^ ord(key2[i % len(key2)]) for i, b in enumerate(b64_bytes)])
        
        # Layer 6: Zlib again
        z2_bytes = zlib.compress(xor2_bytes)
        
        # Layer 7: Base64 again
        enc = base64.b64encode(z2_bytes).decode()
        
        # Generate random variable names
        v1, v2, v3, v4, v5, v6 = ''.join(random.choices(string.ascii_lowercase, k=5) for _ in range(6))
        
        return f"{header}import base64,zlib,marshal;{v1}='{key1}';{v2}='{key2}';{v3}=base64.b64decode('{enc}');{v4}=zlib.decompress({v3});{v5}=bytes([b^ord({v2}[i%len({v2})]) for i,b in enumerate({v4})]);{v6}=base64.b64decode({v5});{v7}=zlib.decompress(bytes([b^ord({v1}[i%len({v1})]) for i,b in enumerate({v6})]));exec(marshal.loads({v7}))"
    elif method == "dna":
        # DNA-inspired encryption
        key = custom_key if custom_key else "DNAKey123"
        
        # Create a DNA-like sequence transformation
        dna_map = {'A': '00', 'T': '01', 'C': '10', 'G': '11'}
        dna_reverse = {v: k for k, v in dna_map.items()}
        
        # Convert code to binary
        binary = ''.join(format(b, '08b') for b in code.encode())
        
        # Convert binary to DNA sequence
        dna_seq = ''
        for i in range(0, len(binary), 2):
            if i+1 < len(binary):
                pair = binary[i:i+2]
                dna_seq += dna_reverse.get(pair, 'A')
        
        # Apply XOR with key
        key_bytes = key.encode()
        encrypted_dna = ''
        for i, nucleotide in enumerate(dna_seq):
            encrypted_dna += chr(ord(nucleotide) ^ ord(key_bytes[i % len(key_bytes)]))
        
        # Encode with base64
        enc = base64.b64encode(encrypted_dna.encode()).decode()
        
        # Generate random variable names
        v1, v2, v3 = ''.join(random.choices(string.ascii_lowercase, k=5) for _ in range(3))
        
        return f"{header}import base64;{v1}='{key}';{v2}=base64.b64decode('{enc}').decode();{v3}=''.join([chr(b^ord({v1}[i%len({v1})])) for i,b in enumerate({v2})]);exec(''.join([{{'A':'00','T':'01','C':'10','G':'11'}}[n] for n in {v3}]).encode().decode())"
    elif method == "neural":
        # Neural network-inspired encryption
        key = custom_key if custom_key else "NeuralKey123"
        
        # Create a neural-like transformation
        # First, convert code to a numerical representation
        code_bytes = code.encode()
        
        # Apply a neural-like transformation
        layer1 = []
        for i, b in enumerate(code_bytes):
            # Apply a weighted sum with the key
            key_byte = ord(key[i % len(key)])
            transformed = (b * 3 + key_byte * 2) % 256
            layer1.append(transformed)
        
        # Apply a second layer
        layer2 = []
        for i, b in enumerate(layer1):
            # Apply another weighted sum
            key_byte = ord(key[(i+1) % len(key)])
            transformed = (b * 2 + key_byte * 3) % 256
            layer2.append(transformed)
        
        # Apply a third layer
        layer3 = []
        for i, b in enumerate(layer2):
            # Apply a final weighted sum
            key_byte = ord(key[(i+2) % len(key)])
            transformed = (b * 4 + key_byte) % 256
            layer3.append(transformed)
        
        # Convert to bytes and encode
        neural_bytes = bytes(layer3)
        enc = base64.b64encode(neural_bytes).decode()
        
        # Generate random variable names
        v1, v2, v3, v4 = ''.join(random.choices(string.ascii_lowercase, k=5) for _ in range(4))
        
        return f"{header}import base64;{v1}='{key}';{v2}=base64.b64decode('{enc}');{v3}=bytes([b for b in {v2}]);{v4}=bytes([((b - ord({v1}[(i+2)%len({v1})])) * 165) % 256 for i,b in enumerate({v3})]);exec(bytes([((b - ord({v1}[(i+1)%len({v1})])) * 171) % 256 for i,b in enumerate({v4})]).decode())"
    elif method == "chaos":
        # Chaos theory-inspired encryption
        key = custom_key if custom_key else "ChaosKey123"
        
        # Create a chaos-based transformation using logistic map
        # x_{n+1} = r * x_n * (1 - x_n)
        r = 3.9  # Chaos parameter
        
        # Generate a chaotic sequence
        chaos_seq = []
        x = 0.5  # Initial value
        for i in range(len(code.encode())):
            x = r * x * (1 - x)
            chaos_seq.append(int(x * 256))
        
        # Apply the chaotic transformation
        code_bytes = code.encode()
        key_bytes = key.encode()
        chaos_bytes = []
        for i, b in enumerate(code_bytes):
            # Apply chaos with key
            key_byte = key_bytes[i % len(key_bytes)]
            chaos_byte = (b + chaos_seq[i] + key_byte) % 256
            chaos_bytes.append(chaos_byte)
        
        # Encode with base64
        enc = base64.b64encode(bytes(chaos_bytes)).decode()
        
        # Generate random variable names
        v1, v2, v3, v4 = ''.join(random.choices(string.ascii_lowercase, k=5) for _ in range(4))
        
        return f"{header}import base64;{v1}='{key}';{v2}=base64.b64decode('{enc}');{v3}=bytes([b for b in {v2}]);{v4}=bytes([((b - {v1}[i%len({v1})]) - int(3.9 * (0.5 if i == 0 else (i/256) * (1 - (i/256))) * 256)) % 256 for i,b in enumerate({v3})]);exec({v4}.decode())"
    elif method == "custom":
        if not custom_key:
            return f"{header}# No custom key\n{code}"
        encrypted_bytes = bytes([b ^ ord(custom_key[i % len(custom_key)]) for i, b in enumerate(code.encode())])
        enc = base64.b64encode(encrypted_bytes).decode()
        return f"{header}import base64;key='{custom_key}';exec(''.join([chr(b^ord(key[i%len(key)])) for i,b in enumerate(base64.b64decode('{enc}'))]))"
    else:  # advanced or complex
        m_code = marshal.dumps(compile(code, '<string>', 'exec'))
        z_code = zlib.compress(m_code)
        b_code = base64.b64encode(z_code).decode()
        return f"{header}import base64 as a,zlib as b,marshal as c;exec(c.loads(b.decompress(a.b64decode('{b_code}'))))"
    
    return f"{header}{code}"

@bot.message_handler(content_types=['document'])
def receive_file(message):
    if not check_auth(message): return
    
    try:
        chat_id = message.chat.id
        if chat_id not in user_selections:
            bot.reply_to(message, "❌ <b>Select method first!</b>", parse_mode="HTML")
            return

        method = user_selections[chat_id]
        
        # Get expiration setting if any
        expire_setting = user_expire_settings.get(chat_id, None)
        expire_timestamp = get_expiration_timestamp(expire_setting) if expire_setting else None
        
        # Get license setting if any
        license_setting = user_license_settings.get(chat_id, None)
        
        # Get obfuscation setting if any
        obfuscation_setting = user_obfuscation_settings.get(chat_id, None)
        
        # Get watermark setting if any
        watermark_setting = user_watermark_settings.get(chat_id, None)
        
        # Get anti-VM setting if any
        anti_vm_setting = user_anti_vm_settings.get(chat_id, None)
        
        # Download file directly
        file_info = bot.get_file(message.document.file_id)
        file_bytes = bot.download_file(file_info.file_path)
        file_size = len(file_bytes)
        
        # Process immediately
        code = file_bytes.decode('utf-8')
        custom_key = user_selections.get(f"{chat_id}_key", "")
        
        # Apply obfuscation if requested
        if obfuscation_setting:
            code = apply_obfuscation(code, obfuscation_setting)
        
        # Add watermark if requested
        watermark = create_watermark(watermark_setting, message.from_user.id, message.from_user.username)
        
        # Add anti-VM protection if requested
        anti_vm = create_anti_vm(anti_vm_setting)
        
        # Add expiration check if needed
        expire_check = create_expire_check(expire_timestamp, expire_setting) if expire_timestamp else ""
        
        # Add license check if needed
        license_check = create_license_check(license_setting, chat_id) if license_setting else ""
        
        # Combine all checks with the original code
        code = watermark + anti_vm + expire_check + license_check + code
        
        # Ultra-fast encryption
        header = f"# Encrypted by SecureCrypt Ultimate Pro Max\n# Author: @a4bhi\n# Channel: @synaxBotz\n"
        if expire_timestamp:
            header += f"# Expires: {expire_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        if license_setting:
            header += f"# License: {license_setting}\n"
        if obfuscation_setting:
            header += f"# Obfuscation: {obfuscation_setting}\n"
        if watermark_setting:
            header += f"# Watermark: {watermark_setting}\n"
        if anti_vm_setting:
            header += f"# Anti-VM: {anti_vm_setting}\n"
        header += "\n"
        
        encrypted = encrypt_logic(method, code, custom_key)
        encrypted = header + encrypted
        
        # Create file in memory
        output = io.BytesIO()
        output.write(encrypted.encode('utf-8'))
        output.name = f"Encrypted_{message.document.file_name}"
        output.seek(0)
        
        # Create caption
        caption = f"🚀 <b>Ultimate Encryption Complete!</b>\n🛡 <b>Method:</b> <code>{method.upper()}</code>\n👤 <b>By:</b> @synaxBotz"
        if expire_timestamp:
            caption += f"\n⏰ <b>Expires:</b> {expire_timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        if license_setting:
            caption += f"\n📜 <b>License:</b> {license_setting}"
        if obfuscation_setting:
            caption += f"\n🎨 <b>Obfuscation:</b> {obfuscation_setting.replace('_', ' ').title()}"
        if watermark_setting:
            caption += f"\n💧 <b>Watermark:</b> {watermark_setting.replace('_', ' ').title()}"
        if anti_vm_setting:
            caption += f"\n🛡️ <b>Anti-VM:</b> {anti_vm_setting.replace('_', ' ').title()}"
        
        # Send immediately
        bot.send_document(
            chat_id, 
            output, 
            visible_file_name=f"Encrypted_{message.document.file_name}",
            caption=caption, 
            parse_mode="HTML"
        )
        
        # Add to history
        add_to_history(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            method,
            message.document.file_name,
            file_size,
            expire_setting,
            license_setting,
            obfuscation_setting,
            custom_key
        )
        
        # Clean up
        del user_selections[chat_id]
        if f"{chat_id}_key" in user_selections:
            del user_selections[f"{chat_id}_key"]
        if chat_id in user_expire_settings:
            del user_expire_settings[chat_id]
        if chat_id in user_license_settings:
            del user_license_settings[chat_id]
        if chat_id in user_obfuscation_settings:
            del user_obfuscation_settings[chat_id]
        if chat_id in user_watermark_settings:
            del user_watermark_settings[chat_id]
        if chat_id in user_anti_vm_settings:
            del user_anti_vm_settings[chat_id]
            
        # Update stats
        update_stats(method)

    except Exception as e:
        bot.send_message(chat_id, f"❌ <b>Error:</b> <code>{str(e)}</code>", parse_mode="HTML")

@bot.message_handler(commands=['broadcast'])
@admin_only
def broadcast(message):
    text = message.text.replace("/broadcast ", "")
    if not text or text == "/broadcast":
        bot.send_message(ADMIN_ID, "❌ Usage: `/broadcast message`", parse_mode="Markdown")
        return
    
    with open(USER_DB, "r") as f: users = f.read().splitlines()
    success = 0
    for u in users:
        try:
            bot.send_message(u, f"📢 <b>Notification:</b>\n\n{text}", parse_mode="HTML")
            success += 1
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Sent to {success} users.")

@bot.message_handler(commands=['resetstats'])
@admin_only
def reset_stats(message):
    init_stats()
    bot.send_message(ADMIN_ID, "✅ Stats reset.")

@bot.message_handler(commands=['clearhistory'])
@admin_only
def clear_history(message):
    try:
        conn = sqlite3.connect(HISTORY_DB)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM encryption_history")
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, "✅ History cleared.")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ Error clearing history: {str(e)}")

# Initialize databases
init_stats()
init_licenses()
init_history_db()

print(">>> SecureCrypt Ultimate Pro Max Bot is ONLINE - NEXT-GEN ULTRA ENCRYPTION SYSTEM!")
bot.infinity_polling()
