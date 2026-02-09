"""
🏥 Nevropatolog Konsultatsiya Boti v2.0
Dr. Abdulatifovich uchun maxsus professional bot
Python 3.14+ | Zamonaviy UI/UX | Kreativ yondashuv
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
    return "✅ Nevropatolog Bot v2.0 ishlamoqda!"

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
        'sana_tanlash': '📅 **Uchrashuv sanasi**\n\nQaysi kun sizga qulay?',
        'vaqt_tanlash': '🕐 **Uchrashuv vaqti**\n\nSana: **{sana}**\n\nQaysi vaqt mos keladi?',
        'kutish_xabar': """✅ **Tasdiqlanmoqda...**

📋 **Uchrashuv raqami:** #{qabul_id}

Hurmatli **{ism}**, so'rovingiz Doktorga yuborildi.

⏳ **Iltimos, sabr qiling!**

Doktor tasdiqlagandan so'ng sizga:
📍 Klinika joylashuvi
📋 Kerakli hujjatlar ro'yxati
📞 Qo'shimcha ma'lumotlar

yuboriladi.

🔔 Xabar olishni kuting!""",
        'tasdiq_xabar': """✅ **TABRIKLAYMIZ! Uchrashuv tasdiqlandi**

📅 **Sana va vaqt:** {sana}, soat {vaqt}
👨‍⚕️ **Doktor:** Dr. Abdulatifovich

📂 **O'zingiz bilan ALBATTA olib keling:**

