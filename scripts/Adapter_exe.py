#!/usr/bin/env python
"""
launch_tmdb_fixed.py - Исправленный запускатель для TMDB
Использование: python launch_tmdb_fixed.py
"""

import sys
import os
import re
import pymysql
print("🔧 Инициализация TMDB адаптера v2...")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mysql_connector import MySQLConnector

# Сохраняем оригиналы
_original_init = MySQLConnector.__init__
_original_select = MySQLConnector.select
_original_test = MySQLConnector.test_connection

class TMDBAdapterV2:
    """Улучшенный адаптер для TMDB"""
    
    @staticmethod
    def adapt_sql(sql):
        """Умная адаптация SQL с исправлением всех проблем"""
        original = sql
        
        # Отладка
        if 'film' in sql.lower():
            print(f"\n🔍 Обрабатываем SQL с 'film'...")
        
        # 1. Сначала заменяем составные таблицы
        sql = sql.replace('film_category', 'movie_genres')
        sql = sql.replace('film_actor', 'cast_credits')
        
        # 2. Заменяем таблицу film -> movies
        sql = re.sub(r'\bfilm\b', 'movies', sql)
        sql = re.sub(r'\bFILM\b', 'MOVIES', sql)
        
        # 3. Заменяем category -> genres
        sql = re.sub(r'\bcategory\b', 'genres', sql)
        sql = re.sub(r'\bCATEGORY\b', 'GENRES', sql)
        
        # 4. Заменяем actor -> people
        sql = re.sub(r'\bactor\b', 'people', sql)
        sql = re.sub(r'\bACTOR\b', 'PEOPLE', sql)
        
        # 5. Заменяем ID поля
        sql = sql.replace('film_id', 'tmdb_id')
        sql = sql.replace('category_id', 'genre_id')
        sql = sql.replace('actor_id', 'person_id')
        
        # 6. Заменяем поля
        sql = sql.replace('.description', '.overview')
        sql = sql.replace('`description`', '`overview`')
        sql = sql.replace(' description,', ' overview,')
        sql = sql.replace(' description ', ' overview ')
        
        sql = sql.replace('.length', '.runtime')
        sql = sql.replace('`length`', '`runtime`')
        sql = sql.replace(' length,', ' runtime,')
        sql = sql.replace(' length ', ' runtime ')
        
        sql = sql.replace('.rating', '.vote_average')
        sql = sql.replace('`rating`', '`vote_average`')
        sql = sql.replace(' rating,', ' vote_average,')
        sql = sql.replace(' rating ', ' vote_average ')
        
        # 7. Обработка release_year
        if 'YEAR(m.release_date) as release_year' not in sql and 'YEAR(release_date) as release_year' not in sql:
            sql = re.sub(r'(\w+)\.release_year', r'YEAR(\1.release_date)', sql)
            sql = re.sub(r'\brelease_year\b', 'YEAR(release_date)', sql)
        
        # 8. ВАЖНО: Исправляем имена актеров во ВСЕХ частях запроса
        # Сначала CONCAT
        sql = sql.replace("CONCAT(a.first_name,' ',a.last_name)", 'a.name')
        sql = sql.replace("CONCAT(a.first_name, ' ', a.last_name)", 'a.name')
        
        # Потом отдельные поля (включая ORDER BY!)
        sql = sql.replace('a.first_name', 'a.name')
        sql = sql.replace('a.last_name', 'a.name')  # В TMDB нет разделения
        
        # Исправляем ORDER BY специфично для актеров
        sql = sql.replace('ORDER BY a.name SEPARATOR', 'ORDER BY a.name SEPARATOR')
        
        # 9. Убираем FIELD для рейтингов
        sql = re.sub(r"FIELD\([^)]+\)", '1', sql)
        
        if sql != original:
            print(f"✅ SQL адаптирован")
            
        return sql
    
    @staticmethod
    def adapt_results(results):
        """Адаптация результатов"""
        if not results:
            return results
            
        adapted = []
        for row in results:
            new_row = {}
            for key, value in row.items():
                if key == 'tmdb_id':
                    new_row['film_id'] = value
                elif key == 'overview':
                    new_row['description'] = value or ''
                elif key == 'runtime':
                    new_row['length'] = value
                elif key == 'vote_average':
                    if value is None:
                        new_row['rating'] = 'NR'
                    elif value >= 8:
                        new_row['rating'] = 'G'
                    elif value >= 7:
                        new_row['rating'] = 'PG'
                    elif value >= 6:
                        new_row['rating'] = 'PG-13'
                    elif value >= 5:
                        new_row['rating'] = 'R'
                    else:
                        new_row['rating'] = 'NC-17'
                elif key == 'genre_id':
                    new_row['category_id'] = value
                elif key == 'person_id':
                    new_row['actor_id'] = value
                else:
                    new_row[key] = value
                    
            adapted.append(new_row)
            
        return adapted

