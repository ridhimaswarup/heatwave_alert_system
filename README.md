# HeatWatch - Heatwave Alert System

College mini-project: a Flask + PostgreSQL dashboard for heatwave monitoring.
It stores weather readings, heatwave forecasts, advisories and stakeholders, and shows
the hottest places on an interactive India map.

## Setup (PyCharm)
1. Open this folder as a PyCharm project and create a virtual environment (venv).
2. In the PyCharm Terminal: `pip install -r requirements.txt`
3. Open `.env` and set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` to match pgAdmin.
4. Run `python test_connection.py` - you should see the row count of all 7 tables.
5. Run `python app.py` and open http://127.0.0.1:5000

Chart.js and Google Fonts load from the internet, so an internet connection is needed
for charts and fonts.

## How data moves
PostgreSQL -> `database.py` (psycopg2, parameterized SQL) -> route in `app.py`
-> `render_template()` -> Jinja loops in `templates/*.html` -> HTML in the browser.

## Files
| File | Job |
|---|---|
| `config.py` | Reads DB_* settings from `.env` |
| `database.py` | Connect + helpers: `query_all`, `query_one`, `execute`, `run_in_transaction`, `next_id` |
| `app.py` | Every route: dashboard, regions, stations (CRUD), observations, forecasts, advisories (CRUD), stakeholders, search |
| `test_connection.py` | Checks the database connection |
| `templates/base.html` | Sidebar, search bar and flash messages shared by all pages |
| `templates/_macros.html` | Reusable pieces: severity badge, temperature display, date format |
| `templates/*.html` | One page per route (dashboard, regions, stations, forecasts, advisories, ...) |
| `static/css/style.css` | Light theme, severity and alert colours, layout, animations, map styles |
| `static/js/script.js` | Count-up numbers, bar animations, small India map, Chart.js charts, dismissing messages |
| `static/js/india-map.js` | Heat Severity Map: state shapes coloured by forecast, zoom, hottest-regions list |
| `static/js/map-detail.js` | Shows the selected state's details (forecast, reading, advisory) beside the map |

## Features
- Dashboard: highest temperature, Heat Severity Map with click-to-zoom state details, KPI cards, severity by region, latest observations, forecasts and advisories
- Regions, stations (add, edit, delete), observations and forecasts with filters and charts
- Advisories (create, edit, delete) linked to stakeholders (many-to-many)
- Global search across regions, stations, advisories and stakeholders

## Design decisions
- Tables use plain INT keys, so new IDs are `MAX(id) + 1` (schema unchanged).
- Forecast/advisory dates are stored as Day, Month, Year; SQL joins them with `make_date(year, month, day)`.
- KPI "Latest Forecasts" and "Active Advisories" count rows on the newest date in the table.
- A station with observations cannot be deleted (foreign key); the app shows a message instead.
- Saving an advisory and its stakeholder links happens in one transaction, so both succeed or neither does.
- The map's state borders are simplified shapes, not survey-accurate.