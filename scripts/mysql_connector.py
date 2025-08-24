# mysql_connector.py - Работа с MySQL базой данных (исправленная версия)
import pymysql
import logging
from typing import List, Dict, Tuple, Optional
from contextlib import contextmanager
from config import MYSQL_CONFIG

class MySQLConnectionError(Exception):
    """Ошибки подключения к MySQL"""
    pass

class MySQLQueryError(Exception):
    """Ошибки выполнения запросов MySQL"""
    pass

class MySQLConnector:
    """Класс для работы с базой данных MySQL Sakila"""

    def __init__(self):
        # Добавляем charset в конфиг если его нет
        self.config = MYSQL_CONFIG.copy()
        if 'charset' not in self.config:
            self.config['charset'] = 'utf8mb4'
        if 'use_unicode' not in self.config:
            self.config['use_unicode'] = True
            
        self.logger = logging.getLogger(__name__)
        self.connection = None

    @contextmanager
    def get_connection(self):
        connection = None
        try:
            connection = pymysql.connect(**self.config)
            yield connection
        except pymysql.Error as e:
            self.logger.error("Ошибка подключения MySQL: %s", e)
            raise MySQLConnectionError(f"Не удалось подключиться к MySQL: {e}")
        finally:
            if connection:
                connection.close()

    def test_connection(self) -> bool:
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True
        except Exception as e:
            self.logger.exception("Тест подключения провален: %s", e)
            return False

    def select(self, sql: str, params=None, args=None):
        """
        Выполняет SELECT-запрос и возвращает список словарей с результатами.
        params - словарь для именованных плейсхолдеров %(name)s
        args - список/кортеж для позиционных плейсхолдеров %s
        """
        try:
            # Создаём новое соединение для каждого запроса с правильной кодировкой
            with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cur:
                    if args is not None:
                        # Позиционные параметры
                        cur.execute(sql, args)
                    elif params is not None:
                        # Именованные параметры
                        cur.execute(sql, params)
                    else:
                        # Без параметров
                        cur.execute(sql)
                    return cur.fetchall()
        except Exception as e:
            self.logger.error(f"Ошибка выполнения запроса: {e}")
            self.logger.error(f"SQL: {sql}")
            self.logger.error(f"Params: {params}, Args: {args}")
            raise MySQLQueryError(f"Ошибка выполнения запроса: {e}")

    def search_by_keyword(self, keyword: str, offset: int = 0, limit: int = 10) -> Tuple[List[Dict], int]:
        """Поиск фильмов по ключевому слову в названии"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    count_query = """
                        SELECT COUNT(*) as total
                        FROM film f
                        WHERE f.title LIKE %s
                    """
                    cursor.execute(count_query, (f'%{keyword}%',))
                    total_count = cursor.fetchone()['total']
                    
                    search_query = """
                        SELECT 
                            f.film_id,
                            f.title,
                            f.release_year,
                            f.length,
                            f.rating,
                            f.description,
                            GROUP_CONCAT(DISTINCT c.name ORDER BY c.name SEPARATOR ', ') as genres
                        FROM film f
                        LEFT JOIN film_category fc ON f.film_id = fc.film_id
                        LEFT JOIN category c ON fc.category_id = c.category_id
                        WHERE f.title LIKE %s
                        GROUP BY f.film_id, f.title, f.release_year, f.length, f.rating, f.description
                        ORDER BY f.title
                        LIMIT %s OFFSET %s
                    """
                    cursor.execute(search_query, (f'%{keyword}%', limit, offset))
                    films = cursor.fetchall()
                    return films, total_count
                    
        except Exception as e:
            self.logger.error(f"Ошибка поиска по ключевому слову '{keyword}': {e}")
            raise MySQLQueryError(f"Ошибка выполнения запроса: {e}")
    
    def get_available_genres(self) -> List[Dict]:
        """Получение списка всех доступных жанров"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    query = """
                        SELECT 
                            c.category_id,
                            c.name,
                            COUNT(fc.film_id) as film_count
                        FROM category c
                        LEFT JOIN film_category fc ON c.category_id = fc.category_id
                        GROUP BY c.category_id, c.name
                        ORDER BY c.name
                    """
                    cursor.execute(query)
                    return cursor.fetchall()
                    
        except Exception as e:
            self.logger.error(f"Ошибка получения жанров: {e}")
            raise MySQLQueryError(f"Ошибка получения списка жанров: {e}")
    
    def get_year_range(self) -> Tuple[int, int]:
        """Получение диапазона годов выпуска фильмов"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT 
                            MIN(release_year) as min_year,
                            MAX(release_year) as max_year
                        FROM film
                        WHERE release_year IS NOT NULL
                    """
                    cursor.execute(query)
                    result = cursor.fetchone()
                    return result[0] or 1900, result[1] or 2025
                    
        except Exception as e:
            self.logger.error(f"Ошибка получения диапазона годов: {e}")
            raise MySQLQueryError(f"Ошибка получения диапазона годов: {e}")
    
    def search_by_genre_and_years(self, genre: str, start_year: int, end_year: int, 
                                 offset: int = 0, limit: int = 10) -> Tuple[List[Dict], int]:
        """Поиск фильмов по жанру и диапазону годов"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    count_query = """
                        SELECT COUNT(DISTINCT f.film_id) as total
                        FROM film f
                        JOIN film_category fc ON f.film_id = fc.film_id
                        JOIN category c ON fc.category_id = c.category_id
                        WHERE c.name = %s 
                        AND f.release_year BETWEEN %s AND %s
                    """
                    cursor.execute(count_query, (genre, start_year, end_year))
                    total_count = cursor.fetchone()['total']
                    
                    search_query = """
                        SELECT DISTINCT
                            f.film_id,
                            f.title,
                            f.release_year,
                            f.length,
                            f.rating,
                            f.description,
                            GROUP_CONCAT(DISTINCT cat.name ORDER BY cat.name SEPARATOR ', ') as genres
                        FROM film f
                        JOIN film_category fc ON f.film_id = fc.film_id
                        JOIN category c ON fc.category_id = c.category_id
                        LEFT JOIN film_category fc2 ON f.film_id = fc2.film_id
                        LEFT JOIN category cat ON fc2.category_id = cat.category_id
                        WHERE c.name = %s 
                        AND f.release_year BETWEEN %s AND %s
                        GROUP BY f.film_id, f.title, f.release_year, f.length, f.rating, f.description
                        ORDER BY f.release_year DESC, f.title
                        LIMIT %s OFFSET %s
                    """
                    cursor.execute(search_query, (genre, start_year, end_year, limit, offset))
                    films = cursor.fetchall()
                    return films, total_count
                    
        except Exception as e:
            self.logger.error(f"Ошибка поиска по жанру '{genre}' и годам {start_year}-{end_year}: {e}")
            raise MySQLQueryError(f"Ошибка выполнения запроса: {e}")
    
    def find_similar_films(self, film_id: int, genres: List[str], year: int, limit: int = 10) -> List[Dict]:
        """Поиск похожих фильмов по жанрам и году"""
        if not genres:
            return []
            
        try:
            with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    # Создаём плейсхолдеры для жанров
                    placeholders = ', '.join(['%s'] * len(genres))
                    
                    query = f"""
                        SELECT DISTINCT f.film_id, f.title, f.release_year, f.rating,
                               GROUP_CONCAT(DISTINCT c.name ORDER BY c.name SEPARATOR ', ') as genres
                        FROM film f
                        JOIN film_category fc ON fc.film_id = f.film_id
                        JOIN category c ON c.category_id = fc.category_id
                        WHERE c.name IN ({placeholders})
                          AND f.film_id != %s
                          AND ABS(f.release_year - %s) <= 5
                        GROUP BY f.film_id, f.title, f.release_year, f.rating
                        ORDER BY COUNT(DISTINCT c.name) DESC, f.rating DESC
                        LIMIT %s
                    """
                    
                    # Параметры: жанры + film_id + year + limit
                    params = genres + [film_id, year, limit]
                    cursor.execute(query, params)
                    return cursor.fetchall()
                    
        except Exception as e:
            self.logger.error(f"Ошибка поиска похожих фильмов для film_id={film_id}: {e}")
            raise MySQLQueryError(f"Ошибка выполнения запроса: {e}")