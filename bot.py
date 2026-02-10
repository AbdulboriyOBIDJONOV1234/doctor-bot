"""
🏥 Nevropatolog Konsultatsiya Boti v2.0 - FIXED
Dr. Abdulatifovich uchun maxsus professional bot
Python 3.14+ | Zamonaviy UI/UX | Kreativ yondashuv

✅ TUZATILGAN: Admin xabarlari ishlayapti!
"""

import os
import json
import sys
import traceback
import logging
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Config
from config import BOT_TOKEN, DOCTOR_PHONE, ADMIN_CHAT_IDS, FAVQULODDA_SOZLAR, CHANNEL_USERNAME

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask Server (Render uchun)
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Nevropatolog Bot v2.0 - FIXED VERSION"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Bot sozlamalari
DOCTOR_USERNAME = "nevropatolog_abdulatifovich"

# Suhbat holatlari
(LANG_SELECT, ISM, FAMILIYA, YOSH, TELEFON, MANZIL, 
 SHIKOYAT, FAVQULODDA, SANA, VAQT, RATING) = range(11)

# Ma'lumotlar bazasi (keyinroq PostgreSQL)
bemorlar = {}
qabullar = {}
ratinglar = {}

# Til sozlamalari
MATNLAR = {
    'uz': {
        'start_admin': """👨‍⚕️ **Assalomu alaykum, Doktor!**

🎯 Bugungi rejangiz:
📊 Statistika | 📅 Qabullar | 👥 Bemorlar""",
        'start_user': """🌟 **Assalomu alaykum!**

Men **Dr. Abdulatifovich**ning shaxsiy yordamchisiman.

💫 Sizga qanday yordam bera olaman?""",
        'progress_1': '▰▱▱▱▱▱ 17%',
        'progress_2': '▰▰▱▱▱▱ 33%',
        'progress_3': '▰▰▰▱▱▱ 50%',
        'progress_4': '▰▰▰▰▱▱ 67%',
        'progress_5': '▰▰▰▰▰▱ 83%',
        'progress_6': '▰▰▰▰▰▰ 100%',
        'ism_savol': '👤 **1/6 - Shaxsiy ma\'lumotlar**\n\n📝 Ismingizni kiriting:',
        'familiya_savol': '👤 **2/6 - Shaxsiy ma\'lumotlar**\n\n📝 Familiyangizni kiriting:',
        'yosh_savol': '🎂 **3/6 - Shaxsiy ma\'lumotlar**\n\n🔢 Yoshingizni kiriting (raqamda):',
        'telefon_savol': '📱 **4/6 - Aloqa ma\'lumotlari**\n\n☎️ Telefon raqamingizni kiriting:\n\n*Masalan:* +998 99 123 45 67',
        'manzil_savol': '🏠 **5/6 - Joylashuv**\n\n📍 Yashash manzilingizni kiriting:\n\n*Masalan:* Toshkent, Chilonzor 12-kvartal',
        'shikoyat_savol': """🩺 **6/6 - Tibbiy ma'lumotlar**

📋 Shikoyatingiz yoki kasalligingiz haqida to'liq ma'lumot bering:

💡 *Quyidagilarni yozing:*
   • Qanday alomatlar bor?
   • Qachondan beri bezovta qilyapti?
   • Og'riq darajasi (1-10)
   • Boshqa muhim belgilar""",
        'favq_savol': """⚠️ **Muhim savol!**

Quyidagi **shoshilinch alomatlardan** biri bormi?

🔴 Keskin bosh og'rig'i
🔴 Nutq buzilishi
🔴 Yuz yoki tananing bir tomonida zaiflik
🔴 Tutqanoq (konvulsiya)
🔴 Ongni yo'qotish
🔴 Ko'rish buzilishi""",
        'favq_ogohlantirish': """🚨 **SHOSHILINCH HOLAT!**

Siz tasvirlagan alomatlar ZUDLIK bilan tibbiy yordam talab qiladi!

‼️ **DARHOL BAJARING:**

1️⃣ ☎️ **103** ga qo'ng'iroq qiling
2️⃣ 🏥 Eng yaqin shifoxonaga boring
3️⃣ 🚑 Tez yordam chaqiring

⚕️ Doktor ham sizga qo'ng'iroq qiladi!

📞 Sizning ma'lumotlaringiz doktorga yuborildi.""",
        'sana_tanlash': '📅 Qabul sanasi\n\nQaysi kun sizga qulay?',
        'vaqt_tanlash': '🕐 Qabul vaqti\n\nSana: {sana}\n\nQaysi vaqt mos keladi?',
        'kutish_xabar': """✅ Tasdiqlanmoqda...

📋 Qabul raqami: #{qabul_id}

Hurmatli {ism}, so'rovingiz Doktorga yuborildi.

⏳ Iltimos, sabr qiling!

Doktor tasdiqlagandan so'ng sizga:
📍 Klinika joylashuvi
📋 Kerakli hujjatlar ro'yxati
📞 Qo'shimcha ma'lumotlar

yuboriladi.

🔔 Xabar olishni kuting!""",
        'tasdiq_xabar': """✅ TABRIKLAYMIZ! Qabulingiz tasdiqlandi

📅 Sana va vaqt: {sana}, soat {vaqt}
👨‍⚕️ Doktor: Dr. Abdulatifovich

📂 O'zingiz bilan ALBATTA olib keling:

1️⃣ 📇 Pasport (ID karta)
2️⃣ 📋 Tibbiy karta (agar bor bo'lsa)
3️⃣ 🧪 Oldingi tahlillar:
   • MRT/MSKT natijalari
   • Qon tahlillari
   • Boshqa tekshiruvlar
4️⃣ 💊 Hozir qabul qilayotgan dorilar ro'yxati

⏰ Eslatma:
Qabul vaqtidan 10-15 daqiqa oldin keling.

📍 Klinika manzili pastda ko'rsatilgan

🌟 Sizni kutamiz!""",
        'bekor_xabar': """❌ Afsuski, qabulingiz bekor qilindi

📞 Boshqa vaqt uchun bog'laning:
{doktor_telefon}

Yoki qaytadan /start buyrug'ini bering.""",
        'aloqa_info': """📞 Bog'lanish ma'lumotlari

👨‍⚕️ Doktor: Dr. Abdulatifovich
📱 Telefon: {telefon}
💬 Telegram: @{username}

🏥 Ish vaqti:
🕐 Dushanba-Shanba: 09:00-18:00
🌙 Yakshanba: Dam olish

📍 Manzil: Toshkent shahri
[Aniq manzil qo'shiladi]

🚨 Favqulodda: 103""",
        'faq': """❓ Tez-tez beriladigan savollar

1️⃣ Qabul qancha davom etadi?
• Birinchi ko'rik: 30-45 daqiqa
• Qayta ko'rik: 20-30 daqiqa

2️⃣ Nima olib borish kerak?
• Pasport
• Tibbiy hujjatlar
• Tahlillar
• Dorilar ro'yxati

3️⃣ Online konsultatsiya bormi?
• Ha, Telegram orqali

4️⃣ To'lov usullari?
• Naqd
• Plastik karta

5️⃣ Bekor qilish mumkinmi?
• Ha, 24 soat oldin xabar bering""",
    },
    'ru': {
        'start_admin': """👨‍⚕️ **Здравствуйте, Доктор!**

🎯 Ваш план на сегодня:
📊 Статистика | 📅 Приёмы | 👥 Пациенты""",
        'start_user': """🌟 **Здравствуйте!**

Я личный помощник **Dr. Abdulatifovich**.

💫 Чем могу помочь?""",
    }
}

