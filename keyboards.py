from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    rows = [
        [KeyboardButton(text="🔎 Kino qidirish")],
        [KeyboardButton(text="🇺🇿 O‘zbek kinolari"), KeyboardButton(text="🇷🇺 Rus kinolari")],
        [KeyboardButton(text="🇬🇧 Ingliz kinolari")],
        [KeyboardButton(text="🌍 Davlatlar"), KeyboardButton(text="🎭 Janrlar")],
        [KeyboardButton(text="📅 Yillar"), KeyboardButton(text="🔥 Mashhur kinolar")],
        [KeyboardButton(text="🆕 Yangi kinolar"), KeyboardButton(text="💎 Premium kinolar")],
        [KeyboardButton(text="❤️ Sevimlilar"), KeyboardButton(text="📜 Ko‘rish tarixi")],
        [KeyboardButton(text="👤 Mening profilim"), KeyboardButton(text="💬 Yordam")]
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def inline(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)

def movie_actions(movie_id, is_fav=False):
    return inline([
        [InlineKeyboardButton(text="❤️ Sevimlilardan olish" if is_fav else "❤️ Sevimlilarga", callback_data=f"fav:{movie_id}")],
        [InlineKeyboardButton(text="ℹ️ Kino ma’lumoti", callback_data=f"info:{movie_id}")]
    ])

def admin_menu():
    rows = [
        [KeyboardButton(text="🎬 Kino boshqaruvi"), KeyboardButton(text="🗂 Kategoriyalar")],
        [KeyboardButton(text="💎 Premium boshqaruvi"), KeyboardButton(text="👥 Foydalanuvchilar")],
        [KeyboardButton(text="📢 Ommaviy xabar"), KeyboardButton(text="🔒 Majburiy obuna")],
        [KeyboardButton(text="💳 To‘lovlar"), KeyboardButton(text="🎟 Promo-kodlar")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👨‍💻 Adminlar")],
        [KeyboardButton(text="⚙️ Bot sozlamalari"), KeyboardButton(text="⬅️ Foydalanuvchi menyusi")]
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
