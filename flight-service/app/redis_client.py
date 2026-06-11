import json
import logging
import redis
from app.config import settings

logger = logging.getLogger(__name__)

_redis = redis.from_url(settings.redis_url, decode_responses=True)

FLIGHT_TTL = 300   # 5 min
SEARCH_TTL = 300   # 5 min


def get_flight(flight_id: str):
    key = f"flight:{flight_id}"
    raw = _redis.get(key)
    if raw:
        logger.info("Cache HIT: %s", key)
        return json.loads(raw)
    logger.info("Cache MISS: %s", key)
    return None


def set_flight(flight_id: str, data: dict):
    key = f"flight:{flight_id}"
    _redis.setex(key, FLIGHT_TTL, json.dumps(data))


def invalidate_flight(flight_id: str):
    key = f"flight:{flight_id}"
    _redis.delete(key)
    logger.info("Cache INVALIDATED: %s", key)


def get_search(origin: str, destination: str, date: str):
    key = f"search:{origin}:{destination}:{date}"
    raw = _redis.get(key)
    if raw:
        logger.info("Cache HIT: %s", key)
        return json.loads(raw)
    logger.info("Cache MISS: %s", key)
    return None


def set_search(origin: str, destination: str, date: str, data: list):
    key = f"search:{origin}:{destination}:{date}"
    _redis.setex(key, SEARCH_TTL, json.dumps(data))


def invalidate_search_for_flight(origin: str, destination: str):
    pattern = f"search:{origin}:{destination}:*"
    keys = _redis.keys(pattern)
    if keys:
        _redis.delete(*keys)
        logger.info("Cache INVALIDATED: %d search keys for %s->%s", len(keys), origin, destination)
