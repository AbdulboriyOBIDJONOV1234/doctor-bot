"""
Professional Neurologist Consultation Telegram Bot
Complete system with patient intake, triage, scheduling, and admin features
"""

import os
import json
import logging
import threading
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Bot Configuration
DOCTOR_ID = os.getenv("DOCTOR_ID", "8104665298")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7173294170:AAEvJTWZg-Td8Xeq5SvuEjxmYNBLh_qNq7U").strip().replace('"', '').replace("'", "")

# Database Configuration
DB_NAME = "bot_data.db"

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Patients table
    c.execute('''CREATE TABLE IF NOT EXISTS patients
                 (user_id TEXT PRIMARY KEY, username TEXT, first_name TEXT, 
                  last_name TEXT, age INTEGER, phone TEXT, location TEXT, created_at TEXT)''')
    # Appointments table
    c.execute('''CREATE TABLE IF NOT EXISTS appointments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, complaint TEXT, 
                  urgency TEXT, date TEXT, time TEXT, status TEXT, rejection_reason TEXT, 
                  files TEXT, created_at TEXT, confirmation_sent INTEGER DEFAULT 0, 
                  reminded_1h INTEGER DEFAULT 0, followup_sent INTEGER DEFAULT 0, confirmed_by_patient INTEGER DEFAULT 0)''')
    # Work hours table
    c.execute('''CREATE TABLE IF NOT EXISTS time_slots (time TEXT PRIMARY KEY)''')
    
    # Default times if empty
    c.execute("SELECT count(*) FROM time_slots")
    if c.fetchone()[0] == 0:
        defaults = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00"]
        c.executemany("INSERT INTO time_slots (time) VALUES (?)", [(t,) for t in defaults])
        conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Conversation states
(LANGUAGE, FIRST_NAME, LAST_NAME, AGE, PHONE, 
 LOCATION, COMPLAINT, UPLOAD_DOCS, URGENCY_CHECK, APPOINTMENT_DATE, 
 APPOINTMENT_TIME, CONFIRM, ADMIN_ACTION) = range(13)

doctor_states = {}

