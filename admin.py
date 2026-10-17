from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS, FORCE_CHANNELS
from database import execute, fetch, fetchrow, fetchval, add_premium
from keyboards import admin_menu, main_menu, inline

router = Router()

def is_admin(user_id):
    return user_id in ADMIN_IDS

class AddMovie(StatesGroup):
    video = State()
    title = State()
    year = State()
    country = State()
    language = State()
    genre = State()
    description = State()
    rating = State()
    premium = State()

class DeleteMovie(StatesGroup):
    movie_id = State()

class Broadcast(StatesGroup):
    text = State()

class AddAdmin(StatesGroup):
    user_id = State()

class PremiumGrant(StatesGroup):
    user_id = State()
    days = State()

class AddPromo(StatesGroup):
    code = State()
    days = State()
    uses = State()

class AddChannel(StatesGroup):
    channel = State()

@router.message(Command("admin"))
async def admin_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("🔐 <b>Admin panel</b>", reply_markup=admin_menu())

@router.message(F.text == "⬅️ Foydalanuvchi menyusi")
async def user_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Foydalanuvchi menyusi:", reply_markup=main_menu())

@router.message(F.text == "🎬 Kino boshqaruvi")
async def movie_manage(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("Kino boshqaruvi:", reply_markup=inline([
        [InlineKeyboardButton(text="➕ Kino qo‘shish", callback_data="adm:addmovie")],
        [InlineKeyboardButton(text="🗑 Kino o‘chirish", callback_data="adm:delmovie")],
        [InlineKeyboardButton(text="📋 Kino ro‘yxati", callback_data="adm:listmovies")],
    ]))

@router.callback_query(F.data == "adm:addmovie")
async def add_movie_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    await state.clear()
    await state.set_state(AddMovie.video)
    await call.message.answer("Kino videosini yuboring:")
    await call.answer()

@router.message(AddMovie.video)
async def add_movie_video(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if not message.video:
        await message.answer("Iltimos, video fayl yuboring.")
        return
    await state.update_data(file_id=message.video.file_id)
    await state.set_state(AddMovie.title)
    await message.answer("Kino nomini yozing:")

@router.message(AddMovie.title)
async def add_movie_title(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Kino nomini matn bilan kiriting.")
        return
    await state.update_data(title=message.text.strip()[:250])
    await state.set_state(AddMovie.year)
    await message.answer("Chiqqan yilini yozing (noma’lum bo‘lsa 0):")

@router.message(AddMovie.year)
async def add_movie_year(message: Message, state: FSMContext):
    try: year = int(message.text.strip())
    except ValueError:
        await message.answer("Yil raqam bo‘lishi kerak.")
        return
    if year and not 1888 <= year <= 2100:
        await message.answer("Yil 1888–2100 oralig‘ida yoki 0 bo‘lsin.")
        return
    await state.update_data(year=year or None)
    await state.set_state(AddMovie.country)
    await message.answer("Ishlab chiqarilgan davlatini yozing:")

@router.message(AddMovie.country)
async def add_movie_country(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Davlat nomini matn bilan kiriting.")
        return
    await state.update_data(country=message.text.strip())
    data = await state.get_data()
    if data.get("forced_language"):
        await state.update_data(language=data["forced_language"])
        await state.set_state(AddMovie.genre)
        await message.answer("Janrini yozing (masalan: Drama, Komediya):")
        return
    await state.set_state(AddMovie.language)
    await message.answer("Kino tilini tanlang: O‘zbek / Rus / Ingliz", reply_markup=inline([
        [InlineKeyboardButton(text=x, callback_data="lang:"+x)] for x in ["O‘zbek","Rus","Ingliz"]
    ]))

@router.callback_query(F.data.startswith("lang:"))
async def add_movie_language(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    if await state.get_state() != AddMovie.language.state:
        return await call.answer("Bu tanlov eskirgan.", show_alert=True)
    await state.update_data(language=call.data.split(":",1)[1])
    await state.set_state(AddMovie.genre)
    await call.message.answer("Janrini yozing (masalan: Drama, Komediya):")
    await call.answer()

@router.message(AddMovie.genre)
async def add_movie_genre(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Janrni matn bilan kiriting.")
        return
    await state.update_data(genre=message.text.strip()[:100])
    await state.set_state(AddMovie.description)
    await message.answer("Kino tavsifini yozing:")

@router.message(AddMovie.description)
async def add_movie_description(message: Message, state: FSMContext):
    if message.text is None:
        await message.answer("Tavsifni matn ko‘rinishida yuboring.")
        return
    await state.update_data(description=message.text.strip()[:3500])
    await state.set_state(AddMovie.rating)
    await message.answer("Reytingini yozing (masalan 8.5 yoki -):")

@router.message(AddMovie.rating)
async def add_movie_rating(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Reytingni matn bilan kiriting, masalan 8.5 yoki -.")
        return
    await state.update_data(rating=message.text.strip()[:20])
    await state.set_state(AddMovie.premium)
    await message.answer("Kino turi:", reply_markup=inline([
        [InlineKeyboardButton(text="🆓 Bepul", callback_data="prem:no"),
         InlineKeyboardButton(text="💎 Premium", callback_data="prem:yes")]
    ]))

@router.callback_query(F.data.startswith("prem:"))
async def add_movie_finish(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    if await state.get_state() != AddMovie.premium.state:
        return await call.answer("Bu tanlov eskirgan.", show_alert=True)
    data = await state.get_data()
    premium = call.data.endswith("yes")
    row = await fetchrow("""
      INSERT INTO movies(title,year,country,language,genre,description,rating,file_id,is_premium)
      VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id
    """, data["title"], data["year"], data["country"], data["language"], data["genre"],
         data["description"], data["rating"], data["file_id"], premium)
    await state.clear()
    await call.message.answer(f"✅ Kino qo‘shildi!\nID: <code>{row['id']}</code>\nNomi: {data['title']}")
    await call.answer()

@router.callback_query(F.data == "adm:delmovie")
async def delete_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    await state.clear()
    await state.set_state(DeleteMovie.movie_id)
    await call.message.answer("O‘chiriladigan kino ID raqamini yuboring:")
    await call.answer()

@router.message(DeleteMovie.movie_id)
async def delete_movie(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try: movie_id = int(message.text.strip())
    except ValueError:
        await message.answer("ID raqam bo‘lishi kerak."); return
    data = await state.get_data()
    lang = data.get("remove_language")
    m = await fetchrow("SELECT title,language FROM movies WHERE id=$1 AND is_active=TRUE", movie_id)
    if not m:
        await message.answer("Faol holatdagi bunday kino ID topilmadi.")
        await state.clear()
        return
    if lang:
        if m["language"] != lang:
            await message.answer(f"Bu kino {lang} kategoriyasiga tegishli emas. Kino tili: {m['language']}.")
            await state.clear()
            return
        await execute("UPDATE movies SET is_active=FALSE WHERE id=$1", movie_id)
        await message.answer(f"🗂 Kino {lang} kategoriyasidan chiqarildi: {m['title']} (ID {movie_id}).")
    else:
        await execute("DELETE FROM movies WHERE id=$1", movie_id)
        await message.answer(f"🗑 Kino o‘chirildi: {m['title']}")
    await state.clear()

@router.callback_query(F.data == "adm:listmovies")
async def list_admin_movies(call: CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    rows = await fetch("SELECT id,title,language,is_premium FROM movies ORDER BY id DESC LIMIT 30")
    if not rows: text = "Kino katalogi bo‘sh."
    else: text = "\n".join(f"#{r['id']} — {r['title']} | {r['language']} | {'Premium' if r['is_premium'] else 'Bepul'}" for r in rows)
    await call.message.answer(text)
    await call.answer()

@router.message(F.text == "🗂 Kategoriyalar")
async def categories_admin(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("Kategoriya bo‘yicha kino boshqaruvi:", reply_markup=inline([
        [InlineKeyboardButton(text="🇺🇿 O‘zbek kinolari", callback_data="cat:O‘zbek")],
        [InlineKeyboardButton(text="🇷🇺 Rus kinolari", callback_data="cat:Rus")],
        [InlineKeyboardButton(text="🇬🇧 Ingliz kinolari", callback_data="cat:Ingliz")],
        [InlineKeyboardButton(text="🌍 Davlatlar", callback_data="catlist:country")],
        [InlineKeyboardButton(text="🎭 Janrlar", callback_data="catlist:genre")],
    ]))

@router.callback_query(F.data.startswith("cat:"))
async def category_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    lang = call.data.split(":",1)[1]
    await call.message.answer(f"{lang} tilidagi kinolar:", reply_markup=inline([
        [InlineKeyboardButton(text="➕ Shu tilga kino qo‘shish", callback_data="catadd:"+lang)],
        [InlineKeyboardButton(text="🗑 Shu tildan kino chiqarish", callback_data="catremove:"+lang)],
        [InlineKeyboardButton(text="📋 Ro‘yxat", callback_data="catshow:"+lang)]
    ]))
    await call.answer()

@router.callback_query(F.data.startswith("catadd:"))
async def category_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    lang = call.data.split(":",1)[1]
    if lang not in ("O‘zbek", "Rus", "Ingliz"):
        return await call.answer("Til noto‘g‘ri.", show_alert=True)
    await state.clear()
    await state.update_data(forced_language=lang)
    await state.set_state(AddMovie.video)
    await call.message.answer(f"{lang} tilidagi kino videosini yuboring. Keyin ma’lumotlarini kiritasiz:")
    await call.answer()

@router.callback_query(F.data.startswith("catremove:"))
async def category_remove_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    lang = call.data.split(":",1)[1]
    if lang not in ("O‘zbek", "Rus", "Ingliz"):
        return await call.answer("Til noto‘g‘ri.", show_alert=True)
    await state.clear()
    await state.update_data(remove_language=lang)
    await state.set_state(DeleteMovie.movie_id)
    await call.message.answer(f"{lang} kategoriyasidan chiqariladigan kino ID raqamini yuboring. Kino butunlay o‘chmaydi, faqat faol emas qilinadi.")
    await call.answer()

@router.callback_query(F.data.startswith("catshow:"))
async def category_show(call: CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    lang = call.data.split(":",1)[1]
    rows = await fetch("SELECT id,title,is_premium FROM movies WHERE language=$1 AND is_active=TRUE ORDER BY id DESC LIMIT 30", lang)
    await call.message.answer("\n".join(f"#{r['id']} {r['title']} {'💎' if r['is_premium'] else '🆓'}" for r in rows) or "Bu kategoriyada kino yo‘q.")
    await call.answer()

@router.message(F.text == "💎 Premium boshqaruvi")
async def premium_admin(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("Premium boshqaruvi:", reply_markup=inline([
        [InlineKeyboardButton(text="👤 Foydalanuvchiga Premium berish", callback_data="premium:grant")],
        [InlineKeyboardButton(text="⛔ Premiumni bekor qilish", callback_data="premium:revoke")],
        [InlineKeyboardButton(text="💰 Tarif narxlari", callback_data="premium:prices")],
    ]))

@router.callback_query(F.data == "premium:grant")
async def premium_grant_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    await state.clear()
    await state.set_state(PremiumGrant.user_id)
    await call.message.answer("Foydalanuvchi Telegram ID sini yuboring:")
    await call.answer()

@router.message(PremiumGrant.user_id)
async def premium_grant_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    data = await state.get_data()
    try: uid=int(message.text.strip())
    except (ValueError, AttributeError): await message.answer("ID raqam bo‘lishi kerak."); return
    if uid <= 0:
        await message.answer("Musbat Telegram ID kiriting.")
        return
    if data.get("revoke"):
        await execute("DELETE FROM premium WHERE user_id=$1", uid)
        await state.clear()
        await message.answer(f"⛔ Premium bekor qilindi: {uid}")
        return
    await state.update_data(uid=uid)
    await state.set_state(PremiumGrant.days)
    await message.answer("Necha kunga Premium berilsin?")

@router.message(PremiumGrant.days)
async def premium_grant_days(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try: days=int(message.text.strip())
    except ValueError: await message.answer("Kun sonini raqamda kiriting."); return
    if days < 1 or days > 3650: await message.answer("1 dan 3650 kungacha kiriting."); return
    data=await state.get_data()
    await add_premium(data["uid"], days)
    await state.clear()
    await message.answer(f"✅ {data['uid']} ID foydalanuvchiga {days} kun Premium berildi.")

@router.callback_query(F.data == "premium:revoke")
async def premium_revoke(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    await state.clear()
    await state.set_state(PremiumGrant.user_id)
    await state.update_data(revoke=True)
    await call.message.answer("Premiumi bekor qilinadigan foydalanuvchi ID sini yuboring:")
    await call.answer()

@router.callback_query(F.data == "premium:prices")
async def premium_prices(call: CallbackQuery):
    if not is_admin(call.from_user.id): return await call.answer("Ruxsat yo‘q", show_alert=True)
    rows=await fetch("SELECT key,value FROM settings WHERE key LIKE 'price_%' ORDER BY key")
    await call.message.answer("Tarif narxlari (Stars):\n"+"\n".join(f"{r['key']}: {r['value']}" for r in rows)+"\nNarxni o‘zgartirish uchun PostgreSQL settings jadvalidan yangilang.")
    await call.answer()

@router.message(F.text == "👥 Foydalanuvchilar")
async def users_admin(message: Message):
    if not is_admin(message.from_user.id): return
    total=await fetchval("SELECT COUNT(*) FROM users")
    blocked=await fetchval("SELECT COUNT(*) FROM users WHERE is_blocked=TRUE")
    await message.answer(f"👥 Jami foydalanuvchilar: {total}\n🚫 Bloklangan: {blocked}\nFoydalanuvchi ID sini ko‘rish yoki Premium berish uchun Premium boshqaruvi bo‘limidan foydalaning.")

@router.message(F.text == "📢 Ommaviy xabar")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(Broadcast.text)
    await message.answer("Yuboriladigan xabarni yozing yoki rasm/video bilan caption yuboring. Hozircha matnli xabar qo‘llanadi:")

@router.message(Broadcast.text)
async def broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if not message.text:
        await message.answer("Hozircha matn yuboring."); return
    users=await fetch("SELECT user_id FROM users WHERE is_blocked=FALSE")
    sent=failed=0
    await message.answer(f"Yuborish boshlandi: {len(users)} foydalanuvchi.")
    for row in users:
        try:
            await message.bot.send_message(row["user_id"], message.text)
            sent+=1
        except Exception:
            failed+=1
            await execute("UPDATE users SET is_blocked=TRUE WHERE user_id=$1", row["user_id"])
    await state.clear()
    await message.answer(f"📢 Yakunlandi.\n✅ Yuborildi: {sent}\n❌ Xato: {failed}")

@router.message(F.text == "🔒 Majburiy obuna")
async def force_sub_admin(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("Majburiy obuna FORCE_CHANNELS Environment Variable orqali sozlanadi.\nHozirgi kanallar:\n" + ("\n".join(FORCE_CHANNELS) if FORCE_CHANNELS else "Sozlanmagan"))

@router.message(F.text == "🎟 Promo-kodlar")
async def promo_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AddPromo.code)
    await message.answer("Yangi promo-kod nomini yozing (masalan PREMIUM30):")

@router.message(AddPromo.code)
async def promo_code_step(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if not message.text or not message.text.strip():
        await message.answer("Promo-kod matn bo‘lishi kerak.")
        return
    code=message.text.strip().upper()[:50]
    await state.update_data(code=code)
    await state.set_state(AddPromo.days)
    await message.answer("Necha kun Premium beradi?")

@router.message(AddPromo.days)
async def promo_days_step(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try: days=int(message.text.strip())
    except (ValueError, AttributeError): await message.answer("Kun sonini raqamda kiriting."); return
    if not 1 <= days <= 3650:
        await message.answer("1 dan 3650 kungacha kiriting.")
        return
    await state.update_data(days=days)
    await state.set_state(AddPromo.uses)
    await message.answer("Necha marta ishlatilishi mumkin?")

@router.message(AddPromo.uses)
async def promo_uses_step(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try: uses=int(message.text.strip())
    except (ValueError, AttributeError): await message.answer("Soni raqam bo‘lishi kerak."); return
    if not 1 <= uses <= 100000:
        await message.answer("1 dan 100000 gacha kiriting.")
        return
    d=await state.get_data()
    try:
        await execute("INSERT INTO promo_codes(code,days,max_uses) VALUES($1,$2,$3)", d["code"], d["days"], uses)
        await message.answer(f"✅ Promo-kod yaratildi: {d['code']} — {d['days']} kun, {uses} marta.")
    except Exception:
        await message.answer("Bu kod mavjud. Boshqa nom tanlang.")
    await state.clear()

@router.message(F.text == "📊 Statistika")
async def stats(message: Message):
    if not is_admin(message.from_user.id): return
    users=await fetchval("SELECT COUNT(*) FROM users")
    movies=await fetchval("SELECT COUNT(*) FROM movies WHERE is_active=TRUE")
    premium_movies=await fetchval("SELECT COUNT(*) FROM movies WHERE is_active=TRUE AND is_premium=TRUE")
    premium_users=await fetchval("SELECT COUNT(*) FROM premium WHERE expires_at>NOW()")
    views=await fetchval("SELECT COALESCE(SUM(views),0) FROM movies")
    payments=await fetchval("SELECT COUNT(*) FROM payments WHERE status='approved'")
    await message.answer(f"📊 <b>Statistika</b>\n👥 Foydalanuvchilar: {users}\n🎬 Kinolar: {movies}\n💎 Premium kinolar: {premium_movies}\n👑 Premium obunalar: {premium_users}\n▶️ Ko‘rishlar: {views}\n💳 Tasdiqlangan to‘lovlar: {payments}")

@router.message(F.text == "👨‍💻 Adminlar")
async def admins_info(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("Asosiy adminlar ADMIN_IDS Environment Variable orqali belgilanadi. Bir nechta ID ni vergul bilan ajrating.")

@router.message(F.text == "⚙️ Bot sozlamalari")
async def settings_info(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("Sozlamalar Render Environment Variables orqali boshqariladi:\nBOT_TOKEN, DATABASE_URL, ADMIN_IDS, FORCE_CHANNELS, SUPPORT_USERNAME.")

@router.message(F.text == "💳 To‘lovlar")
async def payments_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    rows = await fetch("SELECT id,user_id,amount,method,status,days,created_at FROM payments ORDER BY id DESC LIMIT 20")
    if not rows:
        await message.answer("Hozircha to‘lovlar mavjud emas.")
        return
    lines = [f"#{r['id']} | user {r['user_id']} | {r['amount']} {('Stars' if r['method']=='telegram_stars' else r['method'])} | {r['days'] or '?'} kun | {r['status']} | {r['created_at']:%Y-%m-%d %H:%M}" for r in rows]
    await message.answer("💳 So‘nggi to‘lovlar:\n" + "\n".join(lines))
