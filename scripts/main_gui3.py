# main_gui3.py – Sakila Desktop v3 (Максимальный функционал)
import sys, os, csv, webbrowser, json, ctypes, importlib, requests, hashlib
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from functools import lru_cache
import pickle

# --- Хак для PyInstaller ---
if getattr(sys, "frozen", False):
    import pandas as _pandas
    import matplotlib as _matplotlib
    import numpy as _numpy

# Ленивый импорт для быстрого старта
def pd(): return importlib.import_module("pandas")
def plt(): return importlib.import_module("matplotlib.pyplot")
def np(): return importlib.import_module("numpy")

from PyQt6.QtCore import (Qt, QAbstractTableModel, QModelIndex, QTimer, QSize, 
                         QSettings, QThread, pyqtSignal, QPropertyAnimation, 
                         QEasingCurve, QPoint, QRect)
from PyQt6.QtGui import (QAction, QIcon, QPalette, QColor, QFont, QPixmap, 
                        QMovie, QPainter, QBrush, QPen, QKeySequence)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableView, QMessageBox, QFileDialog, 
    QSpinBox, QComboBox, QGroupBox, QFormLayout, QDialog, QTextEdit, QFrame, 
    QMenu, QCheckBox, QSlider, QProgressBar, QListWidget, QSplitter,
    QGraphicsOpacityEffect, QCompleter, QGridLayout, QButtonGroup, QRadioButton
)

# Matplotlib backend
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# твои модули
from mysql_connector import MySQLConnector
from log_writer import LogWriter
from log_stats import LogStats

APP_ID = "com.ich.sakila.desktop.v3"
APP_BUILD = "v3.0"
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".sakila_cache")
FAVORITES_FILE = os.path.join(CACHE_DIR, "favorites.json")
SETTINGS_FILE = os.path.join(CACHE_DIR, "settings.json")
CACHE_FILE = os.path.join(CACHE_DIR, "search_cache.pkl")

# TMDB API (опционально - если есть ключ)
TMDB_API_KEY = ""  # Можно задать в настройках
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w200"

# ---------- Утилиты ----------
def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)

def set_app_id(app_id=APP_ID):
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

def base_dir():
    return getattr(sys, "_MEIPASS", os.path.dirname(__file__))

def res_path(name: str) -> str:
    return os.path.join(base_dir(), name)

def save_df_to_csv(parent, df, default_name="data.csv"):
    if df is None or df.empty:
        parent_notify = getattr(parent, "notify", None)
        if callable(parent_notify):
            parent_notify("No data for export")
        else:
            QMessageBox.information(parent, "Export", "No data for export.")
        return
    path, _ = QFileDialog.getSaveFileName(parent, "Save CSV", default_name, "CSV Files (*.csv)")
    if not path:
        return
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)
    if callable(parent_notify := getattr(parent, "notify", None)):
        parent_notify("File сохранён")

def save_df_to_excel(parent, df, default_name="data.xlsx"):
    """Export в Excel с форматированием"""
    if df is None or df.empty:
        QMessageBox.information(parent, "Export", "No data for export.")
        return
    path, _ = QFileDialog.getSaveFileName(parent, "Save Excel", default_name, "Excel Files (*.xlsx)")
    if not path:
        return
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        
        with pd().ExcelWriter(path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Films')
            worksheet = writer.sheets['Films']
            
            # Форматирование заголовков
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            
            # Автоширина колонок
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        if callable(notify := getattr(parent, "notify", None)):
            notify("Excel file saved")
    except ImportError:
        QMessageBox.warning(parent, "Error", "Install openpyxl for export in Excel:\npip install openpyxl")
    except Exception as e:
        QMessageBox.critical(parent, "Error", f"Error экспорта: {str(e)}")

def set_dark_palette(app: QApplication):
    app.setStyle("Fusion")
    palette = QPalette()
    bg = QColor(15,17,22)
    bg2 = QColor(22,26,35)
    text = QColor(230,230,230)
    acc = QColor(124,92,252)
    palette.setColor(QPalette.ColorRole.Window, bg)
    palette.setColor(QPalette.ColorRole.Base, bg2)
    palette.setColor(QPalette.ColorRole.AlternateBase, bg)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.Button, bg2)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.Highlight, acc)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255,255,255))
    app.setPalette(palette)
    app.setStyleSheet("""
    QMainWindow { background: #0f1116; }
    QFrame#banner { 
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7C5CFC, stop:1 #B794F4);
        border-radius: 10px; 
    }
    QLabel#title { color: white; font-weight: 800; letter-spacing: .2px; }
    QGroupBox { 
        border:1px solid #2b2f3a; 
        border-radius: 10px; 
        margin-top: 12px; 
        padding-top: 10px;
    }
    QGroupBox::title { 
        subcontrol-origin: margin; 
        left: 10px; 
        padding: 0 4px; 
        color: #9aa4ad; 
    }
    QTableView { 
        border:1px solid #2b2f3a; 
        border-radius: 10px; 
        gridline-color: #333; 
        alternate-background-color: #1a1d25;
    }
    QHeaderView::section { 
        background:#1b1f2a; 
        color:#e6e6e6; 
        padding:6px; 
        border:none; 
        font-weight: bold;
    }
    QPushButton {
        background: #7C5CFC; 
        border: none; 
        color: white; 
        padding: 8px 14px;
        border-radius: 10px; 
        font-weight: 700;
    }
    QPushButton:hover { 
        background: #8D6DFF; 
    }
    QPushButton:pressed { 
        background: #6B4BEB; 
    }
    QPushButton:disabled { 
        background: #4a4a4a; 
        color: #888; 
    }
    QLineEdit, QComboBox, QSpinBox { 
        border:1px solid #2b2f3a; 
        border-radius: 8px; 
        padding:6px; 
        background:#161a23; 
        color:#e6e6e6; 
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus { 
        border-color: #7C5CFC; 
    }
    QProgressBar {
        border: 1px solid #2b2f3a;
        border-radius: 10px;
        text-align: center;
        background: #161a23;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7C5CFC, stop:1 #B794F4);
        border-radius: 9px;
    }
    QTabWidget::pane {
        border: 1px solid #2b2f3a;
        border-radius: 10px;
        margin-top: -1px;
    }
    QTabBar::tab {
        background: #1b1f2a;
        color: #888;
        padding: 8px 16px;
        margin-right: 4px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
    }
    QTabBar::tab:selected {
        background: #7C5CFC;
        color: white;
    }
    QTabBar::tab:hover {
        background: #2b2f3a;
        color: #ddd;
    }
    QMenu {
        background: #1b1f2a;
        border: 1px solid #2b2f3a;
        border-radius: 8px;
        padding: 4px;
    }
    QMenu::item {
        padding: 8px 20px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background: #7C5CFC;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid #2b2f3a;
        background: #161a23;
    }
    QCheckBox::indicator:checked {
        background: #7C5CFC;
        image: url(check.png);
    }
    """)

# ---------- Кеш для поиска ----------
class SearchCache:
    def __init__(self, max_size=100):
        self.max_size = max_size
        self.cache = {}
        self.load()
    
    def get(self, key: str) -> Optional[Any]:
        return self.cache.get(key)
    
    def set(self, key: str, value: Any):
        if len(self.cache) >= self.max_size:
            # Удаляем старые записи
            oldest = sorted(self.cache.keys())[:10]
            for k in oldest:
                del self.cache[k]
        self.cache[key] = value
        self.save()
    
    def save(self):
        try:
            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(self.cache, f)
        except Exception:
            pass
    
    def load(self):
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'rb') as f:
                    self.cache = pickle.load(f)
        except Exception:
            self.cache = {}

# ---------- Загрузчик постеров ----------
class PosterLoader(QThread):
    posterLoaded = pyqtSignal(int, QPixmap)
    
    def __init__(self):
        super().__init__()
        self.queue = []
        self.running = True
    
    def add_request(self, film_id: int, title: str, year: Optional[int]):
        self.queue.append((film_id, title, year))
    
    def run(self):
        while self.running:
            if self.queue:
                film_id, title, year = self.queue.pop(0)
                pixmap = self.load_poster(title, year)
                if pixmap:
                    self.posterLoaded.emit(film_id, pixmap)
            else:
                self.msleep(100)
    
    @lru_cache(maxsize=200)
    def load_poster(self, title: str, year: Optional[int]) -> Optional[QPixmap]:
        if not TMDB_API_KEY:
            return None
        try:
            # Search фильма
            search_url = f"{TMDB_BASE_URL}/search/movie"
            params = {
                'api_key': TMDB_API_KEY,
                'query': title,
                'year': year if year else ''
            }
            resp = requests.get(search_url, params=params, timeout=5)
            data = resp.json()
            
            if data.get('results'):
                poster_path = data['results'][0].get('poster_path')
                if poster_path:
                    img_url = f"{TMDB_IMG_BASE}{poster_path}"
                    img_resp = requests.get(img_url, timeout=5)
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_resp.content)
                    return pixmap.scaled(100, 150, Qt.AspectRatioMode.KeepAspectRatio, 
                                       Qt.TransformationMode.SmoothTransformation)
        except Exception:
            pass
        return None
    
    def stop(self):
        self.running = False

# ---------- Анимированная кнопка ----------
class AnimatedButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(100)
        self.animation.setEasingCurve(QEasingCurve.Type.OutElastic)
    
    def enterEvent(self, event):
        rect = self.geometry()
        self.animation.setStartValue(rect)
        self.animation.setEndValue(rect.adjusted(-2, -2, 2, 2))
        self.animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        rect = self.geometry()
        self.animation.setStartValue(rect)
        self.animation.setEndValue(rect.adjusted(2, 2, -2, -2))
        self.animation.start()
        super().leaveEvent(event)

