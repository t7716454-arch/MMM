"""
Foydalanuvchi uchun matnlar: O'zbek (uz), Rus (ru), Ingliz (en).
Yangi matn qo'shsangiz, uchala tilga ham qo'shing.
"""

LANGS = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}

TEXTS: dict[str, dict[str, str]] = {
    # ============================================================== O'ZBEK
    "uz": {
        "btn_download": "📥 Yuklab olish",
        "btn_vip": "💎 VIP Obuna",
        "btn_donate": "❤️ Donat",
        "btn_invite": "👥 Do'st taklif qilish",
        "btn_history": "🕘 Tarix",
        "btn_lang": "🌐 Til",
        "btn_back": "⬅️ Orqaga",
        "btn_check_sub": "✅ Tekshirish",
        "btn_share": "📤 Ulashish",
        "btn_other": "✍️ Boshqa miqdor",
        "btn_mp3": "🎵 MP3",
        "btn_buy_vip": "💎 VIP sotib olish",
        "days_word": "kun",
        "welcome": (
            "👋 Salom, <b>{name}</b>!\n\n"
            "Men <b>Instagram</b> va <b>Pinterest</b> dan "
            "video va rasmlarni yuklab beraman.\n\n"
            "📎 Shunchaki havolani yuboring — qolganini men qilaman.\n"
            "🆓 Bepul: kuniga <b>{limit}</b> ta yuklash\n"
            "💎 VIP: <b>cheksiz</b> yuklash\n\n"
            "Quyidagi menyudan tanlang 👇"
        ),
        "download_info": (
            "📥 <b>Yuklab olish</b>\n\n"
            "Havolani shu yerga yuboring.\n\n"
            "Qo'llab-quvvatlanadi:\n"
            "• Instagram: Reels, post\n"
            "• Pinterest: pin (rasm/video)\n\n"
            "Holat: <b>{status}</b>"
        ),
        "status_vip": "💎 VIP — cheksiz",
        "status_free": "🆓 Bugun: {used}/{limit} • 🎁 Bonus: {bonus}",
        "limit_reached": (
            "⛔️ Bugungi bepul limit (<b>{limit}</b> ta) tugadi.\n\n"
            "Cheksiz yuklash uchun <b>VIP</b> sotib oling, do'stlaringizni taklif "
            "qilib bonus oling yoki ertaga qaytib keling."
        ),
        "busy": "⏳ Oldingi yuklash hali tugamadi, biroz kuting.",
        "processing": "⏳ Yuklanmoqda, iltimos kuting...",
        "audio_processing": "🎵 Audio tayyorlanmoqda...",
        "not_found": (
            "❌ Media topilmadi yoki yuklab bo'lmadi.\n"
            "Havola ochiq (public) ekanini va video {minutes} daqiqadan uzun "
            "emasligini tekshiring."
        ),
        "audio_fail": "❌ Audioni ajratib bo'lmadi.",
        "fail_too_long": "❌ Video juda uzun (maksimum {minutes} daqiqa).",
        "fail_blocked": (
            "❌ Bu videoni hozir yuklab bo'lmadi: sayt so'rovni rad etdi yoki "
            "ko'rish uchun login talab qilinadi. Keyinroq qayta urinib ko'ring."
        ),
        "fail_unavailable": "❌ Video topilmadi, o'chirilgan yoki yopiq (private).",
        "fail_too_big": "❌ Video 50 MB dan katta — Telegram orqali yuborib bo'lmaydi.",
        "fail_unknown": "❌ Yuklab bo'lmadi. Havola to'g'riligini tekshiring yoki keyinroq urinib ko'ring.",
        "audio_expired": "⚠️ Havola topilmadi. Videoning havolasini qayta yuboring.",
        "too_big": "⚠️ Fayl 50 MB dan katta — Telegram orqali yuborib bo'lmaydi.",
        "send_failed": "❌ Faylni yuborib bo'lmadi. Keyinroq urinib ko'ring.",
        "error_generic": "⚠️ Kutilmagan xatolik yuz berdi. Keyinroq qayta urinib ko'ring.",
        "unsupported": (
            "⚠️ Bu havola qo'llab-quvvatlanmaydi.\n"
            "Instagram yoki Pinterest havolasini yuboring."
        ),
        "done": "✅ Tayyor! • @{bot}",
        "done_audio": "🎵 Tayyor! • @{bot}",
        "left": "🆓 Bugungi qolgan yuklashlar: <b>{left}</b> ta",
        "vip_info": (
            "💎 <b>VIP Obuna</b>\n\n"
            "• ♾ Cheksiz yuklash\n"
            "• 🎵 Cheksiz MP3\n"
            "• ⚡️ Hech qanday kunlik limit yo'q\n\n"
            "Tarifni tanlang 👇\n\n"
            "Holat: <b>{status}</b>"
        ),
        "vip_active": "✅ VIP faol ({date} gacha)",
        "vip_inactive": "❌ VIP faol emas",
        "inv_vip_title": "💎 VIP Obuna",
        "inv_vip_desc": "{days} kun davomida cheksiz yuklash",
        "inv_vip_label": "VIP {days} kun",
        "pay_vip_ok": (
            "🎉 <b>To'lov muvaffaqiyatli!</b>\n\n"
            "💎 VIP <b>{date}</b> gacha faollashtirildi."
        ),
        "pay_donate_ok": "❤️ Katta rahmat! <b>{stars} ⭐</b> donatingiz uchun minnatdormiz!",
        "pay_unknown": "✅ To'lov qabul qilindi.",
        "pay_error": (
            "⚠️ To'lov qabul qilindi, lekin faollashtirishda xato bo'ldi. "
            "Adminga murojaat qiling. Tranzaksiya: <code>{charge}</code>"
        ),
        "paysupport": "💬 To'lov bilan bog'liq muammo bo'lsa, tranzaksiya ID bilan adminga yozing.",
        "donate_info": (
            "❤️ <b>Donat</b>\n\n"
            "Botni qo'llab-quvvatlamoqchimisiz? Istalgan miqdordagi "
            "Telegram Stars yuborishingiz mumkin.\n\n"
            "Miqdorni tanlang yoki o'zingiz kiriting 👇"
        ),
        "donate_prompt": "✍️ Necha ⭐ yubormoqchisiz? Son kiriting ({min}–{max}).\nBekor qilish: /start",
        "donate_invalid": "❗️ Iltimos, {min} dan {max} gacha butun son kiriting.",
        "inv_donate_title": "❤️ Donat",
        "inv_donate_desc": "Loyihani qo'llab-quvvatlaganingiz uchun rahmat!",
        "inv_donate_label": "Donat",
        "invoice_error": "Hisob-fakturani yaratib bo'lmadi.",
        "sub_required": (
            "📢 Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling, "
            "so'ng «✅ Tekshirish» tugmasini bosing:"
        ),
        "sub_ok": "✅ Rahmat! Endi havolani yuborishingiz mumkin.",
        "sub_not_yet": "❗️ Hali hamma kanallarga a'zo bo'lmadingiz.",
        "ref_info": (
            "👥 <b>Do'stlarni taklif qilish</b>\n\n"
            "Sizning havolangiz:\n<code>{link}</code>\n\n"
            "Har bir do'stingiz botdan birinchi marta foydalanganda sizga "
            "<b>+{bonus}</b> bonus yuklash beriladi. Har <b>{milestone}</b> ta do'st "
            "uchun esa <b>{vip_days} kun VIP</b> sovg'a qilinadi!\n\n"
            "✅ Tasdiqlangan: <b>{count}</b>\n"
            "⏳ Kutilmoqda: <b>{pending}</b>\n"
            "🎁 Bonus balans: <b>{balance}</b>"
        ),
        "ref_share_text": "Instagram va Pinterest videolarini tez yuklab oling 👇",
        "ref_reward": "🎉 Do'stingiz botdan foydalandi! Sizga <b>+{n}</b> bonus yuklash berildi.",
        "ref_milestone": "🏆 {count} ta do'st! Sovg'a: <b>{days} kun VIP</b> 💎",
        "history_title": "🕘 <b>So'nggi yuklashlar</b>\n\n{items}",
        "history_empty": "🕘 Hozircha yuklashlar yo'q.",
        "lang_choose": "🌐 Tilni tanlang:",
        "lang_changed": "✅ Til o'zgartirildi.",
        "btn_daily": "🎁 Kunlik bonus",
        "btn_promo": "🎟 Promokod",
        "btn_feedback": "💬 Taklif / shikoyat",
        "btn_renew": "💎 VIP ni yangilash",
        "daily_ok": (
            "🎁 <b>Kunlik bonus!</b>\n\n"
            "+<b>{n}</b> yuklash qo'shildi.\n"
            "🔥 Ketma-ket kunlar: <b>{streak}</b>\n\n"
            "Har <b>{every}</b>-kuni qo'shimcha <b>+{extra}</b> sovg'a! Ertaga yana keling."
        ),
        "daily_already": (
            "⏳ Bugungi bonusni allaqachon olgansiz.\n"
            "Ertaga qaytib keling — ketma-ket kunlar seriyasini uzmang! 🔥"
        ),
        "promo_prompt": "🎟 <b>Promokod</b>\n\nPromokodni yuboring:\nBekor qilish: /start",
        "promo_ok_vip": "🎉 Promokod qabul qilindi!\n💎 <b>{days} kun VIP</b> qo'shildi (tugashi: {date}).",
        "promo_ok_bonus": "🎉 Promokod qabul qilindi!\n🎁 <b>+{n}</b> bonus yuklash qo'shildi.",
        "promo_not_found": "❌ Bunday promokod topilmadi. Tekshirib, qayta yuboring.",
        "promo_expired": "⌛ Bu promokodning muddati tugagan.",
        "promo_exhausted": "😕 Bu promokod to'liq ishlatib bo'lingan.",
        "promo_used": "ℹ️ Siz bu promokodni allaqachon ishlatgansiz.",
        "promo_too_many": "⚠️ Juda ko'p noto'g'ri urinish. 10 daqiqadan keyin qayta urinib ko'ring.",
        "feedback_prompt": (
            "💬 <b>Taklif / shikoyat</b>\n\n"
            "Xabaringizni yozing (matn, rasm yoki ovozli xabar). Admin ko'rib chiqib, javob beradi.\n"
            "Bekor qilish: /start"
        ),
        "feedback_sent": "✅ Xabaringiz adminga yuborildi. Rahmat!",
        "feedback_limit": "⚠️ Soatiga {n} tadan ko'p xabar yuborib bo'lmaydi. Keyinroq urinib ko'ring.",
        "admin_reply_header": "💬 <b>Admin javobi</b>",
        "admin_msg_header": "📩 <b>Admin xabari</b>",
        "vip_gift": "🎁 Sizga <b>{days} kun VIP</b> sovg'a qilindi!\n💎 VIP <b>{date}</b> gacha faol.",
        "vip_expiring": (
            "⏰ <b>VIP obunangiz tugayapti!</b>\n\n"
            "💎 Tugash sanasi: <b>{date}</b> ({days} kun qoldi).\n"
            "Uzilishsiz cheksiz yuklash uchun hozir yangilang 👇"
        ),
        "banned_notice": "🚫 Siz botdan foydalanishdan bloklangansiz.",
        "spam_wait": "⚠️ Juda tez-tez harakat qilyapsiz. {sec} soniya kutib turing.",
        "fallback": (
            "🔗 Menga havola yuboring (Instagram yoki Pinterest).\n"
            "Menyu: /start"
        ),
    },
    # ============================================================== RUS
    "ru": {
        "btn_download": "📥 Скачать",
        "btn_vip": "💎 VIP подписка",
        "btn_donate": "❤️ Донат",
        "btn_invite": "👥 Пригласить друга",
        "btn_history": "🕘 История",
        "btn_lang": "🌐 Язык",
        "btn_back": "⬅️ Назад",
        "btn_check_sub": "✅ Проверить",
        "btn_share": "📤 Поделиться",
        "btn_other": "✍️ Другая сумма",
        "btn_mp3": "🎵 MP3",
        "btn_buy_vip": "💎 Купить VIP",
        "days_word": "дн.",
        "welcome": (
            "👋 Привет, <b>{name}</b>!\n\n"
            "Я скачиваю видео и фото из <b>Instagram</b> и "
            "<b>Pinterest</b>.\n\n"
            "📎 Просто отправьте ссылку — остальное сделаю я.\n"
            "🆓 Бесплатно: <b>{limit}</b> загрузок в день\n"
            "💎 VIP: <b>безлимит</b>\n\n"
            "Выберите в меню ниже 👇"
        ),
        "download_info": (
            "📥 <b>Скачать</b>\n\n"
            "Отправьте ссылку сюда.\n\n"
            "Поддерживается:\n"
            "• Instagram: Reels, посты\n"
            "• Pinterest: пины (фото/видео)\n\n"
            "Статус: <b>{status}</b>"
        ),
        "status_vip": "💎 VIP — безлимит",
        "status_free": "🆓 Сегодня: {used}/{limit} • 🎁 Бонус: {bonus}",
        "limit_reached": (
            "⛔️ Бесплатный лимит на сегодня (<b>{limit}</b>) исчерпан.\n\n"
            "Купите <b>VIP</b> для безлимита, пригласите друзей за бонусы "
            "или возвращайтесь завтра."
        ),
        "busy": "⏳ Предыдущая загрузка ещё не завершена, подождите.",
        "processing": "⏳ Загружаю, пожалуйста подождите...",
        "audio_processing": "🎵 Готовлю аудио...",
        "not_found": (
            "❌ Медиа не найдено или не удалось скачать.\n"
            "Проверьте, что ссылка открытая (public) и видео не длиннее {minutes} мин."
        ),
        "audio_fail": "❌ Не удалось извлечь аудио.",
        "fail_too_long": "❌ Видео слишком длинное (максимум {minutes} мин).",
        "fail_blocked": (
            "❌ Сейчас не удалось скачать это видео: сайт отклонил запрос или "
            "требуется вход в аккаунт. Попробуйте позже."
        ),
        "fail_unavailable": "❌ Видео не найдено, удалено или закрыто (private).",
        "fail_too_big": "❌ Видео больше 50 МБ — отправить через Telegram нельзя.",
        "fail_unknown": "❌ Не удалось скачать. Проверьте ссылку или попробуйте позже.",
        "audio_expired": "⚠️ Ссылка не найдена. Отправьте ссылку на видео заново.",
        "too_big": "⚠️ Файл больше 50 МБ — отправить через Telegram нельзя.",
        "send_failed": "❌ Не удалось отправить файл. Попробуйте позже.",
        "error_generic": "⚠️ Произошла непредвиденная ошибка. Попробуйте позже.",
        "unsupported": (
            "⚠️ Эта ссылка не поддерживается.\n"
            "Отправьте ссылку Instagram или Pinterest."
        ),
        "done": "✅ Готово! • @{bot}",
        "done_audio": "🎵 Готово! • @{bot}",
        "left": "🆓 Осталось загрузок на сегодня: <b>{left}</b>",
        "vip_info": (
            "💎 <b>VIP подписка</b>\n\n"
            "• ♾ Безлимитные загрузки\n"
            "• 🎵 Безлимитный MP3\n"
            "• ⚡️ Без дневного лимита\n\n"
            "Выберите тариф 👇\n\n"
            "Статус: <b>{status}</b>"
        ),
        "vip_active": "✅ VIP активен (до {date})",
        "vip_inactive": "❌ VIP не активен",
        "inv_vip_title": "💎 VIP подписка",
        "inv_vip_desc": "Безлимитные загрузки на {days} дн.",
        "inv_vip_label": "VIP {days} дн.",
        "pay_vip_ok": (
            "🎉 <b>Оплата прошла успешно!</b>\n\n"
            "💎 VIP активирован до <b>{date}</b>."
        ),
        "pay_donate_ok": "❤️ Большое спасибо за донат <b>{stars} ⭐</b>!",
        "pay_unknown": "✅ Платёж принят.",
        "pay_error": (
            "⚠️ Платёж принят, но при активации произошла ошибка. "
            "Обратитесь к админу. Транзакция: <code>{charge}</code>"
        ),
        "paysupport": "💬 Если есть проблема с оплатой, напишите админу с ID транзакции.",
        "donate_info": (
            "❤️ <b>Донат</b>\n\n"
            "Хотите поддержать бота? Можно отправить любое количество "
            "Telegram Stars.\n\n"
            "Выберите сумму или введите свою 👇"
        ),
        "donate_prompt": "✍️ Сколько ⭐ хотите отправить? Введите число ({min}–{max}).\nОтмена: /start",
        "donate_invalid": "❗️ Введите целое число от {min} до {max}.",
        "inv_donate_title": "❤️ Донат",
        "inv_donate_desc": "Спасибо, что поддерживаете проект!",
        "inv_donate_label": "Донат",
        "invoice_error": "Не удалось создать счёт.",
        "sub_required": (
            "📢 Чтобы пользоваться ботом, подпишитесь на каналы ниже, "
            "затем нажмите «✅ Проверить»:"
        ),
        "sub_ok": "✅ Спасибо! Теперь можно отправлять ссылку.",
        "sub_not_yet": "❗️ Вы ещё не подписались на все каналы.",
        "ref_info": (
            "👥 <b>Приглашайте друзей</b>\n\n"
            "Ваша ссылка:\n<code>{link}</code>\n\n"
            "Когда друг впервые воспользуется ботом, вы получите "
            "<b>+{bonus}</b> бонусных загрузок. За каждые <b>{milestone}</b> друзей — "
            "подарок <b>{vip_days} дн. VIP</b>!\n\n"
            "✅ Подтверждено: <b>{count}</b>\n"
            "⏳ Ожидает: <b>{pending}</b>\n"
            "🎁 Бонусный баланс: <b>{balance}</b>"
        ),
        "ref_share_text": "Быстро скачивай видео из Instagram и Pinterest 👇",
        "ref_reward": "🎉 Ваш друг воспользовался ботом! Вам начислено <b>+{n}</b> бонусных загрузок.",
        "ref_milestone": "🏆 {count} друзей! Подарок: <b>{days} дн. VIP</b> 💎",
        "history_title": "🕘 <b>Последние загрузки</b>\n\n{items}",
        "history_empty": "🕘 Пока нет загрузок.",
        "lang_choose": "🌐 Выберите язык:",
        "lang_changed": "✅ Язык изменён.",
        "btn_daily": "🎁 Ежедневный бонус",
        "btn_promo": "🎟 Промокод",
        "btn_feedback": "💬 Отзыв / жалоба",
        "btn_renew": "💎 Продлить VIP",
        "daily_ok": (
            "🎁 <b>Ежедневный бонус!</b>\n\n"
            "+<b>{n}</b> загрузок добавлено.\n"
            "🔥 Дней подряд: <b>{streak}</b>\n\n"
            "Каждый <b>{every}</b>-й день — дополнительно <b>+{extra}</b>! Приходите завтра."
        ),
        "daily_already": (
            "⏳ Вы уже получили сегодняшний бонус.\n"
            "Возвращайтесь завтра — не прерывайте серию! 🔥"
        ),
        "promo_prompt": "🎟 <b>Промокод</b>\n\nОтправьте промокод:\nОтмена: /start",
        "promo_ok_vip": "🎉 Промокод принят!\n💎 Добавлено <b>{days} дн. VIP</b> (до {date}).",
        "promo_ok_bonus": "🎉 Промокод принят!\n🎁 Добавлено <b>+{n}</b> бонусных загрузок.",
        "promo_not_found": "❌ Такой промокод не найден. Проверьте и отправьте снова.",
        "promo_expired": "⌛ Срок действия промокода истёк.",
        "promo_exhausted": "😕 Этот промокод уже полностью использован.",
        "promo_used": "ℹ️ Вы уже использовали этот промокод.",
        "promo_too_many": "⚠️ Слишком много неверных попыток. Попробуйте через 10 минут.",
        "feedback_prompt": (
            "💬 <b>Отзыв / жалоба</b>\n\n"
            "Напишите сообщение (текст, фото или голосовое). Админ прочитает и ответит.\n"
            "Отмена: /start"
        ),
        "feedback_sent": "✅ Сообщение отправлено админу. Спасибо!",
        "feedback_limit": "⚠️ Можно отправлять не более {n} сообщений в час. Попробуйте позже.",
        "admin_reply_header": "💬 <b>Ответ админа</b>",
        "admin_msg_header": "📩 <b>Сообщение от админа</b>",
        "vip_gift": "🎁 Вам подарили <b>{days} дн. VIP</b>!\n💎 VIP активен до <b>{date}</b>.",
        "vip_expiring": (
            "⏰ <b>Ваша VIP-подписка заканчивается!</b>\n\n"
            "💎 Дата окончания: <b>{date}</b> (осталось дн.: {days}).\n"
            "Продлите сейчас, чтобы не терять безлимит 👇"
        ),
        "banned_notice": "🚫 Вам запрещено пользоваться ботом.",
        "spam_wait": "⚠️ Слишком частые действия. Подождите {sec} сек.",
        "fallback": (
            "🔗 Отправьте ссылку (Instagram или Pinterest).\n"
            "Меню: /start"
        ),
    },
    # ============================================================== ENGLISH
    "en": {
        "btn_download": "📥 Download",
        "btn_vip": "💎 VIP",
        "btn_donate": "❤️ Donate",
        "btn_invite": "👥 Invite friends",
        "btn_history": "🕘 History",
        "btn_lang": "🌐 Language",
        "btn_back": "⬅️ Back",
        "btn_check_sub": "✅ Check",
        "btn_share": "📤 Share",
        "btn_other": "✍️ Other amount",
        "btn_mp3": "🎵 MP3",
        "btn_buy_vip": "💎 Buy VIP",
        "days_word": "days",
        "welcome": (
            "👋 Hi, <b>{name}</b>!\n\n"
            "I download videos and photos from <b>Instagram</b> and "
            "<b>Pinterest</b>.\n\n"
            "📎 Just send a link — I'll do the rest.\n"
            "🆓 Free: <b>{limit}</b> downloads per day\n"
            "💎 VIP: <b>unlimited</b>\n\n"
            "Choose from the menu below 👇"
        ),
        "download_info": (
            "📥 <b>Download</b>\n\n"
            "Send the link here.\n\n"
            "Supported:\n"
            "• Instagram: Reels, posts\n"
            "• Pinterest: pins (photo/video)\n\n"
            "Status: <b>{status}</b>"
        ),
        "status_vip": "💎 VIP — unlimited",
        "status_free": "🆓 Today: {used}/{limit} • 🎁 Bonus: {bonus}",
        "limit_reached": (
            "⛔️ Today's free limit (<b>{limit}</b>) is used up.\n\n"
            "Get <b>VIP</b> for unlimited downloads, invite friends for bonuses, "
            "or come back tomorrow."
        ),
        "busy": "⏳ Your previous download is still running, please wait.",
        "processing": "⏳ Downloading, please wait...",
        "audio_processing": "🎵 Preparing audio...",
        "not_found": (
            "❌ Media not found or could not be downloaded.\n"
            "Make sure the link is public and the video is not longer than {minutes} min."
        ),
        "audio_fail": "❌ Could not extract audio.",
        "fail_too_long": "❌ The video is too long (maximum {minutes} min).",
        "fail_blocked": (
            "❌ Couldn't download this video right now: the site rejected the request "
            "or requires a login. Please try again later."
        ),
        "fail_unavailable": "❌ Video not found, removed or private.",
        "fail_too_big": "❌ The video is larger than 50 MB and can't be sent via Telegram.",
        "fail_unknown": "❌ Couldn't download. Check the link or try again later.",
        "audio_expired": "⚠️ Link not found. Please send the video link again.",
        "too_big": "⚠️ The file is larger than 50 MB and can't be sent via Telegram.",
        "send_failed": "❌ Could not send the file. Please try again later.",
        "error_generic": "⚠️ Something went wrong. Please try again later.",
        "unsupported": (
            "⚠️ This link is not supported.\n"
            "Send an Instagram or Pinterest link."
        ),
        "done": "✅ Done! • @{bot}",
        "done_audio": "🎵 Done! • @{bot}",
        "left": "🆓 Downloads left today: <b>{left}</b>",
        "vip_info": (
            "💎 <b>VIP</b>\n\n"
            "• ♾ Unlimited downloads\n"
            "• 🎵 Unlimited MP3\n"
            "• ⚡️ No daily limit\n\n"
            "Choose a plan 👇\n\n"
            "Status: <b>{status}</b>"
        ),
        "vip_active": "✅ VIP active (until {date})",
        "vip_inactive": "❌ VIP is not active",
        "inv_vip_title": "💎 VIP",
        "inv_vip_desc": "Unlimited downloads for {days} days",
        "inv_vip_label": "VIP {days} days",
        "pay_vip_ok": (
            "🎉 <b>Payment successful!</b>\n\n"
            "💎 VIP is active until <b>{date}</b>."
        ),
        "pay_donate_ok": "❤️ Thank you so much for your <b>{stars} ⭐</b> donation!",
        "pay_unknown": "✅ Payment received.",
        "pay_error": (
            "⚠️ Payment received, but activation failed. "
            "Please contact the admin. Transaction: <code>{charge}</code>"
        ),
        "paysupport": "💬 If you have a payment problem, message the admin with your transaction ID.",
        "donate_info": (
            "❤️ <b>Donate</b>\n\n"
            "Want to support the bot? You can send any amount of "
            "Telegram Stars.\n\n"
            "Pick an amount or enter your own 👇"
        ),
        "donate_prompt": "✍️ How many ⭐ would you like to send? Enter a number ({min}–{max}).\nCancel: /start",
        "donate_invalid": "❗️ Please enter a whole number from {min} to {max}.",
        "inv_donate_title": "❤️ Donate",
        "inv_donate_desc": "Thank you for supporting the project!",
        "inv_donate_label": "Donation",
        "invoice_error": "Could not create the invoice.",
        "sub_required": (
            "📢 To use the bot, join the channels below, "
            "then press «✅ Check»:"
        ),
        "sub_ok": "✅ Thanks! You can send a link now.",
        "sub_not_yet": "❗️ You haven't joined all the channels yet.",
        "ref_info": (
            "👥 <b>Invite friends</b>\n\n"
            "Your link:\n<code>{link}</code>\n\n"
            "When a friend uses the bot for the first time, you get "
            "<b>+{bonus}</b> bonus downloads. For every <b>{milestone}</b> friends "
            "you get <b>{vip_days} days of VIP</b> as a gift!\n\n"
            "✅ Confirmed: <b>{count}</b>\n"
            "⏳ Pending: <b>{pending}</b>\n"
            "🎁 Bonus balance: <b>{balance}</b>"
        ),
        "ref_share_text": "Download videos from Instagram and Pinterest fast 👇",
        "ref_reward": "🎉 Your friend used the bot! You received <b>+{n}</b> bonus downloads.",
        "ref_milestone": "🏆 {count} friends! Gift: <b>{days} days of VIP</b> 💎",
        "history_title": "🕘 <b>Recent downloads</b>\n\n{items}",
        "history_empty": "🕘 No downloads yet.",
        "lang_choose": "🌐 Choose your language:",
        "lang_changed": "✅ Language changed.",
        "btn_daily": "🎁 Daily bonus",
        "btn_promo": "🎟 Promo code",
        "btn_feedback": "💬 Feedback / complaint",
        "btn_renew": "💎 Renew VIP",
        "daily_ok": (
            "🎁 <b>Daily bonus!</b>\n\n"
            "+<b>{n}</b> downloads added.\n"
            "🔥 Day streak: <b>{streak}</b>\n\n"
            "Every <b>{every}</b>th day you get an extra <b>+{extra}</b>! Come back tomorrow."
        ),
        "daily_already": (
            "⏳ You've already claimed today's bonus.\n"
            "Come back tomorrow — keep your streak alive! 🔥"
        ),
        "promo_prompt": "🎟 <b>Promo code</b>\n\nSend your promo code:\nCancel: /start",
        "promo_ok_vip": "🎉 Promo code accepted!\n💎 <b>{days} days of VIP</b> added (until {date}).",
        "promo_ok_bonus": "🎉 Promo code accepted!\n🎁 <b>+{n}</b> bonus downloads added.",
        "promo_not_found": "❌ Promo code not found. Please check and try again.",
        "promo_expired": "⌛ This promo code has expired.",
        "promo_exhausted": "😕 This promo code has been fully used.",
        "promo_used": "ℹ️ You've already used this promo code.",
        "promo_too_many": "⚠️ Too many wrong attempts. Please try again in 10 minutes.",
        "feedback_prompt": (
            "💬 <b>Feedback / complaint</b>\n\n"
            "Write your message (text, photo or voice). The admin will read it and reply.\n"
            "Cancel: /start"
        ),
        "feedback_sent": "✅ Your message was sent to the admin. Thank you!",
        "feedback_limit": "⚠️ You can send at most {n} messages per hour. Please try later.",
        "admin_reply_header": "💬 <b>Admin reply</b>",
        "admin_msg_header": "📩 <b>Message from admin</b>",
        "vip_gift": "🎁 You've been gifted <b>{days} days of VIP</b>!\n💎 VIP is active until <b>{date}</b>.",
        "vip_expiring": (
            "⏰ <b>Your VIP is about to expire!</b>\n\n"
            "💎 Expiry date: <b>{date}</b> ({days} days left).\n"
            "Renew now to keep unlimited downloads 👇"
        ),
        "banned_notice": "🚫 You are blocked from using this bot.",
        "spam_wait": "⚠️ You're doing that too fast. Please wait {sec} seconds.",
        "fallback": (
            "🔗 Send me a link (Instagram or Pinterest).\n"
            "Menu: /start"
        ),
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Tilga mos matnni qaytaradi (topilmasa o'zbekchasini)."""
    table = TEXTS.get(lang) or TEXTS["uz"]
    text = table.get(key) or TEXTS["uz"][key]
    return text.format(**kwargs) if kwargs else text
