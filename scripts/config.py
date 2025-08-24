# config.py
import os
from pathlib import Path

# Пытаемся подхватить переменные окружения из env.env или .env
try:
    from dotenv import load_dotenv
    env_loaded = False
    for candidate in ("env.env", ".env"):
        p = Path(__file__).with_name(candidate)
        if p.exists():
            load_dotenv(p, override=True)
            env_loaded = True
            break
    if not env_loaded:
        load_dotenv(override=True)  # вдруг .env в другом месте
except Exception:
    # если нет python-dotenv — просто читаем из окружения
    pass

def _need(name: str, default: str | None = None) -> str:
    """Обязательная переменная окружения"""
    val = os.getenv(name, default)
    if val is None or val == "":
        raise RuntimeError(f"ENV var {name} is required but missing")
    return val

# ---------- MySQL ----------
MYSQL_CONFIG = {
    "host": _need("MYSQL_HOST"),
    "user": _need("MYSQL_USER"),
    "password": _need("MYSQL_PASSWORD"),
    "database": _need("MYSQL_DB"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "charset": "utf8mb4",
    "autocommit": True,
}

# ---------- MongoDB ----------
# Рекомендуемый вариант: целиком из MONGO_URI
MONGODB_CONFIG = {
    "connection_string": _need("MONGO_URI"),
    # если DB указана в URI — можно не задавать MONGO_DB; оставь пусто — возьмём get_default_database()
    "database_name": os.getenv("MONGO_DB", ""),
    "collection_name": os.getenv("MONGO_COLLECTION", "logs"),
}

# ---------- Остальное (как у тебя было) ----------
APP_CONFIG = {
    "results_per_page": 10,
    "stats_limit": 5,
    "log_level": "INFO",
}

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "movie_search.log",
            "formatter": "standard",
        },
        "console": {"level": "INFO", "class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["file", "console"], "level": "INFO"},
}