# ---------- Модель для DataFrame с постерами ----------
class DataFrameModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self.set_dataframe(df if df is not None else pd().DataFrame())
        self.posters = {}  # film_id -> QPixmap
        
    def set_dataframe(self, df):
        self.beginResetModel()
        self._df = df.copy()
        self.endResetModel()
    
    def add_poster(self, film_id: int, pixmap: QPixmap):
        self.posters[film_id] = pixmap
        # Обновляем только строку с этим film_id
        if 'film_id' in self._df.columns:
            rows = self._df[self._df['film_id'] == film_id].index.tolist()
            for row in rows:
                self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
    
    def rowCount(self, parent=QModelIndex()):
        return 0 if self._df is None else len(self._df)
    
    def columnCount(self, parent=QModelIndex()):
        return 0 if self._df is None else len(self._df.columns)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.ToolTipRole:
            val = self._df.iat[index.row(), index.column()]
            return "" if val is None else str(val)
        
        elif role == Qt.ItemDataRole.DecorationRole:
            # Показываем постер в первой колонке если есть
            if index.column() == 0 and 'film_id' in self._df.columns:
                film_id = self._df.iat[index.row(), self._df.columns.get_loc('film_id')]
                if film_id in self.posters:
                    return self.posters[film_id]
        
        return None
    
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section]) if self._df is not None else ""
        return str(section + 1)
    
    def dataframe(self):
        return self._df.copy()

# ---------- Карточка фильма с постером ----------
class FilmDialog(QDialog):
    def __init__(self, db: MySQLConnector, film_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.film_id = film_id
        self.setWindowTitle("Movie details")
        self.resize(860, 640)
        self.setMinimumSize(QSize(660, 520))
        
        main = QVBoxLayout(self)
        
        # Верхняя часть с постером
        top = QHBoxLayout()
        
        # Постер
        self.poster_label = QLabel()
        self.poster_label.setFixedSize(200, 300)
        self.poster_label.setStyleSheet("border: 1px solid #2b2f3a; border-radius: 10px;")
        self.poster_label.setScaledContents(True)
        self.poster_label.setText("🎬")
        self.poster_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self.poster_label)
        
        # Информация
        info_layout = QVBoxLayout()
        
        self.title_label = QLabel("Loading…")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        self.title_label.setFont(f)
        info_layout.addWidget(self.title_label)
        
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(self.info)
        
        # Rating пользователя
        rating_box = QGroupBox("Your rating")
        rating_layout = QHBoxLayout(rating_box)
        self.rating_slider = QSlider(Qt.Orientation.Horizontal)
        self.rating_slider.setRange(0, 10)
        self.rating_slider.setValue(0)
        self.rating_label = QLabel("Not rated")
        rating_layout.addWidget(self.rating_slider)
        rating_layout.addWidget(self.rating_label)
        self.rating_slider.valueChanged.connect(lambda v: self.rating_label.setText(f"{v}/10" if v > 0 else "Not rated"))
        info_layout.addWidget(rating_box)
        
        info_layout.addStretch()
        top.addLayout(info_layout, 1)
        
        main.addLayout(top)
        
        # Описание
        self.desc = QTextEdit()
        self.desc.setReadOnly(True)
        self.desc.setPlaceholderText("No description")
        main.addWidget(self.desc, 1)
        
        # Кнопки
        row = QHBoxLayout()
        self.btn_trailer = AnimatedButton("▶️ Trailer")
        self.btn_images  = AnimatedButton("🖼️ Images")
        self.btn_tmdb    = AnimatedButton("ℹ️ TMDB")
        self.btn_imdb    = AnimatedButton("ℹ️ IMDb")
        #self.btn_similar = AnimatedButton("🔍 Похожие")
        self.btn_copy    = AnimatedButton("📋 Copy")
        row.addWidget(self.btn_trailer)
        row.addWidget(self.btn_images)
        row.addWidget(self.btn_tmdb)
        row.addWidget(self.btn_imdb)
        #row.addWidget(self.btn_similar)
        row.addStretch(1)
        row.addWidget(self.btn_copy)
        main.addLayout(row)
        
        # Загружаем данные
        data = self._load_details()
        if data:
            self.title_label.setText(f"{data['title']} ({data.get('release_year','—')})")
            genres = data.get("genres") or "no genres"
            actors = data.get("actors") or "—"
            self.info.setText(
                f"⭐ Rating: <b>{data.get('rating','—')}</b>   ⏱️ Runtime: <b>{data.get('length','—')} min</b><br>"
                f"🎭 Genres: {genres}<br>"
                f"👥 Cast: {actors}"
            )
            self.desc.setText(data.get("description") or "—")
            
            # Загружаем постер
            self._load_poster(data['title'], data.get('release_year'))
            
            # Обработчики
            self.btn_trailer.clicked.connect(lambda: self._open_youtube_trailer(data["title"], data.get("release_year")))
            self.btn_images.clicked.connect(lambda: self._open_images(data["title"]))
            self.btn_copy.clicked.connect(lambda: self._copy_full(data))
            self.btn_tmdb.clicked.connect(lambda: self._open_tmdb(data["title"], data.get("release_year")))
            self.btn_imdb.clicked.connect(lambda: self._open_imdb(data["title"], data.get("release_year")))
            #self.btn_similar.clicked.connect(lambda: self._find_similar(data))
        else:
            self.title_label.setText("Failed to load movie details")
    
    def _load_details(self) -> Optional[Dict]:
        sql = """
            SELECT f.film_id, f.title, f.description, f.release_year, f.length, f.rating,
                   GROUP_CONCAT(DISTINCT c.name ORDER BY c.name SEPARATOR ', ') AS genres,
                   GROUP_CONCAT(DISTINCT CONCAT(a.first_name,' ',a.last_name) ORDER BY a.first_name SEPARATOR ', ') AS actors
            FROM film f
            LEFT JOIN film_category fc ON fc.film_id = f.film_id
            LEFT JOIN category c ON c.category_id = fc.category_id
            LEFT JOIN film_actor fa ON fa.film_id = f.film_id
            LEFT JOIN actor a ON a.actor_id = fa.actor_id
            WHERE f.film_id = %(fid)s
            GROUP BY f.film_id, f.title, f.description, f.release_year, f.length, f.rating
        """
        rows = self.db.select(sql, {"fid": self.film_id})
        return rows[0] if rows else None
    
    def _load_poster(self, title: str, year: Optional[int]):
        if TMDB_API_KEY:
            loader = PosterLoader()
            pixmap = loader.load_poster(title, year)
            if pixmap:
                self.poster_label.setPixmap(pixmap)
    
   
    
    def _open_youtube_trailer(self, title: str, year):
        from urllib.parse import quote_plus
        q = quote_plus(f"{title} trailer {year or ''}")
        webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
    
    def _open_images(self, title: str):
        from urllib.parse import quote_plus
        q = quote_plus(f"{title} movie stills")
        webbrowser.open(f"https://www.google.com/search?tbm=isch&q={q}")
    
    def _open_tmdb(self, title: str, year):
        from urllib.parse import quote_plus
        q = quote_plus(f"{title} {year or ''}")
        webbrowser.open(f"https://www.themoviedb.org/search?query={q}")
    
    def _open_imdb(self, title: str, year):
        from urllib.parse import quote_plus
        q = quote_plus(f"{title} {year or ''}")
        webbrowser.open(f"https://www.imdb.com/find/?q={q}&s=tt")
    
    def _copy_full(self, data: Dict):
        # Добавляем пользовательский рейтинг
        data['user_rating'] = self.rating_slider.value() if self.rating_slider.value() > 0 else None
        text = json.dumps(data, ensure_ascii=False, indent=2)
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Movie details have been copied to the clipboard.")

