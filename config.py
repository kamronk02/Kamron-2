import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
# Comma-separated Telegram numeric IDs, e.g. 123456789,987654321
ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
# Optional channel usernames/IDs, comma-separated. Bot must be able to check membership.
FORCE_CHANNELS = [
    x.strip() for x in os.getenv("FORCE_CHANNELS", "").split(",") if x.strip()
]
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").strip().lstrip("@")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN Environment Variable sozlanmagan.")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL sozlanmagan. Render PostgreSQL URL kiriting.")