# Translations
TRANSLATIONS = {
    'uz': {
        'welcome': "🏥 Assalomu alaykum!\n\nMen Nevrologiya Konsultatsiya Botimanw.\n\nIltimos, tilni tanlang:",
        'language_selected': "✅ Til tanlandi: O'zbek",
        'ask_first_name': "📝 Ismingizni kiriting:",
        'ask_last_name': "📝 Familiyangizni kiriting:",
        'ask_age': "📝 Yoshingizni kiriting:",
        'ask_phone': "📱 Telefon raqamingizni kiriting:\n(Masalan: +998901234567)",
        'ask_location': "📍 Qayerdan ekanligingizni kiriting:\n(Masalan: Toshkent, Chilonzor)",
        'ask_complaint': "🩺 Shikoyatingiz yoki kasalligingiz haqida batafsil yozing:\n\n• Qanday alomatlar bor?\n• Qachondan beri?\n• Og'riq darajasi (1-10)?",
        'ask_docs': "📂 Tibbiy hujjatlar yoki rasmlar bormi? (MRT, Rentgen, Analizlar)\nUlarni shu yerga yuklashingiz mumkin.\n\nAgar yo'q bo'lsa, 'O'tkazib yuborish' tugmasini bosing.",
        'skip': "➡️ O'tkazib yuborish",
        'next': "➡️ Davom etish",
        'file_received': "✅ Fayl qabul qilindi!\n\nYana bormi? Yuklang yoki 'Davom etish' tugmasini bosing.",
        'upload_error': "⚠️ Iltimos, rasm yoki PDF fayl yuklang yoki tugmani bosing.",
        'urgency_check': "⚠️ Quyidagi favqulodda alomatlar bormi?\n\n🔴 Keskin bosh og'rig'i\n🔴 Nutq buzilishi\n🔴 Yuz yoki tananing bir tomonida zaiflik\n🔴 Tutqanoq (konvulsiya)\n🔴 Ongni yo'qotish\n🔴 Ko'rish buzilishi",
        'emergency_detected': "🚨 FAVQULODDA HOLAT!\n\nSiz tasvirlab bergan alomatlar shoshilinch tibbiy yordam talab qiladi.\n\nILTIMOS, DARHOL:\n☎️ 103 ga qo'ng'iroq qiling\n🏥 Yaqin shifoxonaga boring\n\nDoktor sizga ham qo'ng'iroq qiladi!",
        'ask_appointment': "📅 Qabul sanasini tanlang:",
        'ask_time': "🕐 Qulay vaqtni tanlang:",
        'confirm_booking': "✅ Ma'lumotlaringizni tasdiqlang:\n\n👤 Ism: {first_name} {last_name}\n🎂 Yosh: {age}\n📱 Telefon: {phone}\n📍 Manzil: {location}\n🩺 Shikoyat: {complaint}\n📅 Sana: {date}\n🕐 Vaqt: {time}\n\nTo'g'rimi?",
        'booking_confirmed': "✅ Qabul tasdiqlandi!\n\n📋 Qabul raqami: #{id}\n\nDoktor siz bilan {date} {time} da bog'lanadi.\n\n⏰ Eslatma:\n• 24 soat oldin SMS yuboriladi\n• 1 soat oldin Telegram xabar yuboriladi\n\nQabul oldidan quyidagilarni tayyorlang:\n✓ Oldingi tibbiy ma'lumotlar\n✓ Qabul qilayotgan dorilar ro'yxati\n✓ Tahlil natijalari (agar bor bo'lsa)",
        'patient_menu': "📱 Asosiy menyu:\n\n/myappointments - Qabullarim\n/history - Tarix\n/cancel - Qabulni bekor qilish\n/help - Yordam\n/emergency - Shoshilinch yordam",
        'cancel': "❌ Bekor qilindi",
        'yes': "✅ Ha",
        'no': "❌ Yo'q",
        'back': "◀️ Orqaga"
    },
    'ru': {
        'welcome': "🏥 Здравствуйте!\n\nЯ бот для консультаций невролога.\n\nПожалуйста, выберите язык:",
        'language_selected': "✅ Язык выбран: Русский",
        'ask_first_name': "📝 Введите ваше имя:",
        'ask_last_name': "📝 Введите вашу фамилию:",
        'ask_age': "📝 Введите ваш возраст:",
        'ask_phone': "📱 Введите ваш номер телефона:\n(Например: +998901234567)",
        'ask_location': "📍 Введите ваше местоположение:\n(Например: Ташкент, Чиланзар)",
        'ask_complaint': "🩺 Опишите подробно вашу жалобу или заболевание:\n\n• Какие симптомы?\n• Как давно беспокоит?\n• Уровень боли (1-10)?",
        'ask_docs': "📂 Есть ли медицинские документы или фото? (МРТ, Рентген и т.д.)\nВы можете загрузить их здесь.\n\nЕсли нет, нажмите 'Пропустить'.",
        'skip': "➡️ Пропустить",
        'next': "➡️ Далее",
        'file_received': "✅ Файл принят!\n\nЕщё? Загрузите или нажмите 'Далее'.",
        'upload_error': "⚠️ Пожалуйста, загрузите фото или PDF, или нажмите кнопку.",
        'urgency_check': "⚠️ Есть ли у вас следующие срочные симптомы?\n\n🔴 Внезапная сильная головная боль\n🔴 Нарушение речи\n🔴 Слабость на одной стороне тела\n🔴 Судороги\n🔴 Потеря сознания\n🔴 Нарушение зрения",
        'emergency_detected': "🚨 ЭКСТРЕННАЯ СИТУАЦИЯ!\n\nОписанные вами симптомы требуют немедленной медицинской помощи.\n\nПОЖАЛУЙСТА, НЕМЕДЛЕННО:\n☎️ Позвоните 103\n🏥 Обратитесь в ближайшую больницу\n\nВрач также свяжется с вами!",
        'ask_appointment': "📅 Выберите дату приёма:",
        'ask_time': "🕐 Выберите удобное время:",
        'confirm_booking': "✅ Подтвердите ваши данные:\n\n👤 Имя: {first_name} {last_name}\n🎂 Возраст: {age}\n📱 Телефон: {phone}\n📍 Адрес: {location}\n🩺 Жалоба: {complaint}\n📅 Дата: {date}\n🕐 Время: {time}\n\nВсё верно?",
        'booking_confirmed': "✅ Приём подтверждён!\n\n📋 Номер приёма: #{id}\n\nВрач свяжется с вами {date} в {time}.\n\n⏰ Напоминания:\n• SMS за 24 часа\n• Telegram сообщение за 1 час\n\nПодготовьте к приёму:\n✓ Предыдущие мед. документы\n✓ Список принимаемых лекарств\n✓ Результаты анализов (если есть)",
        'patient_menu': "📱 Главное меню:\n\n/myappointments - Мои приёмы\n/history - История\n/cancel - Отменить приём\n/help - Помощь\n/emergency - Экстренная помощь",
        'cancel': "❌ Отменено",
        'yes': "✅ Да",
        'no': "❌ Нет",
        'back': "◀️ Назад"
    },
    'en': {
        'welcome': "🏥 Hello!\n\nI'm a Neurology Consultation Bot.\n\nPlease select your language:",
        'language_selected': "✅ Language selected: English",
        'ask_first_name': "📝 Enter your first name:",
        'ask_last_name': "📝 Enter your last name:",
        'ask_age': "📝 Enter your age:",
        'ask_phone': "📱 Enter your phone number:\n(Example: +998901234567)",
        'ask_location': "📍 Enter your location:\n(Example: Tashkent, Chilanzar)",
        'ask_complaint': "🩺 Describe your complaint or condition in detail:\n\n• What symptoms do you have?\n• How long have you had them?\n• Pain level (1-10)?",
        'ask_docs': "📂 Do you have medical documents or photos? (MRI, X-ray, etc.)\nYou can upload them here.\n\nIf not, press 'Skip'.",
        'skip': "➡️ Skip",
        'next': "➡️ Next",
        'file_received': "✅ File received!\n\nMore? Upload or press 'Next'.",
        'upload_error': "⚠️ Please upload a photo or PDF, or press the button.",
        'urgency_check': "⚠️ Do you have any of these emergency symptoms?\n\n🔴 Sudden severe headache\n🔴 Speech problems\n🔴 Weakness on one side of body\n🔴 Seizures\n🔴 Loss of consciousness\n🔴 Vision problems",
        'emergency_detected': "🚨 EMERGENCY SITUATION!\n\nThe symptoms you described require immediate medical attention.\n\nPLEASE IMMEDIATELY:\n☎️ Call 103\n🏥 Go to nearest hospital\n\nThe doctor will also contact you!",
        'ask_appointment': "📅 Select appointment date:",
        'ask_time': "🕐 Select preferred time:",
        'confirm_booking': "✅ Confirm your information:\n\n👤 Name: {first_name} {last_name}\n🎂 Age: {age}\n📱 Phone: {phone}\n📍 Location: {location}\n🩺 Complaint: {complaint}\n📅 Date: {date}\n🕐 Time: {time}\n\nIs this correct?",
        'booking_confirmed': "✅ Appointment confirmed!\n\n📋 Appointment ID: #{id}\n\nThe doctor will contact you {date} at {time}.\n\n⏰ Reminders:\n• SMS 24 hours before\n• Telegram message 1 hour before\n\nPrepare for appointment:\n✓ Previous medical records\n✓ List of current medications\n✓ Test results (if available)",
        'patient_menu': "📱 Main menu:\n\n/myappointments - My appointments\n/history - History\n/cancel - Cancel appointment\n/help - Help\n/emergency - Emergency help",
        'cancel': "❌ Cancelled",
        'yes': "✅ Yes",
        'no': "❌ No",
        'back': "◀️ Back"
    }
}

# Emergency keywords detection
EMERGENCY_KEYWORDS = {
    'uz': ['keskin', 'birdaniga', 'tutqanoq', 'ong', 'nutq', 'zaiflik', 'ko\'rish'],
    'ru': ['внезапн', 'острый', 'судорог', 'сознан', 'речь', 'слабость', 'зрение'],
    'en': ['sudden', 'severe', 'seizure', 'consciousness', 'speech', 'weakness', 'vision']
}

def get_text(lang, key, **kwargs):
    """Get translated text"""
    text = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    return text.format(**kwargs) if kwargs else text

def detect_emergency(text, lang):
    """Detect emergency symptoms in complaint"""
    text_lower = text.lower()
    keywords = EMERGENCY_KEYWORDS.get(lang, EMERGENCY_KEYWORDS['en'])
    return any(keyword in text_lower for keyword in keywords)

def generate_dates():
    """Generate next 7 days for appointment"""
    dates = []
    for i in range(1, 8):
        date = datetime.now() + timedelta(days=i)
        dates.append(date.strftime("%Y-%m-%d"))
    return dates