# ---------- Вкладка: Advanced search ----------
class AdvancedSearchTab(QWidget):
    def __init__(self, db, lw, favorites_sink, notify=lambda msg: None):
        super().__init__()
        self.db, self.lw = db, lw
        self.favorites_sink = favorites_sink
        self.notify = notify
        self.on_fav_changed = lambda: None
        self.cache = SearchCache()
        
        main = QVBoxLayout(self)
        
        # Группа фильтров
        filters_box = QGroupBox("Advanced filters")
        filters_layout = QGridLayout(filters_box)
        
        # Строка 1
        filters_layout.addWidget(QLabel("Title:"), 0, 0)
        self.ed_title = QLineEdit()
        self.ed_title.setPlaceholderText("Part of title...")
        filters_layout.addWidget(self.ed_title, 0, 1)
        
        filters_layout.addWidget(QLabel("Actor:"), 0, 2)
        self.ed_actor = QLineEdit()
        self.ed_actor.setPlaceholderText("First or last name...")
        filters_layout.addWidget(self.ed_actor, 0, 3)
        
        # Строка 2
        filters_layout.addWidget(QLabel("Genre:"), 1, 0)
        self.cb_genre = QComboBox()
        self.cb_genre.addItem("Any")
        try:
            genres = self.db.get_available_genres()
            for g in genres:
                self.cb_genre.addItem(g['name'])
        except:
            pass
        filters_layout.addWidget(self.cb_genre, 1, 1)
        
        filters_layout.addWidget(QLabel("Rating:"), 1, 2)
        self.cb_rating = QComboBox()
        self.cb_rating.addItems(["Any","G","PG","PG-13","R","NC-17"])
        filters_layout.addWidget(self.cb_rating, 1, 3)
        
        # Строка 3
        filters_layout.addWidget(QLabel("Year from:"), 2, 0)
        self.sb_year_from = QSpinBox()
        self.sb_year_from.setRange(1900, 2100)
        self.sb_year_from.setValue(1980)
        self.sb_year_from.setSpecialValueText("Any")
        filters_layout.addWidget(self.sb_year_from, 2, 1)
        
        filters_layout.addWidget(QLabel("Year to:"), 2, 2)
        self.sb_year_to = QSpinBox()
        self.sb_year_to.setRange(1900, 2100)
        self.sb_year_to.setValue(2025)
        self.sb_year_to.setSpecialValueText("Any")
        filters_layout.addWidget(self.sb_year_to, 2, 3)
        
        # Строка 4
        filters_layout.addWidget(QLabel("Runtime from (min):"), 3, 0)
        self.sb_length_from = QSpinBox()
        self.sb_length_from.setRange(0, 500)
        self.sb_length_from.setValue(0)
        self.sb_length_from.setSpecialValueText("Any")
        filters_layout.addWidget(self.sb_length_from, 3, 1)
        
        filters_layout.addWidget(QLabel("Runtime to (min):"), 3, 2)
        self.sb_length_to = QSpinBox()
        self.sb_length_to.setRange(0, 500)
        self.sb_length_to.setValue(500)
        self.sb_length_to.setSpecialValueText("Any")
        filters_layout.addWidget(self.sb_length_to, 3, 3)
        
        # Строка 5
        filters_layout.addWidget(QLabel("Sort by:"), 4, 0)
        self.cb_sort = QComboBox()
        self.cb_sort.addItems([
            "By year (new first)", "By year (old first)", 
            "By title (А-Я)", "By title (Я-А)",
            "By runtime (↑)", "By runtime (↓)",
            "By rating"
        ])
        filters_layout.addWidget(self.cb_sort, 4, 1)
        
        filters_layout.addWidget(QLabel("Limit:"), 4, 2)
        self.sb_limit = QSpinBox()
        self.sb_limit.setRange(1, 1000)
        self.sb_limit.setValue(100)
        filters_layout.addWidget(self.sb_limit, 4, 3)
        
        main.addWidget(filters_box)
        
        # Кнопки
        row = QHBoxLayout()
        self.btn_search = AnimatedButton("🔍 Search")
        self.btn_reset = AnimatedButton("🔄 Reset")
        self.btn_details = AnimatedButton("📋 Details")
        self.btn_add_fav = AnimatedButton("⭐ Add to favorites")
        self.btn_export_csv = AnimatedButton("📊 CSV")
        self.btn_export_excel = AnimatedButton("📊 Excel")
        
        row.addWidget(self.btn_search)
        row.addWidget(self.btn_reset)
        row.addStretch(1)
        row.addWidget(self.btn_details)
        row.addWidget(self.btn_add_fav)
        row.addWidget(self.btn_export_csv)
        row.addWidget(self.btn_export_excel)
        main.addLayout(row)
        
        # Прогресс бар
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        main.addWidget(self.progress)
        
        # Таблица
        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.open_details)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        main.addWidget(self.table, 1)
        
        # Обработчики
        self.btn_search.clicked.connect(self.on_search)
        self.btn_reset.clicked.connect(self.reset_filters)
        self.btn_details.clicked.connect(self.open_details)
        self.btn_add_fav.clicked.connect(self.on_add_favorite)
        self.btn_export_csv.clicked.connect(lambda: save_df_to_csv(self, self.model.dataframe(), "advanced_search.csv"))
        self.btn_export_excel.clicked.connect(lambda: save_df_to_excel(self, self.model.dataframe(), "advanced_search.xlsx"))
        
        # Горячие клавиши
        self.btn_search.setShortcut(QKeySequence("Ctrl+Return"))
        self.btn_reset.setShortcut(QKeySequence("Ctrl+R"))
    
    def reset_filters(self):
        self.ed_title.clear()
        self.ed_actor.clear()
        self.cb_genre.setCurrentIndex(0)
        self.cb_rating.setCurrentIndex(0)
        self.sb_year_from.setValue(1980)
        self.sb_year_to.setValue(2025)
        self.sb_length_from.setValue(0)
        self.sb_length_to.setValue(500)
        self.cb_sort.setCurrentIndex(0)
        self.notify("Filters cleared")
    
    def _context_menu(self, pos):
        idx = self.table.indexAt(pos)
        menu = QMenu(self)
        act_detail = menu.addAction("📋 Details")
        act_fav    = menu.addAction("⭐ Add to favorites")
        act_copy   = menu.addAction("📄 Copy name")
        act_actors = menu.addAction("👥 Show actors")
        menu.addSeparator()
        #act_similar = menu.addAction("🔍 Найти похожие")
        
        action = menu.exec(self.table.mapToGlobal(pos))
        if not idx.isValid():
            return
        
        r = idx.row()
        df = self.model.dataframe()
        if df.empty:
            return
        row = df.iloc[r].to_dict()
        
        if action == act_detail:
            fid = row.get("film_id")
            if fid is not None:
                FilmDialog(self.db, int(fid), self).exec()
        elif action == act_fav:
            self._add_rows_to_fav([r])
        elif action == act_copy:
            title = str(row.get("title", ""))
            QApplication.clipboard().setText(title)
            self.notify("Title copied")
        elif action == act_actors:
            self._show_actors(row.get("film_id"))
        elif action == act_similar:
            self._find_similar_films(row.get("film_id"))
    
    def _show_actors(self, film_id):
        if not film_id:
            return
        sql = """
            SELECT CONCAT(a.first_name, ' ', a.last_name) as actor_name
            FROM film_actor fa
            JOIN actor a ON a.actor_id = fa.actor_id
            WHERE fa.film_id = %(fid)s
            ORDER BY a.first_name, a.last_name
        """
        rows = self.db.select(sql, {"fid": film_id})
        if rows:
            actors = "\n".join([f"• {r['actor_name']}" for r in rows])
            QMessageBox.information(self, "Cast movies", actors)
    
    def _find_similar_films(self, film_id):
        if not film_id:
            return
        # Используем FilmDialog для поиска похожих
        dialog = FilmDialog(self.db, int(film_id), self)
        data = dialog._load_details()
        if data:
            dialog._find_similar(data)
    
    def on_search(self):
        # Показываем прогресс
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        
        # Формируем ключ кеша
        cache_key = hashlib.md5(json.dumps({
            'title': self.ed_title.text(),
            'actor': self.ed_actor.text(),
            'genre': self.cb_genre.currentText(),
            'rating': self.cb_rating.currentText(),
            'year_from': self.sb_year_from.value(),
            'year_to': self.sb_year_to.value(),
            'length_from': self.sb_length_from.value(),
            'length_to': self.sb_length_to.value(),
            'sort': self.cb_sort.currentText(),
            'limit': self.sb_limit.value()
        }).encode()).hexdigest()
        
        # Проверяем кеш
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.model.set_dataframe(pd().DataFrame(cached_result))
            self.table.resizeColumnsToContents()
            self.progress.setVisible(False)
            self.notify("Results loaded from cache")
            return
        
        # Строим запрос
        sql_parts = ["SELECT DISTINCT f.film_id, f.title, f.description, f.release_year, f.length, f.rating"]
        from_parts = ["FROM film f"]
        where_parts = ["WHERE 1=1"]
        params = {}
        
        # Название
        if self.ed_title.text().strip():
            where_parts.append("AND f.title LIKE %(title)s")
            params['title'] = f"%{self.ed_title.text().strip()}%"
        
        # Актёр
        if self.ed_actor.text().strip():
            from_parts.append("JOIN film_actor fa ON fa.film_id = f.film_id")
            from_parts.append("JOIN actor a ON a.actor_id = fa.actor_id")
            where_parts.append("AND (a.first_name LIKE %(actor)s OR a.last_name LIKE %(actor)s)")
            params['actor'] = f"%{self.ed_actor.text().strip()}%"
        
        # Жанр
        if self.cb_genre.currentText() != "Any":
            from_parts.append("JOIN film_category fc ON fc.film_id = f.film_id")
            from_parts.append("JOIN category c ON c.category_id = fc.category_id")
            where_parts.append("AND c.name = %(genre)s")
            params['genre'] = self.cb_genre.currentText()
        
        # Rating
        if self.cb_rating.currentText() != "Any":
            where_parts.append("AND f.rating = %(rating)s")
            params['rating'] = self.cb_rating.currentText()
        
        # Yearы
        if self.sb_year_from.value() > 1900:
            where_parts.append("AND f.release_year >= %(year_from)s")
            params['year_from'] = self.sb_year_from.value()
        if self.sb_year_to.value() < 2100:
            where_parts.append("AND f.release_year <= %(year_to)s")
            params['year_to'] = self.sb_year_to.value()
        
        # Runtime
        if self.sb_length_from.value() > 0:
            where_parts.append("AND f.length >= %(length_from)s")
            params['length_from'] = self.sb_length_from.value()
        if self.sb_length_to.value() < 500:
            where_parts.append("AND f.length <= %(length_to)s")
            params['length_to'] = self.sb_length_to.value()
        
        # Сортировка
        order_map = {
            "By year (new first)": "f.release_year DESC, f.title",
            "By year (old first)": "f.release_year ASC, f.title",
            "By title (А-Я)": "f.title ASC",
            "By title (Я-А)": "f.title DESC",
            "By runtime (↑)": "f.length ASC, f.title",
            "By runtime (↓)": "f.length DESC, f.title",
            "By rating": "f.rating DESC, f.title"
        }
        order_by = order_map.get(self.cb_sort.currentText(), "f.release_year DESC, f.title")
        
        # Собираем запрос
        sql = f"{' '.join(sql_parts)} {' '.join(from_parts)} {' '.join(where_parts)} ORDER BY {order_by} LIMIT %(limit)s"
        params['limit'] = self.sb_limit.value()
        
        try:
            rows = self.db.select(sql, params)
            df = pd().DataFrame(rows) if rows else pd().DataFrame()
            
            # Сохраняем в кеш
            if rows:
                self.cache.set(cache_key, rows)
            
            self.model.set_dataframe(df)
            self.table.resizeColumnsToContents()
            
            # Логируем
            try:
                self.lw.log_search("advanced", params, len(df))
            except:
                pass
            
            if df.empty:
                self.notify("Nothing found")
            else:
                self.notify(f"Found movies: {len(df)}")
        
        except Exception as e:
            QMessageBox.critical(self, "Search error", str(e))
        finally:
            self.progress.setVisible(False)
    
    def open_details(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            self.notify("Select a row")
            return
        r = sel[0].row()
        row = self.model.dataframe().iloc[r].to_dict()
        fid = row.get("film_id")
        if fid is None:
            self.notify("Could not determine film_id")
            return
        FilmDialog(self.db, int(fid), self).exec()
    
    def _add_rows_to_fav(self, rows_idx: List[int]):
        df = self.model.dataframe()
        if df.empty:
            self.notify("No data to add")
            return
        added = 0
        for r in rows_idx:
            item = df.iloc[r].to_dict()
            added += self.favorites_sink.add(item)
        if added > 0:
            self.on_fav_changed()
            self.notify(f"Added to favorites: {added}")
        else:
            self.notify("These films are already in favorites")
    
    def on_add_favorite(self):
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        if not rows:
            self.notify("Select at least one row")
            return
        self._add_rows_to_fav(rows)

# ---------- Вкладка: Analytics ----------
class AnalyticsTab(QWidget):
    def __init__(self, db: MySQLConnector):
        super().__init__()
        self.db = db
        
        main = QVBoxLayout(self)
        
        # Панель управления
        control_panel = QHBoxLayout()
        self.btn_refresh = AnimatedButton("🔄 Update all charts")
        self.btn_export = AnimatedButton("💾 Save charts")
        control_panel.addWidget(self.btn_refresh)
        control_panel.addStretch()
        control_panel.addWidget(self.btn_export)
        main.addLayout(control_panel)
        
        # Создаём сплиттер для графиков
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Верхний ряд графиков
        top_row = QSplitter(Qt.Orientation.Horizontal)
        
        # График 1: Распределение по годам
        self.year_chart = self._create_chart_widget("Distribution of films by year")
        top_row.addWidget(self.year_chart)
        
        # График 2: Top genres
        self.genre_chart = self._create_chart_widget("Top genres")
        top_row.addWidget(self.genre_chart)
        
        splitter.addWidget(top_row)
        
        # Нижний ряд графиков
        bottom_row = QSplitter(Qt.Orientation.Horizontal)
        
        # График 3: Ratingи
        self.rating_chart = self._create_chart_widget("Distribution by ratings")
        bottom_row.addWidget(self.rating_chart)
        
        # График 4: Runtime по жанрам
        self.length_chart = self._create_chart_widget("Average runtime by genre")
        bottom_row.addWidget(self.length_chart)
        
        splitter.addWidget(bottom_row)
        
        main.addWidget(splitter)
        
        # Обработчики
        self.btn_refresh.clicked.connect(self.refresh_all)
        self.btn_export.clicked.connect(self.export_charts)
        
        # Загружаем данные
        QTimer.singleShot(100, self.refresh_all)
    
    def _create_chart_widget(self, title: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        label = QLabel(title)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        
        figure = Figure(figsize=(5, 4), dpi=80)
        canvas = FigureCanvas(figure)
        canvas.setStyleSheet("border: 1px solid #2b2f3a; border-radius: 10px;")
        layout.addWidget(canvas)
        
        widget.figure = figure
        widget.canvas = canvas
        
        return widget
    
    def refresh_all(self):
        self._plot_years()
        self._plot_genres()
        self._plot_ratings()
        self._plot_length_by_genre()
    
    def _plot_years(self):
        try:
            sql = """
                SELECT YEAR(release_date) as release_year, COUNT(*) as count
                FROM movies
                WHERE release_date IS NOT NULL
                GROUP BY YEAR(release_date)
                ORDER BY release_year
            """
            data = self.db.select(sql)
            if not data:
                return
            
            df = pd().DataFrame(data)
            
            fig = self.year_chart.figure
            fig.clear()
            ax = fig.add_subplot(111)
            
            ax.bar(df['release_year'], df['count'], color='#7C5CFC', alpha=0.8)
            ax.set_xlabel('Year', fontsize=10)
            ax.set_ylabel('Количество movies', fontsize=10)
            ax.grid(True, alpha=0.3)
            
            # Тёмная тема
            fig.patch.set_facecolor('#161a23')
            ax.set_facecolor('#161a23')
            ax.tick_params(colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            self.year_chart.canvas.draw()
        except Exception as e:
            print(f"Error in years: {e}")
    
    def _plot_genres(self):
        try:
            sql = """
                SELECT g.name as genre, COUNT(*) as count
                FROM movie_genres mg
                JOIN genres g ON g.genre_id = mg.genre_id
                GROUP BY g.name
                ORDER BY count DESC
                LIMIT 10
            """
            data = self.db.select(sql)
            if not data:
                return
            
            df = pd().DataFrame(data)
            
            fig = self.genre_chart.figure
            fig.clear()
            ax = fig.add_subplot(111)
            
            colors = plt().cm.viridis(np().linspace(0, 1, len(df)))
            wedges, texts, autotexts = ax.pie(df['count'], labels=df['genre'], 
                                             autopct='%1.1f%%', colors=colors)
            
            # Тёмная тема для текста
            for text in texts:
                text.set_color('white')
                text.set_fontsize(9)
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(8)
            
            fig.patch.set_facecolor('#161a23')
            
            self.genre_chart.canvas.draw()
        except Exception as e:
            print(f"Error в графике жанров: {e}")
    
    def _plot_ratings(self):
        try:
            # Для TMDB используем распределение по vote_average
            sql = """
                SELECT 
                    CASE 
                        WHEN vote_average >= 9 THEN '9-10'
                        WHEN vote_average >= 8 THEN '8-9'
                        WHEN vote_average >= 7 THEN '7-8'
                        WHEN vote_average >= 6 THEN '6-7'
                        WHEN vote_average >= 5 THEN '5-6'
                        WHEN vote_average >= 4 THEN '4-5'
                        WHEN vote_average >= 3 THEN '3-4'
                        WHEN vote_average >= 2 THEN '2-3'
                        WHEN vote_average >= 1 THEN '1-2'
                        ELSE '0-1'
                    END as rating_range,
                    COUNT(*) as count
                FROM movies
                WHERE vote_average IS NOT NULL AND vote_average > 0
                GROUP BY rating_range
                ORDER BY rating_range
            """
            data = self.db.select(sql)
            if not data:
                return
            
            df = pd().DataFrame(data)
            
            fig = self.rating_chart.figure
            fig.clear()
            ax = fig.add_subplot(111)
            
            # Сортируем по порядку
            rating_order = ['0-1', '1-2', '2-3', '3-4', '4-5', '5-6', '6-7', '7-8', '8-9', '9-10']
            df['rating_range'] = pd().Categorical(df['rating_range'], categories=rating_order, ordered=True)
            df = df.sort_values('rating_range')
            
            bars = ax.bar(df['rating_range'], df['count'], color='#B794F4', alpha=0.8)
            
            # Добавляем значения на столбцы
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}', ha='center', va='bottom', color='white', fontsize=9)
            
            ax.set_xlabel('Rating', fontsize=10)
            ax.set_ylabel('Количество movies', fontsize=10)
            ax.grid(True, alpha=0.3, axis='y')
            
            # Тёмная тема
            fig.patch.set_facecolor('#161a23')
            ax.set_facecolor('#161a23')
            ax.tick_params(colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            self.rating_chart.canvas.draw()
        except Exception as e:
            print(f"Error ratings: {e}")
    
    def _plot_length_by_genre(self):
        try:
            sql = """
                SELECT g.name as genre, AVG(m.runtime) as avg_length, 
                       MIN(m.runtime) as min_length, MAX(m.runtime) as max_length
                FROM movies m
                JOIN movie_genres mg ON mg.tmdb_id = m.tmdb_id
                JOIN genres g ON g.genre_id = mg.genre_id
                WHERE m.runtime IS NOT NULL AND m.runtime > 0
                GROUP BY g.name
                ORDER BY avg_length DESC
            """
            data = self.db.select(sql)
            if not data:
                return
            
            df = pd().DataFrame(data)
            
            fig = self.length_chart.figure
            fig.clear()
            ax = fig.add_subplot(111)
            
            x = range(len(df))
            ax.barh(x, df['avg_length'], color='#7C5CFC', alpha=0.8, label='Averege')
            
            # Добавляем minимум и максимум
            for i, row in df.iterrows():
                ax.plot([row['min_length'], row['max_length']], [i, i], 
                       'w-', linewidth=2, alpha=0.6)
                ax.plot(row['min_length'], i, 'wo', markersize=4)
                ax.plot(row['max_length'], i, 'wo', markersize=4)
            
            ax.set_yticks(x)
            ax.set_yticklabels(df['genre'])
            ax.set_xlabel('Runtime (min)', fontsize=10)
            ax.grid(True, alpha=0.3, axis='x')
            
            # Тёмная тема
            fig.patch.set_facecolor('#161a23')
            ax.set_facecolor('#161a23')
            ax.tick_params(colors='white')
            ax.xaxis.label.set_color('white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            self.length_chart.canvas.draw()
        except Exception as e:
            print(f"Error leght: {e}")
    
    def export_charts(self):
        path = QFileDialog.getExistingDirectory(self, "Select a folder to save")
        if not path:
            return
        
        try:
            # Сохраняем все графики
            self.year_chart.figure.savefig(
                os.path.join(path, "years_distribution.png"), 
                dpi=150, bbox_inches='tight', facecolor='#161a23'
            )
            self.genre_chart.figure.savefig(
                os.path.join(path, "genres_pie.png"), 
                dpi=150, bbox_inches='tight', facecolor='#161a23'
            )
            self.rating_chart.figure.savefig(
                os.path.join(path, "ratings_bar.png"), 
                dpi=150, bbox_inches='tight', facecolor='#161a23'
            )
            self.length_chart.figure.savefig(
                os.path.join(path, "length_by_genre.png"), 
                dpi=150, bbox_inches='tight', facecolor='#161a23'
            )
            
            QMessageBox.information(self, "Export", "Charts saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error save: {str(e)}")

# ---------- Вкладка: Search (оригинальная, но улучшенная) ----------
class SearchTab(QWidget):
    def __init__(self, db, lw, favorites_sink, notify=lambda msg: None):
        super().__init__()
        self.db, self.lw = db, lw
        self.favorites_sink = favorites_sink
        self.notify = notify
        self.on_fav_changed = lambda: None
        
        main = QVBoxLayout(self)
        
        box = QGroupBox("Keyword search")
        form = QFormLayout(box)
        
        # Поле с автодополнением
        self.ed_keyword = QLineEdit()
        self.ed_keyword.setPlaceholderText("Start typing a title...")
        
        # Автодополнение
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.ed_keyword.setCompleter(self.completer)
        self._update_completer()
        
        self.cb_rating = QComboBox()
        self.cb_rating.addItems(["All","G","PG","PG-13","R","NC-17"])
        
        self.sb_limit = QSpinBox()
        self.sb_limit.setRange(1, 500)
        self.sb_limit.setValue(50)
        
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["By title","By description","By title and description"])
        
        # Чекбокс для постеров
        self.cb_load_posters = QCheckBox("Load posters (slow)")
        
        form.addRow("Keyword:", self.ed_keyword)
        form.addRow("Rating:", self.cb_rating)
        form.addRow("Limit:", self.sb_limit)
        form.addRow("Mode:", self.cb_mode)
        form.addRow("", self.cb_load_posters)
        main.addWidget(box)
        
        row = QHBoxLayout()
        self.btn_search = AnimatedButton("🔍 Search")
        self.btn_details = AnimatedButton("📋 Details")
        self.btn_add_fav = AnimatedButton("⭐ Add to favorites")
        self.btn_export = AnimatedButton("📊 Export CSV")
        
        # Горячая клавиша для поиска
        self.btn_search.setShortcut(QKeySequence("Return"))
        
        row.addWidget(self.btn_search)
        row.addStretch(1)
        row.addWidget(self.btn_details)
        row.addWidget(self.btn_add_fav)
        row.addWidget(self.btn_export)
        main.addLayout(row)
        
        # Прогресс для загрузки постеров
        self.poster_progress = QProgressBar()
        self.poster_progress.setVisible(False)
        main.addWidget(self.poster_progress)
        
        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.open_details)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        
        # Увеличиваем высоту строк для постеров
        self.table.verticalHeader().setDefaultSectionSize(60)
        
        main.addWidget(self.table, 1)
        
        self.btn_search.clicked.connect(self.on_search)
        self.btn_export.clicked.connect(lambda: save_df_to_csv(self, self.model.dataframe(), "search_results.csv"))
        self.btn_add_fav.clicked.connect(self.on_add_favorite)
        self.btn_details.clicked.connect(self.open_details)
        
        # Загрузчик постеров
        self.poster_loader = PosterLoader()
        self.poster_loader.posterLoaded.connect(self.model.add_poster)
    
    def _update_completer(self):
        """Обновляет список автодополнения"""
        try:
            sql = "SELECT DISTINCT title FROM film ORDER BY title LIMIT 500"
            rows = self.db.select(sql)
            titles = [r['title'] for r in rows]
            self.completer.setModel(self.completer.model())
            self.completer.model().setStringList(titles)
        except:
            pass
    
    def _context_menu(self, pos):
        idx = self.table.indexAt(pos)
        menu = QMenu(self)
        
        act_detail = menu.addAction("📋 Details")
        act_fav    = menu.addAction("⭐ Add to favorites")
        act_copy   = menu.addAction("📄 Copy name")
        menu.addSeparator()
        act_trailer = menu.addAction("▶️ Watch trailer")
        #act_similar = menu.addAction("🔍 Найти похожие")
        
        action = menu.exec(self.table.mapToGlobal(pos))
        if not idx.isValid():
            return
        
        r = idx.row()
        df = self.model.dataframe()
        if df.empty:
            return
        row = df.iloc[r].to_dict()
        
        if action == act_detail:
            fid = row.get("film_id")
            if fid is not None:
                FilmDialog(self.db, int(fid), self).exec()
        elif action == act_fav:
            self._add_rows_to_fav([r])
        elif action == act_copy:
            title = str(row.get("title", ""))
            QApplication.clipboard().setText(title)
            self.notify("Title copied")
        elif action == act_trailer:
            from urllib.parse import quote_plus
            title = row.get("title", "")
            year = row.get("release_year", "")
            q = quote_plus(f"{title} trailer {year}")
            webbrowser.open(f"https://www.youtube.com/results?search_query={q}")
        elif action == act_similar:
            dialog = FilmDialog(self.db, int(row.get("film_id", 0)), self)
            data = dialog._load_details()
            if data:
                dialog._find_similar(data)
    
    def open_details(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            self.notify("Select a row")
            return
        r = sel[0].row()
        row = self.model.dataframe().iloc[r].to_dict()
        fid = row.get("film_id")
        if fid is None:
            self.notify("Could not determine film_id")
            return
        FilmDialog(self.db, int(fid), self).exec()
    
    def on_search(self):
        kw = self.ed_keyword.text().strip()
        if not kw:
            self.notify("Enter a keyword")
            return
        
        if self.cb_mode.currentText() == "By title":
            search_field = "f.title LIKE %(kw)s"
        elif self.cb_mode.currentText() == "By description":
            search_field = "f.description LIKE %(kw)s"
        else:
            search_field = "(f.title LIKE %(kw)s OR f.description LIKE %(kw)s)"
        
        sql = f"""
            SELECT f.film_id, f.title, f.description, f.release_year, f.length, f.rating,
                   GROUP_CONCAT(DISTINCT c.name ORDER BY c.name SEPARATOR ', ') as genres
            FROM film f
            LEFT JOIN film_category fc ON fc.film_id = f.film_id
            LEFT JOIN category c ON c.category_id = fc.category_id
            WHERE {search_field}
        """
        params = {"kw": f"%{kw}%"}
        
        if self.cb_rating.currentText() != "All":
            sql += " AND f.rating = %(rating)s"
            params["rating"] = self.cb_rating.currentText()
        
        sql += " GROUP BY f.film_id, f.title, f.description, f.release_year, f.length, f.rating"
        sql += " ORDER BY f.release_year DESC, f.title ASC LIMIT %(lim)s"
        params["lim"] = int(self.sb_limit.value())
        
        try:
            rows = self.db.select(sql, params)
            df = pd().DataFrame(rows) if rows else pd().DataFrame()
            self.model.set_dataframe(df)
            self.table.resizeColumnsToContents()
            
            # Загружаем постеры если включено
            if self.cb_load_posters.isChecked() and not df.empty and TMDB_API_KEY:
                self.poster_progress.setVisible(True)
                self.poster_progress.setRange(0, len(df))
                self.poster_progress.setValue(0)
                
                for i, row in df.iterrows():
                    self.poster_loader.add_request(
                        row['film_id'], 
                        row['title'], 
                        row.get('release_year')
                    )
                    self.poster_progress.setValue(i + 1)
                
                QTimer.singleShot(2000, lambda: self.poster_progress.setVisible(False))
            
            try:
                self.lw.log_search("keyword", {"keyword": kw, "rating": self.cb_rating.currentText()}, len(df))
            except:
                pass
            
            if df.empty:
                self.notify("Nothing found")
            else:
                self.notify(f"Found: {len(df)} movies")
        
        except Exception as e:
            QMessageBox.critical(self, "Search error", str(e))
    
    def _add_rows_to_fav(self, rows_idx: List[int]):
        df = self.model.dataframe()
        if df.empty:
            self.notify("No data to add")
            return
        added = 0
        for r in rows_idx:
            item = df.iloc[r].to_dict()
            added += self.favorites_sink.add(item)
        if added > 0:
            self.on_fav_changed()
            self.notify(f"Added to favorites: {added}")
        else:
            self.notify("These films are already in favorites")
    
    def on_add_favorite(self):
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        if not rows:
            self.notify("Select at least one row")
            return
        self._add_rows_to_fav(rows)

# ---------- Favorites с сохранением ----------
class FavoritesStore:
    def __init__(self):
        self._items: List[Dict] = []
        self._user_data: Dict[int, Dict] = {}  # film_id -> {rating, notes, tags}
        self.load()
    
    def add(self, item: Dict) -> int:
        fid = item.get("film_id")
        if fid is not None and any(x.get("film_id")==fid for x in self._items):
            return 0
        self._items.append(item)
        self.save()
        return 1
    
    def remove(self, film_id: int):
        self._items = [x for x in self._items if x.get("film_id") != film_id]
        if film_id in self._user_data:
            del self._user_data[film_id]
        self.save()
    
    def set_user_data(self, film_id: int, data: Dict):
        self._user_data[film_id] = data
        self.save()
    
    def get_user_data(self, film_id: int) -> Dict:
        return self._user_data.get(film_id, {})
    
    def all(self) -> List[Dict]:
        # Добавляем пользовательские данные к элементам
        result = []
        for item in self._items:
            fid = item.get("film_id")
            if fid and fid in self._user_data:
                item_copy = item.copy()
                item_copy.update(self._user_data[fid])
                result.append(item_copy)
            else:
                result.append(item.copy())
        return result
    
    def clear(self):
        self._items.clear()
        self._user_data.clear()
        self.save()
    
    def save(self):
        ensure_cache_dir()
        data = {
            'items': self._items,
            'user_data': self._user_data
        }
        try:
            with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error save selected: {e}")
    
    def load(self):
        try:
            if os.path.exists(FAVORITES_FILE):
                with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._items = data.get('items', [])
                    self._user_data = {int(k): v for k, v in data.get('user_data', {}).items()}
        except Exception as e:
            print(f"Error downolad selected: {e}")
            self._items = []
            self._user_data = {}

class FavoritesTab(QWidget):
    def __init__(self, store: FavoritesStore, notify=lambda msg: None):
        super().__init__()
        self.store = store
        self.notify = notify
        
        main = QVBoxLayout(self)
        
        # Панель управления
        row = QHBoxLayout()
        
        # Фильтр по тегам
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("All tags")
        self.tag_filter.currentTextChanged.connect(self.apply_tag_filter)
        
        row.addWidget(QLabel("Filter:"))
        row.addWidget(self.tag_filter)
        row.addStretch(1)
        
        self.btn_refresh = AnimatedButton("🔄 Refresh")
        self.btn_edit = AnimatedButton("✏️ Edit")
        self.btn_remove = AnimatedButton("🗑️ Delete")
        self.btn_export = AnimatedButton("📊 Export CSV")
        self.btn_clear = AnimatedButton("🧹 Clear all")
        
        row.addWidget(self.btn_refresh)
        row.addWidget(self.btn_edit)
        row.addWidget(self.btn_remove)
        row.addWidget(self.btn_export)
        row.addWidget(self.btn_clear)
        main.addLayout(row)
        
        # Таблица
        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.edit_item)
        main.addWidget(self.table, 1)
        
        # Обработчики
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_edit.clicked.connect(self.edit_item)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_clear.clicked.connect(self.clear)
        
        self.refresh()
    
    def refresh(self):
        items = self.store.all()
        
        # Обновляем список тегов
        all_tags = set()
        for item in items:
            tags = item.get('tags', '')
            if tags:
                all_tags.update(tag.strip() for tag in tags.split(','))
        
        current_tag = self.tag_filter.currentText()
        self.tag_filter.clear()
        self.tag_filter.addItem("All tags")
        self.tag_filter.addItems(sorted(all_tags))
        
        # Восстанавливаем выбор
        idx = self.tag_filter.findText(current_tag)
        if idx >= 0:
            self.tag_filter.setCurrentIndex(idx)
        
        # Применяем фильтр
        self.apply_tag_filter()
    
    def apply_tag_filter(self):
        items = self.store.all()
        current_tag = self.tag_filter.currentText()
        
        if current_tag == "All теги":
            filtered_items = items
        else:
            filtered_items = []
            for item in items:
                tags = item.get('tags', '')
                if tags and current_tag in [t.strip() for t in tags.split(',')]:
                    filtered_items.append(item)
        
        df = pd().DataFrame(filtered_items) if filtered_items else pd().DataFrame(columns=["No data"])
        self.model.set_dataframe(df)
        self.table.resizeColumnsToContents()
    
    def edit_item(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            self.notify("Select a movie to edit")
            return
        
        r = sel[0].row()
        row = self.model.dataframe().iloc[r].to_dict()
        film_id = row.get("film_id")
        if not film_id:
            return
        
        # Диалог редактирования
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit selected")
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Название фильма
        layout.addWidget(QLabel(f"Film: {row.get('title', 'unknown')}"))
        
        # Rating
        rating_layout = QHBoxLayout()
        rating_layout.addWidget(QLabel("Your rating:"))
        rating_slider = QSlider(Qt.Orientation.Horizontal)
        rating_slider.setRange(0, 10)
        rating_slider.setValue(row.get('user_rating', 0))
        rating_label = QLabel(str(row.get('user_rating', 0)))
        rating_slider.valueChanged.connect(lambda v: rating_label.setText(str(v)))
        rating_layout.addWidget(rating_slider)
        rating_layout.addWidget(rating_label)
        layout.addLayout(rating_layout)
        
        # Теги
        layout.addWidget(QLabel("Tags (comma separated):"))
        tags_edit = QLineEdit(row.get('tags', ''))
        tags_edit.setPlaceholderText("e.g. comedy, favorite, rewatch")
        layout.addWidget(tags_edit)
        
        # Заметки
        layout.addWidget(QLabel("Notes:"))
        notes_edit = QTextEdit(row.get('notes', ''))
        notes_edit.setPlaceholderText("Your notes about the film...")
        layout.addWidget(notes_edit)
        
        # Кнопки
        buttons = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        buttons.addStretch()
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_cancel)
        layout.addLayout(buttons)
        
        btn_save.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Сохраняем данные
            user_data = {
                'user_rating': rating_slider.value(),
                'tags': tags_edit.text(),
                'notes': notes_edit.toPlainText()
            }
            self.store.set_user_data(film_id, user_data)
            self.refresh()
            self.notify("Saved")
    
    def remove_selected(self):
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()}, reverse=True)
        if not rows:
            self.notify("Select movies to remove")
            return
        
        reply = QMessageBox.question(self, "Deletion", 
                                   f"Delete {len(rows)} фильм(ов) from favorites?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            df = self.model.dataframe()
            for r in rows:
                film_id = df.iloc[r].get('film_id')
                if film_id:
                    self.store.remove(film_id)
            self.refresh()
            self.notify(f"Удалено movies: {len(rows)}")
    
    def export_csv(self):
        save_df_to_csv(self, self.model.dataframe(), "favorites.csv")
    
    def clear(self):
        reply = QMessageBox.question(self, "Clear", 
                                   "Delete all movies from favorites?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.store.clear()
            self.refresh()
            self.notify("Favorites list cleared")

# ---------- Settings ----------
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(500, 400)
        
        self.settings = self._load_settings()
        
        layout = QVBoxLayout(self)
        
        # TMDB API
        api_group = QGroupBox("TMDB API")
        api_layout = QFormLayout(api_group)
        self.api_key_edit = QLineEdit(self.settings.get('tmdb_api_key', ''))
        self.api_key_edit.setPlaceholderText("Enter API key to load posters")
        api_layout.addRow("API key:", self.api_key_edit)
        api_layout.addRow(QLabel("Get a key: https://www.themoviedb.org/settings/api"))
        layout.addWidget(api_group)
        
        # Database
        db_group = QGroupBox("Database")
        db_layout = QFormLayout(db_group)
        self.db_host = QLineEdit(self.settings.get('db_host', 'localhost'))
        self.db_port = QLineEdit(self.settings.get('db_port', '3306'))
        self.db_user = QLineEdit(self.settings.get('db_user', 'root'))
        self.db_pass = QLineEdit(self.settings.get('db_pass', ''))
        self.db_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_name = QLineEdit(self.settings.get('db_name', 'TMDB'))
        
        db_layout.addRow("Host:", self.db_host)
        db_layout.addRow("Port:", self.db_port)
        db_layout.addRow("User:", self.db_user)
        db_layout.addRow("Password:", self.db_pass)
        db_layout.addRow("Database:", self.db_name)
        layout.addWidget(db_group)
        
        # Кэш
        cache_group = QGroupBox("Cache and data")
        cache_layout = QVBoxLayout(cache_group)
        self.btn_clear_cache = QPushButton("Clear search cache")
        self.btn_clear_cache.clicked.connect(self._clear_cache)
        cache_layout.addWidget(self.btn_clear_cache)
        
        cache_info = QLabel(f"Data folder: {CACHE_DIR}")
        cache_info.setWordWrap(True)
        cache_layout.addWidget(cache_info)
        layout.addWidget(cache_group)
        
        # Кнопки
        buttons = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_cancel = QPushButton("Cancel")
        buttons.addStretch()
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_cancel)
        layout.addLayout(buttons)
        
        btn_save.clicked.connect(self.save_settings)
        btn_cancel.clicked.connect(self.reject)
    
    def _load_settings(self) -> Dict:
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save_settings(self):
        global TMDB_API_KEY
        
        self.settings = {
            'tmdb_api_key': self.api_key_edit.text().strip(),
            'db_host': self.db_host.text().strip(),
            'db_port': self.db_port.text().strip(),
            'db_user': self.db_user.text().strip(),
            'db_pass': self.db_pass.text().strip(),
            'db_name': self.db_name.text().strip()
        }
        
        ensure_cache_dir()
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            TMDB_API_KEY = self.settings['tmdb_api_key']
            
            QMessageBox.information(self, "Success", "Settings saving!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error save: {str(e)}")
    
    def _clear_cache(self):
        try:
            if os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE)
            QMessageBox.information(self, "Success", "Cache cleared!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cash clearing: {str(e)}")

