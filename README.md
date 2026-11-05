# KH SHOP — Render Free webhook

1. GitHub repositoryga bot.py, requirements.txt, .gitignore, .env.example fayllarini yuklang. .env va *.db fayllarini yuklamang.
2. Render -> New -> Web Service -> GitHub repository.
3. Runtime: Python; Build: `pip install -r requirements.txt`; Start: `python bot.py`; Instance: Free.
4. Environment: TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_IDS, DATABASE_PATH=kh_shop.db.
5. Render avtomatik RENDER_EXTERNAL_URL bersa, bot shu manzildan foydalanadi. Aks holda WEBHOOK_BASE_URL=https://<service>.onrender.com kiriting.
6. Deploy. Loglarda xatolik yo'qligini tekshiring, Telegramda /start yuboring.

DIQQAT: Render Free bo'sh turganda uxlaydi, shuning uchun webhook xabarlari kechikishi mumkin. Lokal SQLite fayli restart/deployda yo'qolishi mumkin. Haqiqiy buyurtmalar yoki to'lovlar uchun doimiy baza va rasmiy Telegram Stars invoice integratsiyasi zarur. Bu kod haqiqiy to'lovni qabul qilmaydi.
Lokal CMD test uchun eski polling versiyasidan foydalaning yoki WEBHOOK_BASE_URL va tashqaridan kiriladigan HTTPS manzilni sozlang.