1️⃣ 📇 Pasport (ID karta)
2️⃣ 📋 Tibbiy karta (agar bor bo'lsa)
3️⃣ 🧪 Oldingi tahlillar:
   • MRT/MSKT natijalari
   • Qon tahlillari
   • Boshqa tekshiruvlar
4️⃣ 💊 Hozir qabul qilayotgan dorilar ro'yxati

⏰ **Eslatma:**
Uchrashuv vaqtidan 10-15 daqiqa oldin keling.

📍 **Klinika manzili pastda ko'rsatilgan**

🌟 Sizni kutamiz!""",
        'bekor_xabar': """❌ **Afsuski, uchrashuv bekor qilindi**

📞 Boshqa vaqt uchun bog'laning:
{doktor_telefon}

Yoki qaytadan /start buyrug'ini bering.""",
        'aloqa_info': """📞 **Bog'lanish ma'lumotlari**

👨‍⚕️ **Doktor:** Dr. Abdulatifovich
📱 **Telefon:** {telefon}
💬 **Telegram:** @{username}

🏥 **Ish vaqti:**
🕐 Dushanba-Shanba: 09:00-18:00
🌙 Yakshanba: Dam olish

📍 **Manzil:** Toshkent shahri
*[Aniq manzil qo'shiladi]*

🚨 **Favqulodda:** 103""",
        'faq': """❓ **Tez-tez beriladigan savollar**

**1️⃣ Uchrashuv qancha davom etadi?**
• Birinchi ko'rik: 30-45 daqiqa
• Qayta ko'rik: 20-30 daqiqa

**2️⃣ Nima olib borish kerak?**
• Pasport
• Tibbiy hujjatlar
• Tahlillar
• Dorilar ro'yxati

**3️⃣ Online konsultatsiya bormi?**
• Ha, Telegram orqali

**4️⃣ To'lov usullari?**
• Naqd
• Plastik karta

**5️⃣ Bekor qilish mumkinmi?**
• Ha, 24 soat oldin xabar bering""",
        'rating_request': """⭐ **Fikr-mulohazangiz muhim!**

Doktor xizmatini baholang:

🌟🌟🌟🌟🌟 - A'lo
🌟🌟🌟🌟 - Yaxshi
🌟🌟🌟 - O'rtacha
🌟🌟 - Qoniqarsiz
🌟 - Yomon"""
    },
    'ru': {
        'start_admin': """👨‍⚕️ **Здравствуйте, Доктор!**

🎯 Ваш план на сегодня:
📊 Статистика | 📅 Приёмы | 👥 Пациенты""",
        'start_user': """🌟 **Здравствуйте!**

Я личный помощник **Dr. Abdulatifovich**.

💫 Чем могу помочь?""",
        'progress_1': '▰▱▱▱▱▱ 17%',
        'progress_2': '▰▰▱▱▱▱ 33%',
        'progress_3': '▰▰▰▱▱▱ 50%',
        'progress_4': '▰▰▰▰▱▱ 67%',
        'progress_5': '▰▰▰▰▰▱ 83%',
        'progress_6': '▰▰▰▰▰▰ 100%',
        'ism_savol': '👤 **1/6 - Личные данные**\n\n📝 Введите ваше имя:',
        'familiya_savol': '👤 **2/6 - Личные данные**\n\n📝 Введите фамилию:',
        'yosh_savol': '🎂 **3/6 - Личные данные**\n\n🔢 Введите возраст (цифрами):',
        'telefon_savol': '📱 **4/6 - Контакты**\n\n☎️ Введите номер телефона:\n\n*Например:* +998 99 123 45 67',
        'manzil_savol': '🏠 **5/6 - Местоположение**\n\n📍 Введите адрес:\n\n*Например:* Ташкент, Чиланзар 12-квартал',
        'shikoyat_savol': """🩺 **6/6 - Медицинская информация**

📋 Опишите подробно ваши жалобы:

💡 *Укажите:*
   • Какие симптомы?
   • С какого времени беспокоят?
   • Степень боли (1-10)
   • Другие признаки""",
        'favq_savol': """⚠️ **Важный вопрос!**

Есть ли у вас **срочные симптомы**?

🔴 Острая головная боль
🔴 Нарушение речи
🔴 Слабость в лице или теле
🔴 Судороги
🔴 Потеря сознания
🔴 Нарушение зрения""",
        'favq_ogohlantirish': """🚨 **СРОЧНАЯ СИТУАЦИЯ!**

Описанные симптомы требуют НЕМЕДЛЕННОЙ помощи!

‼️ **СРОЧНО:**

1️⃣ ☎️ Звоните **103**
2️⃣ 🏥 Езжайте в ближайшую больницу
3️⃣ 🚑 Вызовите скорую

⚕️ Доктор тоже вам позвонит!

📞 Ваши данные отправлены доктору.""",
        'sana_tanlash': '📅 **Дата встречи**\n\nКакой день вам удобен?',
        'vaqt_tanlash': '🕐 **Время встречи**\n\nДата: **{sana}**\n\nВыберите время:',
        'kutish_xabar': """✅ **Подтверждается...**

📋 **Номер записи:** #{qabul_id}

Уважаемый **{ism}**, запрос отправлен Доктору.

⏳ **Ожидайте!**

После подтверждения вы получите:
📍 Адрес клиники
📋 Список документов
📞 Доп. информацию

🔔 Ждите уведомление!""",
        'tasdiq_xabar': """✅ **ПОЗДРАВЛЯЕМ! Приём подтверждён**

📅 **Дата и время:** {sana}, {vaqt}
👨‍⚕️ **Доктор:** Dr. Abdulatifovich

📂 **Возьмите с собой:**

1️⃣ 📇 Паспорт
2️⃣ 📋 Мед. карту (если есть)
3️⃣ 🧪 Анализы:
   • МРТ/КТ
   • Анализы крови
   • Другие обследования
4️⃣ 💊 Список лекарств

⏰ **Напоминание:**
Приходите за 10-15 минут.

📍 **Адрес ниже**

🌟 Ждём вас!""",
        'bekor_xabar': """❌ **К сожалению, приём отменён**

📞 Для записи позвоните:
{doktor_telefon}

Или начните заново /start""",
        'aloqa_info': """📞 **Контакты**

👨‍⚕️ **Доктор:** Dr. Abdulatifovich
📱 **Телефон:** {telefon}
💬 **Telegram:** @{username}

🏥 **Часы работы:**
🕐 Пн-Сб: 09:00-18:00
🌙 Вс: Выходной

📍 **Адрес:** Ташкент
*[Точный адрес будет добавлен]*

🚨 **Скорая:** 103""",
        'faq': """❓ **Частые вопросы**

**1️⃣ Длительность приёма?**
• Первичный: 30-45 мин
• Повторный: 20-30 мин

**2️⃣ Что взять с собой?**
• Паспорт
• Мед. документы
• Анализы
• Список лекарств

**3️⃣ Онлайн консультация?**
• Да, через Telegram

**4️⃣ Способы оплаты?**
• Наличные
• Карта

**5️⃣ Можно отменить?**
• Да, за 24 часа""",
        'rating_request': """⭐ **Ваш отзыв важен!**

Оцените приём доктора:

🌟🌟🌟🌟🌟 - Отлично
🌟🌟🌟🌟 - Хорошо
🌟🌟🌟 - Средне
🌟🌟 - Плохо
🌟 - Ужасно"""
    }
}