# ---------- Главное окно ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_cache_dir()
        
        self.settings = QSettings("Dmitriy", "TMDB_desktop")
        self.setWindowTitle(f"TMDB Movie Database – Desktop ({APP_BUILD})")
        self.resize(1400, 860)
        
        icon_path = res_path("app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Загружаем настройки
        self._load_app_settings()
        
        self.db = MySQLConnector()
        self.lw = LogWriter()
        self.ls = LogStats()
        self.favorites = FavoritesStore()
        
        # Баннер с анимацией
        banner = QFrame()
        banner.setObjectName("banner")
        banner.setFixedHeight(60)
        hb = QHBoxLayout(banner)
        hb.setContentsMargins(16,10,16,10)
        
        logo = QLabel()
        logo_path = res_path("logo.png")
        if os.path.exists(logo_path):
            logo.setPixmap(QPixmap(logo_path).scaled(40,40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        title = QLabel("TMDB Movie Database – Desktop v3")
        title.setObjectName("title")
        f = QFont()
        f.setPointSize(16)
        f.setBold(True)
        title.setFont(f)
        
        # Анимация прозрачности для заголовка
        self.title_effect = QGraphicsOpacityEffect()
        title.setGraphicsEffect(self.title_effect)
        self.title_anim = QPropertyAnimation(self.title_effect, b"opacity")
        self.title_anim.setDuration(1000)
        self.title_anim.setStartValue(0.3)
        self.title_anim.setEndValue(1.0)
        self.title_anim.start()
        
        hb.addWidget(logo)
        hb.addSpacing(8)
        hb.addWidget(title)
        hb.addStretch(1)
        
        # Кнопка настроек
        self.btn_settings = AnimatedButton("⚙️")
        self.btn_settings.setFixedSize(40, 40)
        self.btn_settings.clicked.connect(self.open_settings)
        hb.addWidget(self.btn_settings)
        
        # Вкладки
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        
        # Уведомления
        notify = lambda msg: self.statusBar().showMessage(msg, 3000)
        
        # Создаём вкладки
        self.tab_search = SearchTab(self.db, self.lw, self.favorites, notify=notify)
        self.tab_advanced = AdvancedSearchTab(self.db, self.lw, self.favorites, notify=notify)
        self.tab_gy = GenreYearTab(self.db, self.lw, self.favorites, notify=notify)
        self.tab_analytics = AnalyticsTab(self.db)
        #self.tab_popular = PopularRecentTab(self.ls, "popular")
        #self.tab_recent = PopularRecentTab(self.ls, "recent")
        self.tab_fav = FavoritesTab(self.favorites, notify=notify)
        
        # Добавляем вкладки
        tabs.addTab(self.tab_search, "🔍 Quick search")
        tabs.addTab(self.tab_advanced, "🔎 Advanced search")
        tabs.addTab(self.tab_gy, "🎭 Genres / Years")
        tabs.addTab(self.tab_analytics, "📊 Analytics")
        #tabs.addTab(self.tab_popular, "🔥 Популярные")
        #tabs.addTab(self.tab_recent, "🕐 Recent")
        tabs.addTab(self.tab_fav, "⭐ Favorites")
        
        # Хук на обновление «Избранного»
        self.tab_search.on_fav_changed = self.tab_fav.refresh
        self.tab_advanced.on_fav_changed = self.tab_fav.refresh
        self.tab_gy.on_fav_changed = self.tab_fav.refresh
        tabs.currentChanged.connect(lambda i: self.on_tab_changed(tabs, i))
        
        # Основной layout
        wrapper = QWidget()
        lay = QVBoxLayout(wrapper)
        lay.setContentsMargins(10,10,10,10)
        lay.setSpacing(10)
        lay.addWidget(banner)
        lay.addWidget(tabs, 1)
        self.setCentralWidget(wrapper)
        
        # Меню
        self._create_menu()
        
        # Статусбар с прогрессом
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)
        
        # Восстанавливаем состояние
        if (geo := self.settings.value("geometry")):
            self.restoreGeometry(geo)
        tabs.setCurrentIndex(int(self.settings.value("tab_index", 0)))
        tabs.currentChanged.connect(lambda i: self.settings.setValue("tab_index", i))
        
        # Проверка подключения
        QTimer.singleShot(300, self._ping)
        
        # Запускаем загрузчик постеров
        if hasattr(self.tab_search, 'poster_loader'):
            self.tab_search.poster_loader.start()
    
    def _create_menu(self):
        # Меню File
        file_menu = self.menuBar().addMenu("File")
        
        act_export_csv = QAction("📊 Export current table to CSV", self)
        act_export_csv.setShortcut(QKeySequence("Ctrl+E"))
        act_export_csv.triggered.connect(self.export_current_table)
        
        act_export_excel = QAction("📊 Export current table to Excel", self)
        act_export_excel.setShortcut(QKeySequence("Ctrl+Shift+E"))
        act_export_excel.triggered.connect(self.export_current_excel)
        
        act_import = QAction("📥 Import list of movies", self)
        act_import.triggered.connect(self.import_films)
        
        act_settings = QAction("⚙️ Settings", self)
        act_settings.setShortcut(QKeySequence("Ctrl+,"))
        act_settings.triggered.connect(self.open_settings)
        
        act_exit = QAction("❌ Exit", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        
        file_menu.addAction(act_export_csv)
        file_menu.addAction(act_export_excel)
        file_menu.addSeparator()
        file_menu.addAction(act_import)
        file_menu.addSeparator()
        file_menu.addAction(act_settings)
        file_menu.addSeparator()
        file_menu.addAction(act_exit)
        
        # Меню View
        view_menu = self.menuBar().addMenu("View")
        
        act_fullscreen = QAction("🖥️ Fullscreen mode", self)
        act_fullscreen.setShortcut(QKeySequence("F11"))
        act_fullscreen.setCheckable(True)
        act_fullscreen.triggered.connect(self.toggle_fullscreen)
        
        act_refresh = QAction("🔄 Refresh the current tab", self)
        act_refresh.setShortcut(QKeySequence("F5"))
        act_refresh.triggered.connect(self.refresh_current_tab)
        
        view_menu.addAction(act_fullscreen)
        view_menu.addAction(act_refresh)
        
        # Меню Инструменты
        tools_menu = self.menuBar().addMenu("Tools")
        
        act_stats = QAction("📈 Statistics database", self)
        act_stats.triggered.connect(self.show_db_stats)
        
        #act_backup = QAction("💾 Резервная копия избранного", self)
        #act_backup.triggered.connect(self.backup_favorites)
        
        act_restore = QAction("📂 Restore favorites", self)
        act_restore.triggered.connect(self.restore_favorites)
        
        tools_menu.addAction(act_stats)
        tools_menu.addSeparator()
        #tools_menu.addAction(act_backup)
        tools_menu.addAction(act_restore)
        
        # Меню Помощь
        help_menu = self.menuBar().addMenu("Help")
        
        act_shortcuts = QAction("⌨️ Hotkeys", self)
        act_shortcuts.triggered.connect(self.show_shortcuts)
        
        act_about = QAction("ℹ️ About", self)
        act_about.triggered.connect(self.show_about)
        
        help_menu.addAction(act_shortcuts)
        help_menu.addSeparator()
        help_menu.addAction(act_about)
    
    def on_tab_changed(self, tabs: QTabWidget, index: int):
        # Обновляем избранное при переходе
        if tabs.widget(index) is self.tab_fav:
            self.tab_fav.refresh()
        # Обновляем аналитику при переходе
        elif tabs.widget(index) is self.tab_analytics:
            self.tab_analytics.refresh_all()
    
    def closeEvent(self, e):
        self.settings.setValue("geometry", self.saveGeometry())
        # Останавливаем загрузчик постеров
        if hasattr(self.tab_search, 'poster_loader'):
            self.tab_search.poster_loader.stop()
            self.tab_search.poster_loader.wait()
        super().closeEvent(e)
    
    def _ping(self):
        ok_mysql = self.db.test_connection()
        ok_mongo = self.lw.test_connection()
        
        if ok_mysql and ok_mongo:
            self.statusBar().showMessage("✅ All системы работают", 3000)
        else:
            msg = f"MySQL: {'✅ OK' if ok_mysql else '❌ Error'} | MongoDB: {'✅ OK' if ok_mongo else '❌ Error'}"
            QMessageBox.warning(self, "Подключение", msg)
    
    def _load_app_settings(self):
        """Загружает настройки приложения"""
        global TMDB_API_KEY
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    TMDB_API_KEY = settings.get('tmdb_api_key', '')
        except:
            pass
    
    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Перезагружаем настройки
            self._load_app_settings()
            QMessageBox.information(self, "Settings", 
                "Some settings will take effect after restarting the application.")
    
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def refresh_current_tab(self):
        """Обновляет текущую активную вкладку"""
        current_widget = self.centralWidget().findChild(QTabWidget).currentWidget()
        
        # Ищем метод refresh или reload
        for method_name in ['refresh', 'reload', 'on_search']:
            if hasattr(current_widget, method_name):
                method = getattr(current_widget, method_name)
                if callable(method):
                    method()
                    self.statusBar().showMessage("Tab refreshed", 2000)
                    return
        
        self.statusBar().showMessage("This tab cannot be refreshed", 2000)
    
    def export_current_table(self):
        """Exportирует текущую таблицу в CSV"""
        w = self.centralWidget().findChild(QTabWidget).currentWidget()
        for child in w.findChildren(QTableView):
            model: DataFrameModel = child.model()
            if hasattr(model, 'dataframe'):
                save_df_to_csv(self, model.dataframe(), "export.csv")
                return
        self.statusBar().showMessage("No table found on current tab", 2500)
    
    def export_current_excel(self):
        """Exportирует текущую таблицу в Excel"""
        w = self.centralWidget().findChild(QTabWidget).currentWidget()
        for child in w.findChildren(QTableView):
            model: DataFrameModel = child.model()
            if hasattr(model, 'dataframe'):
                save_df_to_excel(self, model.dataframe(), "export.xlsx")
                return
        self.statusBar().showMessage("No table found on current tab", 2500)
    
    def import_films(self):
        """Import списка movies из CSV"""
        path, _ = QFileDialog.getOpenFileName(self, "Choose CSV file", "", "CSV Files (*.csv)")
        if not path:
            return
        
        try:
            df = pd().read_csv(path)
            
            # Проверяем обязательные колонки
            required_cols = ['title']
            if not all(col in df.columns for col in required_cols):
                QMessageBox.warning(self, "Error", 
                    "CSV must contain at least one column 'title'")
                return
            
            # Importируем в избранное
            imported = 0
            for _, row in df.iterrows():
                item = row.to_dict()
                # Генерируем временный film_id если его нет
                if 'film_id' not in item:
                    item['film_id'] = hash(item['title']) % 1000000
                imported += self.favorites.add(item)
            
            self.tab_fav.refresh()
            QMessageBox.information(self, "Import", 
                f"Importировано movies: {imported}\nDuplicates skipped: {len(df) - imported}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error import", str(e))
    
    def show_db_stats(self):
        """Показывает статистику базы данных TMDB"""
        try:
            stats = {}
            
            # Общее количество movies
            rows = self.db.select("SELECT COUNT(*) as cnt FROM movies")
            stats['total_films'] = rows[0]['cnt'] if rows else 0
            
            # Количество актёров
            rows = self.db.select("SELECT COUNT(*) as cnt FROM people")
            stats['total_people'] = rows[0]['cnt'] if rows else 0
            
            # Количество жанров
            rows = self.db.select("SELECT COUNT(*) as cnt FROM genres")
            stats['total_genres'] = rows[0]['cnt'] if rows else 0
            
            # Средняя длительность
            rows = self.db.select("SELECT AVG(runtime) as avg_len FROM movies WHERE runtime IS NOT NULL AND runtime > 0")
            stats['avg_length'] = round(rows[0]['avg_len'], 1) if rows and rows[0]['avg_len'] else 0
            
            # Средний рейтинг
            rows = self.db.select("SELECT AVG(vote_average) as avg_rating FROM movies WHERE vote_average IS NOT NULL AND vote_average > 0")
            stats['avg_rating'] = round(rows[0]['avg_rating'], 1) if rows and rows[0]['avg_rating'] else 0
            
            # Самый продуктивный год
            rows = self.db.select("""
                SELECT YEAR(release_date) as year, COUNT(*) as cnt 
                FROM movies 
                WHERE release_date IS NOT NULL 
                GROUP BY YEAR(release_date) 
                ORDER BY cnt DESC 
                LIMIT 1
            """)
            if rows:
                stats['most_productive_year'] = f"{rows[0]['year']} ({rows[0]['cnt']} movies)"
            else:
                stats['most_productive_year'] = "Н/Д"
            
            # Самый популярный жанр
            rows = self.db.select("""
                SELECT g.name, COUNT(*) as cnt 
                FROM movie_genres mg 
                JOIN genres g ON g.genre_id = mg.genre_id 
                GROUP BY g.name 
                ORDER BY cnt DESC 
                LIMIT 1
            """)
            if rows:
                stats['most_popular_genre'] = f"{rows[0]['name']} ({rows[0]['cnt']} movies)"
            else:
                stats['most_popular_genre'] = "Н/Д"
            
            # Топ актёр по количеству movies
            rows = self.db.select("""
                SELECT p.name, COUNT(DISTINCT cc.tmdb_id) as cnt
                FROM cast_credits cc
                JOIN people p ON p.person_id = cc.person_id
                GROUP BY p.person_id, p.name
                ORDER BY cnt DESC
                LIMIT 1
            """)
            if rows:
                stats['top_actor'] = f"{rows[0]['name']} ({rows[0]['cnt']} movies)"
            else:
                stats['top_actor'] = "Н/Д"
            
            # Формируем сообщение
            msg = f"""
            📊 TMDB database statistics (moviesdb):

            🎬 Total movies: {stats['total_films']:,}
            👥 Total people (actors/directors): {stats['total_people']:,}
            🎭 Total genres: {stats['total_genres']}
            ⏱️ Average runtime: {stats['avg_length']} min
            ⭐ Average rating: {stats['avg_rating']}/10
            📅 Most productive year: {stats['most_productive_year']}
            🏆 Most popular genre: {stats['most_popular_genre']}
            🎯 Top actor: {stats['top_actor']}
            """
            
            QMessageBox.information(self, "Database stats", msg)
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get stats: {str(e)}")
    
        def backup_favorites(self):
            """Создаёт резервную копию избранного"""
            path, _ = QFileDialog.getSaveFileName(self, "Save a backup copy", 
                f"favorites_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 
                "JSON Files (*.json)")
            if not path:
                return
        
            try:
                data = {
                    'version': APP_BUILD,
                    'date': datetime.now().isoformat(),
                    'items': self.favorites._items,
                    'user_data': self.favorites._user_data
                }
            
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
                QMessageBox.information(self, "backup copy", 
                    f"Резервная копия создана!\nФильмов: {len(self.favorites._items)}")
        
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error save backup copy: {str(e)}")
    
    def restore_favorites(self):
        """Восстанавливает избранное из резервной копии"""
        path, _ = QFileDialog.getOpenFileName(self, "Select backup copy", "", "JSON Files (*.json)")
        if not path:
            return
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем формат
            if 'items' not in data:
                raise ValueError("Invalid backup file format")
            
            reply = QMessageBox.question(self, "Restore", 
                f"Восстановить {len(data['items'])} movies?\n"
                "Current favorites will be replaced!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.favorites._items = data['items']
                self.favorites._user_data = {int(k): v for k, v in data.get('user_data', {}).items()}
                self.favorites.save()
                self.tab_fav.refresh()
                
                QMessageBox.information(self, "Restore", 
                    f"Favorites восстановлено!\nФильмов: {len(data['items'])}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error restore: {str(e)}")
    
    def show_shortcuts(self):
        """Показывает список горячих клавиш"""
        shortcuts = """
        ⌨️ Keyboard shortcuts:
        
        Ctrl+Return - Run search
        Ctrl+R - Reset filters
        F5 - Refresh current tab
        F11 - Fullscreen mode
        
        Ctrl+E - Export to CSV
        Ctrl+Shift+E - Export to Excel
        Ctrl+, - Settings
        Ctrl+Q - Exit
        
        Double click - Movie details
        Right click - Context menu
        """
        QMessageBox.information(self, "Keyboard shortcuts", shortcuts)
    
    def show_about(self):
        """Показывает информацию о программе"""
        about_text = f"""
        <h2>TMDB Database Desktop</h2>
        <p><b>Version:</b> {APP_BUILD}</p>
        <p><b>Autor:</b> Dmitriy Koenig</p>
        <p><b>Description:</b> An advanced client for working with the TMDB database</p>
        
        <h3>Features:</h3>
        <ul>
          <li>🔍 Advanced search with filters</li>
          <li>📊 Analytics and data visualization</li>
          <li>⭐ Favorites management with tags and notes</li>
          <li>🎬 TMDB integration for posters</li>
          <li>💾 Export to CSV and Excel</li>
          <li>🎨 Modern dark interface</li>
        </ul>
        
        <p><b>Tech stack:</b> Python, PyQt6, MySQL, MongoDB, Matplotlib</p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("About")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(about_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

# ---------- Жанр/Yearы (оригинальная вкладка) ----------
class GenreYearTab(QWidget):
    def __init__(self, db, lw, favorites_sink, notify=lambda msg: None):
        super().__init__()
        self.db, self.lw = db, lw
        self.favorites_sink = favorites_sink
        self.notify = notify
        self.on_fav_changed = lambda: None
        
        main = QVBoxLayout(self)
        box = QGroupBox("Search by genre and year")
        form = QFormLayout(box)
        
        self.cb_genre = QComboBox()
        self.sb_year_from = QSpinBox()
        self.sb_year_to = QSpinBox()
        self.sb_year_from.setRange(1900, 2100)
        self.sb_year_to.setRange(1900, 2100)
        self.sb_limit = QSpinBox()
        self.sb_limit.setRange(1, 500)
        self.sb_limit.setValue(100)
        
        form.addRow("Genre:", self.cb_genre)
        form.addRow("From year:", self.sb_year_from)
        form.addRow("To year:", self.sb_year_to)
        form.addRow("Limit:", self.sb_limit)
        main.addWidget(box)
        
        row = QHBoxLayout()
        self.btn_search = AnimatedButton("🔍 Search")
        self.btn_details = AnimatedButton("📋 Details")
        self.btn_add_fav = AnimatedButton("⭐ Add to favorites")
        self.btn_export = AnimatedButton("📊 Export CSV")
        
        row.addWidget(self.btn_search)
        row.addStretch(1)
        row.addWidget(self.btn_details)
        row.addWidget(self.btn_add_fav)
        row.addWidget(self.btn_export)
        main.addLayout(row)
        
        self.table = QTableView()
        self.model = DataFrameModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self.open_details)
        self.table.horizontalHeader().setStretchLastSection(True)
        main.addWidget(self.table, 1)
        
        self.btn_search.clicked.connect(self.on_search)
        self.btn_export.clicked.connect(lambda: save_df_to_csv(self, self.model.dataframe(), "genre_year_results.csv"))
        self.btn_add_fav.clicked.connect(self.on_add_favorite)
        self.btn_details.clicked.connect(self.open_details)
        
        # Загружаем жанры
        try:
            genres = self.db.get_available_genres()
            names = [g["name"] for g in genres] if genres else []
            self.cb_genre.addItems(names or ["Comedy","Action","Drama"])
        except Exception:
            self.cb_genre.addItems(["Comedy","Action","Drama"])
        
        # Загружаем диапазон годов
        try:
            y_min, y_max = self.db.get_year_range()
        except Exception:
            y_min, y_max = 1980, 2025
        self.sb_year_from.setValue(y_min)
        self.sb_year_to.setValue(y_max)
    
    def open_details(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            self.notify("Select a row")
            return
        r = sel[0].row()
        row = self.model.dataframe().iloc[r].to_dict()
        fid = row.get("film_id")
        if fid is None:
            self.notify("Could not determine film_id")
            return
        FilmDialog(self.db, int(fid), self).exec()
    
    def on_search(self):
        genre = self.cb_genre.currentText()
        y1, y2 = int(self.sb_year_from.value()), int(self.sb_year_to.value())
        if y1 > y2:
            self.notify("The starting year is more important than the end year")
            return
        try:
            films, total = self.db.search_by_genre_and_years(genre, y1, y2, 0, int(self.sb_limit.value()))
            df = pd().DataFrame(films) if films else pd().DataFrame()
            self.model.set_dataframe(df)
            self.table.resizeColumnsToContents()
            try:
                self.lw.log_search("genre_year", {"genre": genre, "start_year": y1, "end_year": y2}, int(total))
            except Exception:
                pass
            if not films:
                self.notify("Nothing found")
            else:
                self.notify(f"Found: {total} movies")
        except Exception as e:
            QMessageBox.critical(self, "Search error", str(e))
    
    def on_add_favorite(self):
        df = self.model.dataframe()
        if df.empty:
            self.notify("No data to add")
            return
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        if not rows:
            self.notify("Select at least one row")
            return
        added = 0
        for r in rows:
            item = df.iloc[r].to_dict()
            added += self.favorites_sink.add(item)
        if added > 0:
            self.on_fav_changed()
            self.notify(f"Added to favorites: {added}")
        else:
            self.notify("These films are already in favorites")

# ---------- main ----------
def main():
    set_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName("TMDB base Desktop")
    app.setOrganizationName("Dmitriy")
    
    # Устанавливаем тёмную тему
    set_dark_palette(app)
    
    # Показываем заставку
    from PyQt6.QtWidgets import QSplashScreen
    splash = QSplashScreen(QPixmap(), Qt.WindowType.WindowStaysOnTopHint)
    splash.showMessage("Loading TMDB base Desktop v3...", 
                      Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                      QColor(255, 255, 255))
    splash.show()
    app.processEvents()
    
    # Создаём главное окно
    w = MainWindow()
    w.show()
    splash.finish(w)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()