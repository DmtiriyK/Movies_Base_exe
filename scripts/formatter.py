# formatter.py - Форматирование вывода данных
from typing import List, Dict, Any
from datetime import datetime
from tabulate import tabulate
import textwrap
from colorama import init, Fore, Back, Style

# Инициализация colorama для цветного вывода в консоли
init(autoreset=True)


class Formatter:
    """Класс для форматирования вывода данных"""
    
    def __init__(self):
        self.max_width = 120  # Максимальная ширина вывода
        self.description_width = 50  # Ширина колонки описания
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Обрезка текста с добавлением многоточия"""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def _wrap_text(self, text: str, width: int) -> str:
        """Перенос длинного текста"""
        if not text:
            return ""
        return '\n'.join(textwrap.wrap(text, width))
    
    def _colorize_rating(self, rating: str) -> str:
        """Цветовая маркировка рейтинга"""
        rating_colors = {
            'G': Fore.GREEN,
            'PG': Fore.CYAN,
            'PG-13': Fore.YELLOW,
            'R': Fore.MAGENTA,
            'NC-17': Fore.RED
        }
        color = rating_colors.get(rating, Fore.WHITE)
        return f"{color}{rating}{Style.RESET_ALL}"
    
    def _colorize_year(self, year: int) -> str:
        """Цветовая маркировка года"""
        if year >= 2010:
            return f"{Fore.GREEN}{year}{Style.RESET_ALL}"
        elif year >= 2000:
            return f"{Fore.YELLOW}{year}{Style.RESET_ALL}"
        else:
            return f"{Fore.CYAN}{year}{Style.RESET_ALL}"
    
    def format_films_table(self, films: List[Dict]) -> str:
        """Форматирование списка фильмов в виде красивой таблицы"""
        if not films:
            return "Нет данных для отображения"
        
        # Подготовка данных для таблицы
        table_data = []
        for i, film in enumerate(films, 1):
            # Форматируем каждую строку
            row = [
                f"{Fore.CYAN}{i}{Style.RESET_ALL}",
                f"{Fore.WHITE}{self._truncate_text(film.get('title', 'N/A'), 30)}{Style.RESET_ALL}",
                self._colorize_year(film.get('release_year', 0)),
                self._colorize_rating(film.get('rating', 'N/A')),
                f"{film.get('length', 0)} мин",
                self._truncate_text(film.get('genres', 'N/A'), 30),
                self._truncate_text(film.get('description', 'N/A'), 50)
            ]
            table_data.append(row)
        
        # Заголовки таблицы с цветом
        headers = [
            f"{Fore.YELLOW}#{Style.RESET_ALL}",
            f"{Fore.YELLOW}Название{Style.RESET_ALL}",
            f"{Fore.YELLOW}Год{Style.RESET_ALL}",
            f"{Fore.YELLOW}Рейтинг{Style.RESET_ALL}",
            f"{Fore.YELLOW}Длительность{Style.RESET_ALL}",
            f"{Fore.YELLOW}Жанры{Style.RESET_ALL}",
            f"{Fore.YELLOW}Описание{Style.RESET_ALL}"
        ]
        
        # Создание таблицы
        table = tabulate(
            table_data,
            headers=headers,
            tablefmt="fancy_grid",
            numalign="left",
            stralign="left"
        )
        
        return table
    
    def format_films_cards(self, films: List[Dict]) -> str:
        """Форматирование фильмов в виде карточек"""
        if not films:
            return "Нет данных для отображения"
        
        cards = []
        for i, film in enumerate(films, 1):
            card = f"""
{Fore.CYAN}{'='*60}{Style.RESET_ALL}
{Fore.YELLOW}#{i}{Style.RESET_ALL} {Fore.WHITE}{Style.BRIGHT}{film.get('title', 'N/A')}{Style.RESET_ALL}
{Fore.CYAN}{'─'*60}{Style.RESET_ALL}
📅 Год: {self._colorize_year(film.get('release_year', 0))}
⭐ Рейтинг: {self._colorize_rating(film.get('rating', 'N/A'))}
⏱️  Длительность: {film.get('length', 0)} мин
🎭 Жанры: {film.get('genres', 'N/A')}

