KINO BOT — ISHGA TUSHIRISH

1) Fayllarni GitHub repositoriyga bir xil papkaga joylang:
   main.py, config.py, database.py, keyboards.py, handlers.py, admin.py,
   requirements.txt, render.yaml

2) Render'da PostgreSQL database yarating. DATABASE_URL qiymatiga Internal Database URL kiriting.
   render.yaml ishlatilsa, Render blueprint orqali servis va baza yaratilishi mumkin.

3) Environment Variables:
   BOT_TOKEN = Telegram bot tokeni
   DATABASE_URL = PostgreSQL connection string
   ADMIN_IDS = admin Telegram ID raqamlari, vergul bilan: 123456789,987654321
   FORCE_CHANNELS = ixtiyoriy kanal username/ID, vergul bilan
   SUPPORT_USERNAME = ixtiyoriy yordam username

4) Botni ishga tushirish:
   python main.py

5) Telegramda /start yuboring. Admin paneli uchun /admin.

MUHIM:
- Botga kanal a'zoligini tekshirish uchun kanalni botga qo'shing va tegishli ruxsat bering.
- Video qo'shishda botga video sifatida yuboring; Telegram file_id bazada saqlanadi.
- Premium raqamli kontenti uchun Telegram Stars checkout qo‘llanadi; so‘mda tashqi checkout bu kodga kiritilmagan.
- To‘lovni haqiqiy Telegram botida, test xaridi va qaytarish ssenariylari bilan tekshirish kerak.
- Render free servis/baza resurslari va uxlab qolish siyosati o'zgarishi mumkin.
- Bot tokenini hech kimga yubormang; faqat Render Environment Variables ichida saqlang.


TELEGRAM STARS TO'LOVI:
- /premium buyrug'i orqali tarif tanlanadi va Telegram Stars invoice ochiladi.
- Premium faqat Telegram successful_payment update'i kelgandan keyin faollashadi.
- Digital content Telegram ichida sotilayotgani sababli to'lov uchun Telegram Stars ishlatiladi.
- Narxlar settings jadvalidagi price_7, price_30, price_90, price_365 qiymatlaridan olinadi.
- Standart boshlang'ich narxlar: 7 kun=50, 30 kun=150, 90 kun=400, 365 kun=1200 Stars.
- Bu narxlarni ishga tushirishdan oldin o'zingizga moslab tekshiring.

Eslatma: Kodni sintaksis jihatdan tekshirish mumkin, ammo haqiqiy bot tokeni, Render PostgreSQL va Telegram to'lovlari bilan jonli sinov qilinmaguncha 100% xatosizligiga kafolat berib bo'lmaydi.
