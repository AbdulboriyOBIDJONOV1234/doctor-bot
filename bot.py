"""
Nevropatolog Konsultatsiya Boti
Dr. Abdulatifovich uchun maxsus bot
Python 3.14+ uchun yangilangan versiya
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

# Configdan ma'lumotlarni yuklash
from config import BOT_TOKEN, DOCTOR_PHONE, ADMIN_CHAT_IDS, FAVQULODDA_SOZLAR, CHANNEL_USERNAME

# Logging sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- RENDER UCHUN WEB SERVER (Keep-Alive) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlamoqda! (Render Health Check)"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
# ---------------------------------------------

# Bot sozlamalari
DOCTOR_USERNAME = "nevropatolog_abdulatifovich"

# Suhbat holatlari
(ISM, FAMILIYA, YOSH, TELEFON, MANZIL, 
 SHIKOYAT, FAVQULODDA, SANA, VAQT) = range(9)

# Ma'lumotlar bazasi (oddiy - keyinroq PostgreSQL qo'shamiz)
bemorlar = {}
qabullar = {}

def favqulodda_tekshir(matn):
    """Shikoyatda favqulodda belgilar bormi tekshirish"""
    matn_kichik = matn.lower()
    return any(soz in matn_kichik for soz in FAVQULODDA_SOZLAR)

def kunlar_yasash():
    """Keyingi 7 kunni yaratish"""
    kunlar = []
    hafta_kunlari = ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba', 'Yakshanba']
    
    for i in range(1, 8):
        kun = datetime.now() + timedelta(days=i)
        hafta_kuni = hafta_kunlari[kun.weekday()]
        if kun.weekday() == 6:  # Yakshanba - dam olish
            continue
        kunlar.append({
            'sana': kun.strftime("%d.%m.%Y"),
            'hafta_kuni': hafta_kuni,
            'kun_obj': kun
        })
    return kunlar

def vaqtlar_yasash():
    """Qabul vaqtlarini yaratish"""
    vaqtlar = []
    # Ish vaqti: 09:00 dan 18:00 gacha, tushlik 13:00-14:00
    for soat in range(9, 18):
        if soat == 13:  # Tushlik
            continue
        vaqtlar.append(f"{soat:02d}:00")
        if soat < 17:  # Oxirgi vaqt 17:00
            vaqtlar.append(f"{soat:02d}:30")
    return vaqtlar

async def check_subscription(user_id, context):
    """Foydalanuvchi kanalga a'zo ekanligini tekshirish"""
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        logger.error(f"Obuna tekshirishda xato: {e}")
        # Agar bot kanal admini bo'lmasa yoki xato bo'lsa, o'tkazib yuboramiz (xalaqit bermasligi uchun)
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botni boshlash va tilni tanlashni taklif qilish"""
    
    user_id = update.effective_user.id

    # 0. Admin tekshiruvi (Eng birinchi bo'lishi kerak)
    if user_id in ADMIN_CHAT_IDS:
        keyboard = [
            [InlineKeyboardButton("📅 Bugungi qabullar", callback_data='admin_today')],
            [InlineKeyboardButton("📊 Statistika", callback_data='admin_stat')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👨‍⚕️ **Xush kelibsiz, Doktor!**\n\nAsosiy menyu:",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    # 1. Majburiy obuna tekshiruvi
    is_member = await check_subscription(user_id, context)
    
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 Kanalga a'zo bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("✅ A'zo bo'ldim", callback_data='check_sub')]
        ]
        msg = f"⚠️ **Hurmatli foydalanuvchi!**\n\nBotdan foydalanish uchun bizning rasmiy kanalimizga a'zo bo'lishingiz shart.\n\n👉 {CHANNEL_USERNAME}"
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data='set_lang_uz')],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='set_lang_ru')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Agar suhbat ichida /start bosilsa, uni tugatish uchun
    if 'ism' in context.user_data:
        context.user_data.clear()

    await update.message.reply_text(
        "Assalomu alaykum! Bot tilini tanlang.\n\n"
        "Здравствуйте! Выберите язык бота.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def boshlash_suhbat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Suhbatni boshlash (qabulga yozilish)"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📝 Yaxshi! Keling, sizning ma'lumotlaringizni to'ldiramiz.\n\n"
        "Iltimos, **ismingizni** kiriting:"
    )
    return ISM

async def tugma_bosildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Suhbatdan tashqari inline tugmalar bosilganda"""
    query = update.callback_query
    await query.answer()
    data = query.data

    # --- OBUNA TEKSHIRISH ---
    if data == 'check_sub':
        is_member = await check_subscription(update.effective_user.id, context)
        if is_member:
            await query.delete_message()
            await start(query, context) # Qaytadan start funksiyasini chaqiramiz
        else:
            await query.answer("❌ Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)
        return

    # --- TILNI SOZLASH ---
    if data.startswith('set_lang_'):
        lang = data.split('_')[-1]
        context.user_data['lang'] = lang
        
        # Admin menyusini ko'rsatish
        if update.effective_user.id in ADMIN_CHAT_IDS:
            keyboard = [
                [InlineKeyboardButton("📅 Bugungi qabullar", callback_data='admin_today')],
                [InlineKeyboardButton("📊 Statistika", callback_data='admin_stat')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "👨‍⚕️ **Xush kelibsiz, Doktor!**\n\nAsosiy menyu:",
                reply_markup=reply_markup
            )
        # Oddiy foydalanuvchi menyusini ko'rsatish
        else:
            xabar = """🏥 Assalomu alaykum!

Men **Dr. Abdulatifovich** ning konsultatsiya botiman.

Boshlash uchun pastdagi tugmani bosing."""
            keyboard = [
                [InlineKeyboardButton("📝 Qabulga yozilish", callback_data='boshlash')],
                [InlineKeyboardButton("📞 Aloqa ma'lumotlari", callback_data='aloqa')],
                [InlineKeyboardButton("❓ Savollar", callback_data='savol')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(xabar, reply_markup=reply_markup)
        return

    # --- ADMIN MENYUSI ---
    elif data == 'admin_stat':
        bemorlar_soni = len(bemorlar)
        qabullar_soni = len(qabullar)
        bugun = datetime.now().strftime("%d.%m.%Y")
        bugungi_qabullar = sum(1 for q in qabullar.values() if q.get('sana') == bugun)
        
        stat_xabar = f"""📊 **Klinika Statistikasi**

👥 **Jami bemorlar:** {bemorlar_soni} ta
📝 **Jami qabullar:** {qabullar_soni} ta
📅 **Bugungi qabullar:** {bugungi_qabullar} ta
"""
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='admin_menu_back')]]
        await query.edit_message_text(stat_xabar, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif data == 'admin_today':
        bugun_str = datetime.now().strftime("%d.%m.%Y")
        bugungi_qabullar_list = [q for q in qabullar.values() if q.get('sana') == bugun_str]
        
        if not bugungi_qabullar_list:
            text = f"📅 **{bugun_str}**\n\nBugun uchun rejalashtirilgan qabullar mavjud emas."
        else:
            text = f"📅 **{bugun_str} uchun qabullar:**\n\n"
            bugungi_qabullar_list.sort(key=lambda x: x.get('vaqt', '00:00'))
            for q in bugungi_qabullar_list:
                text += f"🕒 **{q.get('vaqt')}** - {q.get('ism')} {q.get('familiya')} ({q.get('telefon')})\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='admin_menu_back')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif data == 'admin_menu_back':
        keyboard = [
            [InlineKeyboardButton("📅 Bugungi qabullar", callback_data='admin_today')],
            [InlineKeyboardButton("📊 Statistika", callback_data='admin_stat')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👨‍⚕️ Asosiy menyu:", reply_markup=reply_markup)
        return

    # --- BEMOR MENYUSI ---
    elif data == 'aloqa':
        aloqa_xabar = f"""📞 **Aloqa ma'lumotlari:**

👨‍⚕️ **Doktor:** Dr. Abdulatifovich
📱 **Telefon:** {DOCTOR_PHONE}
💬 **Telegram:** @{DOCTOR_USERNAME}

🏥 **Ish vaqti:**
Dushanba-Shanba: 09:00 - 18:00
Yakshanba: Dam olish kuni

📍 **Manzil:** Toshkent shahri
[Aniq manzilni qo'shing]

⚠️ Favqulodda holatlarda: 103
"""
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='main_menu_back')]]
        await query.edit_message_text(aloqa_xabar, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'savol':
        savol_xabar = """❓ **Ko'p beriladigan savollar:**

**1. Qabul qancha vaqt davom etadi?**
Birinchi qabul 30-45 daqiqa, keyingi qabullar 20-30 daqiqa.

**2. O'zim bilan nima olib borishim kerak?**
• Avvalgi tibbiy hujjatlar
• Qabul qilayotgan dorilar ro'yxati
• Tahlil natijalari (agar bor bo'lsa)

**3. Onlayn konsultatsiya bormi?**
Ha, Telegram orqali ham konsultatsiya beriladi.

**4. To'lov qanday amalga oshiriladi?**
Qabuldan keyin naqd yoki plastik karta orqali.

**5. Qabulni bekor qilsam bo'ladimi?**
Ha, kamida 24 soat oldin xabar bering.
"""
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='main_menu_back')]]
        await query.edit_message_text(savol_xabar, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'main_menu_back':
        xabar = "Bosh menyu."
        keyboard = [
            [InlineKeyboardButton("📝 Qabulga yozilish", callback_data='boshlash')],
            [InlineKeyboardButton("📞 Aloqa ma'lumotlari", callback_data='aloqa')],
            [InlineKeyboardButton("❓ Savollar", callback_data='savol')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(xabar, reply_markup=reply_markup)

async def ism_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bemor ismini olish"""
    context.user_data['ism'] = update.message.text
    await update.message.reply_text(
        "✅ Yaxshi!\n\n"
        "Endi **familiyangizni** kiriting:"
    )
    return FAMILIYA

async def familiya_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bemor familiyasini olish"""
    context.user_data['familiya'] = update.message.text
    await update.message.reply_text(
        "✅ Ajoyib!\n\n"
        "**Yoshingizni** kiriting (raqam bilan):"
    )
    return YOSH

async def yosh_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bemor yoshini olish"""
    try:
        yosh = int(update.message.text)
        if yosh < 1 or yosh > 120:
            raise ValueError
        context.user_data['yosh'] = yosh
        await update.message.reply_text(
            "✅ Rahmat!\n\n"
            "**Telefon raqamingizni** kiriting:\n"
            "(Masalan: +998 99 123 45 67)"
        )
        return TELEFON
    except ValueError:
        await update.message.reply_text(
            "❌ Iltimos, to'g'ri yosh kiriting (1 dan 120 gacha):"
        )
        return YOSH

async def telefon_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bemor telefon raqamini olish"""
    context.user_data['telefon'] = update.message.text
    await update.message.reply_text(
        "✅ Yaxshi!\n\n"
        "**Qayerdan ekanligingizni** kiriting:\n"
        "(Masalan: Toshkent, Chilonzor tumani)"
    )
    return MANZIL

async def manzil_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bemor manzilini olish"""
    context.user_data['manzil'] = update.message.text
    await update.message.reply_text(
        "✅ Ajoyib!\n\n"
        "Endi **shikoyatingiz yoki kasalligingiz** haqida batafsil yozing:\n\n"
        "• Qanday alomatlar bor?\n"
        "• Qachondan beri bezovta qilyapti?\n"
        "• Og'riq darajasi (1 dan 10 gacha)?\n"
        "• Boshqa muhim ma'lumotlar"
    )
    return SHIKOYAT

async def shikoyat_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bemor shikoyatini olish va favqulodda holatni tekshirish"""
    shikoyat = update.message.text
    context.user_data['shikoyat'] = shikoyat
    
    # Favqulodda holatni tekshirish
    if favqulodda_tekshir(shikoyat):
        context.user_data['favqulodda'] = True
        xabar = """🚨 **FAVQULODDA HOLAT!**

Siz tasvirlab bergan alomatlar shoshilinch tibbiy yordam talab qiladi!

‼️ ILTIMOS, DARHOL:
☎️ **103** ga qo'ng'iroq qiling
🏥 Yaqin shifoxonaga boring
🚑 Tez yordam chaqiring

Siz tasvirlab bergan alomatlar:
• Insult (miyaga qon ketish)
• Epileptik tutqanoq
• Boshqa jiddiy holat

belgilari bo'lishi mumkin.

⚠️ Doktor ham sizga qo'ng'iroq qiladi!

Sizning ma'lumotlaringiz doktorga yuborildi.
"""
        await update.message.reply_text(xabar)
        
        # Adminlarga favqulodda xabar yuborish
        await favqulodda_adminlarga(context, context.user_data)
        
        return ConversationHandler.END
    
    # Oddiy holat - qabul belgilash
    keyboard = [
        [InlineKeyboardButton("✅ Ha", callback_data='favq_ha')],
        [InlineKeyboardButton("❌ Yo'q", callback_data='favq_yoq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ Quyidagi **favqulodda alomatlardan** birortasi bormi?\n\n"
        "🔴 Keskin bosh og'rig'i\n"
        "🔴 Nutq buzilishi yoki gapirolmaslik\n"
        "🔴 Yuz yoki tananing bir tomonida zaiflik\n"
        "🔴 Tutqanoq (konvulsiya)\n"
        "🔴 Ongni yo'qotish\n"
        "🔴 Ko'rish buzilishi",
        reply_markup=reply_markup
    )
    return FAVQULODDA

async def favqulodda_javob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Favqulodda savolga javob"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'favq_ha':
        xabar = """🚨 **FAVQULODDA!**

DARHOL 103 ga qo'ng'iroq qiling!
Yoki eng yaqin shifoxonaga boring!

Doktor ham sizga qo'ng'iroq qiladi.
"""
        await query.edit_message_text(xabar)
        
        # Adminlarga favqulodda xabar
        await favqulodda_adminlarga(context, context.user_data)
        
        return ConversationHandler.END
    
    context.user_data['favqulodda'] = False
    
    # Qabul sanasini tanlash
    kunlar = kunlar_yasash()
    keyboard = []
    for kun in kunlar:
        keyboard.append([InlineKeyboardButton(
            f"{kun['hafta_kuni']}, {kun['sana']}", 
            callback_data=f"sana_{kun['sana']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "📅 **Qabul sanasini tanlang:**\n\n"
        "Qaysi kun sizga qulay?",
        reply_markup=reply_markup
    )
    return SANA

async def sana_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qabul sanasini tanlash"""
    query = update.callback_query
    await query.answer()
    
    sana = query.data.replace('sana_', '')
    context.user_data['sana'] = sana
    
    # Vaqtlarni ko'rsatish
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
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"🕐 **Vaqtni tanlang:**\n\n"
        f"Sana: **{sana}**\n"
        f"Qaysi vaqt sizga qulay?",
        reply_markup=reply_markup
    )
    return VAQT

async def vaqt_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qabul vaqtini tanlash va tasdiqlash"""
    query = update.callback_query
    await query.answer()
    
    vaqt = query.data.replace('vaqt_', '')
    context.user_data['vaqt'] = vaqt
    
    # --- MA'LUMOTLARNI SAQLASH VA YAKUNLASH ---
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
    
    # Adminlarga xabar yuborish
    await adminlarga_xabar_yuborish(context, bemor_malumot)
    
    # Bemorga xabar (Kutish rejimi)
    kutish_xabar = f"""✅ **Ma'lumotlaringiz qabul qilindi!**

📋 **So'rov raqami:** #{qabul_id:04d}

Hurmatli **{context.user_data['ism']}**, sizning so'rovingiz Doktorga yuborildi.

⏳ **Iltimos, kuting!**
Doktor qabul vaqtini tasdiqlashi bilan sizga:
📍 Klinika lokatsiyasi
📋 Kerakli hujjatlar ro'yxati
yuboriladi.
"""
    
    await query.edit_message_text(kutish_xabar)
    
    # Menyu ko'rsatish
    keyboard = [
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data='bosh_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "Yana nima yordam kerak? /start ni bosing",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

async def bekor_qilish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Suhbatni bekor qilish"""
    await update.message.reply_text(
        "❌ Bekor qilindi.\n\n"
        "Qaytadan boshlash uchun /start ni bosing."
    )
    return ConversationHandler.END

async def adminlarga_xabar_yuborish(context, bemor):
    """Barcha adminlarga yangi bemor haqida xabar yuborish"""
    xabar = f"""🔔 **YANGI BEMOR QO'SHILDI!**

📋 **Qabul ID:** #{bemor['id']:04d}

👤 **Bemor ma'lumotlari:**
━━━━━━━━━━━━━━━━━━━━
• **Ism-familiya:** {bemor['ism']} {bemor['familiya']}
• **Yosh:** {bemor['yosh']} yosh
• **Telefon:** {bemor['telefon']}
• **Manzil:** {bemor['manzil']}

🩺 **Shikoyat:**
{bemor['shikoyat']}

📅 **So'ralgan vaqt:**
• **Sana:** {bemor['sana']}
• **Vaqt:** {bemor['vaqt']}

⏰ **Ro'yxatdan o'tdi:** {bemor['yaratilgan']}

━━━━━━━━━━━━━━━━━━━━
✅ Iltimos, bemor bilan bog'laning!
"""
    
    # Admin uchun tugmalar
    keyboard = [
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"qabul_tasdiq_{bemor['id']}")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data=f"qabul_bekor_{bemor['id']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Har bir adminga xabar yuborish
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id, 
                text=xabar,
                reply_markup=reply_markup
            )
            logger.info(f"Xabar yuborildi: Admin {admin_id}")
        except Exception as e:
            logger.error(f"Admin {admin_id} ga xabar yuborishda xato: {e}")

async def favqulodda_adminlarga(context, bemor_data):
    """Favqulodda holat haqida adminlarga xabar"""
    xabar = f"""🚨 **FAVQULODDA HOLAT!**

‼️ Bemorga SHOSHILINCH yordam kerak!

👤 **Bemor:**
━━━━━━━━━━━━━━━━━━━━
• **Ism-familiya:** {bemor_data.get('ism', "Noma'lum")} {bemor_data.get('familiya', '')}
• **Yosh:** {bemor_data.get('yosh', "Noma'lum")} yosh
• **Telefon:** {bemor_data.get('telefon', "Noma'lum")}
• **Manzil:** {bemor_data.get('manzil', "Noma'lum")}

🩺 **Favqulodda shikoyat:**
{bemor_data.get('shikoyat', "Noma'lum")}

━━━━━━━━━━━━━━━━━━━━
⚠️ **DARHOL CHORALAR KO'RING!**

Bemor 103 ga qo'ng'iroq qilishga yo'naltirildi.

☎️ Iltimos, bemor bilan bog'laning:
{bemor_data.get('telefon', "Noma'lum")}
"""
    
    # Har bir adminga xabar yuborish
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id, 
                text=xabar
            )
            logger.info(f"FAVQULODDA xabar yuborildi: Admin {admin_id}")
        except Exception as e:
            logger.error(f"Admin {admin_id} ga favqulodda xabar yuborishda xato: {e}")

async def yangi_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi qabul buyrug'i"""
    await start(update, context)

async def admin_qabul_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin qabulni tasdiqlashi yoki bekor qilishi"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # ID ni ajratib olish
    action, qabul_id_str = data.rsplit('_', 1)
    qabul_id = int(qabul_id_str)
    bemor = qabullar.get(qabul_id)
    
    if not bemor:
        await query.edit_message_text("❌ Bu qabul topilmadi.")
        return

    if action == 'qabul_tasdiq':
        # 1. Bemorga xabar yuborish
        tasdiq_xabar = f"""✅ **XUSHXABAR! Qabulingiz tasdiqlandi.**

📅 **Vaqt:** {bemor['sana']} soat {bemor['vaqt']}
👨‍⚕️ **Doktor:** Dr. Abdulatifovich

📂 **O'zingiz bilan olib kelishingiz SHART:**
1. Pasport (shaxsni tasdiqlovchi hujjat)
2. Tibbiy karta (agar bor bo'lsa)
3. Oldingi tahlil natijalari (MRT, MSKT, qon tahlillari)
4. Hozir ichayotgan dorilaringiz ro'yxati

📍 **Manzilimiz pastda:**
"""
        try:
            # Xabar
            await context.bot.send_message(chat_id=bemor['user_id'], text=tasdiq_xabar)
            
            # Lokatsiya (Toshkent markazi misolida - buni o'zgartiring)
            # TODO: Aniq lokatsiyani kiriting
            await context.bot.send_location(
                chat_id=bemor['user_id'], 
                latitude=40.371810, 
                longitude=71.789557
            )
            
            # Adminga o'zgarish
            await query.edit_message_text(
                f"✅ **Qabul TASDIQLANDI!**\n\nBemor: {bemor['ism']} {bemor['familiya']}\nVaqt: {bemor['sana']} {bemor['vaqt']}\n\nBemorga lokatsiya va eslatma yuborildi."
            )
            bemor['holat'] = 'TASDIQLANDI'
            
        except Exception as e:
            await query.message.reply_text(f"❌ Bemorga xabar yuborishda xatolik: {e}")

    elif action == 'qabul_bekor':
        # Bemorga xabar
        bekor_xabar = f"❌ **Afsuski, qabulingiz bekor qilindi.**\n\nIltimos, boshqa vaqt tanlang yoki administrator bilan bog'laning: {DOCTOR_PHONE}"
        try:
            await context.bot.send_message(chat_id=bemor['user_id'], text=bekor_xabar)
        except:
            pass
            
        await query.edit_message_text(f"❌ **Qabul BEKOR QILINDI.**\n\nBemor: {bemor['ism']} {bemor['familiya']}")
        bemor['holat'] = 'BEKOR_QILINDI'

def main():
    """Botni ishga tushirish"""
    try:
        if not BOT_TOKEN:
            print("❌ XATO: BOT_TOKEN topilmadi! Render Environment Variables bo'limini tekshiring.")
            sys.exit(1)
        
        print("🤖 Bot ishga tushmoqda...")
        print(f"📱 Bot username: @{DOCTOR_USERNAME}")
        print(f"👥 Adminlar soni: {len(ADMIN_CHAT_IDS)} ta")
        print(f"🆔 Admin IDlari: {ADMIN_CHAT_IDS}")
        
        # Render uchun web serverni alohida oqimda ishga tushirish
        try:
            server_thread = Thread(target=run_web_server, daemon=True)
            server_thread.start()
            print("✅ Web server ishga tushdi")
        except Exception as e:
            print(f"⚠️ Web serverda xatolik: {e}")

        # Application yaratish
        application = Application.builder().token(BOT_TOKEN).build()
        
    except Exception as e:
        print(f"❌ KRITIK XATO (Boshlanishda): {e}")
        traceback.print_exc()
        sys.exit(1)

    # Suhbat handler
    conv_handler = ConversationHandler(
        entry_points=[
            # Suhbat faqat "Qabulga yozilish" tugmasi bosilganda boshlanadi
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
    
    # Handlerlarni qo'shish
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('yangi_qabul', start)) # Alias
    application.add_handler(CallbackQueryHandler(tugma_bosildi))
    application.add_handler(CallbackQueryHandler(admin_qabul_callback, pattern='^qabul_'))
    
    # Botni ishga tushirish
    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    print("🔄 Botni to'xtatish uchun Ctrl+C ni bosing\n")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"❌ KRITIK XATO (Ishlash vaqtida): {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()