📝 Описание:
{self._wrap_text(film.get('description', 'Описание отсутствует'), 58)}
{Fore.CYAN}{'='*60}{Style.RESET_ALL}"""
            cards.append(card)
        
        return '\n'.join(cards)
    
    def format_genres_list(self, genres: List[Dict]) -> str:
        """Форматирование списка жанров"""
        if not genres:
            return "Нет данных о жанрах"
        
        # Сортируем по количеству фильмов
        sorted_genres = sorted(genres, key=lambda x: x['film_count'], reverse=True)
        
        # Подготовка данных для таблицы
        table_data = []
        for i, genre in enumerate(sorted_genres, 1):
            # Цветовая маркировка по популярности
            count = genre['film_count']
            if count >= 60:
                count_str = f"{Fore.GREEN}{count}{Style.RESET_ALL}"
            elif count >= 40:
                count_str = f"{Fore.YELLOW}{count}{Style.RESET_ALL}"
            else:
                count_str = f"{Fore.CYAN}{count}{Style.RESET_ALL}"
            
            # Визуальная шкала популярности
            bar_length = min(30, count // 2)
            bar = f"{Fore.GREEN}{'█' * bar_length}{Style.RESET_ALL}"
            
            row = [
                f"{Fore.CYAN}{i}{Style.RESET_ALL}",
                f"{Fore.WHITE}{genre['name']}{Style.RESET_ALL}",
                count_str,
                bar
            ]
            table_data.append(row)
        
        headers = [
            f"{Fore.YELLOW}#{Style.RESET_ALL}",
            f"{Fore.YELLOW}Жанр{Style.RESET_ALL}",
            f"{Fore.YELLOW}Фильмов{Style.RESET_ALL}",
            f"{Fore.YELLOW}Популярность{Style.RESET_ALL}"
        ]
        
        table = tabulate(
            table_data,
            headers=headers,
            tablefmt="rounded_outline",
            numalign="left",
            stralign="left"
        )
        
        # Добавляем статистику
        total_films = sum(g['film_count'] for g in genres)
        avg_films = total_films // len(genres) if genres else 0
        
        stats = f"""
{Fore.CYAN}{'─'*60}{Style.RESET_ALL}
📊 Статистика:
  • Всего жанров: {Fore.GREEN}{len(genres)}{Style.RESET_ALL}
  • Всего фильмов: {Fore.GREEN}{total_films}{Style.RESET_ALL}
  • В среднем фильмов на жанр: {Fore.YELLOW}{avg_films}{Style.RESET_ALL}
{Fore.CYAN}{'─'*60}{Style.RESET_ALL}"""
        
        return table + stats
    
    def format_popular_searches(self, searches: List[Dict]) -> str:
        """Форматирование популярных запросов"""
        if not searches:
            return "Нет данных о популярных запросах"
        
        table_data = []
        max_count = max(s.get('count', 0) for s in searches) if searches else 1
        
        for i, search in enumerate(searches, 1):
            # Форматирование параметров
            params = search.get('params', {})
            if isinstance(params, dict):
                if 'keyword' in params:
                    param_str = f"🔍 {params['keyword']}"
                elif 'genre' in params:
                    param_str = f"🎬 {params['genre']} ({params.get('start_year', '?')}-{params.get('end_year', '?')})"
                else:
                    param_str = str(params)
            else:
                param_str = str(params)
            
            # Визуальная шкала популярности
            count = search.get('count', 0)
            bar_length = int((count / max_count) * 30) if max_count > 0 else 0
            bar = f"{Fore.RED}{'█' * bar_length}{Style.RESET_ALL}"
            
            # Цветовая маркировка по популярности
            if i <= 3:
                rank = f"{Fore.YELLOW}🏆 {i}{Style.RESET_ALL}"
            else:
                rank = f"{Fore.CYAN}{i}{Style.RESET_ALL}"
            
            row = [
                rank,
                search.get('search_type', 'N/A'),
                param_str,
                f"{Fore.GREEN}{count}{Style.RESET_ALL}",
                bar
            ]
            table_data.append(row)
        
        headers = [
            f"{Fore.YELLOW}Место{Style.RESET_ALL}",
            f"{Fore.YELLOW}Тип{Style.RESET_ALL}",
            f"{Fore.YELLOW}Запрос{Style.RESET_ALL}",
            f"{Fore.YELLOW}Повторов{Style.RESET_ALL}",
            f"{Fore.YELLOW}График{Style.RESET_ALL}"
        ]
        
        table = tabulate(
            table_data,
            headers=headers,
            tablefmt="rounded_outline",
            numalign="left",
            stralign="left"
        )
        
        return f"\n{Fore.RED}🔥 ТОП ЗАПРОСОВ 🔥{Style.RESET_ALL}\n{table}"
    
    def format_recent_searches(self, searches: List[Dict]) -> str:
        """Форматирование последних запросов"""
        if not searches:
            return "Нет данных о последних запросах"
        
        table_data = []
        
        for i, search in enumerate(searches, 1):
            # Форматирование времени
            timestamp = search.get('timestamp', '')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%d.%m.%Y %H:%M:%S')
                    # Цветовая маркировка по свежести
                    time_diff = (datetime.now() - dt.replace(tzinfo=None)).total_seconds()
                    if time_diff < 3600:  # Менее часа назад
                        time_str = f"{Fore.GREEN}{time_str} 🆕{Style.RESET_ALL}"
                    elif time_diff < 86400:  # Менее дня назад
                        time_str = f"{Fore.YELLOW}{time_str}{Style.RESET_ALL}"
                    else:
                        time_str = f"{Fore.CYAN}{time_str}{Style.RESET_ALL}"
                except:
                    time_str = timestamp
            else:
                time_str = "N/A"
            
            # Форматирование параметров
            params = search.get('params', {})
            if isinstance(params, dict):
                if 'keyword' in params:
                    param_str = f"🔍 {params['keyword']}"
                elif 'genre' in params:
                    param_str = f"🎬 {params['genre']} ({params.get('start_year', '?')}-{params.get('end_year', '?')})"
                else:
                    param_str = str(params)
            else:
                param_str = str(params)
            
            # Индикатор результатов
            results = search.get('results_count', 0)
            if results == 0:
                results_str = f"{Fore.RED}0 ❌{Style.RESET_ALL}"
            elif results < 10:
                results_str = f"{Fore.YELLOW}{results}{Style.RESET_ALL}"
            else:
                results_str = f"{Fore.GREEN}{results} ✅{Style.RESET_ALL}"
            
            row = [
                f"{Fore.CYAN}{i}{Style.RESET_ALL}",
                time_str,
                search.get('search_type', 'N/A'),
                param_str,
                results_str
            ]
            table_data.append(row)
        
        headers = [
            f"{Fore.YELLOW}#{Style.RESET_ALL}",
            f"{Fore.YELLOW}Время{Style.RESET_ALL}",
            f"{Fore.YELLOW}Тип{Style.RESET_ALL}",
            f"{Fore.YELLOW}Запрос{Style.RESET_ALL}",
            f"{Fore.YELLOW}Результатов{Style.RESET_ALL}"
        ]
        
        table = tabulate(
            table_data,
            headers=headers,
            tablefmt="rounded_outline",
            numalign="left",
            stralign="left"
        )
        
        return f"\n{Fore.CYAN}🕒 ПОСЛЕДНИЕ ЗАПРОСЫ 🕒{Style.RESET_ALL}\n{table}"
    
    def format_welcome_banner(self) -> str:
        """Красивый баннер приветствия"""
        banner = f"""
{Fore.CYAN}{'═'*70}{Style.RESET_ALL}
{Fore.YELLOW}{Style.BRIGHT}
   ███████╗ █████╗ ██╗  ██╗██╗██╗      █████╗ 
   ██╔════╝██╔══██╗██║ ██╔╝██║██║     ██╔══██╗
   ███████╗███████║█████╔╝ ██║██║     ███████║
   ╚════██║██╔══██║██╔═██╗ ██║██║     ██╔══██║
   ███████║██║  ██║██║  ██╗██║███████╗██║  ██║
   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝
{Style.RESET_ALL}
           {Fore.WHITE}🎬 MOVIE DATABASE SEARCH SYSTEM 🎬{Style.RESET_ALL}
                {Fore.CYAN}Powered by MySQL & MongoDB{Style.RESET_ALL}
{Fore.CYAN}{'═'*70}{Style.RESET_ALL}
"""
        return banner
    
    def format_statistics_dashboard(self, stats: Dict[str, Any]) -> str:
        """Форматирование дашборда со статистикой"""
        dashboard = f"""
{Fore.CYAN}{'═'*70}{Style.RESET_ALL}
{Fore.YELLOW}{Style.BRIGHT}📊 СТАТИСТИКА СИСТЕМЫ{Style.RESET_ALL}
{Fore.CYAN}{'─'*70}{Style.RESET_ALL}