def generate_time_slots():
    """Generate available time slots"""
    conn = get_db_connection()
    rows = conn.execute("SELECT time FROM time_slots ORDER BY time").fetchall()
    conn.close()
    return [row['time'] for row in rows]

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start conversation and ask for language"""
    user_id = update.effective_user.id
    # Check if user is doctor
    if str(user_id) == DOCTOR_ID:
        return await doctor_menu(update, context)

    # Check if the patient is already registered
    conn = get_db_connection()
    patient = conn.execute("SELECT * FROM patients WHERE user_id = ?", (str(user_id),)).fetchone()
    conn.close()
    if patient:
        return await patient_menu(update, context)

    keyboard = [
        [InlineKeyboardButton("🇺🇿 O'zbek", callback_data='lang_uz')],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = "🏥 Welcome to Neurology Consultation Bot!\n\nПожалуйста, выберите язык / Please select language / Iltimos, tilni tanlang:"
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    return LANGUAGE

async def doctor_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show doctor's main menu with reply buttons."""
    keyboard = [
        ["📅 Bugungi qabullar", "📋 Barcha qabullar"],
        ["📊 Statistika", "📢 Reklama yuborish", "⚙️ Ish vaqti"],
        ["🆘 Yordam"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("👨‍⚕️ Xush kelibsiz, Doktor! Asosiy menyu:", reply_markup=reply_markup)
    return ConversationHandler.END

async def patient_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show patient's main menu."""
    keyboard = [
        ["📝 Yangi qabul", "📅 Mening qabullarim"],
        ["📔 Oldingi qabullarim", "📞 Doktor bilan bog'lanish"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    msg_text = (
        "📱 <b>Asosiy menyu:</b>\n\n"
        "📢 Yangiliklardan xabardor bo'lib turish uchun guruhimizga qo'shiling:\n"
        "https://t.me/DrNeuropathology07"
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode='HTML')

    return ConversationHandler.END

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu button clicks for both patient and doctor."""
    query = update.callback_query
    await query.answer()
    
    # Patient actions
    if query.data == 'patient_new_appointment':
        # This will effectively restart the conversation handler
        await start(query, context)
    elif query.data == 'patient_my_appointments':
        await my_appointments(query.message, context)
    elif query.data == 'patient_history':
        await history_command(query.message, context)
    elif query.data == 'patient_contact_doctor':
        await contact_doctor_command(query.message, context)
        
    # Doctor actions
    elif query.data == 'doc_today':
        await today_appointments(query.message, context)
    elif query.data == 'doc_all_pending':
        await all_pending_appointments(query.message, context)
    elif query.data == 'doc_help':
        await doctor_help_command(query.message, context)
    elif query.data.startswith('delete_time_'):
        await delete_work_hour(update, context)

async def all_pending_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows all appointments to the doctor."""
    conn = get_db_connection()
    all_apts = conn.execute("SELECT * FROM appointments ORDER BY date DESC, time DESC").fetchall()
    conn.close()
    
    if not all_apts:
        await update.message.reply_text("Hozircha qabullar yo'q.")
    else:
        message = f"📋 <b>Barcha qabullar ({len(all_apts)} ta):</b>\n\n"
        for apt in all_apts:
            status_emojis = {
                'PENDING': '⏳', 'CONFIRMED': '✅', 
                'CANCELLED': '❌', 'COMPLETED': '✔️', 
                'REJECTED': '🚫'
            }
            status_icon = status_emojis.get(apt['status'], '❓')
            # Fetch patient details for name if needed, but we stored names in appointments or patients table.
            # For simplicity, we'll query patient info
            conn = get_db_connection()
            patient = conn.execute("SELECT * FROM patients WHERE user_id = ?", (apt['user_id'],)).fetchone()
            conn.close()
            
            first_name = patient['first_name'] if patient else "Noma'lum"
            last_name = patient['last_name'] if patient else ""
            phone = patient['phone'] if patient else ""
            username = f"@{patient['username']}" if patient and patient['username'] else ""
            
            message += (
                f"{status_icon} <b>{apt['date']} {apt['time']}</b> ({apt['status']})\n"
                f" {first_name} {last_name}\n"
                f"📞 {phone} {username}\n"
                f"🩺 {apt['complaint'][:50]}...\n"
                f"🆔 #{apt['id']}\n"
                f"-------------------\n"
            )
        
        if len(message) > 4096:
            for x in range(0, len(message), 4096):
                await update.message.reply_text(message[x:x+4096], parse_mode='HTML')
        else:
            await update.message.reply_text(message, parse_mode='HTML')

async def doctor_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows help for doctor."""
    await update.message.reply_text(
        "🛠 <b>Texnik yordam:</b>\n\n"
        "Bot bo'yicha texnik nosozliklar kuzatilsa, adminga murojaat qiling:\n"
        "@Abdulboriy7700",
        parse_mode='HTML'
    )

async def contact_doctor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows doctor contact info to patient."""
    help_text = """
📞 Doktor bilan to'g'ridan-to'g'ri aloqa:
+998998644754

🛠 Texnik yordam:
@Abdulboriy7700
    """
    await update.reply_text(help_text)

async def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store language and ask for first name"""
    query = update.callback_query
    await query.answer()
    
    lang = query.data.split('_')[1]
    context.user_data['language'] = lang
    
    await query.edit_message_text(get_text(lang, 'language_selected'))
    await query.message.reply_text(get_text(lang, 'ask_first_name'))
    
    return FIRST_NAME

async def first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store first name and ask for last name"""
    lang = context.user_data.get('language', 'en')
    context.user_data['first_name'] = update.message.text
    
    await update.message.reply_text(get_text(lang, 'ask_last_name'))
    return LAST_NAME

async def last_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store last name and ask for age"""
    lang = context.user_data.get('language', 'en')
    context.user_data['last_name'] = update.message.text
    
    await update.message.reply_text(get_text(lang, 'ask_age'))
    return AGE

async def age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store age and ask for phone"""
    lang = context.user_data.get('language', 'en')
    
    try:
        age_value = int(update.message.text)
        if age_value < 1 or age_value > 120:
            raise ValueError
        context.user_data['age'] = age_value
        await update.message.reply_text(get_text(lang, 'ask_phone'))
        return PHONE
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid age (1-120)")
        return AGE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store phone and ask for location"""
    lang = context.user_data.get('language', 'en')
    context.user_data['phone'] = update.message.text
    
    await update.message.reply_text(get_text(lang, 'ask_location'))
    return LOCATION

async def location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store location and ask for complaint"""
    lang = context.user_data.get('language', 'en')
    context.user_data['location'] = update.message.text
    
    await update.message.reply_text(get_text(lang, 'ask_complaint'))
    return COMPLAINT

async def complaint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store complaint and check for emergency"""
    lang = context.user_data.get('language', 'en')
    complaint_text = update.message.text
    context.user_data['complaint'] = complaint_text
    
    # Check for emergency
    if detect_emergency(complaint_text, lang):
        context.user_data['urgency'] = 'EMERGENCY'
        await update.message.reply_text(get_text(lang, 'emergency_detected'))
        
        # Notify doctor immediately
        await notify_doctor_emergency(context, update.effective_user)
        
        return ConversationHandler.END
    
    # Ask for documents
    keyboard = [[InlineKeyboardButton(get_text(lang, 'skip'), callback_data='skip_docs')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(get_text(lang, 'ask_docs'), reply_markup=reply_markup)
    return UPLOAD_DOCS

async def upload_docs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document uploads"""
    lang = context.user_data.get('language', 'en')
    
    # If user clicked Skip/Next
    if update.callback_query:
        await update.callback_query.answer()
        # Proceed to urgency check
        return await ask_urgency(update, context)
    
    # Handle file upload
    if update.message.document or update.message.photo:
        if 'files' not in context.user_data:
            context.user_data['files'] = []
        
        # Get file info
        if update.message.document:
            file_id = update.message.document.file_id
            file_type = 'doc'
        else:
            # Photos come in array of sizes, take last (largest)
            file_id = update.message.photo[-1].file_id
            file_type = 'photo'
            
        context.user_data['files'].append({'type': file_type, 'id': file_id})
        
        keyboard = [[InlineKeyboardButton(get_text(lang, 'next'), callback_data='skip_docs')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(get_text(lang, 'file_received'), reply_markup=reply_markup)
        return UPLOAD_DOCS
        
    await update.message.reply_text(get_text(lang, 'upload_error'))
    return UPLOAD_DOCS

async def ask_urgency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show urgency check question"""
    lang = context.user_data.get('language', 'en')
    
    # Ask for urgency confirmation
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'yes'), callback_data='urgent_yes')],
        [InlineKeyboardButton(get_text(lang, 'no'), callback_data='urgent_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(get_text(lang, 'urgency_check'), reply_markup=reply_markup)
    else:
        await update.message.reply_text(get_text(lang, 'urgency_check'), reply_markup=reply_markup)
        
    return URGENCY_CHECK

async def urgency_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check urgency and proceed to appointment scheduling"""
    query = update.callback_query
    await query.answer()
    
    lang = context.user_data.get('language', 'en')
    
    if query.data == 'urgent_yes':
        context.user_data['urgency'] = 'URGENT'
        await query.edit_message_text(get_text(lang, 'emergency_detected'))
        await notify_doctor_emergency(context, update.effective_user)
        return ConversationHandler.END
    
    context.user_data['urgency'] = 'ROUTINE'
    
    # Show available dates
    dates = generate_dates()
    keyboard = [[InlineKeyboardButton(date, callback_data=f'date_{date}')] for date in dates]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(get_text(lang, 'ask_appointment'), reply_markup=reply_markup)
    return APPOINTMENT_DATE

async def appointment_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store appointment date and ask for time"""
    query = update.callback_query
    await query.answer()
    
    lang = context.user_data.get('language', 'en')
    date = query.data.split('_')[1]
    context.user_data['appointment_date'] = date
    
    # Show available times
    times = generate_time_slots()
    keyboard = [[InlineKeyboardButton(time, callback_data=f'time_{time}')] for time in times]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(get_text(lang, 'ask_time'), reply_markup=reply_markup)
    return APPOINTMENT_TIME

async def appointment_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store appointment time and show confirmation"""
    query = update.callback_query
    await query.answer()
    
    lang = context.user_data.get('language', 'en')
    time = query.data.split('_')[1]
    context.user_data['appointment_time'] = time
    
    # Show confirmation
    confirmation_text = get_text(
        lang, 'confirm_booking',
        first_name=context.user_data['first_name'],
        last_name=context.user_data['last_name'],
        age=context.user_data['age'],
        phone=context.user_data['phone'],
        location=context.user_data['location'],
        complaint=context.user_data['complaint'][:100] + '...',
        date=context.user_data['appointment_date'],
        time=time
    )
    
    keyboard = [
        [InlineKeyboardButton(get_text(lang, 'yes'), callback_data='confirm_yes')],
        [InlineKeyboardButton(get_text(lang, 'no'), callback_data='confirm_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(confirmation_text, reply_markup=reply_markup)
    return CONFIRM

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm booking and notify doctor"""
    query = update.callback_query
    await query.answer()
    
    lang = context.user_data.get('language', 'en')
    
    if query.data == 'confirm_no':
        await query.edit_message_text(get_text(lang, 'cancel'))
        return ConversationHandler.END
    
    # Save to database
    conn = get_db_connection()
    
    # Upsert patient
    conn.execute("""
        INSERT OR REPLACE INTO patients (user_id, username, first_name, last_name, age, phone, location, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(update.effective_user.id),
        update.effective_user.username,
        context.user_data['first_name'],
        context.user_data['last_name'],
        context.user_data['age'],
        context.user_data['phone'],
        context.user_data['location'],
        datetime.now().isoformat()
    ))
    
    # Insert appointment
    cursor = conn.execute("""
        INSERT INTO appointments (user_id, complaint, urgency, date, time, status, files, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(update.effective_user.id),
        context.user_data['complaint'],
        context.user_data.get('urgency', 'ROUTINE'),
        context.user_data['appointment_date'],
        context.user_data['appointment_time'],
        'PENDING',
        json.dumps(context.user_data.get('files', [])),
        datetime.now().isoformat()
    ))
    appointment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Prepare data for notification
    patient_data = context.user_data.copy()
    patient_data['id'] = appointment_id
    patient_data['username'] = update.effective_user.username
    patient_data['created_at'] = datetime.now().isoformat()
    
    # Notify doctor
    await notify_doctor_new_patient(context, patient_data)
    
    # Confirm to patient
    confirmation_msg = get_text(
        lang, 'booking_confirmed',
        id=appointment_id,
        date=context.user_data['appointment_date'],
        time=context.user_data['appointment_time']
    )
    
    await query.edit_message_text(confirmation_msg)
    
    # Show patient main menu
    await patient_menu(query.message, context)
    
    return ConversationHandler.END

async def doctor_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle doctor's actions (Accept/Reject)"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("admin_"):
        return

    try:
        action = data.split("_")[1]
        apt_id = int(data.split("_")[2])
    except (IndexError, ValueError):
        return

    conn = get_db_connection()
    appointment = conn.execute("SELECT * FROM appointments WHERE id = ?", (apt_id,)).fetchone()
    
    if not appointment:
        conn.close()
        await query.edit_message_text("⚠️ Bu qabul ma'lumotlari topilmadi.")
        return

    patient_id = int(appointment['user_id'])
    original_text = query.message.text_html if query.message.text_html else query.message.text
    
    if action == "accept":
        conn.execute("UPDATE appointments SET status = 'CONFIRMED' WHERE id = ?", (apt_id,))
        conn.commit()
        
        # Message to patient
        patient_msg = (
            "✅ <b>Qabulingiz tasdiqlandi!</b>\n\n"
            "Doktor qabulingizni tasdiqladi. Belgilangan vaqtingizga kelishingiz mumkin.\n\n"
            "📍 <b>Manzil:</b> Farg’ona shaxar Oybek ko’chasi 8G uy\n"
            "🗺 <b>Lokatsiya:</b> https://maps.app.goo.gl/5GL8XAuYbihEkNnN9"
        )
        
        try:
            await context.bot.send_message(chat_id=patient_id, text=patient_msg, parse_mode='HTML')
            # Send actual location point
            await context.bot.send_location(chat_id=patient_id, latitude=40.3717652, longitude=71.7880633)
        except Exception as e:
            logger.error(f"Failed to send confirmation to patient {patient_id}: {e}")
            
        # Update doctor's message but KEEP info
        await query.edit_message_text(
            text=f"{original_text}\n\n✅ <b>QABUL TASDIQLANDI</b>",
            parse_mode='HTML',
            reply_markup=None
        )

    elif action == "reject":
        # Ask for reason instead of rejecting immediately
        doctor_states[update.effective_user.id] = {
            'action': 'reject_reason',
            'apt_id': apt_id,
            'message_id': query.message.message_id,
            'original_text': original_text
        }
        
        await query.edit_message_text(
            text=f"{original_text}\n\n✍️ <b>Iltimos, rad etish sababini yozing:</b>",
            parse_mode='HTML',
            reply_markup=None
        )
    conn.close()

async def notify_doctor_new_patient(context, patient_data):
    """Send new patient notification to doctor"""
    urgency_emoji = {
        'EMERGENCY': '🔴',
        'URGENT': '🟡',
        'ROUTINE': '🟢'
    }
    
    username_text = f"@{patient_data['username']}" if patient_data.get('username') else "Mavjud emas"
    
    message = f"""
🔔 YANGI BEMOR RO'YXATDAN O'TDI

{urgency_emoji.get(patient_data['urgency'], '🟢')} Muhimlik darajasi: {patient_data['urgency']}

📋 Qabul ID: #{patient_data['id']}

👤 Bemor ma'lumotlari:
• Ism: {patient_data['first_name']} {patient_data['last_name']}
• Yosh: {patient_data['age']}
• Tel: {patient_data['phone']}
• Username: {username_text}
• Manzil: {patient_data['location']}

🩺 Shikoyat:
{patient_data['complaint']}

📅 So'ralgan vaqt:
• Sana: {patient_data['date']}
• Vaqt: {patient_data['time']}

⏰ Ro'yxatdan o'tdi: {patient_data['created_at']}
    """
    
    # Send files first if any
    if patient_data.get('files'):
        for file in patient_data['files']:
            try:
                if file['type'] == 'photo':
                    await context.bot.send_photo(chat_id=DOCTOR_ID, photo=file['id'], caption=f"Bemor: {patient_data['first_name']}")
                else:
                    await context.bot.send_document(chat_id=DOCTOR_ID, document=file['id'], caption=f"Bemor: {patient_data['first_name']}")
            except Exception as e:
                logger.error(f"Failed to send file: {e}")

    keyboard = [
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_accept_{patient_data['id']}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_reject_{patient_data['id']}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(chat_id=DOCTOR_ID, text=message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Failed to notify doctor: {e}")

async def notify_doctor_emergency(context, user):
    """Send emergency notification to doctor"""
    patient_data = context.user_data
    username_text = f"@{user.username}" if user.username else "Mavjud emas"
    
    message = f"""
🚨 FAVQULODDA BEMOR XABARI! 🚨

Bemor shoshilinch tibbiy yordam talab qiladigan alomatlarga ega!

👤 Bemor ma'lumotlari:
• Ism: {patient_data.get('first_name', "Noma'lum")} {patient_data.get('last_name', '')}
• Yosh: {patient_data.get('age', "Noma'lum")}
• Tel: {patient_data.get('phone', "Noma'lum")}
• Username: {username_text}
• Manzil: {patient_data.get('location', "Noma'lum")}

🩺 Shikoyat:
{patient_data.get('complaint', 'Kiritilmagan')}

⚠️ DARHOL CHORA KO'RISH KERAK
Bemorga 103 ga qo'ng'iroq qilish va shifoxonaga borish tavsiya qilindi.

Iltimos, bemor bilan darhol bog'laning: {patient_data.get('phone', "Noma'lum")}
    """
    
    try:
        await context.bot.send_message(chat_id=DOCTOR_ID, text=message)
    except Exception as e:
        logger.error(f"Failed to notify doctor about emergency: {e}")

async def my_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's appointments"""
    user_id = update.effective_user.id
    lang = context.user_data.get('language', 'en')
    
    conn = get_db_connection()
    user_appointments = conn.execute("SELECT * FROM appointments WHERE user_id = ? ORDER BY id DESC", (str(user_id),)).fetchall()
    conn.close()
    
    if not user_appointments:
        await update.message.reply_text("📭 You have no appointments yet.")
        return
    
    message = "📅 Sizning Qabullaringiz:\n\n"
    for apt in user_appointments:
        status_emoji = {'PENDING': '⏳', 'CONFIRMED': '✅', 'COMPLETED': '✔️', 'CANCELLED': '❌'}
        message += f"{status_emoji.get(apt['status'], '•')} #{apt['id']} - {apt['date']} soat {apt['time']}\n"
        message += f"   Holat: {apt['status']}\n\n"
    
    await update.message.reply_text(message)

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show appointment history"""
    # For now, same as my_appointments but could be filtered for past dates
    await my_appointments(update, context)

async def emergency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send emergency contact"""
    await update.message.reply_text("🚨 Shoshilinch tez tibbiy yordam (103) bilan bog'lanish:")
    await update.message.reply_contact(phone_number="103", first_name="Tez", last_name="Yordam")

async def cancel_booking_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel pending or confirmed appointments"""
    user_id = update.effective_user.id
    conn = get_db_connection()
    active_apts = conn.execute("SELECT * FROM appointments WHERE user_id = ? AND status IN ('PENDING', 'CONFIRMED')", (str(user_id),)).fetchall()
    
    if not active_apts:
        conn.close()
        await update.message.reply_text("❌ Bekor qilish uchun faol (kutilayotgan yoki tasdiqlangan) qabullar topilmadi.")
        return

    # Cancel them
    for apt in active_apts:
        old_status = apt['status']
        conn.execute("UPDATE appointments SET status = 'CANCELLED' WHERE id = ?", (apt['id'],))
        
        # Get patient info for notification
        patient = conn.execute("SELECT * FROM patients WHERE user_id = ?", (str(user_id),)).fetchone()
        
        # Notify doctor
        username_text = f"@{update.effective_user.username}" if update.effective_user.username else "Mavjud emas"
        status_text = "Tasdiqlangan" if old_status == 'CONFIRMED' else "Kutilayotgan"
        
        msg = (
            f"❌ <b>BEMOR QABULNI BEKOR QILDI</b>\n\n"
            f"🆔 ID: #{apt['id']}\n"
            f"👤 Bemor: {patient['first_name']} {patient['last_name']} ({username_text})\n"
            f"📅 Sana: {apt['date']} {apt['time']}\n"
            f"ℹ️ Holati: {status_text}"
        )
        try:
            await context.bot.send_message(chat_id=DOCTOR_ID, text=msg, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to notify doctor of cancellation: {e}")

    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Sizning qabulingiz bekor qilindi va doktor xabardor qilindi.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information"""
    # Check if doctor
    if str(update.effective_user.id) == DOCTOR_ID:
        await doctor_help_command(update, context)
        return

    help_text = """
📱 Asosiy menyu:

/myappointments - Qabullarim
/history - Tarix
/cancel - Qabulni bekor qilish
/help - Yordam
/emergency - Shoshilinch yordam

📞 Doktor bilan to'g'ridan-to'g'ri aloqa:
+998998644754

🛠 Texnik yordam:
@Abdulboriy7700
    """
    await update.message.reply_text(help_text)

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation and check for active appointments"""
    user_id = update.effective_user.id
    conn = get_db_connection()
    active_apt = conn.execute("SELECT 1 FROM appointments WHERE user_id = ? AND status IN ('PENDING', 'CONFIRMED')", (str(user_id),)).fetchone()
    conn.close()
    
    if active_apt:
        await cancel_booking_command(update, context)
    else:
        lang = context.user_data.get('language', 'en')
        await update.message.reply_text(get_text(lang, 'cancel'))
        
    return ConversationHandler.END

async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Check for upcoming appointments and send reminders"""
    now = datetime.now()
    conn = get_db_connection()
    
    # Get confirmed appointments
    apts = conn.execute("SELECT * FROM appointments WHERE status = 'CONFIRMED'").fetchall()
    
    for apt in apts:
        apt_id = apt['id']
            
        try:
            # Parse appointment datetime
            apt_dt_str = f"{apt['date']} {apt['time']}"
            apt_dt = datetime.strptime(apt_dt_str, "%Y-%m-%d %H:%M")
        except ValueError as e:
            logger.error(f"Date parsing error for apt {apt_id}: {e}")
            continue
            
        # 0. Confirmation Request (2 hours before)
        if not apt['confirmation_sent']:
            time_remaining = apt_dt - now
            # Send between 1 hour and 2.5 hours before (targeting ~2 hours)
            if timedelta(minutes=65) < time_remaining <= timedelta(minutes=150):
                user_id = apt['user_id']
                patient = conn.execute("SELECT first_name FROM patients WHERE user_id=?", (user_id,)).fetchone()
                first_name = patient['first_name'] if patient else "Bemor"
                msg = (
                    f"👋 Hurmatli {first_name},\n"
                    f"Sizning qabulingizga 2 soat vaqt qoldi.\n\n"
                    f"📅 Vaqt: {apt['time']}\n"
                    f"Kelishingizni tasdiqlaysizmi?"
                )
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Ha, boraman", callback_data=f"confirm_visit_yes_{apt_id}"),
                        InlineKeyboardButton("❌ Yo'q, bekor qilaman", callback_data=f"confirm_visit_no_{apt_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                try:
                    await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=reply_markup)
                    conn.execute("UPDATE appointments SET confirmation_sent = 1 WHERE id = ?", (apt_id,))
                except Exception as e:
                    logger.error(f"Failed to send confirmation request to {user_id}: {e}")

        # 1. Reminder Logic (1 hour before)
        if not apt['reminded_1h']:
            time_remaining = apt_dt - now
            if timedelta(minutes=0) < time_remaining <= timedelta(minutes=60):
                user_id = apt['user_id']
                patient = conn.execute("SELECT first_name FROM patients WHERE user_id=?", (user_id,)).fetchone()
                first_name = patient['first_name'] if patient else "Bemor"
                msg = (
                    f"⏰ <b>ESLATMA!</b>\n\n"
                    f"Hurmatli {first_name},\n"
                    f"Sizning qabulingizga 1 soat vaqt qoldi.\n\n"
                    f"📅 Vaqt: {apt['time']}\n"
                    f"📍 Manzil: Farg’ona shaxar Oybek ko’chasi 8G uy\n"
                    f"🗺 Lokatsiya: https://maps.app.goo.gl/5GL8XAuYbihEkNnN9"
                )
                try:
                    await context.bot.send_message(chat_id=user_id, text=msg, parse_mode='HTML')
                    conn.execute("UPDATE appointments SET reminded_1h = 1 WHERE id = ?", (apt_id,))
                except Exception as e:
                    logger.error(f"Failed to send reminder to {user_id}: {e}")

        # 2. Follow-up Logic (2 hours after appointment)
        if not apt['followup_sent']:
            time_passed = now - apt_dt
            if time_passed >= timedelta(hours=2):
                user_id = apt['user_id']
                patient = conn.execute("SELECT first_name FROM patients WHERE user_id=?", (user_id,)).fetchone()
                first_name = patient['first_name'] if patient else "Bemor"
                msg = (
                    f"👋 Assalomu alaykum, {first_name}!\n\n"
                    f"Bugun shifokor qabulida bo'ldingiz.\n"
                    f"Hozir ahvolingiz qanday? Iltimos, baholang:"
                )
                keyboard = [
                    [
                        InlineKeyboardButton("🟢 Yaxshi", callback_data=f"feedback_good_{apt_id}"),
                        InlineKeyboardButton("🟡 O'rtacha", callback_data=f"feedback_ok_{apt_id}"),
                        InlineKeyboardButton("🔴 Yomon", callback_data=f"feedback_bad_{apt_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                try:
                    await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=reply_markup)
                    conn.execute("UPDATE appointments SET followup_sent = 1 WHERE id = ?", (apt_id,))
                except Exception as e:
                    logger.error(f"Failed to send follow-up to {user_id}: {e}")
    
    conn.commit()
    conn.close()

async def today_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's appointments for the doctor"""
    # Check if user is doctor
    if str(update.effective_user.id) != DOCTOR_ID:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    today_apts = conn.execute("SELECT * FROM appointments WHERE date = ? AND status IN ('CONFIRMED', 'PENDING') ORDER BY time", (today,)).fetchall()
    
    if not today_apts:
        conn.close()
        await update.message.reply_text(f"📅 {today} sanasi uchun qabullar mavjud emas.")
        return

    message = f"📅 <b>Bugungi qabullar ({today}):</b>\n\n"
    for apt in today_apts:
        status_icon = "✅" if apt['status'] == 'CONFIRMED' else "⏳"
        
        patient = conn.execute("SELECT * FROM patients WHERE user_id = ?", (apt['user_id'],)).fetchone()
        first_name = patient['first_name'] if patient else "Noma'lum"
        last_name = patient['last_name'] if patient else ""
        phone = patient['phone'] if patient else ""
        username = f"@{patient['username']}" if patient and patient['username'] else ""
        
        message += (
            f"{status_icon} <b>{apt['time']}</b> - {first_name} {last_name}\n"
            f"📞 {phone} {username}\n"
            f"🩺 {apt['complaint'][:50]}...\n"
            f"🆔 #{apt['id']}\n\n"
        )
    
    conn.close()
    await update.message.reply_text(message, parse_mode='HTML')

async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle patient feedback after appointment"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("feedback_"):
        return

    parts = data.split("_")
    status = parts[1] # good, ok, bad
    apt_id = parts[2]
    
    if status == "good":
        await query.edit_message_text("✅ Javobingiz uchun rahmat! Salomat bo'ling.")
    elif status == "ok":
        await query.edit_message_text("😐 Javobingiz uchun rahmat. Agar bezovtalik kuchaysa, albatta xabar bering.")
    elif status == "bad":
        await query.edit_message_text("🔴 Tushunarli. Shifokorga bu haqida xabar beramiz.")
        # Notify doctor
        conn = get_db_connection()
        apt = conn.execute("SELECT * FROM appointments WHERE id = ?", (apt_id,)).fetchone()
        if apt:
            patient = conn.execute("SELECT * FROM patients WHERE user_id = ?", (apt['user_id'],)).fetchone()
            first_name = patient['first_name'] if patient else "Noma'lum"
            phone = patient['phone'] if patient else ""
            doc_msg = (
                f"⚠️ <b>BEMOR AHVOLI YOMON!</b>\n\n"
                f"Bemor: {first_name} {patient['last_name']}\n"
                f"Tel: {phone}\n"
                f"Qabul ID: #{apt_id}\n\n"
                f"Bemor qabuldan keyingi so'rovnomada ahvolini 'Yomon' deb baholadi."
            )
            try:
                await context.bot.send_message(chat_id=DOCTOR_ID, text=doc_msg, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Failed to notify doctor about feedback: {e}")
        conn.close()

async def confirm_visit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle patient confirmation response (Yes/No) before appointment"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("confirm_visit_"):
        return

    parts = data.split("_")
    action = parts[2] # yes or no
    try:
        apt_id = int(parts[3])
    except (IndexError, ValueError):
        return
    
    conn = get_db_connection()
    apt = conn.execute("SELECT * FROM appointments WHERE id = ?", (apt_id,)).fetchone()
    
    if not apt:
        conn.close()
        await query.edit_message_text("⚠️ Qabul ma'lumotlari topilmadi.")
        return

    if action == "yes":
        conn.execute("UPDATE appointments SET confirmed_by_patient = 1 WHERE id = ?", (apt_id,))
        await query.edit_message_text(f"✅ Rahmat! Sizni {apt['time']} da kutamiz.")
    elif action == "no":
        conn.execute("UPDATE appointments SET status = 'CANCELLED' WHERE id = ?", (apt_id,))
        await query.edit_message_text("❌ Qabul bekor qilindi.")
        
        # Notify doctor
        patient = conn.execute("SELECT * FROM patients WHERE user_id = ?", (apt['user_id'],)).fetchone()
        username_text = f"@{patient['username']}" if patient and patient['username'] else "Mavjud emas"
        first_name = patient['first_name'] if patient else "Noma'lum"
        
        msg = f"❌ <b>BEMOR QABULNI BEKOR QILDI (Tasdiqlash so'rovi)</b>\n\nID: #{apt['id']}\nBemor: {first_name} {patient['last_name']} ({username_text})\nSana: {apt['date']} {apt['time']}"
        try:
            await context.bot.send_message(chat_id=DOCTOR_ID, text=msg, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to notify doctor of cancellation: {e}")
    conn.commit()
    conn.close()

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start new appointment booking (skip registration if known)"""
    user_id = update.effective_user.id
    conn = get_db_connection()
    data = conn.execute("SELECT * FROM patients WHERE user_id = ?", (str(user_id),)).fetchone()
    conn.close()
    
    if data:
        # Load data
        context.user_data.update({
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'age': data['age'],
            'phone': data['phone'],
            'location': data['location']
        })
        lang = context.user_data.get('language', 'uz')
        await update.message.reply_text(get_text(lang, 'ask_complaint'))
        return COMPLAINT
    else:
        return await start(update, context)

async def doctor_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics to the doctor."""
    if str(update.effective_user.id) != DOCTOR_ID:
        return

    conn = get_db_connection()
    total_patients = conn.execute("SELECT count(*) FROM patients").fetchone()[0]
    total_appointments = conn.execute("SELECT count(*) FROM appointments").fetchone()[0]
    
    rows = conn.execute("SELECT status, count(*) as count FROM appointments GROUP BY status").fetchall()
    conn.close()
    
    status_counts = {
        'PENDING': 0,
        'CONFIRMED': 0,
        'CANCELLED': 0,
        'COMPLETED': 0,
        'REJECTED': 0
    }
    for row in rows:
        status_counts[row['status']] = row['count']

    msg = (
        f"📊 <b>Statistika:</b>\n\n"
        f"👥 Jami bemorlar: {total_patients}\n"
        f"📑 Jami qabullar: {total_appointments}\n\n"
        f"⏳ Kutilayotgan: {status_counts.get('PENDING', 0)}\n"
        f"✅ Tasdiqlangan: {status_counts.get('CONFIRMED', 0)}\n"
        f"❌ Bekor qilingan: {status_counts.get('CANCELLED', 0)}\n"
        f"🚫 Rad etilgan: {status_counts.get('REJECTED', 0)}\n"
        f"✔️ Yakunlangan: {status_counts.get('COMPLETED', 0)}"
    )
    
    await update.message.reply_text(msg, parse_mode='HTML')

async def manage_work_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current work hours and allow editing"""
    conn = get_db_connection()
    slots = conn.execute("SELECT time FROM time_slots ORDER BY time").fetchall()
    conn.close()
    
    msg = "⚙️ <b>Ish vaqtlarini boshqarish</b>\n\nHozirgi vaqtlar:\n"
    keyboard = []
    
    for slot in slots:
        time = slot['time']
        msg += f"• {time}\n"
        keyboard.append([InlineKeyboardButton(f"🗑 {time} ni o'chirish", callback_data=f"delete_time_{time}")])
    
    msg += "\n➕ Yangi vaqt qo'shish uchun shunchaki soatni yozing (masalan: 18:30)"
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
    
    # Set state to expect time input
    doctor_states[update.effective_user.id] = {'action': 'manage_hours'}

async def delete_work_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a time slot"""
    query = update.callback_query
    await query.answer()
    
    time_to_delete = query.data.split('_')[2]
    
    conn = get_db_connection()
    conn.execute("DELETE FROM time_slots WHERE time = ?", (time_to_delete,))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"✅ {time_to_delete} vaqti o'chirildi.")

async def add_work_hour(update: Update, context: ContextTypes.DEFAULT_TYPE, time_str):
    """Add a new time slot"""
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO time_slots (time) VALUES (?)", (time_str,))
        conn.commit()
        await update.message.reply_text(f"✅ {time_str} vaqti qo'shildi.")
    except sqlite3.IntegrityError:
        await update.message.reply_text(f"⚠️ {time_str} vaqti allaqachon mavjud.")
    conn.close()

async def doctor_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle doctor menu text buttons"""
    # Clear any pending states when switching menus
    if update.effective_user.id in doctor_states:
        del doctor_states[update.effective_user.id]

    text = update.message.text
    if text == "📅 Bugungi qabullar":
        await today_appointments(update, context)
    elif text == "📋 Barcha qabullar":
        await all_pending_appointments(update, context)
    elif text == "📊 Statistika":
        await doctor_statistics(update, context)
    elif text == "⚙️ Ish vaqti":
        await manage_work_hours(update, context)
    elif text == "📢 Reklama yuborish":
        doctor_states[update.effective_user.id] = {'action': 'broadcast_message'}
        await update.message.reply_text(
            "📢 <b>Reklama yuborish rejimi</b>\n\n"
            "Barcha bemorlarga yubormoqchi bo'lgan xabaringizni yozing (matn, rasm yoki video).\n"
            "Bekor qilish uchun boshqa menyu tugmasini bosing.",
            parse_mode='HTML'
        )
    elif text == "🆘 Yordam":
        await doctor_help_command(update, context)

async def patient_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle patient menu text buttons"""
    text = update.message.text
    if text == "📅 Mening qabullarim":
        await my_appointments(update, context)
    elif text == "📔 Oldingi qabullarim":
        await history_command(update, context)
    elif text == "📞 Doktor bilan bog'lanish":
        await contact_doctor_command(update, context)

async def doctor_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle input from doctor (rejection reasons, broadcasts)"""
    user_id = update.effective_user.id
    if str(user_id) != DOCTOR_ID:
        return

    state = doctor_states.get(user_id)
    if not state:
        return

    if state['action'] == 'manage_hours':
        # Validate time format HH:MM
        import re
        if re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', update.message.text):
            await add_work_hour(update, context, update.message.text)
        else:
            await update.message.reply_text("⚠️ Noto'g'ri format. Iltimos, HH:MM formatida yozing (masalan: 14:30)")
        return

    if state['action'] == 'reject_reason':
        if not update.message.text:
            await update.message.reply_text("⚠️ Iltimos, rad etish sababini matn ko'rinishida yozing.")
            return
            
        reason = update.message.text
        apt_id = state['apt_id']
        
        conn = get_db_connection()
        conn.execute("UPDATE appointments SET status = 'REJECTED', rejection_reason = ? WHERE id = ?", (reason, apt_id))
        
        # Get patient ID
        apt = conn.execute("SELECT user_id FROM appointments WHERE id = ?", (apt_id,)).fetchone()
        if apt:
            patient_id = apt['user_id']
            
            # Notify patient
            patient_msg = (
                f"❌ <b>Qabul rad etildi</b>\n\n"
                f"Doktor qabulni rad etdi.\n"
                f"<b>Sabab:</b> {reason}\n\n"
                f"Iltimos, boshqa vaqtni tanlang."
            )
            try:
                await context.bot.send_message(chat_id=patient_id, text=patient_msg, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Failed to send rejection to patient: {e}")

            # Update doctor message
            try:
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=state['message_id'],
                    text=f"{state['original_text']}\n\n❌ <b>RAD ETILDI</b>\nSabab: {reason}",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Failed to edit doctor message: {e}")
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ Rad etish sababi yuborildi va bemor xabardor qilindi.")
        del doctor_states[user_id]
        
    elif state['action'] == 'broadcast_message':
        count = 0
        status_msg = await update.message.reply_text("⏳ Xabar yuborilmoqda...")
        
        conn = get_db_connection()
        patients = conn.execute("SELECT user_id FROM patients").fetchall()
        conn.close()
        
        for row in patients:
            pid = row['user_id']
            if str(pid) == DOCTOR_ID:
                continue
            try:
                # Copy the message (text, photo, video, etc.)
                await update.message.copy(chat_id=pid)
                count += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to {pid}: {e}")
        
        await context.bot.delete_message(chat_id=user_id, message_id=status_msg.message_id)
        await update.message.reply_text(f"✅ Xabar {count} ta bemorga muvaffaqiyatli yuborildi.")
        del doctor_states[user_id]

# Render Health Check Server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def start_web_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "Boshlash"),
        BotCommand("myappointments", "Qabullarim"),
        BotCommand("history", "Tarix"),
        BotCommand("cancel", "Qabulni bekor qilish"),
        BotCommand("help", "Yordam"),
        BotCommand("emergency", "Shoshilinch yordam"),
    ])
    
    # Start reminder job (runs every 60 seconds)
    if application.job_queue:
        application.job_queue.run_repeating(check_reminders, interval=60, first=10)

def main():
    """Start the bot"""
    # Initialize Database
    init_db()
    
    # Start dummy web server for Render
    threading.Thread(target=start_web_server, daemon=True).start()

    # Create application
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), MessageHandler(filters.Regex("^📝 Yangi qabul$"), start_booking)],
        states={
            LANGUAGE: [CallbackQueryHandler(language_selected)],
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, last_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location)],
            COMPLAINT: [MessageHandler(filters.TEXT & ~filters.COMMAND, complaint)],
            UPLOAD_DOCS: [MessageHandler(filters.PHOTO | filters.Document.ALL, upload_docs), CallbackQueryHandler(upload_docs)],
            URGENCY_CHECK: [CallbackQueryHandler(urgency_check)],
            APPOINTMENT_DATE: [CallbackQueryHandler(appointment_date)],
            APPOINTMENT_TIME: [CallbackQueryHandler(appointment_time)],
            CONFIRM: [CallbackQueryHandler(confirm_booking)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation), CommandHandler('help', help_command)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('myappointments', my_appointments))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('history', history_command))
    application.add_handler(CommandHandler('emergency', emergency_command))
    application.add_handler(CommandHandler('cancel', cancel_booking_command))
    application.add_handler(CommandHandler('today', today_appointments))
    application.add_handler(CallbackQueryHandler(doctor_action, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(feedback_handler, pattern="^feedback_"))
    application.add_handler(CallbackQueryHandler(confirm_visit_handler, pattern="^confirm_visit_"))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(📅 Bugungi qabullar|📋 Barcha qabullar|📊 Statistika|📢 Reklama yuborish|🆘 Yordam)$"), doctor_menu_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(📅 Mening qabullarim|📔 Oldingi qabullarim|📞 Doktor bilan bog'lanish)$"), patient_menu_handler))
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL) & ~filters.COMMAND, doctor_input_handler))
    
    # Start bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()