def get_text(user_data, key):
    """Tilga mos matnni olish"""
    lang = user_data.get('lang', 'uz')
    return MATNLAR[lang].get(key, MATNLAR['uz'].get(key, key))

def favqulodda_tekshir(matn):
    """Favqulodda belgilarni tekshirish"""
    matn_kichik = matn.lower()
    return any(soz in matn_kichik for soz in FAVQULODDA_SOZLAR)

def kunlar_yasash():
    """Keyingi 7 kunni yaratish"""
    kunlar = []
    hafta_kunlari_uz = ['Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan', 'Yak']
    hafta_kunlari_ru = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    
    for i in range(1, 8):
        kun = datetime.now() + timedelta(days=i)
        if kun.weekday() == 6:  # Yakshanba - dam olish
            continue
        kunlar.append({
            'sana': kun.strftime("%d.%m.%Y"),
            'hafta_kuni_uz': hafta_kunlari_uz[kun.weekday()],
            'hafta_kuni_ru': hafta_kunlari_ru[kun.weekday()],
            'kun_obj': kun
        })
    return kunlar

def vaqtlar_yasash():
    """Qabul vaqtlarini yaratish"""
    vaqtlar = []
    for soat in range(9, 18):
        if soat == 13:  # Tushlik
            continue
        vaqtlar.append(f"{soat:02d}:00")
        if soat < 17:
            vaqtlar.append(f"{soat:02d}:30")
    return vaqtlar

