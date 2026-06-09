# 🎮 Raqam Topish O'yini — Telegram Bot

Bot 1 dan 100 gacha son o'ylaydi, foydalanuvchi 5 ta urinishda topishga harakat qiladi.

---

## 🚀 O'rnatish va ishga tushirish

### 1. Talablar
- Python 3.10+

### 2. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. `.env` faylni sozlash
`.env` faylini oching va quyidagilarni kiriting:
```
BOT_TOKEN=siz_botingiz_tokeni
ADMIN_ID=sizning_telegram_id_ingiz
```

**Bot token olish:** [@BotFather](https://t.me/BotFather) orqali yangi bot yarating.  
**Admin ID olish:** [@userinfobot](https://t.me/userinfobot) botiga `/start` yuboring.

### 4. Botni ishga tushirish
```bash
python bot.py
```

---

## 🎯 O'yin qoidalari

1. Bot `/start` buyrug'idan so'ng **"O'yinni boshlash"** tugmasini ko'rsatadi
2. Tugma bosilganda bot 1-100 oralig'ida yashirin son o'ylaydi
3. Foydalanuvchi raqam kiritadi:
   - 🔼 **Tepparoq** — kiriting raqam kichik, kattaroq kiriting
   - 🔽 **Pastroq** — kiriting raqam katta, kichikroq kiriting
4. Jami **5 ta urinish** beriladi
5. Topsa — tabrik xabari
6. Topa olmasa — bot o'ylagan sonni ochib beradi

---

## 📁 Fayl tuzilmasi

```
guess_bot/
├── bot.py          # Asosiy bot kodi
├── requirements.txt
├── .env            # Token va admin ID (maxfiy!)
└── README.md
```
