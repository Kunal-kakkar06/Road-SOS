"""
In-memory cache service with TTL support.
If Redis is available, uses it. Otherwise, falls back to a simple dict cache.
This ensures the app works out-of-the-box without requiring a Redis install.
"""
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

# ── In-memory fallback cache ──────────────────────────────────
_memory_cache: dict = {}   # { key: (value, expire_timestamp) }


def _cleanup_expired():
    """Remove expired keys from in-memory cache."""
    now = time.time()
    expired = [k for k, (_, exp) in _memory_cache.items() if exp <= now]
    for k in expired:
        del _memory_cache[k]


# ── Try Redis, fallback to in-memory ─────────────────────────
_redis = None
_redis_attempted = False


async def _get_redis():
    global _redis, _redis_attempted
    if _redis_attempted:
        return _redis
    _redis_attempted = True

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("[Cache] No REDIS_URL set — using in-memory cache")
        return None

    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(redis_url, decode_responses=True)
        await _redis.ping()
        print("[Cache] Connected to Redis")
        return _redis
    except Exception as e:
        print(f"[Cache] Redis unavailable ({e}) — using in-memory cache")
        _redis = None
        return None


async def get_cached(key: str):
    """Get a cached value. Returns None if not found or expired."""
    r = await _get_redis()
    if r is not None:
        try:
            return await r.get(key)
        except Exception:
            pass

    # In-memory fallback
    _cleanup_expired()
    if key in _memory_cache:
        value, expire_at = _memory_cache[key]
        if time.time() < expire_at:
            return value
        del _memory_cache[key]
    return None


async def set_cached(key: str, value, ttl: int = 60):
    """
    Cache a value with TTL in seconds.
    Set value=None to invalidate/delete the key.
    """
    r = await _get_redis()
    if r is not None:
        try:
            if value is None:
                await r.delete(key)
            else:
                await r.setex(key, ttl, value)
            return
        except Exception:
            pass

    # In-memory fallback
    if value is None:
        _memory_cache.pop(key, None)
    else:
        _memory_cache[key] = (value, time.time() + ttl)


async def get_bed_counts_cached(hospital_id: str, db_fallback):
    """
    Get bed counts from Cache. Falls back to DB if not cached.
    Bed counts cached for 60 seconds.
    """
    key = f"beds:{hospital_id}"
    cached = await get_cached(key)
    if cached:
        return json.loads(cached)

    # Fallback to DB
    from models.hospital_model import Hospital
    from sqlalchemy.future import select

    stmt = select(Hospital).filter(Hospital.id == hospital_id)
    result = await db_fallback.execute(stmt)
    hospital = result.scalar_one_or_none()

    if not hospital:
        return None

    data = {
        "trauma_beds":  hospital.trauma_beds_available,
        "icu_beds":     hospital.icu_beds_available,
        "general_beds": hospital.general_beds_available,
        "blood_types":  hospital.blood_types_available,
    }
    await set_cached(key, json.dumps(data), ttl=60)
    return data