async def check_subscription(user_id, context):
    """Kanalga obuna tekshirish"""
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        logger.error(f"Obuna tekshirishda xato: {e}")
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botni boshlash"""
    user_id = update.effective_user.id
    
    # Admin tekshiruvi - ENG BIRINCHI!
    if user_id in ADMIN_CHAT_IDS:
        logger.info(f"✅ Admin kirdi: {user_id}")
        keyboard = [
            [
                InlineKeyboardButton("📊 Statistika", callback_data='admin_stat'),
                InlineKeyboardButton("📅 Bugun", callback_data='admin_today')
            ],
            [
                InlineKeyboardButton("👥 Bemorlar", callback_data='admin_patients'),
                InlineKeyboardButton("📈 Grafik", callback_data='admin_chart')
            ],
            [
                InlineKeyboardButton("💰 Daromad", callback_data='admin_income'),
                InlineKeyboardButton("⚙️ Sozlamalar", callback_data='admin_settings')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        matn = """👨‍⚕️ **Assalomu alaykum, Doktor!**

🎯 **Bugungi rejangiz:**

📊 Statistika - Umumiy ma'lumotlar
📅 Bugun - Bugungi qabullar
👥 Bemorlar - Bemorlar bazasi
📈 Grafik - Ko'rsatkichlar
💰 Daromad - Moliyaviy hisobot
⚙️ Sozlamalar - Bot sozlamalari"""
        
        await update.message.reply_text(matn, reply_markup=reply_markup)
        return ConversationHandler.END
    
    # Obuna tekshiruvi
    is_member = await check_subscription(user_id, context)
    
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 Kanalga a'zo bo'lish", 
                                url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("✅ A'zo bo'ldim", callback_data='check_sub')]
        ]
        msg = f"""⚠️ **Hurmatli foydalanuvchi!**

Botdan foydalanish uchun rasmiy kanalimizga a'zo bo'ling.

📢 Kanal: {CHANNEL_USERNAME}

🎁 Kanalda:
• Tibbiy maslahatlar
• Sog'liq haqida ma'lumotlar
• Yangiliklar va chegirmalar"""
        
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    # Tilni tanlash
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data='set_lang_uz'),
            InlineKeyboardButton("🇷🇺 Русский", callback_data='set_lang_ru')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if 'ism' in context.user_data:
        context.user_data.clear()
    
    await update.message.reply_text(
        "🌐 **Tilni tanlang / Выберите язык**",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def boshlash_suhbat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qabulga yozilishni boshlash"""
    query = update.callback_query
    await query.answer()
    
    matn = get_text(context.user_data, 'ism_savol')
    progress = get_text(context.user_data, 'progress_1')
    
    await query.edit_message_text(f"{progress}\n\n{matn}")
    return ISM

