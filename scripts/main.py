# main.py - Точка входа в приложение
import sys
import logging
from typing import Optional

from mysql_connector import MySQLConnector
from log_writer import LogWriter
from log_stats import LogStats
from formatter import Formatter


class MovieSearchApp:
    """Основное приложение для поиска фильмов"""
    
    def __init__(self):
        self.setup_logging()
        self.mysql_conn = MySQLConnector()
        self.log_writer = LogWriter()
        self.log_stats = LogStats()
        self.formatter = Formatter()
        
    def setup_logging(self):
        """Настройка системы логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('app.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def show_menu(self):
        """Отображение главного меню"""
        menu = """
╔══════════════════════════════════════════════════════════════╗
║                    ПОИСК ФИЛЬМОВ - SAKILA                   ║
╚══════════════════════════════════════════════════════════════╝

1. 🔍 Поиск по ключевому слову
2. 🎬 Поиск по жанру и годам
3. 📊 Популярные запросы
4. 🕒 Последние запросы
5. 🚪 Выход

Выберите действие (1-5): """
        return input(menu).strip()
    
    def search_by_keyword(self):
        """Поиск фильмов по ключевому слову"""
        try:
            keyword = input("\n🔍 Введите ключевое слово для поиска: ").strip()
            if not keyword:
                print("❌ Ключевое слово не может быть пустым!")
                return
            
            page = 0
            while True:
                offset = page * 10
                films, total_count = self.mysql_conn.search_by_keyword(keyword, offset)
                
                if not films and page == 0:
                    print(f"❌ Фильмы с ключевым словом '{keyword}' не найдены.")
                    # Логируем даже пустые результаты
                    self.log_writer.log_search("keyword", {"keyword": keyword}, 0)
                    return
                
                if not films:
                    print("\n📋 Больше результатов нет.")
                    break
                
                # Первый раз логируем запрос
                if page == 0:
                    self.log_writer.log_search("keyword", {"keyword": keyword}, total_count)
                
                # Отображаем результаты
                print(f"\n📽️  Результаты поиска '{keyword}' (показано {offset + 1}-{offset + len(films)} из {total_count}):")
                print(self.formatter.format_films_table(films))
                
                # Спрашиваем о продолжении
                if len(films) == 10:  # Есть потенциально еще результаты
                    choice = input("\n➡️  Показать следующие 10 результатов? (y/n): ").lower()
                    if choice != 'y':
                        break
                    page += 1
                else:
                    break
                    
        except Exception as e:
            self.logger.error(f"Ошибка при поиске по ключевому слову: {e}")
            print("❌ Произошла ошибка при поиске. Попробуйте еще раз.")
    
    def search_by_genre_and_years(self):
        """Поиск фильмов по жанру и диапазону годов"""
        try:
            # Получаем доступные жанры и диапазон годов
            genres = self.mysql_conn.get_available_genres()
            year_range = self.mysql_conn.get_year_range()
            
            if not genres:
                print("❌ Не удалось получить список жанров.")
                return
            
            # Показываем доступные жанры
            print("\n🎭 Доступные жанры:")
            print(self.formatter.format_genres_list(genres))
            
            # Показываем диапазон годов
            min_year, max_year = year_range
            print(f"\n📅 Диапазон годов в базе: {min_year} - {max_year}")
            
            # Запрашиваем жанр
            genre = input(f"\n🎬 Введите жанр из списка: ").strip()
            if genre not in [g['name'] for g in genres]:
                print("❌ Выбран недоступный жанр!")
                return
            
            # Запрашиваем годы
            year_input = input(f"📅 Введите год или диапазон (например: 2005 или 2005-2010): ").strip()
            
            try:
                if '-' in year_input:
                    start_year, end_year = map(int, year_input.split('-'))
                else:
                    start_year = end_year = int(year_input)
                
                if not (min_year <= start_year <= max_year and min_year <= end_year <= max_year):
                    print(f"❌ Годы должны быть в диапазоне {min_year}-{max_year}!")
                    return
                    
            except ValueError:
                print("❌ Неверный формат года!")
                return
            
            # Выполняем поиск с пагинацией
            page = 0
            search_params = {
                "genre": genre,
                "start_year": start_year,
                "end_year": end_year
            }
            
            while True:
                offset = page * 10
                films, total_count = self.mysql_conn.search_by_genre_and_years(
                    genre, start_year, end_year, offset
                )
                
                if not films and page == 0:
                    print(f"❌ Фильмы жанра '{genre}' за {start_year}-{end_year} не найдены.")
                    self.log_writer.log_search("genre_year", search_params, 0)
                    return
                
                if not films:
                    print("\n📋 Больше результатов нет.")
                    break
                
                # Первый раз логируем запрос
                if page == 0:
                    self.log_writer.log_search("genre_year", search_params, total_count)
                
                # Отображаем результаты
                year_str = f"{start_year}-{end_year}" if start_year != end_year else str(start_year)
                print(f"\n🎬 Фильмы жанра '{genre}' за {year_str} (показано {offset + 1}-{offset + len(films)} из {total_count}):")
                print(self.formatter.format_films_table(films))
                
                # Спрашиваем о продолжении
                if len(films) == 10:
                    choice = input("\n➡️  Показать следующие 10 результатов? (y/n): ").lower()
                    if choice != 'y':
                        break
                    page += 1
                else:
                    break
                    
        except Exception as e:
            self.logger.error(f"Ошибка при поиске по жанру и годам: {e}")
            print("❌ Произошла ошибка при поиске. Попробуйте еще раз.")
    
    def show_popular_searches(self):
        """Показать популярные запросы"""
        try:
            popular = self.log_stats.get_popular_searches(5)
            if not popular:
                print("\n📊 Популярных запросов пока нет.")
                return
            
            print("\n📊 ТОП-5 популярных запросов:")
            print(self.formatter.format_popular_searches(popular))
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении популярных запросов: {e}")
            print("❌ Не удалось получить статистику популярных запросов.")
    
    def show_recent_searches(self):
        """Показать последние запросы"""
        try:
            recent = self.log_stats.get_recent_searches(5)
            if not recent:
                print("\n🕒 Последних запросов пока нет.")
                return
            
            print("\n🕒 Последние 5 уникальных запросов:")
            print(self.formatter.format_recent_searches(recent))
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении последних запросов: {e}")
            print("❌ Не удалось получить статистику последних запросов.")
    
    def run(self):
        """Основной цикл приложения"""
        print("🎬 Добро пожаловать в систему поиска фильмов Sakila!")
        
        # Проверяем подключения при запуске
        if not self.mysql_conn.test_connection():
            print("❌ Не удалось подключиться к MySQL. Проверьте настройки подключения.")
            return
        
        if not self.log_writer.test_connection():
            print("❌ Не удалось подключиться к MongoDB. Проверьте настройки подключения.")
            return
        
        print("✅ Подключения к базам данных установлены успешно!")
        
        while True:
            try:
                choice = self.show_menu()
                
                if choice == '1':
                    self.search_by_keyword()
                elif choice == '2':
                    self.search_by_genre_and_years()
                elif choice == '3':
                    self.show_popular_searches()
                elif choice == '4':
                    self.show_recent_searches()
                elif choice == '5':
                    print("\n👋 До свидания!")
                    break
                else:
                    print("❌ Неверный выбор. Попробуйте еще раз.")
                
                # Пауза между действиями
                input("\n⏸️  Нажмите Enter для продолжения...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Программа прервана пользователем. До свидания!")
                break
            except Exception as e:
                self.logger.error(f"Неожиданная ошибка в главном цикле: {e}")
                print("❌ Произошла неожиданная ошибка. Попробуйте еще раз.")


if __name__ == "__main__":
    app = MovieSearchApp()
    app.run()