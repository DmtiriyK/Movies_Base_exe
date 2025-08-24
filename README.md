TMDB Movie Database — Desktop v3

A desktop client for exploring your local movies database with rich search, analytics and favorites. UI in English. Data lives in your own MySQL database (not Sakila). Actions and app events are additionally logged to MongoDB for auditing and analysis.

✨ Features

Quick & Advanced search by title, description, actor; filters by rating, years, runtime; sorting presets

Genres / Years tab for targeted discovery

Analytics: distribution by year, top genres, ratings histogram, average runtime by genre

Favorites with tags and notes; CSV/Excel export

Details modal with poster, rating, genres, cast; shortcuts for trailer and external pages

Settings: TMDB API key for posters, DB connection, cache controls

Keyboard shortcuts for search, refresh, export, fullscreen

🧱 Tech stack

Python, PyQt6, MySQL (primary data), MongoDB (logs), Matplotlib. Repository is primarily Python and licensed under Apache-2.0. 
GitHub

🖼 Screenshots

Put images into screenshots/ (already present in the repo) and keep names readable.

Quick search (empty)
screenshots/01_quick-search_empty.png

Results + Movie details
screenshots/02_quick-search_results_movie-details.png

Genres / Years
screenshots/03_genres-years_tab.png

Analytics overview
screenshots/05_analytics_overview.png

Favorites (empty state)
screenshots/11_favorites_empty.png

Settings dialog
screenshots/12_settings_modal_on_analytics.png

About dialog
screenshots/06_about_dialog.png

Menus (File / View / Tools / Help)
screenshots/07_menu_file_open.png, 08_menu_view_open.png, 09_menu_tools_open.png, 10_menu_help_open.png

📦 Project layout
.
├─ scripts/                 # helper scripts (import/export/seed, etc.)
├─ screenshots/             # images used in README
├─ docs/                    # extra docs/assets
├─ LICENSE
└─ README.md


(Папки scripts/, screenshots/, docs/ и лицензия видны в репозитории сейчас. ) 
GitHub

⚙️ Requirements

Python 3.10+

MySQL 8.x (local instance for the main dataset)

MongoDB 6.x (for app logs)

A TMDB API key for posters

🔧 Configuration

Create an .env at the repo root:

# MySQL (primary data)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=moviesdb
MYSQL_USER=root
MYSQL_PASSWORD=your_password

# MongoDB (logs)
MONGO_URI=mongodb://localhost:27017
MONGO_DB=tmdb_desktop_logs

# App
TMDB_API_KEY=your_tmdb_key
APP_LANG=en

▶️ Run locally
# 1) Create venv & install deps
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2) Launch the app
python main_gui3_en.py
# or, if you’ve wrapped it as a package:
# python -m tmdb_desktop


If you ship a packaged EXE later, add the link and command here.

🗄️ Data model (high level)

Relational core in MySQL (films, people, genres, links). App writes behavioral and error logs to MongoDB collections like:

app_events: actions, search queries, favorites ops

errors: exceptions with context

analytics_snapshots: optional precomputed stats

🧭 Keyboard shortcuts

Ctrl+Enter run search, Ctrl+R reset filters

F5 refresh current tab, F11 fullscreen

Ctrl+E CSV export, Ctrl+Shift+E Excel export

Ctrl+, settings, Ctrl+Q exit

Double click row → movie details; right click → context menu

🧼 Privacy & API

Posters use TMDB; the app does not ship TMDB data. You need your own API key.

Logs stay in your MongoDB unless you change the URI.

🧪 Smoke test

Populate MySQL with your movie dataset.

Set .env and start the app.

Quick search: type “star,” open movie details.

Analytics tab should render four charts.

Open Settings, paste TMDB key, test cache clear.

Add a movie to Favorites and export CSV.

🚀 Roadmap

i18n JSON dictionaries (EN already default)

Packaging: Windows installer

More analytics (per-actor, per-decade)

Better poster caching and retries

🤝 Contributing

PRs are welcome. Keep functions small, type-hinted, and add docstrings. For UI labels, prefer i18n wrappers over hard-coded strings.

📜 License

Apache-2.0. See LICENSE in the repo.
