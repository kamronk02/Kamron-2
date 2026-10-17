import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import execute, fetch, fetchrow, fetchval, register_user, is_premium, add_premium, record_star_payment
from config import FORCE_CHANNELS, SUPPORT_USERNAME
from keyboards import main_menu, movie_actions, inline

router = Router()
LANGS = {
    "🇺🇿 O‘zbek kinolari": "O‘zbek",
    "🇷🇺 Rus kinolari": "Rus",
    "🇬🇧 Ingliz kinolari": "Ingliz",
}

class SearchState(StatesGroup):
    query = State()

class PromoState(StatesGroup):
    code = State()

async def subscribed(bot, user_id):
    for channel in FORCE_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ("left", "kicked"):
                return False
        except Exception:
            return False
    return True

async def show_movie(message, movie, user_id):
    if movie["is_premium"] and not await is_premium(user_id):
        await message.answer(
            f"💎 <b>{movie['title']}</b>\nBu Premium kino. Uni ko‘rish uchun obunani faollashtiring."
        )
        return
    await execute("UPDATE movies SET views=views+1 WHERE id=$1", movie["id"])
    await execute("""
      INSERT INTO watch_history(user_id,movie_id) VALUES($1,$2)
      ON CONFLICT(user_id,movie_id) DO UPDATE SET watched_at=NOW()
    """, user_id, movie["id"])
    caption = (f"🎬 <b>{movie['title']}</b>\n"
               f"📅 Yil: {movie['year'] or 'Noma’lum'}\n"
               f"🌍 Davlat: {movie['country']}\n"
               f"🗣 Til: {movie['language']}\n"
               f"🎭 Janr: {movie['genre']}\n"
               f"⭐ Reyting: {movie['rating']}\n"
               f"💎 {'Premium' if movie['is_premium'] else 'Bepul'}\n\n"
               f"📝 {movie['description'] or 'Tavsif mavjud emas.'}")
    await message.answer_video(movie["file_id"], caption=caption, reply_markup=movie_actions(movie["id"]))

async def list_movies(message, rows, user_id):
    if not rows:
        await message.answer("Bu bo‘limda hozircha kino yo‘q.")
        return
    for movie in rows[:15]:
        mark = "💎" if movie["is_premium"] else "🎬"
        await message.answer(
            f"{mark} <b>{movie['title']}</b> ({movie['year'] or '—'})\n"
            f"🌍 {movie['country']} · 🗣 {movie['language']} · 🎭 {movie['genre']}",
            reply_markup=inline([[__import__('aiogram').types.InlineKeyboardButton(
                text="▶️ Ko‘rish", callback_data=f"watch:{movie['id']}")]])
        )
    if len(rows) > 15:
        await message.answer("Natijalar 15 ta bilan cheklangan. Aniqroq qidiruvdan foydalaning.")

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await register_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    if not await subscribed(message.bot, message.from_user.id):
        channels = "\n".join(FORCE_CHANNELS)
        await message.answer(f"Botdan foydalanish uchun quyidagi kanal(lar)ga obuna bo‘ling:\n{channels}\n\nObunani tekshirish uchun /start ni qayta bosing.")
        return
    await message.answer("🎬 <b>Kino olamiga xush kelibsiz!</b>\nKerakli bo‘limni tanlang.", reply_markup=main_menu())

@router.message(Command("promo"))
async def promo_start(message: Message, state: FSMContext):
    await state.set_state(PromoState.code)
    await message.answer("Promo-kodni yuboring:")

