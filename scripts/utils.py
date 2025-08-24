# utils.py - Вспомогательные утилиты
import re
from typing import Optional, Tuple


def validate_year_input(year_input: str) -> bool:
    """Валидация ввода года или диапазона лет"""
    if not year_input:
        return False
    
    # Проверяем формат: год или год-год
    pattern = r'^\d{4}(-\d{4})?$'
    return bool(re.match(pattern, year_input))


def parse_year_range(year_input: str) -> Optional[Tuple[int, int]]:
    """
    Парсинг диапазона годов
    
    Args:
        year_input: Строка с годом или диапазоном (например: "2005" или "2005-2010")
        
    Returns:
        Optional[Tuple[int, int]]: (начальный_год, конечный_год) или None при ошибке
    """
    try:
        if '-' in year_input:
            start_year, end_year = map(int, year_input.split('-'))
            if start_year > end_year:
                start_year, end_year = end_year, start_year  # Меняем местами
        else:
            start_year = end_year = int(year_input)
        
        return start_year, end_year
    except ValueError:
        return None


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Обрезание текста до максимальной длины
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста
        
    Returns:
        str: Обрезанный текст
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_duration(minutes: Optional[int]) -> str:
    """
    Форматирование продолжительности фильма
    
    Args:
        minutes: Продолжительность в минутах
        
    Returns:
        str: Форматированная строка (например: "2ч 30м" или "90м")
    """
    if not minutes:
        return "N/A"
    
    if minutes >= 60:
        hours = minutes // 60
        mins = minutes % 60
        if mins:
            return f"{hours}ч {mins}м"
        else:
            return f"{hours}ч"
    else:
        return f"{minutes}м"


def sanitize_search_input(query: str) -> str:
    """
    Очистка поискового запроса от потенциально опасных символов
    
    Args:
        query: Поисковый запрос
        
    Returns:
        str: Очищенный запрос
    """
    if not query:
        return ""
    
    # Удаляем потенциально опасные символы для SQL
    dangerous_chars = [';', '--', '/*', '*/', 'xp_', 'sp_']
    
    cleaned = query.strip()
    for char in dangerous_chars:
        cleaned = cleaned.replace(char, '')
    
    return cleaned[:100]  # Ограничиваем длину