def get_text(user_data, key):
    """Tilga mos matnni olish"""
    lang = user_data.get('lang', 'uz')
    return MATNLAR[lang].get(key, MATNLAR['uz'][key])

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
    
    # Admin tekshiruvi
    if user_id in ADMIN_CHAT_IDS:
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
    
    # Obuna tekshirish
    if data == 'check_sub':
        is_member = await check_subscription(update.effective_user.id, context)
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
        
        if update.effective_user.id in ADMIN_CHAT_IDS:
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
                [InlineKeyboardButton("📝 Uchrashuv belgilash", callback_data='boshlash')],
                [
                    InlineKeyboardButton("📞 Bog'lanish", callback_data='aloqa'),
                    InlineKeyboardButton("❓ FAQ", callback_data='savol')
                ],
                [InlineKeyboardButton("📋 Mening uchrashuvlarim", callback_data='my_appointments')]
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
        
        # O'rtacha reyting
        avg_rating = 0
        if ratinglar:
            avg_rating = sum(ratinglar.values()) / len(ratinglar)
        
        stat = f"""📊 **Klinika Statistikasi**

👥 **Bemorlar:** {bemorlar_soni} ta
📝 **Uchrashuv:** {qabullar_soni} ta
📅 **Bugun:** {bugungi} ta
⭐ **Reyting:** {avg_rating:.1f}/5.0

📈 **Oxirgi 7 kun:**
• Uchrashuv: {qabullar_soni} ta
• Yangi bemorlar: {bemorlar_soni} ta
• Bekor qilingan: 0 ta

💰 **Moliyaviy:**
• Bugungi daromad: 0 so'm
• Oylik: 0 so'm"""
        
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='admin_back')]]
        await query.edit_message_text(stat, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    elif data == 'admin_today':
        bugun_str = datetime.now().strftime("%d.%m.%Y")
        bugungi_list = [q for q in qabullar.values() if q.get('sana') == bugun_str]
        
        if not bugungi_list:
            text = f"📅 **{bugun_str}**\n\n✨ Bugun uchun uchrashuv yo'q."
        else:
            text = f"📅 **{bugun_str} - Uchrashuv jadvali**\n\n"
            bugungi_list.sort(key=lambda x: x.get('vaqt', '00:00'))
            for i, q in enumerate(bugungi_list, 1):
                text += f"{i}. 🕐 **{q.get('vaqt')}** - {q.get('ism')} {q.get('familiya')}\n"
                text += f"   📞 {q.get('telefon')}\n"
                text += f"   📍 {q.get('manzil')}\n\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='admin_back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    elif data == 'admin_patients':
        if not bemorlar:
            text = "👥 **Bemorlar bazasi**\n\n📭 Hali bemorlar yo'q."
        else:
            text = f"👥 **Bemorlar bazasi** ({len(bemorlar)} ta)\n\n"
            for user_id, bemor in list(bemorlar.items())[:10]:
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
            "👨‍⚕️ **Admin Panel**",
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
        user_appointments = [q for q in qabullar.values() if q.get('user_id') == update.effective_user.id]
        
        if not user_appointments:
            text = "📋 **Mening uchrashuvlarim**\n\n📭 Hozircha uchrashuvlar yo'q."
        else:
            text = f"📋 **Mening uchrashuvlarim** ({len(user_appointments)} ta)\n\n"
            for q in user_appointments:
                status_emoji = "✅" if q.get('holat') == 'TASDIQLANDI' else "⏳"
                text += f"{status_emoji} **#{q.get('id')}** - {q.get('sana')} {q.get('vaqt')}\n"
                text += f"   Holat: {q.get('holat', 'KUTILMOQDA')}\n\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='user_back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'user_back':
        lang = context.user_data.get('lang', 'uz')
        keyboard = [
            [InlineKeyboardButton("📝 Uchrashuv belgilash", callback_data='boshlash')],
            [
                InlineKeyboardButton("📞 Bog'lanish", callback_data='aloqa'),
                InlineKeyboardButton("❓ FAQ", callback_data='savol')
            ],
            [InlineKeyboardButton("📋 Mening uchrashuvlarim", callback_data='my_appointments')]
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
    
    # Adminlarga xabar
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
    """Adminlarga yangi bemor xabari"""
    xabar = f"""🔔 **YANGI UCHRASHUV SO'ROVI**

📋 **ID:** #{bemor['id']:04d}

👤 **Bemor:**
━━━━━━━━━━━━━━
• Ism: {bemor['ism']} {bemor['familiya']}
• Yosh: {bemor['yosh']}
• Tel: {bemor['telefon']}
• Manzil: {bemor['manzil']}

🩺 **Shikoyat:**
{bemor['shikoyat']}

📅 **So'ralgan vaqt:**
{bemor['sana']}, {bemor['vaqt']}

⏰ **Yaratildi:** {bemor['yaratilgan'][:16]}
━━━━━━━━━━━━━━

✅ Bemor bilan bog'laning!"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"qabul_tasdiq_{bemor['id']}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"qabul_bekor_{bemor['id']}")
        ],
        [InlineKeyboardButton("📞 Qo'ng'iroq qilish", url=f"tel:{bemor['telefon']}")],
        [InlineKeyboardButton("💬 Xabar yozish", url=f"https://t.me/{bemor.get('username', '')}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=xabar,
                reply_markup=reply_markup
            )
            logger.info(f"✅ Admin {admin_id}ga xabar yuborildi")
        except Exception as e:
            logger.error(f"❌ Admin {admin_id}: {e}")

async def favqulodda_adminlarga(context, bemor_data):
    """Favqulodda xabar"""
    xabar = f"""🚨 **FAVQULODDA! SHOSHILINCH!**

‼️ **ZUDLIK BILAN CHORALAR KO'RING!**

👤 **Bemor:**
━━━━━━━━━━━━━━
• Ism: {bemor_data.get('ism', 'N/A')} {bemor_data.get('familiya', '')}
• Yosh: {bemor_data.get('yosh', 'N/A')}
• Tel: {bemor_data.get('telefon', 'N/A')}
• Manzil: {bemor_data.get('manzil', 'N/A')}

🆘 **FAVQULODDA SHIKOYAT:**
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
            logger.info(f"🚨 Favqulodda xabar: Admin {admin_id}")
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
                f"✅ **TASDIQLANDI!**\n\nBemor: {bemor['ism']} {bemor['familiya']}\n"
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
            f"❌ **RAD ETILDI**\n\nBemor: {bemor['ism']} {bemor['familiya']}"
        )
        bemor['holat'] = 'BEKOR_QILINDI'

def main():
    """Botni ishga tushirish"""
    try:
        if not BOT_TOKEN:
            print("❌ XATO: BOT_TOKEN topilmadi!")
            sys.exit(1)
        
        print("🤖 Bot ishga tushmoqda...")
        print(f"📱 Bot: @{DOCTOR_USERNAME}")
        print(f"👥 Adminlar: {len(ADMIN_CHAT_IDS)} ta")
        print(f"🆔 Admin IDlari: {ADMIN_CHAT_IDS}")
        
        # Web server (Render)
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