{Fore.GREEN}База данных:{Style.RESET_ALL}
  • Всего фильмов: {Fore.WHITE}{stats.get('total_films', 0)}{Style.RESET_ALL}
  • Всего жанров: {Fore.WHITE}{stats.get('total_genres', 0)}{Style.RESET_ALL}
  • Диапазон годов: {Fore.WHITE}{stats.get('year_range', 'N/A')}{Style.RESET_ALL}

{Fore.YELLOW}Поисковая активность:{Style.RESET_ALL}
  • Всего запросов: {Fore.WHITE}{stats.get('total_searches', 0)}{Style.RESET_ALL}
  • Уникальных запросов: {Fore.WHITE}{stats.get('unique_searches', 0)}{Style.RESET_ALL}
  • Средний результат: {Fore.WHITE}{stats.get('avg_results', 0):.1f} фильмов{Style.RESET_ALL}

{Fore.MAGENTA}Популярные тренды:{Style.RESET_ALL}
  • Топ жанр: {Fore.WHITE}{stats.get('top_genre', 'N/A')}{Style.RESET_ALL}
  • Топ ключевое слово: {Fore.WHITE}{stats.get('top_keyword', 'N/A')}{Style.RESET_ALL}
  • Пиковое время: {Fore.WHITE}{stats.get('peak_time', 'N/A')}{Style.RESET_ALL}

{Fore.CYAN}{'═'*70}{Style.RESET_ALL}
"""
        return dashboard