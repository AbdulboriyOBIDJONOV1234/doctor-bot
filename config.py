# -*- coding: utf-8 -*-
"""
Bot uchun konfiguratsiya fayli.
Bu fayl .env faylidan ma'lumotlarni o'qiydi.
"""
import os
import logging
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Logger sozlash
logger = logging.getLogger(__name__)

# --- BOT KONFIGURATSIYASI ---

# Telegram Bot Tokeni
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.warning("⚠️ OGOHLANTIRISH: BOT_TOKEN topilmadi! Bot ishga tushmaydi.")

# Adminlarning Chat ID raqamlari
ADMIN_CHAT_IDS_STR = os.getenv("ADMIN_CHAT_IDS", "")
if not ADMIN_CHAT_IDS_STR:
    logger.warning("⚠️ DIQQAT: ADMIN_CHAT_IDS .env faylida topilmadi. Bemor ma'lumotlari hech qayerga yuborilmaydi.")
    ADMIN_CHAT_IDS = []
else:
    try:
        # Vergul bilan ajratilgan ID'larni raqamlar ro'yxatiga o'tkazish
        ADMIN_CHAT_IDS = [int(chat_id.strip()) for chat_id in ADMIN_CHAT_IDS_STR.split(',') if chat_id.strip()]
    except ValueError:
        logger.error("❌ XATO: ADMIN_CHAT_IDS noto'g'ri formatda.")
        ADMIN_CHAT_IDS = []

# Doktor telefoni va foydalanuvchi nomi
DOCTOR_PHONE = os.getenv("DOCTOR_PHONE", "Noma'lum")

# --- FAVQULODDA HOLAT SOZLAMALARI ---
FAVQULODDA_SOZLAR = [
    'keskin bosh og\'rig\'i', 'birdaniga', 'tutqanoq', 'konvulsiya',
    'ongni yo\'qotish', 'hushni yo\'qotish', 'hushimdan ketdim',
    'nutq buzilishi', 'nutq qiynalmoq', 'gapirolmayman',
    'zaiflik', 'ko\'rish buzilishi', 'ko\'rmayapman', 'falaj', 'insult',
    'yuz egilishi', 'og\'iz egri', 'qo\'l ko\'tarolmayman', 'oyoq harakatlanmayapti',
    'bosh aylanmoqda', 'muvozanat', 'titroq', 'miyaga qon quyilishi'
]
