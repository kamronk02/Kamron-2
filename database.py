import asyncpg
from config import DATABASE_URL

_pool = None

def _db_url():
    # Render sometimes supplies postgres://; asyncpg accepts postgresql://
    return DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL

async def init_db():
    global _pool
    _pool = await asyncpg.create_pool(_db_url(), min_size=1, max_size=5, command_timeout=30)
    async with _pool.acquire() as c:
        await c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY, username TEXT, full_name TEXT,
            is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS movies (
            id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, year INTEGER,
            country TEXT NOT NULL DEFAULT 'Noma’lum', language TEXT NOT NULL,
            genre TEXT NOT NULL DEFAULT 'Boshqa', description TEXT NOT NULL DEFAULT '',
            rating TEXT NOT NULL DEFAULT '-', file_id TEXT NOT NULL,
            is_premium BOOLEAN NOT NULL DEFAULT FALSE, is_active BOOLEAN NOT NULL DEFAULT TRUE,
            views BIGINT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS favorites (
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            movie_id BIGINT NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
            PRIMARY KEY(user_id, movie_id)
        );
        CREATE TABLE IF NOT EXISTS watch_history (
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            movie_id BIGINT NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
            watched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY(user_id, movie_id)
        );
        CREATE TABLE IF NOT EXISTS premium (
            user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            expires_at TIMESTAMPTZ NOT NULL
        );
        CREATE TABLE IF NOT EXISTS payments (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            method TEXT NOT NULL, amount TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            payload TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            reviewed_by BIGINT, reviewed_at TIMESTAMPTZ,
            telegram_charge_id TEXT, days INTEGER
        );
        ALTER TABLE payments ADD COLUMN IF NOT EXISTS telegram_charge_id TEXT;
        ALTER TABLE payments ADD COLUMN IF NOT EXISTS days INTEGER;
        CREATE UNIQUE INDEX IF NOT EXISTS payments_telegram_charge_unique
            ON payments(telegram_charge_id) WHERE telegram_charge_id IS NOT NULL;
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY, days INTEGER NOT NULL, max_uses INTEGER NOT NULL DEFAULT 1,
            used_count INTEGER NOT NULL DEFAULT 0, active BOOLEAN NOT NULL DEFAULT TRUE,
            expires_at TIMESTAMPTZ
        );
        CREATE TABLE IF NOT EXISTS promo_uses (
            code TEXT NOT NULL REFERENCES promo_codes(code) ON DELETE CASCADE,
            user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            PRIMARY KEY(code, user_id)
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS movie_categories (
            movie_id BIGINT NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
            category_type TEXT NOT NULL, category_value TEXT NOT NULL,
            PRIMARY KEY(movie_id, category_type, category_value)
        );
        """)
        await c.execute("INSERT INTO settings(key,value) VALUES('price_7','50'),('price_30','150'),('price_90','400'),('price_365','1200') ON CONFLICT(key) DO NOTHING")

async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

async def execute(query, *args):
    async with _pool.acquire() as c:
        return await c.execute(query, *args)

async def fetch(query, *args):
    async with _pool.acquire() as c:
        return await c.fetch(query, *args)

async def fetchrow(query, *args):
    async with _pool.acquire() as c:
        return await c.fetchrow(query, *args)

async def fetchval(query, *args):
    async with _pool.acquire() as c:
        return await c.fetchval(query, *args)

async def register_user(user_id, username, full_name):
    await execute("""
      INSERT INTO users(user_id,username,full_name) VALUES($1,$2,$3)
      ON CONFLICT(user_id) DO UPDATE SET username=EXCLUDED.username,
      full_name=EXCLUDED.full_name,last_seen=NOW()
    """, user_id, username, full_name)

async def is_premium(user_id):
    return bool(await fetchval("SELECT EXISTS(SELECT 1 FROM premium WHERE user_id=$1 AND expires_at>NOW())", user_id))

async def add_premium(user_id, days):
    await execute("""
      INSERT INTO premium(user_id,expires_at)
      VALUES($1,NOW()+($2::text || ' days')::interval)
      ON CONFLICT(user_id) DO UPDATE SET expires_at=
      GREATEST(premium.expires_at,NOW())+($2::text || ' days')::interval
    """, user_id, days)


async def record_star_payment(user_id, amount, payload, charge_id, days):
    """Atomically record a unique Telegram Stars payment and grant its premium time."""
    async with _pool.acquire() as c:
        async with c.transaction():
            existing = await c.fetchval(
                "SELECT EXISTS(SELECT 1 FROM payments WHERE telegram_charge_id=$1)", charge_id
            )
            if existing:
                return False
            await c.execute(
                """INSERT INTO payments(user_id,method,amount,status,payload,telegram_charge_id,days)
                   VALUES($1,'telegram_stars',$2,'approved',$3,$4,$5)""",
                user_id, str(amount), payload, charge_id, days
            )
            await c.execute(
                """INSERT INTO premium(user_id,expires_at) VALUES($1,NOW()+($2::text || ' days')::interval)
                   ON CONFLICT(user_id) DO UPDATE SET expires_at=
                   GREATEST(premium.expires_at,NOW())+($2::text || ' days')::interval""",
                user_id, days
            )
            return True