@router.message(PromoState.code)
async def promo_apply(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Promo-kodni matn ko‘rinishida yuboring.")
        return
    code = message.text.strip().upper()
    await register_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    try:
        # Lock the promo row so simultaneous attempts cannot exceed max_uses.
        async with __import__('database')._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("SELECT * FROM promo_codes WHERE code=$1 AND active=TRUE AND used_count<max_uses AND (expires_at IS NULL OR expires_at>NOW()) FOR UPDATE", code)
                if not row:
                    await message.answer("Promo-kod noto‘g‘ri yoki muddati tugagan.")
                else:
                    await conn.execute("INSERT INTO promo_uses(code,user_id) VALUES($1,$2)", code, message.from_user.id)
                    await conn.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE code=$1", code)
                    await conn.execute("""INSERT INTO premium(user_id,expires_at) VALUES($1,NOW()+($2::text || ' days')::interval)
                        ON CONFLICT(user_id) DO UPDATE SET expires_at=GREATEST(premium.expires_at,NOW())+($2::text || ' days')::interval""", message.from_user.id, row["days"])
                    await message.answer(f"✅ Promo-kod qabul qilindi. Premium {row['days']} kunga faollashtirildi.")
    except Exception:
        await message.answer("Bu promo-koddan avval foydalangansiz yoki uni qo‘llashda xato yuz berdi.")
    await state.clear()

@router.message(F.text == "🔎 Kino qidirish")
async def search_start(message: Message, state: FSMContext):
    await state.set_state(SearchState.query)
    await message.answer("Kino nomini yoki nomining bir qismini yozing:")

@router.message(SearchState.query)
async def search_results(message: Message, state: FSMContext):
    q = message.text.strip()
    rows = await fetch("SELECT * FROM movies WHERE is_active=TRUE AND title ILIKE $1 ORDER BY views DESC LIMIT 30", f"%{q}%")
    await state.clear()
    await list_movies(message, rows, message.from_user.id)

@router.message(F.text.in_(list(LANGS.keys())))
async def by_language(message: Message):
    lang = LANGS[message.text]
    rows = await fetch("SELECT * FROM movies WHERE is_active=TRUE AND language=$1 ORDER BY created_at DESC LIMIT 30", lang)
    await list_movies(message, rows, message.from_user.id)

@router.message(F.text == "🌍 Davlatlar")
async def countries(message: Message):
    rows = await fetch("SELECT DISTINCT country FROM movies WHERE is_active=TRUE ORDER BY country")
    if not rows:
        await message.answer("Hozircha davlatlar mavjud emas.")
        return
    await message.answer("Davlatni tanlang:", reply_markup=inline([
        [__import__('aiogram').types.InlineKeyboardButton(text=r["country"], callback_data="country:"+r["country"])]
        for r in rows[:50]
    ]))

@router.callback_query(F.data.startswith("country:"))
async def country_pick(call: CallbackQuery):
    country = call.data.split(":",1)[1]
    rows = await fetch("SELECT * FROM movies WHERE is_active=TRUE AND country=$1 ORDER BY created_at DESC LIMIT 30", country)
    await call.message.answer(f"🌍 {country}", reply_markup=None)
    await list_movies(call.message, rows, call.from_user.id)
    await call.answer()

@router.message(F.text == "🎭 Janrlar")
async def genres(message: Message):
    rows = await fetch("SELECT DISTINCT genre FROM movies WHERE is_active=TRUE ORDER BY genre")
    if not rows:
        await message.answer("Hozircha janrlar mavjud emas.")
        return
    await message.answer("Janrni tanlang:", reply_markup=inline([
        [__import__('aiogram').types.InlineKeyboardButton(text=r["genre"], callback_data="genre:"+r["genre"])]
        for r in rows[:50]
    ]))

@router.callback_query(F.data.startswith("genre:"))
async def genre_pick(call: CallbackQuery):
    genre = call.data.split(":",1)[1]
    rows = await fetch("SELECT * FROM movies WHERE is_active=TRUE AND genre=$1 ORDER BY created_at DESC LIMIT 30", genre)
    await list_movies(call.message, rows, call.from_user.id)
    await call.answer()

@router.message(F.text == "📅 Yillar")
async def years(message: Message):
    rows = await fetch("SELECT DISTINCT year FROM movies WHERE is_active=TRUE AND year IS NOT NULL ORDER BY year DESC")
    if not rows:
        await message.answer("Hozircha yillar bo‘yicha kino yo‘q.")
        return
    await message.answer("Yilni tanlang:", reply_markup=inline([
        [__import__('aiogram').types.InlineKeyboardButton(text=str(r["year"]), callback_data=f"year:{r['year']}")]
        for r in rows[:60]
    ]))

@router.callback_query(F.data.startswith("year:"))
async def year_pick(call: CallbackQuery):
    year = int(call.data.split(":",1)[1])
    rows = await fetch("SELECT * FROM movies WHERE is_active=TRUE AND year=$1 ORDER BY created_at DESC LIMIT 30", year)
    await list_movies(call.message, rows, call.from_user.id)
    await call.answer()

@router.message(F.text == "🔥 Mashhur kinolar")
async def popular(message: Message):
    rows = await fetch("SELECT * FROM movies WHERE is_active=TRUE ORDER BY views DESC LIMIT 30")
    await list_movies(message, rows, message.from_user.id)

@router.message(F.text == "🆕 Yangi kinolar")
async def new_movies(message: Message):
    rows = await fetch("SELECT * FROM movies WHERE is_active=TRUE ORDER BY created_at DESC LIMIT 30")
    await list_movies(message, rows, message.from_user.id)

@router.message(F.text == "💎 Premium kinolar")
async def premium_movies(message: Message):
    rows = await fetch("SELECT * FROM movies WHERE is_active=TRUE AND is_premium=TRUE ORDER BY created_at DESC LIMIT 30")
    await list_movies(message, rows, message.from_user.id)

@router.message(F.text == "❤️ Sevimlilar")
async def favorites(message: Message):
    rows = await fetch("""SELECT m.* FROM movies m JOIN favorites f ON f.movie_id=m.id
      WHERE f.user_id=$1 AND m.is_active=TRUE ORDER BY m.created_at DESC LIMIT 30""", message.from_user.id)
    await list_movies(message, rows, message.from_user.id)

@router.message(F.text == "📜 Ko‘rish tarixi")
async def history(message: Message):
    rows = await fetch("""SELECT m.* FROM movies m JOIN watch_history h ON h.movie_id=m.id
      WHERE h.user_id=$1 AND m.is_active=TRUE ORDER BY h.watched_at DESC LIMIT 30""", message.from_user.id)
    await list_movies(message, rows, message.from_user.id)

@router.message(F.text == "👤 Mening profilim")
async def profile(message: Message):
    user_id = message.from_user.id
    premium = await fetchrow("SELECT expires_at FROM premium WHERE user_id=$1 AND expires_at>NOW()", user_id)
    count = await fetchval("SELECT COUNT(*) FROM watch_history WHERE user_id=$1", user_id)
    await message.answer(f"👤 <b>Profilingiz</b>\nID: <code>{user_id}</code>\n💎 Premium: {'Faol — '+premium['expires_at'].strftime('%Y-%m-%d')+' gacha' if premium else 'Faol emas'}\n🎬 Ko‘rilgan kinolar: {count}\n\nObuna uchun /premium buyrug‘idan foydalaning.")

@router.message(Command("premium"))
async def premium_info(message: Message):
    await register_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    prices = await fetch("SELECT key,value FROM settings WHERE key LIKE 'price_%' ORDER BY key")
    text = "💎 <b>Premium tariflari</b>\\n\\n"
    buttons = []
    for p in prices:
        try:
            days = int(p["key"].replace("price_", ""))
            stars = int(p["value"])
        except (ValueError, TypeError):
            continue
        text += f"• {days} kun — ⭐ {stars} Stars\\n"
        buttons.append([__import__('aiogram').types.InlineKeyboardButton(
            text=f"⭐ {days} kun — {stars} Stars", callback_data=f"buy:{days}")])
    text += "\\nPremium kinolarga kirish Telegram Stars orqali to‘lanadi."
    if buttons:
        await message.answer(text, reply_markup=inline(buttons))
    else:
        await message.answer(text + "\\nTariflar hali sozlanmagan.")

@router.callback_query(F.data.startswith("buy:"))
async def buy_premium(call: CallbackQuery):
    try:
        days = int(call.data.split(":", 1)[1])
    except ValueError:
        await call.answer("Tarif noto‘g‘ri.", show_alert=True)
        return
    if days not in (7, 30, 90, 365):
        await call.answer("Bu tarif mavjud emas.", show_alert=True)
        return
    price = await fetchval("SELECT value FROM settings WHERE key=$1", f"price_{days}")
    try:
        stars = int(price)
    except (TypeError, ValueError):
        await call.answer("Tarif narxi sozlanmagan.", show_alert=True)
        return
    if stars < 1:
        await call.answer("Tarif narxi noto‘g‘ri.", show_alert=True)
        return
    payload = f"premium:{days}:{call.from_user.id}"
    try:
        await call.message.answer_invoice(
            title=f"Premium — {days} kun",
            description=f"{days} kun davomida Premium kinolarga kirish.",
            payload=payload,
            currency="XTR",
            prices=[LabeledPrice(label=f"Premium {days} kun", amount=stars)],
            provider_token=""
        )
        await call.answer()
    except Exception:
        logging.exception("Could not create Telegram Stars invoice")
        await call.answer("To‘lov oynasini ochib bo‘lmadi. Keyinroq urinib ko‘ring.", show_alert=True)

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    try:
        parts = pre_checkout_query.invoice_payload.split(":")
        days = int(parts[1]) if len(parts) == 3 else 0
        expected = await fetchval("SELECT value FROM settings WHERE key=$1", f"price_{days}") if days in (7, 30, 90, 365) else None
        valid = (len(parts) == 3 and parts[0] == "premium"
                 and days in (7, 30, 90, 365)
                 and int(parts[2]) == pre_checkout_query.from_user.id
                 and pre_checkout_query.currency == "XTR"
                 and expected is not None and int(expected) == pre_checkout_query.total_amount
                 and pre_checkout_query.total_amount > 0)
    except (ValueError, TypeError):
        valid = False
    if valid:
        await pre_checkout_query.answer(ok=True)
    else:
        await pre_checkout_query.answer(ok=False, error_message="To‘lov ma’lumotlari noto‘g‘ri.")

@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment
    try:
        parts = payment.invoice_payload.split(":")
        if len(parts) != 3 or parts[0] != "premium" or int(parts[2]) != message.from_user.id:
            await message.answer("To‘lov ma’lumotlarini tekshirishda xatolik. Admin bilan bog‘laning.")
            return
        days = int(parts[1])
        if days not in (7, 30, 90, 365) or payment.currency != "XTR":
            await message.answer("To‘lov ma’lumotlarini tekshirishda xatolik. Admin bilan bog‘laning.")
            return
        expected = await fetchval("SELECT value FROM settings WHERE key=$1", f"price_{days}")
        if expected is None or int(expected) != payment.total_amount:
            await message.answer("To‘lov summasi tarifga mos kelmadi. Admin bilan bog‘laning.")
            return
        await register_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
        recorded = await record_star_payment(
            message.from_user.id, payment.total_amount, payment.invoice_payload,
            payment.telegram_payment_charge_id, days
        )
        if not recorded:
            await message.answer("Bu to‘lov avval qayta ishlangan.")
            return
        await message.answer(f"✅ To‘lov muvaffaqiyatli! Premium {days} kunga faollashtirildi.")
    except Exception:
        logging.exception("Successful payment processing failed")
        await message.answer("To‘lov qabul qilingan bo‘lishi mumkin, ammo Premium holatini tekshirish kerak. Admin bilan bog‘laning.")

@router.message(F.text == "💬 Yordam")
async def help_user(message: Message):
    if SUPPORT_USERNAME:
        await message.answer(f"Yordam uchun: @{SUPPORT_USERNAME}")
    else:
        await message.answer("Yordam kerak bo‘lsa, bot egasiga murojaat qiling.")

@router.callback_query(F.data.startswith("watch:"))
async def watch_movie(call: CallbackQuery):
    try: movie_id = int(call.data.split(":",1)[1])
    except (ValueError, IndexError): return await call.answer("Kino ID noto‘g‘ri.", show_alert=True)
    movie = await fetchrow("SELECT * FROM movies WHERE id=$1 AND is_active=TRUE", movie_id)
    if not movie:
        await call.answer("Kino topilmadi.", show_alert=True)
    else:
        if movie["is_premium"] and not await is_premium(call.from_user.id):
            await call.answer("Bu Premium kino. Obunani faollashtiring.", show_alert=True)
        else:
            await show_movie(call.message, movie, call.from_user.id)
            await call.answer()

@router.callback_query(F.data.startswith("fav:"))
async def favorite_toggle(call: CallbackQuery):
    try: movie_id = int(call.data.split(":",1)[1])
    except (ValueError, IndexError): return await call.answer("Kino ID noto‘g‘ri.", show_alert=True)
    exists = await fetchval("SELECT EXISTS(SELECT 1 FROM favorites WHERE user_id=$1 AND movie_id=$2)", call.from_user.id, movie_id)
    if exists:
        await execute("DELETE FROM favorites WHERE user_id=$1 AND movie_id=$2", call.from_user.id, movie_id)
        await call.answer("Sevimlilardan olib tashlandi.")
    else:
        await execute("INSERT INTO favorites(user_id,movie_id) VALUES($1,$2) ON CONFLICT DO NOTHING", call.from_user.id, movie_id)
        await call.answer("Sevimlilarga qo‘shildi.")

@router.callback_query(F.data.startswith("info:"))
async def movie_info(call: CallbackQuery):
    try: movie_id = int(call.data.split(":",1)[1])
    except (ValueError, IndexError): return await call.answer("Kino ID noto‘g‘ri.", show_alert=True)
    m = await fetchrow("SELECT * FROM movies WHERE id=$1 AND is_active=TRUE", movie_id)
    if m:
        await call.message.answer(f"🎬 <b>{m['title']}</b>\n🌍 {m['country']}\n🗣 {m['language']}\n🎭 {m['genre']}\n📅 {m['year'] or '—'}\n⭐ {m['rating']}\n\n{m['description'] or 'Tavsif mavjud emas.'}")
    await call.answer()