async def tugma_bosildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback tugmalar"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    
    # Obuna tekshirish
    if data == 'check_sub':
        is_member = await check_subscription(user_id, context)
        if is_member:
            await query.delete_message()
            keyboard = [
                [
                    InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data='set_lang_uz'),
                    InlineKeyboardButton("🇷🇺 Русский", callback_data='set_lang_ru')
                ]
            ]
            await query.message.reply_text(
                "🌐 **Tilni tanlang / Выберите язык**",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.answer("❌ Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)
        return
    
    # Til sozlash
    if data.startswith('set_lang_'):
        lang = data.split('_')[-1]
        context.user_data['lang'] = lang
        
        # Admin check QAYTADAN
        if user_id in ADMIN_CHAT_IDS:
            keyboard = [
                [
                    InlineKeyboardButton("📊 Statistika", callback_data='admin_stat'),
                    InlineKeyboardButton("📅 Bugun", callback_data='admin_today')
                ],
                [
                    InlineKeyboardButton("👥 Bemorlar", callback_data='admin_patients'),
                    InlineKeyboardButton("📈 Grafik", callback_data='admin_chart')
                ]
            ]
            await query.edit_message_text(
                get_text(context.user_data, 'start_admin'),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            keyboard = [
                [InlineKeyboardButton("📝 Qabulga yozilish", callback_data='boshlash')],
                [
                    InlineKeyboardButton("📞 Bog'lanish", callback_data='aloqa'),
                    InlineKeyboardButton("❓ FAQ", callback_data='savol')
                ],
                [InlineKeyboardButton("📋 Mening qabullarim", callback_data='my_appointments')]
            ]
            await query.edit_message_text(
                get_text(context.user_data, 'start_user'),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    # Admin paneli
    if data == 'admin_stat':
        bemorlar_soni = len(bemorlar)
        qabullar_soni = len(qabullar)
        bugun = datetime.now().strftime("%d.%m.%Y")
        bugungi = sum(1 for q in qabullar.values() if q.get('sana') == bugun)
        
        stat = f"""📊 Klinika Statistikasi

👥 Bemorlar: {bemorlar_soni} ta
📝 Qabullar: {qabullar_soni} ta
📅 Bugun: {bugungi} ta

📈 Oxirgi 7 kun:
• Qabullar: {qabullar_soni} ta
• Yangi bemorlar: {bemorlar_soni} ta"""
        
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='admin_back')]]
        await query.edit_message_text(stat, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    elif data == 'admin_today':
        bugun_str = datetime.now().strftime("%d.%m.%Y")
        bugungi_list = [q for q in qabullar.values() if q.get('sana') == bugun_str]
        
        if not bugungi_list:
            text = f"📅 {bugun_str}\n\n✨ Bugun uchun qabullar yo'q."
        else:
            text = f"📅 {bugun_str} - Qabul jadvali\n\n"
            bugungi_list.sort(key=lambda x: x.get('vaqt', '00:00'))
            for i, q in enumerate(bugungi_list, 1):
                text += f"{i}. 🕐 {q.get('vaqt')} - {q.get('ism')} {q.get('familiya')}\n"
                text += f"   📞 {q.get('telefon')}\n\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='admin_back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    elif data == 'admin_patients':
        if not bemorlar:
            text = "👥 Bemorlar bazasi\n\n📭 Hali bemorlar yo'q."
        else:
            text = f"👥 Bemorlar bazasi ({len(bemorlar)} ta)\n\n"
            for user_id_b, bemor in list(bemorlar.items())[:10]:
                text += f"• {bemor.get('ism')} {bemor.get('familiya')}\n"
                text += f"  📞 {bemor.get('telefon')}\n\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='admin_back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    elif data == 'admin_back':
        keyboard = [
            [
                InlineKeyboardButton("📊 Statistika", callback_data='admin_stat'),
                InlineKeyboardButton("📅 Bugun", callback_data='admin_today')
            ],
            [
                InlineKeyboardButton("👥 Bemorlar", callback_data='admin_patients'),
                InlineKeyboardButton("📈 Grafik", callback_data='admin_chart')
            ]
        ]
        await query.edit_message_text(
            "👨‍⚕️ Admin Panel",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Bemor paneli
    elif data == 'aloqa':
        aloqa = get_text(context.user_data, 'aloqa_info').format(
            telefon=DOCTOR_PHONE,
            username=DOCTOR_USERNAME
        )
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='user_back')]]
        await query.edit_message_text(aloqa, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'savol':
        faq = get_text(context.user_data, 'faq')
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='user_back')]]
        await query.edit_message_text(faq, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'my_appointments':
        user_appointments = [q for q in qabullar.values() if q.get('user_id') == user_id]
        
        if not user_appointments:
            text = "📋 Mening qabullarim\n\n📭 Hozircha qabullar yo'q."
        else:
            text = f"📋 Mening qabullarim ({len(user_appointments)} ta)\n\n"
            for q in user_appointments:
                status_emoji = "✅" if q.get('holat') == 'TASDIQLANDI' else "⏳"
                text += f"{status_emoji} #{q.get('id')} - {q.get('sana')} {q.get('vaqt')}\n"
                text += f"   Holat: {q.get('holat', 'KUTILMOQDA')}\n\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='user_back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'user_back':
        keyboard = [
            [InlineKeyboardButton("📝 Qabulga yozilish", callback_data='boshlash')],
            [
                InlineKeyboardButton("📞 Bog'lanish", callback_data='aloqa'),
                InlineKeyboardButton("❓ FAQ", callback_data='savol')
            ],
            [InlineKeyboardButton("📋 Mening qabullarim", callback_data='my_appointments')]
        ]
        await query.edit_message_text(
            get_text(context.user_data, 'start_user'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def ism_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ism olish"""
    context.user_data['ism'] = update.message.text
    
    matn = get_text(context.user_data, 'familiya_savol')
    progress = get_text(context.user_data, 'progress_2')
    
    await update.message.reply_text(f"{progress}\n\n{matn}")
    return FAMILIYA

async def familiya_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Familiya olish"""
    context.user_data['familiya'] = update.message.text
    
    matn = get_text(context.user_data, 'yosh_savol')
    progress = get_text(context.user_data, 'progress_3')
    
    await update.message.reply_text(f"{progress}\n\n{matn}")
    return YOSH

async def yosh_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yosh olish"""
    try:
        yosh = int(update.message.text)
        if yosh < 1 or yosh > 120:
            raise ValueError
        context.user_data['yosh'] = yosh
        
        matn = get_text(context.user_data, 'telefon_savol')
        progress = get_text(context.user_data, 'progress_4')
        
        await update.message.reply_text(f"{progress}\n\n{matn}")
        return TELEFON
    except ValueError:
        await update.message.reply_text("❌ Iltimos, to'g'ri yosh kiriting (1-120):")
        return YOSH

async def telefon_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telefon olish"""
    context.user_data['telefon'] = update.message.text
    
    matn = get_text(context.user_data, 'manzil_savol')
    progress = get_text(context.user_data, 'progress_5')
    
    await update.message.reply_text(f"{progress}\n\n{matn}")
    return MANZIL

async def manzil_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manzil olish"""
    context.user_data['manzil'] = update.message.text
    
    matn = get_text(context.user_data, 'shikoyat_savol')
    progress = get_text(context.user_data, 'progress_6')
    
    await update.message.reply_text(f"{progress}\n\n{matn}")
    return SHIKOYAT

async def shikoyat_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shikoyat olish"""
    shikoyat = update.message.text
    context.user_data['shikoyat'] = shikoyat
    
    # Favqulodda tekshirish
    if favqulodda_tekshir(shikoyat):
        context.user_data['favqulodda'] = True
        xabar = get_text(context.user_data, 'favq_ogohlantirish')
        await update.message.reply_text(xabar)
        await favqulodda_adminlarga(context, context.user_data)
        return ConversationHandler.END
    
    # Favqulodda savol
    keyboard = [
        [
            InlineKeyboardButton("✅ Ha", callback_data='favq_ha'),
            InlineKeyboardButton("❌ Yo'q", callback_data='favq_yoq')
        ]
    ]
    
    matn = get_text(context.user_data, 'favq_savol')
    await update.message.reply_text(matn, reply_markup=InlineKeyboardMarkup(keyboard))
    return FAVQULODDA

async def favqulodda_javob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Favqulodda javob"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'favq_ha':
        xabar = get_text(context.user_data, 'favq_ogohlantirish')
        await query.edit_message_text(xabar)
        await favqulodda_adminlarga(context, context.user_data)
        return ConversationHandler.END
    
    context.user_data['favqulodda'] = False
    
    # Sana tanlash
    kunlar = kunlar_yasash()
    keyboard = []
    lang = context.user_data.get('lang', 'uz')
    
    for kun in kunlar:
        hafta_kuni = kun['hafta_kuni_uz'] if lang == 'uz' else kun['hafta_kuni_ru']
        keyboard.append([InlineKeyboardButton(
            f"{hafta_kuni}, {kun['sana']}", 
            callback_data=f"sana_{kun['sana']}"
        )])
    
    matn = get_text(context.user_data, 'sana_tanlash')
    await query.edit_message_text(matn, reply_markup=InlineKeyboardMarkup(keyboard))
    return SANA

async def sana_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sana tanlash"""
    query = update.callback_query
    await query.answer()
    
    sana = query.data.replace('sana_', '')
    context.user_data['sana'] = sana
    
    # Vaqt tanlash
    vaqtlar = vaqtlar_yasash()
    keyboard = []
    row = []
    
    for i, vaqt in enumerate(vaqtlar):
        row.append(InlineKeyboardButton(vaqt, callback_data=f"vaqt_{vaqt}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    matn = get_text(context.user_data, 'vaqt_tanlash').format(sana=sana)
    await query.edit_message_text(matn, reply_markup=InlineKeyboardMarkup(keyboard))
    return VAQT

async def vaqt_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vaqt tanlash va yakunlash"""
    query = update.callback_query
    await query.answer()
    
    vaqt = query.data.replace('vaqt_', '')
    context.user_data['vaqt'] = vaqt
    
    # Saqlash
    qabul_id = len(qabullar) + 1
    bemor_malumot = {
        'id': qabul_id,
        'user_id': update.effective_user.id,
        'username': update.effective_user.username,
        'ism': context.user_data['ism'],
        'familiya': context.user_data['familiya'],
        'yosh': context.user_data['yosh'],
        'telefon': context.user_data['telefon'],
        'manzil': context.user_data['manzil'],
        'shikoyat': context.user_data['shikoyat'],
        'sana': context.user_data['sana'],
        'vaqt': context.user_data['vaqt'],
        'holat': 'KUTILMOQDA',
        'yaratilgan': datetime.now().isoformat()
    }
    
    qabullar[qabul_id] = bemor_malumot
    bemorlar[update.effective_user.id] = bemor_malumot
    
    # ✅ ADMINLARGA XABAR - ASOSIY FIX!
    logger.info(f"📤 Adminlarga xabar yuborish boshlandi... ID: {qabul_id}")
    logger.info(f"👥 Adminlar ro'yxati: {ADMIN_CHAT_IDS}")
    
    await adminlarga_xabar_yuborish(context, bemor_malumot)
    
    # Bemorga kutish xabari
    kutish = get_text(context.user_data, 'kutish_xabar').format(
        qabul_id=qabul_id,
        ism=context.user_data['ism']
    )
    
    await query.edit_message_text(kutish)
    
    # Menyu
    keyboard = [[InlineKeyboardButton("🏠 Bosh menyu", callback_data='user_back')]]
    await query.message.reply_text(
        "Yana nima yordam kerak?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

async def bekor_qilish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bekor qilish"""
    await update.message.reply_text(
        "❌ Bekor qilindi.\n\n/start - qaytadan boshlash"
    )
    return ConversationHandler.END

async def adminlarga_xabar_yuborish(context, bemor):
    """✅ FIXED: Adminlarga yangi bemor xabari"""
    
    # DEBUGGING
    logger.info("="*60)
    logger.info("📤 ADMINLARGA XABAR YUBORISH BOSHLANDI")
    logger.info(f"👥 Adminlar soni: {len(ADMIN_CHAT_IDS)}")
    logger.info(f"🆔 Admin IDs: {ADMIN_CHAT_IDS}")
    logger.info(f"📋 Qabul ID: {bemor['id']}")
    logger.info("="*60)
    
    if not ADMIN_CHAT_IDS:
        logger.error("❌ ADMIN_CHAT_IDS BO'SH! Xabar yuborilmadi!")
        print("\n" + "!"*60)
        print("❌ XATO: ADMIN_CHAT_IDS bo'sh!")
        print("!"*60 + "\n")
        return
    
    xabar = f"""🔔 YANGI QABUL SO'ROVI

📋 ID: #{bemor['id']:04d}

👤 Bemor:
━━━━━━━━━━━━━━
• Ism: {bemor['ism']} {bemor['familiya']}
• Yosh: {bemor['yosh']}
• Tel: {bemor['telefon']}
• Manzil: {bemor['manzil']}

🩺 Shikoyat:
{bemor['shikoyat']}

📅 So'ralgan vaqt:
{bemor['sana']}, {bemor['vaqt']}

⏰ Yaratildi: {bemor['yaratilgan'][:16]}
━━━━━━━━━━━━━━

✅ Bemor bilan bog'laning!"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"qabul_tasdiq_{bemor['id']}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"qabul_bekor_{bemor['id']}")
        ],
        [InlineKeyboardButton("📞 Qo'ng'iroq", url=f"tel:{bemor['telefon']}")],
    ]
    
    # Username mavjud bo'lsa
    if bemor.get('username'):
        keyboard.append([InlineKeyboardButton("💬 Xabar", url=f"https://t.me/{bemor['username']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    success_count = 0
    for admin_id in ADMIN_CHAT_IDS:
        try:
            logger.info(f"📨 Admin {admin_id} ga yuborilmoqda...")
            await context.bot.send_message(
                chat_id=admin_id,
                text=xabar,
                reply_markup=reply_markup
            )
            success_count += 1
            logger.info(f"✅ Admin {admin_id}ga MUVAFFAQIYATLI yuborildi!")
            print(f"✅ Xabar yuborildi: Admin {admin_id}")
        except Exception as e:
            logger.error(f"❌ Admin {admin_id} ga xabar yuborishda XATO: {e}")
            print(f"❌ XATO: Admin {admin_id} - {e}")
    
    logger.info(f"📊 NATIJA: {success_count}/{len(ADMIN_CHAT_IDS)} adminlarga yuborildi")
    print(f"\n📊 Jami {success_count} ta adminlarga xabar yuborildi\n")

async def favqulodda_adminlarga(context, bemor_data):
    """✅ FIXED: Favqulodda xabar"""
    logger.info("🚨 FAVQULODDA XABAR yuborilmoqda...")
    
    xabar = f"""🚨🚨🚨 FAVQULODDA! SHOSHILINCH! 🚨🚨🚨

‼️ ZUDLIK BILAN CHORALAR KO'RING!

👤 Bemor:
━━━━━━━━━━━━━━
• Ism: {bemor_data.get('ism', 'N/A')} {bemor_data.get('familiya', '')}
• Yosh: {bemor_data.get('yosh', 'N/A')}
• Tel: {bemor_data.get('telefon', 'N/A')}
• Manzil: {bemor_data.get('manzil', 'N/A')}

🆘 FAVQULODDA SHIKOYAT:
{bemor_data.get('shikoyat', 'N/A')}

━━━━━━━━━━━━━━
⚠️ Bemor 103ga yo'naltirildi!
☎️ DARHOL qo'ng'iroq qiling!"""
    
    keyboard = [
        [InlineKeyboardButton("📞 ZUDLIK BILAN QO'NG'IROQ", 
                            url=f"tel:{bemor_data.get('telefon', '')}")]
    ]
    
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=xabar,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            logger.info(f"🚨 Favqulodda xabar yuborildi: Admin {admin_id}")
        except Exception as e:
            logger.error(f"❌ Favqulodda xabar xatosi {admin_id}: {e}")

async def admin_qabul_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin tasdiqlash/rad etish"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    action, qabul_id_str = data.rsplit('_', 1)
    qabul_id = int(qabul_id_str)
    bemor = qabullar.get(qabul_id)
    
    if not bemor:
        await query.edit_message_text("❌ Uchrashuv topilmadi.")
        return
    
    if action == 'qabul_tasdiq':
        # Bemorga tasdiqlash xabari
        lang = bemorlar.get(bemor['user_id'], {}).get('lang', 'uz')
        user_data_temp = {'lang': lang}
        
        tasdiq = get_text(user_data_temp, 'tasdiq_xabar').format(
            sana=bemor['sana'],
            vaqt=bemor['vaqt']
        )
        
        try:
            await context.bot.send_message(chat_id=bemor['user_id'], text=tasdiq)
            
            # Lokatsiya (o'zingizning lokatsiyangizni qo'ying)
            await context.bot.send_location(
                chat_id=bemor['user_id'],
                latitude=41.311158,  # Toshkent
                longitude=69.279737
            )
            
            await query.edit_message_text(
                f"✅ TASDIQLANDI!\n\nBemor: {bemor['ism']} {bemor['familiya']}\n"
                f"Vaqt: {bemor['sana']} {bemor['vaqt']}\n\n"
                f"📍 Bemorga lokatsiya yuborildi."
            )
            bemor['holat'] = 'TASDIQLANDI'
            
        except Exception as e:
            await query.message.reply_text(f"❌ Xatolik: {e}")
    
    elif action == 'qabul_bekor':
        lang = bemorlar.get(bemor['user_id'], {}).get('lang', 'uz')
        user_data_temp = {'lang': lang}
        
        bekor = get_text(user_data_temp, 'bekor_xabar').format(
            doktor_telefon=DOCTOR_PHONE
        )
        
        try:
            await context.bot.send_message(chat_id=bemor['user_id'], text=bekor)
        except:
            pass
        
        await query.edit_message_text(
            f"❌ RAD ETILDI\n\nBemor: {bemor['ism']} {bemor['familiya']}"
        )
        bemor['holat'] = 'BEKOR_QILINDI'

def main():
    """Botni ishga tushirish"""
    try:
        if not BOT_TOKEN:
            print("❌ XATO: BOT_TOKEN topilmadi!")
            print("💡 .env faylida BOT_TOKEN ni qo'shing")
            sys.exit(1)
        
        print("\n" + "="*70)
        print("🧠 NEVROPATOLOG BOT v2.0 - FIXED VERSION")
        print("="*70)
        print(f"📱 Bot: @{DOCTOR_USERNAME}")
        print(f"👥 Adminlar soni: {len(ADMIN_CHAT_IDS)} ta")
        
        # KRITIK: Admin tekshiruvi
        if not ADMIN_CHAT_IDS:
            print("\n" + "⚠️"*25)
            print("❌ DIQQAT: ADMIN_CHAT_IDS BO'SH!")
            print("❌ BEMORLARDAN XABARLAR HECH KIMGA KELMAYDI!")
            print("⚠️"*25 + "\n")
            print("📝 TUZATISH:")
            print("   1. .env faylini oching")
            print("   2. Quyidagini qo'shing:")
            print("      ADMIN_CHAT_IDS=8104665298,7523126393")
            print("   3. Botni qayta ishga tushiring")
            print("="*70 + "\n")
            
            import time
            print("⏳ 5 soniyadan keyin bot ishga tushadi...")
            for i in range(5, 0, -1):
                print(f"   {i}...")
                time.sleep(1)
            print("\n⚠️ ADMINLAR YO'Q - XABARLAR YUBORILMAYDI!\n")
        else:
            print(f"✅ Admin IDs: {ADMIN_CHAT_IDS}")
        
        print("="*70 + "\n")
        
        # Web server
        try:
            server_thread = Thread(target=run_web_server, daemon=True)
            server_thread.start()
            print("✅ Web server ishga tushdi (Render)")
        except Exception as e:
            print(f"⚠️ Web server xatosi: {e}")
        
        # Application
        application = Application.builder().token(BOT_TOKEN).build()
        
    except Exception as e:
        print(f"❌ KRITIK XATO: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(boshlash_suhbat, pattern='^boshlash$')
        ],
        states={
            ISM: [MessageHandler(filters.TEXT & ~filters.COMMAND, ism_olish)],
            FAMILIYA: [MessageHandler(filters.TEXT & ~filters.COMMAND, familiya_olish)],
            YOSH: [MessageHandler(filters.TEXT & ~filters.COMMAND, yosh_olish)],
            TELEFON: [MessageHandler(filters.TEXT & ~filters.COMMAND, telefon_olish)],
            MANZIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, manzil_olish)],
            SHIKOYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, shikoyat_olish)],
            FAVQULODDA: [CallbackQueryHandler(favqulodda_javob)],
            SANA: [CallbackQueryHandler(sana_tanlash, pattern='^sana_')],
            VAQT: [CallbackQueryHandler(vaqt_tanlash, pattern='^vaqt_')]
        },
        fallbacks=[
            CommandHandler('cancel', bekor_qilish),
            CommandHandler('start', start)
        ]
    )
    
    # Handlerlar
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(admin_qabul_callback, pattern='^qabul_'))
    application.add_handler(CallbackQueryHandler(tugma_bosildi))
    
    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    print("🔄 To'xtatish: Ctrl+C\n")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"❌ XATO: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()