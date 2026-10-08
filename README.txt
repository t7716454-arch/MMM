Media yuklovchi Telegram bot — JustRunMy.App uchun toza arxiv.

Ishga tushirish buyrug'i:  python main.py
Kutubxonalar:              requirements.txt (avtomatik o'rnatiladi)

MUHIM — panelda RAM ni kamida 512 MB qiling (bot ~180 MB band qiladi, 256 MB dan kam bo'lsa OOM/137 xatosi chiqadi).

Sozlamalar (muhit o'zgaruvchilari):
  BOT_TOKEN=...            (majburiy)
  ADMIN_IDS=...            (majburiy, sizning Telegram ID)
  MAX_PARALLEL=1           (xotirani tejaydi)
  DB_PATH=...              (doimiy disk yo'lida bo'lsa yaxshi — bot.db yo'qolmasligi uchun)
Qolganlari uchun .env.example fayliga qarang.

Bu arxivda .env, venv, bot.db YO'Q — token arxivga solinmagan.
