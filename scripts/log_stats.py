# log_stats.py — чтение статистики из MongoDB (без хардкода)
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from config import MONGODB_CONFIG


class MongoStatsError(Exception):
    """Ошибки получения статистики из MongoDB"""
    pass


class LogStats:
    """Возвращает популярные и последние поисковые запросы из логов"""

    def __init__(self) -> None:
        self._uri: str = MONGODB_CONFIG["connection_string"]
        self._db_name: str = MONGODB_CONFIG["database_name"] or ""   # если пусто — берём из URI
        self._col_name: str = MONGODB_CONFIG["collection_name"]

        self._client: Optional[MongoClient] = None
        self._db = None
        self._col = None

    def _get_client(self) -> MongoClient:
        if self._client is None:
            try:
                self._client = MongoClient(self._uri, serverSelectionTimeoutMS=5000)
                self._client.server_info()
            except Exception as e:
                self._client = None
                raise MongoStatsError(f"Ошибка подключения к MongoDB: {e}") from e
        return self._client

    def _get_collection(self):
        if self._col is None:
            client = self._get_client()
            self._db = client[self._db_name] if self._db_name else client.get_default_database()
            self._col = self._db[self._col_name]
        return self._col

    def get_popular_searches(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Топ одинаковых запросов (агрегируем по типу + параметрам)"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": {"search_type": "$search_type", "params": "$params"},
                        "count": {"$sum": 1},
                        "total_results": {"$sum": "$results_count"},
                        "last_search": {"$max": "$timestamp"},
                    }
                },
                {"$sort": {"count": -1}},
                {"$limit": limit},
                {
                    "$project": {
                        "_id": 0,
                        "search_type": "$_id.search_type",
                        "params": "$_id.params",
                        "count": 1,
                        "total_results": 1,
                        "last_search": 1,
                    }
                },
            ]
            return list(self._get_collection().aggregate(pipeline))
        except Exception as e:
            raise MongoStatsError(f"Не удалось получить популярные запросы: {e}") from e

    def get_recent_searches(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Последние уникальные запросы (по сочетанию тип+параметры)"""
        try:
            pipeline = [
                {"$sort": {"timestamp": -1}},
                {
                    "$group": {
                        "_id": {"search_type": "$search_type", "params": "$params"},
                        "timestamp": {"$first": "$timestamp"},
                        "results_count": {"$first": "$results_count"},
                    }
                },
                {"$sort": {"timestamp": -1}},
                {"$limit": limit},
                {
                    "$project": {
                        "_id": 0,
                        "search_type": "$_id.search_type",
                        "params": "$_id.params",
                        "timestamp": 1,
                        "results_count": 1,
                    }
                },
            ]
            return list(self._get_collection().aggregate(pipeline))
        except Exception as e:
            raise MongoStatsError(f"Не удалось получить последние запросы: {e}") from e

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            self._col = None
