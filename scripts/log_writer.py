# log_writer.py — запись логов в MongoDB (без хардкода, через config)
from datetime import datetime
from typing import Dict, Any, Optional
from pymongo import MongoClient
from config import MONGODB_CONFIG


class MongoConnectionError(Exception):
    """Ошибки подключения к MongoDB"""
    pass


class MongoWriteError(Exception):
    """Ошибки записи в MongoDB"""
    pass


class LogWriter:
    """Пишет логи поисковых запросов в коллекцию MongoDB"""

    def __init__(self) -> None:
        self._uri: str = MONGODB_CONFIG["connection_string"]
        self._db_name: str = MONGODB_CONFIG["database_name"] or ""   # если пусто — берём из URI
        self._col_name: str = MONGODB_CONFIG["collection_name"]

        self._client: Optional[MongoClient] = None
        self._db = None
        self._col = None

    def _ensure(self) -> None:
        """Ленивая инициализация клиента/БД/коллекции"""
        if self._client is None:
            try:
                self._client = MongoClient(
                    self._uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000,
                )
                self._client.server_info()  # проверяем подключение
                self._db = (
                    self._client[self._db_name]
                    if self._db_name else self._client.get_default_database()
                )
                self._col = self._db[self._col_name]
            except Exception as e:
                self._client = None
                raise MongoConnectionError(f"Ошибка подключения к MongoDB: {e}") from e

    def test_connection(self) -> bool:
        try:
            self._ensure()
            self._client.server_info()
            return True
        except Exception:
            return False

    def log_search(self, search_type: str, params: Dict[str, Any], results_count: int) -> Optional[str]:
        """Логируем один поиск"""
        try:
            self._ensure()
            doc = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "search_type": search_type,
                "params": params,
                "results_count": results_count,
            }
            res = self._col.insert_one(doc)
            return str(res.inserted_id)
        except Exception as e:
            raise MongoWriteError(f"Ошибка логирования: {e}") from e

    def close_connection(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            self._col = None
