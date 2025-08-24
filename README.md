TMDB Movie Database — Desktop v3
<p align="center"> <img src="screenshots/hero.png" alt="TMDB Desktop v3 — overview" width="100%"> </p> <p align="center"> <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a> <a href="https://www.qt.io/"><img src="https://img.shields.io/badge/PyQt6-desktop-41CD52?logo=qt&logoColor=white" alt="PyQt6"></a> <a href="#"><img src="https://img.shields.io/badge/MySQL-local-4479A1?logo=mysql&logoColor=white" alt="MySQL local"></a> <a href="#"><img src="https://img.shields.io/badge/MongoDB-logs-47A248?logo=mongodb&logoColor=white" alt="MongoDB logs"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache--2.0-blue.svg" alt="License"></a> </p>

A desktop client for exploring a local movies database with quick/advanced search, analytics, favorites and a clean dark UI.
Uses MySQL for primary data and MongoDB for app logs. Posters are loaded via TMDB API.

Table of contents

Features

Tech stack

Screenshots

Project layout

Getting started

Configuration

Keyboard shortcuts

Data & logging

Roadmap

License

✨ Features

Quick & Advanced search: title/actor/mode toggles, rating/year/runtime filters, preset sort

Genres / Years tab for targeted discovery

Analytics: distribution by year, top genres, ratings histogram, average runtime by genre

Favorites with tags & notes, CSV/Excel export

Movie details modal with poster, rating, genres, cast + shortcuts (Trailer, TMDB, IMDb)

Settings: TMDB API key, DB connection, cache control

Dark UI tuned for readability

🧱 Tech stack

Python 3.10+, PyQt6

MySQL as the primary store (your local DB, not Sakila)

MongoDB for logs and audit trail

Matplotlib for charts

Packaging/scripts in scripts/

🖼 Screenshots

Images live in screenshots/. If your filenames differ, adjust the paths below.

Search & Details
<img src="screenshots/01_quick-search_empty.png" width="49%"> <img src="screenshots/02_quick-search_results_movie-details.png" width="49%">

Genres / Years
<img src="screenshots/03_genres-years_tab.png" width="100%">

Analytics
<img src="screenshots/05_analytics_overview.png" width="100%">

Favorites & Settings
<img src="screenshots/07_favor.png" width="49%"> <img src="screenshots/12_settings_modal_on_analytics.png" width="49%">

About
<img src="screenshots/06_about_dialog.png" width="60%">


🗂 Project layout
.
├─ scripts/                # helper scripts (import/export/seed, etc.)
├─ screenshots/            # images used in README and promo
├─ docs/                   # extra docs / diagrams (optional)
├─ main_gui3_en.py         # app entry (or your package entry point)
├─ requirements.txt
└─ README.md

🚀 Getting started
# 1) Create venv & install deps
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt

# 2) Set environment (see .env example below)

# 3) Run the app
python main_gui3.py
# or, if packaged as a module:
# python -m tmdb_desktop

⚙️ Configuration

Create .env in the repo root:

# MySQL (primary data)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=*******
MYSQL_USER=root
MYSQL_PASSWORD=your_password

# MongoDB (logs)
MONGO_URI=mongodb://localhost:27017
MONGO_DB=tmdb_desktop_logs

# External
TMDB_API_KEY=your_tmdb_key

# UI
APP_LANG=en

⌨️ Keyboard shortcuts

Ctrl+Enter run search, Ctrl+R reset filters

F5 refresh current tab, F11 fullscreen

Ctrl+E export CSV, Ctrl+Shift+E export Excel

Ctrl+, settings, Ctrl+Q exit

Double-click row → details; Right-click → context menu

📊 Data & logging

Primary DB: your local MySQL instance with movies, people, genres, links.

Logging: app events, errors and optional analytics snapshots go to MongoDB:

app_events — user actions (search, favorites ops)

errors — exceptions with context

analytics_snapshots — optional precomputed stats


🗺️ Roadmap

i18n dictionaries (EN default already)

Packaging for Windows (.exe)

More analytics (per-actor trends, decades)

Smarter poster caching & retries

Optional Docker setup for DBs

📜 License

Apache-2.0 — see LICENSE
.
