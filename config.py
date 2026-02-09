# -*- coding: utf-8 -*-
"""
🔐 Bot Konfiguratsiya Fayli v2.0
Barcha sozlamalar .env faylidan olinadi
"""
import os
import logging
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Logger
logger = logging.getLogger(__name__)

# ============================================
# BOT ASOSIY SOZLAMALARI
# ============================================

# Telegram Bot Token (MAJBURIY)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("❌ BOT_TOKEN topilmadi! Bot ishlamaydi.")

# ============================================
# ADMIN SOZLAMALARI
# ============================================

# Admin Chat IDlari (vergul bilan ajratilgan)
ADMIN_CHAT_IDS_STR = os.getenv("ADMIN_CHAT_IDS", "")

if not ADMIN_CHAT_IDS_STR:
    logger.critical("❌ DIQQAT: ADMIN_CHAT_IDS bo'sh! Adminlar mavjud emas.")
    logger.critical("❌ Bemorlardan xabarlar HECH KIMGA kelmaydi!")
    print("\n" + "="*60)
    print("❌ KRITIK XATO: ADMIN_CHAT_IDS topilmadi!")
    print("="*60)
    print("📝 .env faylida ADMIN_CHAT_IDS qo'shing:")
    print("   ADMIN_CHAT_IDS=7523126393")
    print("="*60 + "\n")
    ADMIN_CHAT_IDS = []
else:
    try:
        # Vergul bilan ajratilgan ID'larni list ga aylantirish
        ADMIN_CHAT_IDS = [
            int(chat_id.strip()) 
            for chat_id in ADMIN_CHAT_IDS_STR.split(',') 
            if chat_id.strip()
        ]
        logger.info(f"✅ {len(ADMIN_CHAT_IDS)} ta admin yuklandi: {ADMIN_CHAT_IDS}")
        print(f"✅ Adminlar: {ADMIN_CHAT_IDS}")
    except ValueError as e:
        logger.error(f"❌ ADMIN_CHAT_IDS noto'g'ri formatda: {e}")
        print(f"❌ XATO: ADMIN_CHAT_IDS noto'g'ri: {ADMIN_CHAT_IDS_STR}")
        ADMIN_CHAT_IDS = []

# ============================================
# DOKTOR MA'LUMOTLARI
# ============================================

# Doktor telefon raqami
DOCTOR_PHONE = os.getenv("DOCTOR_PHONE", "+998 XX XXX XX XX")

# Doktor Telegram username (@ belgisisiz)
DOCTOR_USERNAME = os.getenv("DOCTOR_USERNAME", "nevropatolog_abdulatifovich")

# ============================================
# KANAL SOZLAMALARI
# ============================================

# Majburiy obuna kanali (@ bilan)
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@DrNeuropathology07")

# ============================================
# FAVQULODDA HOLAT KALIT SO'ZLARI
# ============================================

FAVQULODDA_SOZLAR = [
    # Bosh og'rig'i
    'keskin bosh og\'rig\'i', 
    'kuchli bosh og\'rig\'i',
    'birdaniga bosh og\'ridi',
    'portlatib og\'riyapti',
    
    # Tutqanoq
    'tutqanoq', 
    'konvulsiya',
    'titroq',
    'tana bukildi',
    
    # Ong holati
    'ongni yo\'qotish', 
    'hushni yo\'qotish', 
    'hushimdan ketdim',
    'uyqusirash',
    'aqldan toyish',
    
    # Nutq
    'nutq buzilishi', 
    'nutq qiynalmoq', 
    'gapirolmayman',
    'tili tutildi',
    
    # Zaiflik/Falaj
    'zaiflik', 
    'falaj',
    'qo\'l ko\'tarolmayman', 
    'oyoq harakatlanmayapti',
    'tananing bir tomoni ishlamayapti',
    
    # Ko'rish
    'ko\'rish buzilishi', 
    'ko\'rmayapman',
    'ko\'zlarim qoraydi',
    'ikki ko\'rayapman',
    
    # Insult belgilari
    'insult',
    'yuz egilishi', 
    'og\'iz egri',
    'yuz bir tomoni tushdi',
    
    # Boshqa
    'bosh aylanmoqda juda',
    'muvozanat yo\'q',
    'miyaga qon quyilishi',
    'qon bosimi juda yuqori',
    'yurak to\'xtadi',
    'nafas ololmayapman'
]

# ============================================
# ISH VAQTI SOZLAMALARI
# ============================================

# Ish kunlari (0=Dushanba, 6=Yakshanba)
ISH_KUNLARI = [0, 1, 2, 3, 4, 5]  # Yakshanba (6) - dam olish

# Ish vaqti
ISH_BOSHLANISH = 9  # 09:00
ISH_TUGASH = 18     # 18:00
TUSHLIK_BOSHLANISH = 13  # 13:00
TUSHLIK_TUGASH = 14      # 14:00

# Qabul davomiyligi (daqiqalarda)
QABUL_DAVOMIYLIGI = 30

# ============================================
# ESLATMA SOZLAMALARI
# ============================================

# Qabuldan necha soat oldin eslatma (ro'yxat)
ESLATMA_VAQTLARI = [24, 2, 1]  # 24 soat, 2 soat, 1 soat oldin

# ============================================
# LOKATSIYA SOZLAMALARI
# ============================================

# Klinika lokatsiyasi (Google Maps)
KLINIKA_LATITUDE = float(os.getenv("KLINIKA_LATITUDE", "41.311158"))
KLINIKA_LONGITUDE = float(os.getenv("KLINIKA_LONGITUDE", "69.279737"))
KLINIKA_MANZIL = os.getenv("KLINIKA_MANZIL", "Toshkent shahri, Amir Temur ko'chasi")

# ============================================
# XAVFSIZLIK
# ============================================

# Bir foydalanuvchi uchun maksimal uchrashuv soni (oyiga)
MAX_UCHRASHUV_OYIGA = int(os.getenv("MAX_UCHRASHUV_OYIGA", "10"))

# ============================================
# LOGGING
# ============================================

# Log darajasi
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================
# RENDER/WEB SERVER SOZLAMALARI
# ============================================

# Port (Render uchun)
PORT = int(os.getenv("PORT", "8080"))

# ============================================
# VALIDATOR FUNKSIYALAR
# ============================================

def validate_config():
    """Konfiguratsiyani tekshirish"""
    errors = []
    warnings = []
    
    # Kritik xatolar
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN mavjud emas!")
    
    if not ADMIN_CHAT_IDS:
        warnings.append("ADMIN_CHAT_IDS bo'sh - adminlar mavjud emas!")
    
    # Ogohlantirishlar
    if DOCTOR_PHONE == "+998 XX XXX XX XX":
        warnings.append("DOCTOR_PHONE standart qiymatda - o'zgartiring!")
    
    if CHANNEL_USERNAME == "@DrNeuropathology07":
        warnings.append("CHANNEL_USERNAME standart qiymatda - tekshiring!")
    
    # Natijalar
    if errors:
        logger.critical("❌ KRITIK XATOLAR:")
        for error in errors:
            logger.critical(f"   • {error}")
        return False
    
    if warnings:
        logger.warning("⚠️ OGOHLANTIRISHLAR:")
        for warning in warnings:
            logger.warning(f"   • {warning}")
    
    logger.info("✅ Konfiguratsiya tasdiqlandi!")
    return True

# Konfiguratsiyani tekshirish
if __name__ == "__main__":
    validate_config()