# Патчим методы
def patched_init(self):
    _original_init(self)
    print("✅ TMDB адаптер v2 активирован")

def patched_select(self, sql, params=None, args=None):
    adapted_sql = TMDBAdapterV2.adapt_sql(sql)
    
    # Финальная проверка на проблемы
    if 'f.YEAR(' in adapted_sql or '.YEAR(' in adapted_sql:
        print("⚠️  Финальная коррекция YEAR...")
        adapted_sql = adapted_sql.replace('f.YEAR(', 'YEAR(f.')
        adapted_sql = adapted_sql.replace('.YEAR(', 'YEAR(')
    
    try:
        results = _original_select(self, adapted_sql, params, args)
        return TMDBAdapterV2.adapt_results(results)
    except Exception as e:
        print(f"\n❌ Ошибка SQL: {e}")
        print(f"📝 Проблемный запрос:\n{adapted_sql}\n")
        # Попробуем еще раз найти проблему
        if 'film' in str(e).lower():
            print("⚠️  Обнаружена необработанная таблица 'film'")
        raise

def patched_test(self):
    result = _original_test(self)
    if result:
        print("✅ Подключение к TMDB успешно")
    return result

# Методы для жанров и годов
def patched_get_genres(self):
    try:
        sql = """
            SELECT g.genre_id as category_id, g.name, COUNT(mg.tmdb_id) as film_count
            FROM genres g
            LEFT JOIN movie_genres mg ON g.genre_id = mg.genre_id
            GROUP BY g.genre_id, g.name
            ORDER BY g.name
        """
        results = self.select(sql)
        return results if results else get_default_genres()
    except:
        return get_default_genres()

def get_default_genres():
    return [
        {'name': 'Action', 'category_id': 28, 'film_count': 1000},
        {'name': 'Adventure', 'category_id': 12, 'film_count': 1000},
        {'name': 'Animation', 'category_id': 16, 'film_count': 1000},
        {'name': 'Comedy', 'category_id': 35, 'film_count': 1000},
        {'name': 'Crime', 'category_id': 80, 'film_count': 1000},
        {'name': 'Documentary', 'category_id': 99, 'film_count': 1000},
        {'name': 'Drama', 'category_id': 18, 'film_count': 1000},
        {'name': 'Family', 'category_id': 10751, 'film_count': 1000},
        {'name': 'Fantasy', 'category_id': 14, 'film_count': 1000},
        {'name': 'Horror', 'category_id': 27, 'film_count': 1000},
        {'name': 'Mystery', 'category_id': 9648, 'film_count': 1000},
        {'name': 'Romance', 'category_id': 10749, 'film_count': 1000},
        {'name': 'Science Fiction', 'category_id': 878, 'film_count': 1000},
        {'name': 'Thriller', 'category_id': 53, 'film_count': 1000},
        {'name': 'War', 'category_id': 10752, 'film_count': 1000},
        {'name': 'Western', 'category_id': 37, 'film_count': 1000}
    ]

def patched_get_years(self):
    try:
        sql = """
            SELECT YEAR(MIN(release_date)) as min_year, YEAR(MAX(release_date)) as max_year
            FROM movies
            WHERE release_date IS NOT NULL
        """
        results = self.select(sql)
        if results and results[0]['min_year']:
            return results[0]['min_year'], results[0]['max_year']
    except:
        pass
    return 1900, 2025

# Специальный патч для методов которые не используют select
# tmdb_fixes.py - Добавьте этот код в launch_tmdb_fixed.py ПЕРЕД строкой "import main_gui3"

# 1. ИСПРАВЛЕНИЕ ПРОБЛЕМЫ С ЖАНРАМИ
# Замените функцию patched_search_by_genre_and_years на эту:

