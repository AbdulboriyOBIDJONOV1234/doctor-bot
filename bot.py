"""
Nevropatolog Konsultatsiya Boti
Dr. Abdulatifovich uchun maxsus bot
Python 3.14+ uchun yangilangan versiya
"""

import os
import json
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
from config import BOT_TOKEN, DOCTOR_PHONE, ADMIN_CHAT_IDS, FAVQULODDA_SOZLAR

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
 SHIKOYAT, FAVQULODDA, SANA, VAQT, TASDIQLASH) = range(10)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botni boshlash"""
    xabar = """🏥 Assalomu alaykum!

Men **Dr. Abdulatifovich** ning konsultatsiya botiman.

Siz bu yerda:
✅ Konsultatsiya uchun yozilishingiz mumkin
✅ Nevrologik muammolar bo'yicha maslahat olishingiz mumkin
✅ Favqulodda holatlarda yordam so'rashingiz mumkin

Boshlash uchun pastdagi tugmani bosing yoki /yangi_qabul buyrug'ini yuboring.

⚠️ **Favqulodda holat bo'lsa:**
• Keskin bosh og'rig'i
• Nutq buzilishi
• Yuz yoki tananing bir tomonida zaiflik
• Tutqanoq (konvulsiya)
• Ongni yo'qotish

DARHOL 103 ga qo'ng'iroq qiling! ☎️
"""
    
    keyboard = [
        [InlineKeyboardButton("📝 Qabulga yozilish", callback_data='boshlash')],
        [InlineKeyboardButton("📞 Aloqa ma'lumotlari", callback_data='aloqa')],
        [InlineKeyboardButton("❓ Ko'p beriladigan savollar", callback_data='savol')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(xabar, reply_markup=reply_markup)

async def tugma_bosildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline tugmalar bosilganda"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'boshlash':
        await query.edit_message_text(
            "📝 Yaxshi! Keling, sizning ma'lumotlaringizni to'ldiramiz.\n\n"
            "Iltimos, **ismingizni** kiriting:"
        )
        return ISM
    
    elif query.data == 'aloqa':
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
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='orqaga')]]
        await query.edit_message_text(aloqa_xabar, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif query.data == 'savol':
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
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data='orqaga')]]
        await query.edit_message_text(savol_xabar, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif query.data == 'orqaga':
        await query.message.reply_text("Qaytadan /start ni bosing")
        return ConversationHandler.END

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
    
    # Ma'lumotlarni ko'rsatish
    shikoyat_qisqa = context.user_data['shikoyat']
    if len(shikoyat_qisqa) > 100:
        shikoyat_qisqa = shikoyat_qisqa[:100] + "..."
    
    tasdiqlash_xabar = f"""✅ **Ma'lumotlaringizni tekshiring:**

👤 **Ism:** {context.user_data['ism']} {context.user_data['familiya']}
🎂 **Yosh:** {context.user_data['yosh']}
📱 **Telefon:** {context.user_data['telefon']}
📍 **Manzil:** {context.user_data['manzil']}
🩺 **Shikoyat:** {shikoyat_qisqa}
📅 **Sana:** {context.user_data['sana']}
🕐 **Vaqt:** {context.user_data['vaqt']}

Hammasi to'g'rimi?
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Ha, to'g'ri", callback_data='tasdiqlash_ha')],
        [InlineKeyboardButton("❌ Yo'q, qaytadan", callback_data='tasdiqlash_yoq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(tasdiqlash_xabar, reply_markup=reply_markup)
    return TASDIQLASH

async def tasdiqlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Qabulni tasdiqlash"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'tasdiqlash_yoq':
        await query.edit_message_text(
            "❌ Bekor qilindi.\n\n"
            "Qaytadan boshlash uchun /start ni bosing."
        )
        return ConversationHandler.END
    
    # Qabulni saqlash
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
    
    # Bemorga tasdiqlash
    muvaffaqiyat_xabar = f"""✅ **Qabul tasdiqlandi!**

📋 **Qabul raqami:** #{qabul_id:04d}

Doktor siz bilan **{bemor_malumot['sana']}** kuni soat **{bemor_malumot['vaqt']}** da bog'lanadi.

⏰ **Eslatma:**
• Qabuldan 24 soat oldin SMS yuboriladi
• 1 soat oldin Telegram orqali eslatma keladi

📝 **Qabul oldidan tayyorlang:**
✓ Avvalgi tibbiy hujjatlar
✓ Qabul qilayotgan dorilar ro'yxati
✓ Tahlil natijalari (agar bor bo'lsa)

📞 **Aloqa:**
Telefon: {DOCTOR_PHONE}
Telegram: @{DOCTOR_USERNAME}

Sog'lig'ingiz yaxshi bo'lsin! 💚
"""
    
    await query.edit_message_text(muvaffaqiyat_xabar)
    
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
    
    # Har bir adminga xabar yuborish
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id, 
                text=xabar
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
• **Ism-familiya:** {bemor_data.get('ism', 'Noma\'lum')} {bemor_data.get('familiya', '')}
• **Yosh:** {bemor_data.get('yosh', 'Noma\'lum')} yosh
• **Telefon:** {bemor_data.get('telefon', 'Noma\'lum')}
• **Manzil:** {bemor_data.get('manzil', 'Noma\'lum')}

🩺 **Favqulodda shikoyat:**
{bemor_data.get('shikoyat', 'Noma\'lum')}

━━━━━━━━━━━━━━━━━━━━
⚠️ **DARHOL CHORALAR KO'RING!**

Bemor 103 ga qo'ng'iroq qilishga yo'naltirildi.

☎️ Iltimos, bemor bilan bog'laning:
{bemor_data.get('telefon', 'Noma\'lum')}
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

def main():
    """Botni ishga tushirish"""
    if not BOT_TOKEN:
        print("❌ XATO: BOT_TOKEN topilmadi! Render Environment Variables bo'limini tekshiring.")
        return
    
    print("🤖 Bot ishga tushmoqda...")
    print(f"📱 Bot username: @{DOCTOR_USERNAME}")
    print(f"👥 Adminlar soni: {len(ADMIN_CHAT_IDS)} ta")
    print(f"🆔 Admin IDlari: {ADMIN_CHAT_IDS}")
    
    # Render uchun web serverni alohida oqimda ishga tushirish
    # daemon=True qildik, shunda asosiy dastur to'xtasa, server ham to'xtaydi
    server_thread = Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # Application yaratish
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Suhbat handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('yangi_qabul', yangi_qabul),
            CallbackQueryHandler(tugma_bosildi, pattern='^boshlash$')
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
            VAQT: [CallbackQueryHandler(vaqt_tanlash, pattern='^vaqt_')],
            TASDIQLASH: [CallbackQueryHandler(tasdiqlash, pattern='^tasdiqlash_')]
        },
        fallbacks=[
            CommandHandler('cancel', bekor_qilish),
            CommandHandler('start', start)
        ]
    )
    
    # Handlerlarni qo'shish
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(tugma_bosildi))
    
    # Botni ishga tushirish
    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    print("🔄 Botni to'xtatish uchun Ctrl+C ni bosing\n")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()