def patched_search_by_genre_and_years(self, genre, start_year, end_year, offset=0, limit=10):
    """Исправленная версия поиска по жанрам - БЕЗ адаптера"""
    try:
        # Прямые SQL запросы к TMDB структуре
        with self.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # Считаем количество
                count_sql = """
                    SELECT COUNT(DISTINCT m.tmdb_id) as total
                    FROM movies m
                    JOIN movie_genres mg ON m.tmdb_id = mg.tmdb_id
                    JOIN genres g ON mg.genre_id = g.genre_id
                    WHERE g.name = %s 
                    AND YEAR(m.release_date) BETWEEN %s AND %s
                """
                cursor.execute(count_sql, (genre, start_year, end_year))
                total_count = cursor.fetchone()['total']
                
                # Получаем фильмы
                search_sql = """
                    SELECT DISTINCT
                        m.tmdb_id as film_id,
                        m.title,
                        YEAR(m.release_date) as release_year,
                        m.runtime as length,
                        m.vote_average,
                        m.overview as description,
                        GROUP_CONCAT(DISTINCT g2.name ORDER BY g2.name SEPARATOR ', ') as genres
                    FROM movies m
                    JOIN movie_genres mg ON m.tmdb_id = mg.tmdb_id
                    JOIN genres g ON mg.genre_id = g.genre_id
                    LEFT JOIN movie_genres mg2 ON m.tmdb_id = mg2.tmdb_id
                    LEFT JOIN genres g2 ON mg2.genre_id = g2.genre_id
                    WHERE g.name = %s 
                    AND YEAR(m.release_date) BETWEEN %s AND %s
                    GROUP BY m.tmdb_id, m.title, release_year, m.runtime, m.vote_average, m.overview
                    ORDER BY release_year DESC, m.title
                    LIMIT %s OFFSET %s
                """
                cursor.execute(search_sql, (genre, start_year, end_year, limit, offset))
                films = cursor.fetchall()
                
                # Конвертируем рейтинги
                for film in films:
                    vote_avg = film.pop('vote_average', None)
                    if vote_avg is None:
                        film['rating'] = 'NR'
                    elif vote_avg >= 8:
                        film['rating'] = 'G'
                    elif vote_avg >= 7:
                        film['rating'] = 'PG'
                    elif vote_avg >= 6:
                        film['rating'] = 'PG-13'
                    elif vote_avg >= 5:
                        film['rating'] = 'R'
                    else:
                        film['rating'] = 'NC-17'
                
                return films, total_count
                
    except Exception as e:
        print(f"❌ Ошибка в search_by_genre_and_years: {e}")
        return [], 0


# 2. ПРОВЕРКА TMDB API для постеров
# Добавьте эту функцию для тестирования API:

def test_tmdb_api():
    """Проверка работы TMDB API"""
    try:
        # Читаем настройки
        import json
        import os
        
        settings_file = os.path.join(os.path.expanduser("~"), ".sakila_cache", "settings.json")
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                api_key = settings.get('tmdb_api_key', '')
                
                if api_key:
                    print(f"✅ TMDB API ключ найден: {api_key[:8]}...")
                    
                    # Тестовый запрос
                    import requests
                    test_url = f"https://api.themoviedb.org/3/movie/550?api_key={api_key}"
                    response = requests.get(test_url, timeout=5)
                    
                    if response.status_code == 200:
                        print("✅ TMDB API работает!")
                        data = response.json()
                        if 'poster_path' in data:
                            print(f"✅ Постер найден: {data['poster_path']}")
                    else:
                        print(f"❌ TMDB API ошибка: {response.status_code}")
                else:
                    print("❌ TMDB API ключ не установлен!")
                    print("   Откройте Настройки в приложении и добавьте ключ")
                    print("   Получить ключ: https://www.themoviedb.org/settings/api")
        else:
            print("❌ Файл настроек не найден")
            print("   Откройте Настройки в приложении и добавьте TMDB API ключ")
            
    except Exception as e:
        print(f"❌ Ошибка проверки API: {e}")

# Вызываем проверку API
print("\n🔍 Проверка TMDB API для постеров...")
test_tmdb_api()

# 3. ПАТЧ ДЛЯ ИСПРАВЛЕНИЯ TMDB_API_KEY
# Добавьте после импорта main_gui3 но ПЕРЕД main_gui3.main():

def patch_tmdb_api():
    """Загружает TMDB API ключ из настроек"""
    try:
        import json
        import os
        
        settings_file = os.path.join(os.path.expanduser("~"), ".sakila_cache", "settings.json")
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                api_key = settings.get('tmdb_api_key', '')
                
                if api_key and hasattr(main_gui3, 'TMDB_API_KEY'):
                    main_gui3.TMDB_API_KEY = api_key
                    print(f"✅ TMDB API ключ загружен в приложение")
                    
                    # Также обновляем глобальную переменную если она есть
                    if 'TMDB_API_KEY' in dir(main_gui3):
                        setattr(main_gui3, 'TMDB_API_KEY', api_key)
    except Exception as e:
        print(f"⚠️  Не удалось загрузить API ключ: {e}")

# Применяем патч для search_by_genre_and_years
MySQLConnector.search_by_genre_and_years = patched_search_by_genre_and_years

# ВАЖНО: Добавьте эти строки в самый конец файла launch_tmdb_fixed.py
# ПОСЛЕ строки "import main_gui3" но ПЕРЕД "main_gui3.main()":
#
# patch_tmdb_api()
# main_gui3.main()

# Применяем все патчи
MySQLConnector.__init__ = patched_init
MySQLConnector.select = patched_select
MySQLConnector.test_connection = patched_test
MySQLConnector.get_available_genres = patched_get_genres
MySQLConnector.get_year_range = patched_get_years
MySQLConnector.search_by_genre_and_years = patched_search_by_genre_and_years

print("✅ TMDB адаптер v2 установлен")
print("🚀 Запускаем приложение...\n")

try:
    import main_gui3
    main_gui3.main()
except Exception as e:
    print(f"\n❌ Критическая ошибка: {e}")
    import traceback
    traceback.print_exc()
    input("\nНажмите Enter для выхода...")