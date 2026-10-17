"""
app.py - the Flask application (all routes live here).

A "route" is a Python function that runs when the browser visits a URL.
Each route does the same 3 things:
    1. read the request (URL, form, filters)
    2. run SQL through database.py
    3. render_template(...) -> Jinja fills an HTML page with the rows

Run with:  python app.py    then open  http://127.0.0.1:5000
"""
from datetime import date

import psycopg2
import psycopg2.errors
from flask import Flask, flash, redirect, render_template, request, url_for

import config
import database as db

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

SEVERITY_LEVELS = ["LOW", "MODERATE", "HIGH", "SEVERE"]   # stored in HEATWAVE_FORECAST
ALERT_LEVELS = ["YELLOW", "ORANGE", "RED"]                # stored in HEATWAVE_ADVISORY
STATION_STATUSES = ["Active", "Inactive"]
HOT_LIMIT = 40  # temperatures above this (deg C) are highlighted


# ---------------------------------------------------------------- helpers
@app.context_processor
def inject_globals():
    """Values available in EVERY template (used by the top bar)."""
    return {"today": date.today().strftime("%A, %d %B %Y")}


@app.errorhandler(psycopg2.OperationalError)
def database_down(error):
    """Shown when PostgreSQL is off or the .env details are wrong."""
    return ("<h2>Cannot connect to PostgreSQL</h2>"
            "<p>Check your <b>.env</b> file and make sure PostgreSQL is running.</p>"
            f"<pre>{error}</pre>"), 500


def get_text(name):
    """Read ?name=value from the URL. Empty text becomes None."""
    value = request.args.get(name, "").strip()
    return value or None


def get_number(name):
    """Read a number from the URL. Bad or empty input becomes None."""
    value = get_text(name)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        flash(f"'{value}' is not a valid number for {name}.", "error")
        return None


def get_date(name):
    """Read a YYYY-MM-DD date from the URL. Bad or empty input becomes None."""
    value = get_text(name)
    if value is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        flash(f"'{value}' is not a valid date.", "error")
        return None


def like(value):
    """'del' -> '%del%' so ILIKE finds it anywhere in the text."""
    return f"%{value}%" if value else None


def all_regions():
    return db.query_all("SELECT region_id, region_name FROM region ORDER BY region_name")


def to_float(value):
    """Decimal -> float (or None). Needed because JSON cannot hold Decimal."""
    return float(value) if value is not None else None


# -------------------------------------------------------------- dashboard
@app.route("/")
def dashboard():
    # KPI cards: each number is one COUNT query.
    kpi = {
        "regions": db.query_one("SELECT COUNT(*) AS n FROM region")["n"],
        "stations": db.query_one("SELECT COUNT(*) AS n FROM weather_station")["n"],
        "forecasts": db.query_one("""
            SELECT COUNT(*) AS n FROM heatwave_forecast
            WHERE make_date(year, month, day) =
                  (SELECT MAX(make_date(year, month, day)) FROM heatwave_forecast)
        """)["n"],
        "advisories": db.query_one("""
            SELECT COUNT(*) AS n FROM heatwave_advisory
            WHERE make_date(year, month, day) =
                  (SELECT MAX(make_date(year, month, day)) FROM heatwave_advisory)
        """)["n"],
    }

    # Highest reading at each station, then the 5 hottest stations overall.
    # Used by the highlight widget (big temperature + India map pins).
    hottest = db.query_all("""
        SELECT * FROM (
            SELECT DISTINCT ON (s.station_id)
                   o.observation_date, o.temperature, s.station_name,
                   s.latitude, s.longitude, r.region_name, r.state
            FROM weather_observation o
            JOIN weather_station s ON s.station_id = o.station_id
            JOIN region r ON r.region_id = s.region_id
            ORDER BY s.station_id, o.temperature DESC, o.observation_date DESC
        ) t
        ORDER BY temperature DESC
        LIMIT 5
    """)
    pins = [{"name": h["station_name"], "lat": float(h["latitude"]),
             "lon": float(h["longitude"]), "temp": float(h["temperature"])} for h in hottest]

    severity_by_region = db.query_all("""
        SELECT DISTINCT ON (r.region_id)
               r.region_id, r.region_name, f.max_temperature, f.severity_level
        FROM region r
        LEFT JOIN heatwave_forecast f ON f.region_id = r.region_id
        ORDER BY r.region_id,
                 make_date(f.year, f.month, f.day) DESC NULLS LAST, f.forecast_id DESC
    """)
    for row in severity_by_region:
        row["percent"] = min(100, round(float(row["max_temperature"] or 0) / 50 * 100))

    observations = db.query_all("""
        SELECT o.observation_id, o.observation_date, o.temperature, o.humidity,
               s.station_name, r.region_name
        FROM weather_observation o
        JOIN weather_station s ON s.station_id = o.station_id
        JOIN region r ON r.region_id = s.region_id
        ORDER BY o.observation_date DESC, o.observation_id DESC
        LIMIT 5
    """)

    forecasts = db.query_all("""
        SELECT f.forecast_id, make_date(f.year, f.month, f.day) AS forecast_date,
               f.max_temperature, f.severity_level, r.region_name
        FROM heatwave_forecast f
        JOIN region r ON r.region_id = f.region_id
        ORDER BY forecast_date DESC, f.forecast_id DESC
        LIMIT 5
    """)

    advisories = db.query_all("""
        SELECT a.advisory_id, make_date(a.year, a.month, a.day) AS advisory_date,
               a.alert_level, a.message, r.region_name
        FROM heatwave_advisory a
        JOIN heatwave_forecast f ON f.forecast_id = a.forecast_id
        JOIN region r ON r.region_id = f.region_id
        ORDER BY advisory_date DESC, a.advisory_id DESC
        LIMIT 4
    """)

    # Heat Severity Map: for every region, its latest forecast + its station's position
    # + the station's latest reading + the latest advisory for that forecast.
    # LEFT JOIN LATERAL = "for each row on the left, run this small sub-query".
    map_rows = db.query_all("""
        SELECT DISTINCT ON (r.region_id)
               r.region_id, r.region_name, r.state, r.climate_zone,
               s.station_name, s.status, s.latitude, s.longitude,
               make_date(f.year, f.month, f.day) AS forecast_date,
               f.max_temperature, f.severity_level,
               o.temperature AS obs_temp, o.humidity AS obs_humidity,
               adv.advisory_id, adv.alert_level, adv.message AS alert_message,
               (SELECT COUNT(*) FROM advisory_stakeholder x
                WHERE x.advisory_id = adv.advisory_id) AS notified
        FROM region r
        JOIN heatwave_forecast f ON f.region_id = r.region_id
        JOIN weather_station s ON s.region_id = r.region_id
        LEFT JOIN LATERAL (
            SELECT temperature, humidity FROM weather_observation
            WHERE station_id = s.station_id
            ORDER BY observation_date DESC, observation_id DESC LIMIT 1
        ) o ON TRUE
        LEFT JOIN LATERAL (
            SELECT advisory_id, alert_level, message FROM heatwave_advisory
            WHERE forecast_id = f.forecast_id
            ORDER BY make_date(year, month, day) DESC, advisory_id DESC LIMIT 1
        ) adv ON TRUE
        WHERE s.latitude IS NOT NULL AND s.longitude IS NOT NULL
          AND f.max_temperature IS NOT NULL
        ORDER BY r.region_id,
                 make_date(f.year, f.month, f.day) DESC, f.forecast_id DESC, s.station_id
    """)
    map_points = [
        {"name": r["region_name"], "state": r["state"], "climate": r["climate_zone"],
         "lat": float(r["latitude"]), "lon": float(r["longitude"]),
         "temp": float(r["max_temperature"]), "severity": r["severity_level"],
         "fdate": r["forecast_date"].strftime("%d %b %Y"),
         "station": r["station_name"], "status": r["status"],
         "obs_temp": to_float(r["obs_temp"]), "obs_hum": to_float(r["obs_humidity"]),
         "alert": r["alert_level"], "message": r["alert_message"], "notified": r["notified"],
         "region_url": url_for("region_detail", region_id=r["region_id"]),
         "adv_url": (url_for("advisory_detail", advisory_id=r["advisory_id"])
                     if r["advisory_id"] else None)}
        for r in map_rows
    ]

    return render_template("dashboard.html", kpi=kpi, hottest=hottest, pins=pins,
                           map_points=map_points,
                           severity_by_region=severity_by_region,
                           observations=observations, forecasts=forecasts,
                           advisories=advisories, hot_limit=HOT_LIMIT)


# ---------------------------------------------------------------- regions
@app.route("/regions")
def regions():
    q = get_text("q")
    state = get_text("state")

    # LEFT JOIN keeps regions that have 0 stations. COUNT counts stations.
    # The sub-query finds the newest forecast's severity for each region.
    # "(%(q)s IS NULL OR ...)" means: ignore the filter when it is empty.
    rows = db.query_all("""
        SELECT r.region_id, r.region_name, r.state, r.climate_zone,
               COUNT(s.station_id) AS station_count,
               (SELECT f.severity_level FROM heatwave_forecast f
                WHERE f.region_id = r.region_id
                ORDER BY make_date(f.year, f.month, f.day) DESC, f.forecast_id DESC
                LIMIT 1) AS latest_severity
        FROM region r
        LEFT JOIN weather_station s ON s.region_id = r.region_id
        WHERE (%(q)s IS NULL OR r.region_name ILIKE %(like)s
               OR r.state ILIKE %(like)s OR r.climate_zone ILIKE %(like)s)
          AND (%(state)s IS NULL OR r.state = %(state)s)
        GROUP BY r.region_id
        ORDER BY r.region_id
    """, {"q": q, "like": like(q), "state": state})

    states = db.query_all("SELECT DISTINCT state FROM region ORDER BY state")
    return render_template("regions.html", regions=rows, states=states, q=q, state=state)


@app.route("/regions/<int:region_id>")
def region_detail(region_id):
    region = db.query_one("SELECT * FROM region WHERE region_id = %s", (region_id,))
    if region is None:
        flash("Region not found.", "error")
        return redirect(url_for("regions"))

    stations = db.query_all(
        "SELECT * FROM weather_station WHERE region_id = %s ORDER BY station_id", (region_id,))

    observations = db.query_all("""
        SELECT o.observation_id, o.observation_date, o.temperature, o.humidity, s.station_name
        FROM weather_observation o
        JOIN weather_station s ON s.station_id = o.station_id
        WHERE s.region_id = %s
        ORDER BY o.observation_date DESC
    """, (region_id,))

    forecasts = db.query_all("""
        SELECT forecast_id, make_date(year, month, day) AS forecast_date,
               max_temperature, severity_level
        FROM heatwave_forecast WHERE region_id = %s
        ORDER BY forecast_date DESC
    """, (region_id,))

    advisories = db.query_all("""
        SELECT a.advisory_id, make_date(a.year, a.month, a.day) AS advisory_date,
               a.alert_level, a.message
        FROM heatwave_advisory a
        JOIN heatwave_forecast f ON f.forecast_id = a.forecast_id
        WHERE f.region_id = %s
        ORDER BY advisory_date DESC
    """, (region_id,))

    return render_template("region_detail.html", region=region, stations=stations,
                           observations=observations, forecasts=forecasts,
                           advisories=advisories)


# --------------------------------------------------------------- stations
@app.route("/stations")
def stations():
    q = get_text("q")
    status = get_text("status")
    rows = db.query_all("""
        SELECT s.station_id, s.station_name, s.latitude, s.longitude, s.status,
               r.region_name
        FROM weather_station s
        JOIN region r ON r.region_id = s.region_id
        WHERE (%(q)s IS NULL OR s.station_name ILIKE %(like)s OR r.region_name ILIKE %(like)s)
          AND (%(status)s IS NULL OR s.status = %(status)s)
        ORDER BY s.station_id
    """, {"q": q, "like": like(q), "status": status})
    return render_template("stations.html", stations=rows, q=q, status=status,
                           statuses=STATION_STATUSES)


def check_station_form(form):
    """Validate the station form. Returns (clean_values, list_of_errors)."""
    errors = []
    name = form.get("station_name", "").strip()
    status = form.get("status", "")
    region_id = form.get("region_id", "")

    if not name:
        errors.append("Station name is required.")
    elif len(name) > 100:
        errors.append("Station name must be 100 characters or fewer.")

    try:
        latitude = float(form.get("latitude", ""))
        if not -90 <= latitude <= 90:
            errors.append("Latitude must be between -90 and 90.")
    except ValueError:
        latitude = None
        errors.append("Latitude must be a number.")

    try:
        longitude = float(form.get("longitude", ""))
        if not -180 <= longitude <= 180:
            errors.append("Longitude must be between -180 and 180.")
    except ValueError:
        longitude = None
        errors.append("Longitude must be a number.")

    if status not in STATION_STATUSES:
        errors.append("Choose Active or Inactive.")

    if not region_id.isdigit() or db.query_one(
            "SELECT 1 FROM region WHERE region_id = %s", (int(region_id),)) is None:
        errors.append("Choose a valid region.")

    clean = {"station_name": name, "latitude": form.get("latitude", ""),
             "longitude": form.get("longitude", ""), "status": status,
             "region_id": int(region_id) if region_id.isdigit() else None}
    return clean, errors


@app.route("/stations/add", methods=["GET", "POST"])
def station_add():
    if request.method == "POST":
        clean, errors = check_station_form(request.form)
        if not errors:
            db.execute("""
                INSERT INTO weather_station
                    (station_id, station_name, latitude, longitude, status, region_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (db.next_id("weather_station", "station_id"), clean["station_name"],
                  clean["latitude"], clean["longitude"], clean["status"], clean["region_id"]))
            flash("Station added.", "success")
            return redirect(url_for("stations"))
        for message in errors:
            flash(message, "error")
        return render_template("station_form.html", station=clean, regions=all_regions(),
                               statuses=STATION_STATUSES, mode="Add")

    blank = {"station_name": "", "latitude": "", "longitude": "",
             "status": "Active", "region_id": None}
    return render_template("station_form.html", station=blank, regions=all_regions(),
                           statuses=STATION_STATUSES, mode="Add")


@app.route("/stations/<int:station_id>/edit", methods=["GET", "POST"])
def station_edit(station_id):
    station = db.query_one("SELECT * FROM weather_station WHERE station_id = %s", (station_id,))
    if station is None:
        flash("Station not found.", "error")
        return redirect(url_for("stations"))

    if request.method == "POST":
        clean, errors = check_station_form(request.form)
        if not errors:
            db.execute("""
                UPDATE weather_station
                SET station_name = %s, latitude = %s, longitude = %s,
                    status = %s, region_id = %s
                WHERE station_id = %s
            """, (clean["station_name"], clean["latitude"], clean["longitude"],
                  clean["status"], clean["region_id"], station_id))
            flash("Station updated.", "success")
            return redirect(url_for("stations"))
        for message in errors:
            flash(message, "error")
        clean["station_id"] = station_id
        station = clean

    return render_template("station_form.html", station=station, regions=all_regions(),
                           statuses=STATION_STATUSES, mode="Edit")





# ----------------------------------------------------------- observations
@app.route("/observations")
def observations():
    filters = {
        "date": get_date("date"),
        "region_id": get_text("region_id"),
        "min_temp": get_number("min_temp"),
        "max_humidity": get_number("max_humidity"),
    }
    region_id = int(filters["region_id"]) if (filters["region_id"] or "").isdigit() else None

    rows = db.query_all("""
        SELECT o.observation_id, o.observation_date, o.temperature, o.humidity,
               s.station_name, r.region_name
        FROM weather_observation o
        JOIN weather_station s ON s.station_id = o.station_id
        JOIN region r ON r.region_id = s.region_id
        WHERE (%(date)s IS NULL OR o.observation_date = %(date)s)
          AND (%(region_id)s IS NULL OR r.region_id = %(region_id)s)
          AND (%(min_temp)s IS NULL OR o.temperature >= %(min_temp)s)
          AND (%(max_humidity)s IS NULL OR o.humidity <= %(max_humidity)s)
        ORDER BY o.observation_date DESC, o.observation_id DESC
    """, {"date": filters["date"], "region_id": region_id,
          "min_temp": filters["min_temp"], "max_humidity": filters["max_humidity"]})

    # Data for the Chart.js line chart (oldest on the left).
    ordered = sorted(rows, key=lambda r: (r["observation_date"], r["observation_id"]))
    chart = {
        "type": "line",
        "data": {
            "labels": [f'{r["observation_date"].strftime("%d %b")} {r["region_name"]}'
                       for r in ordered],
            "datasets": [
                {"label": "Temperature (°C)", "data": [float(r["temperature"]) for r in ordered],
                 "borderColor": "#f97316", "backgroundColor": "#f97316", "tension": 0.3},
                {"label": "Humidity (%)", "data": [float(r["humidity"]) for r in ordered],
                 "borderColor": "#3b82f6", "backgroundColor": "#3b82f6", "tension": 0.3},
            ],
        },
        "options": {"responsive": True, "maintainAspectRatio": False},
    }
    return render_template("observations.html", observations=rows, regions=all_regions(),
                           chart=chart, f={"date": filters["date"] or "", "region_id": region_id,
                                           "min_temp": request.args.get("min_temp", ""),
                                           "max_humidity": request.args.get("max_humidity", "")},
                           hot_limit=HOT_LIMIT)
# -------------------------------------------------------------- forecasts
@app.route("/forecasts")
def forecasts():
    severity = get_text("severity")
    region_text = get_text("region_id")
    region_id = int(region_text) if (region_text or "").isdigit() else None

    rows = db.query_all("""
        SELECT f.forecast_id, make_date(f.year, f.month, f.day) AS forecast_date,
               f.max_temperature, f.severity_level, r.region_name
        FROM heatwave_forecast f
        JOIN region r ON r.region_id = f.region_id
        WHERE (%(severity)s IS NULL OR f.severity_level = %(severity)s)
          AND (%(region_id)s IS NULL OR f.region_id = %(region_id)s)
        ORDER BY forecast_date DESC, f.forecast_id DESC
    """, {"severity": severity, "region_id": region_id})

    # Build one bar-dataset per region, one label per date.
    dates = sorted({r["forecast_date"] for r in rows})
    region_names = sorted({r["region_name"] for r in rows})
    colours = ["#f97316", "#0f1b33", "#3b82f6", "#22c55e", "#a855f7", "#eab308"]
    datasets = []
    for i, name in enumerate(region_names):
        temps = {r["forecast_date"]: float(r["max_temperature"])
                 for r in rows if r["region_name"] == name}
        datasets.append({"type": "bar", "label": name,
                         "data": [temps.get(d) for d in dates],
                         "backgroundColor": colours[i % len(colours)], "borderRadius": 6})
    datasets.append({"type": "line", "label": f"{HOT_LIMIT}°C danger line",
                     "data": [HOT_LIMIT] * len(dates), "borderColor": "#dc2626",
                     "borderDash": [6, 6], "pointRadius": 0})
    chart = {"type": "bar",
             "data": {"labels": [d.strftime("%d %b %Y") for d in dates], "datasets": datasets},
             "options": {"responsive": True, "maintainAspectRatio": False,
                         "scales": {"y": {"title": {"display": True, "text": "Max temperature (°C)"}}}}}

    return render_template("forecasts.html", forecasts=rows, regions=all_regions(),
                           severities=SEVERITY_LEVELS, severity=severity,
                           region_id=region_id, chart=chart, hot_limit=HOT_LIMIT)


# ------------------------------------------------------------- advisories
ADVISORY_LIST_SQL = """
    SELECT a.advisory_id, make_date(a.year, a.month, a.day) AS advisory_date,
           a.alert_level, a.message, r.region_name
    FROM heatwave_advisory a
    JOIN heatwave_forecast f ON f.forecast_id = a.forecast_id
    JOIN region r ON r.region_id = f.region_id
"""


@app.route("/advisories")
def advisories():
    level = get_text("level")
    q = get_text("q")
    rows = db.query_all(ADVISORY_LIST_SQL + """
        WHERE (%(level)s IS NULL OR a.alert_level = %(level)s)
          AND (%(q)s IS NULL OR a.message ILIKE %(like)s OR r.region_name ILIKE %(like)s)
        ORDER BY advisory_date DESC, a.advisory_id DESC
    """, {"level": level, "q": q, "like": like(q)})
    return render_template("advisories.html", advisories=rows, levels=ALERT_LEVELS,
                           level=level, q=q)


@app.route("/advisories/<int:advisory_id>")
def advisory_detail(advisory_id):
    advisory = db.query_one("""
        SELECT a.advisory_id, make_date(a.year, a.month, a.day) AS advisory_date,
               a.alert_level, a.message, f.forecast_id, f.max_temperature,
               f.severity_level, r.region_id, r.region_name, r.state
        FROM heatwave_advisory a
        JOIN heatwave_forecast f ON f.forecast_id = a.forecast_id
        JOIN region r ON r.region_id = f.region_id
        WHERE a.advisory_id = %s
    """, (advisory_id,))
    if advisory is None:
        flash("Advisory not found.", "error")
        return redirect(url_for("advisories"))

    # Many-to-many: ADVISORY_STAKEHOLDER links advisories to stakeholders.
    stakeholders = db.query_all("""
        SELECT s.stakeholder_id, s.stakeholder_name, s.stakeholder_type,
               s.contact_no, r.region_name
        FROM advisory_stakeholder x
        JOIN stakeholder s ON s.stakeholder_id = x.stakeholder_id
        JOIN region r ON r.region_id = s.region_id
        WHERE x.advisory_id = %s
        ORDER BY s.stakeholder_name
    """, (advisory_id,))
    return render_template("advisory_detail.html", advisory=advisory, stakeholders=stakeholders)


def advisory_form_data():
    """Lists needed by the Add/Edit advisory form (dropdown + checkboxes)."""
    forecast_options = db.query_all("""
        SELECT f.forecast_id, make_date(f.year, f.month, f.day) AS forecast_date,
               f.severity_level, r.region_name
        FROM heatwave_forecast f JOIN region r ON r.region_id = f.region_id
        ORDER BY forecast_date DESC, f.forecast_id DESC
    """)
    stakeholder_options = db.query_all("""
        SELECT s.stakeholder_id, s.stakeholder_name, r.region_name
        FROM stakeholder s JOIN region r ON r.region_id = s.region_id
        ORDER BY r.region_name, s.stakeholder_name
    """)
    return forecast_options, stakeholder_options


def check_advisory_form(form):
    """Validate the advisory form. Returns (clean_values, errors)."""
    errors = []
    forecast_id = form.get("forecast_id", "")
    level = form.get("alert_level", "")
    message = form.get("message", "").strip()
    chosen = [int(x) for x in form.getlist("stakeholder_ids") if x.isdigit()]

    if not forecast_id.isdigit() or db.query_one(
            "SELECT 1 FROM heatwave_forecast WHERE forecast_id = %s", (int(forecast_id),)) is None:
        errors.append("Choose a valid forecast.")
    try:
        issued = date.fromisoformat(form.get("advisory_date", ""))
    except ValueError:
        issued = None
        errors.append("Enter a valid advisory date.")
    if level not in ALERT_LEVELS:
        errors.append("Choose YELLOW, ORANGE or RED.")
    if len(message) < 10:
        errors.append("Message must be at least 10 characters.")

    clean = {"forecast_id": int(forecast_id) if forecast_id.isdigit() else None,
             "advisory_date": issued, "alert_level": level, "message": message,
             "stakeholder_ids": chosen}
    return clean, errors


def render_advisory_form(advisory, mode):
    forecast_options, stakeholder_options = advisory_form_data()
    return render_template("advisory_form.html", advisory=advisory, mode=mode,
                           forecast_options=forecast_options,
                           stakeholder_options=stakeholder_options, levels=ALERT_LEVELS)


@app.route("/advisories/add", methods=["GET", "POST"])
def advisory_add():
    if request.method == "POST":
        clean, errors = check_advisory_form(request.form)
        if not errors:
            new_id = db.next_id("heatwave_advisory", "advisory_id")
            d = clean["advisory_date"]
            # One transaction: the advisory AND its stakeholder links are saved together.
            statements = [("""
                INSERT INTO heatwave_advisory
                    (advisory_id, day, month, year, alert_level, message, forecast_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (new_id, d.day, d.month, d.year, clean["alert_level"],
                  clean["message"], clean["forecast_id"]))]
            for sid in clean["stakeholder_ids"]:
                statements.append(("INSERT INTO advisory_stakeholder (advisory_id, stakeholder_id) "
                                   "VALUES (%s, %s)", (new_id, sid)))
            db.run_in_transaction(statements)
            flash("Advisory created.", "success")
            return redirect(url_for("advisory_detail", advisory_id=new_id))
        for message in errors:
            flash(message, "error")
        return render_advisory_form(clean, "Create")

    blank = {"forecast_id": None, "advisory_date": date.today(), "alert_level": "YELLOW",
             "message": "", "stakeholder_ids": []}
    return render_advisory_form(blank, "Create")


@app.route("/advisories/<int:advisory_id>/edit", methods=["GET", "POST"])
def advisory_edit(advisory_id):
    current = db.query_one("""
        SELECT advisory_id, make_date(year, month, day) AS advisory_date,
               alert_level, message, forecast_id
        FROM heatwave_advisory WHERE advisory_id = %s
    """, (advisory_id,))
    if current is None:
        flash("Advisory not found.", "error")
        return redirect(url_for("advisories"))

    if request.method == "POST":
        clean, errors = check_advisory_form(request.form)
        if not errors:
            d = clean["advisory_date"]
            statements = [
                ("""UPDATE heatwave_advisory
                    SET day = %s, month = %s, year = %s, alert_level = %s,
                        message = %s, forecast_id = %s
                    WHERE advisory_id = %s""",
                 (d.day, d.month, d.year, clean["alert_level"], clean["message"],
                  clean["forecast_id"], advisory_id)),
                # Simplest way to edit a many-to-many list: delete old links, insert new ones.
                ("DELETE FROM advisory_stakeholder WHERE advisory_id = %s", (advisory_id,)),
            ]
            for sid in clean["stakeholder_ids"]:
                statements.append(("INSERT INTO advisory_stakeholder (advisory_id, stakeholder_id) "
                                   "VALUES (%s, %s)", (advisory_id, sid)))
            db.run_in_transaction(statements)
            flash("Advisory updated.", "success")
            return redirect(url_for("advisory_detail", advisory_id=advisory_id))
        for message in errors:
            flash(message, "error")
        clean["advisory_id"] = advisory_id
        return render_advisory_form(clean, "Edit")

    links = db.query_all("SELECT stakeholder_id FROM advisory_stakeholder WHERE advisory_id = %s",
                         (advisory_id,))
    current["stakeholder_ids"] = [row["stakeholder_id"] for row in links]
    return render_advisory_form(current, "Edit")


@app.route("/advisories/<int:advisory_id>/delete", methods=["POST"])
def advisory_delete(advisory_id):
    # Child rows (links) must be deleted before the parent advisory.
    db.run_in_transaction([
        ("DELETE FROM advisory_stakeholder WHERE advisory_id = %s", (advisory_id,)),
        ("DELETE FROM heatwave_advisory WHERE advisory_id = %s", (advisory_id,)),
    ])
    flash("Advisory deleted.", "success")
    return redirect(url_for("advisories"))


# ----------------------------------------------------------- stakeholders
@app.route("/stakeholders")
def stakeholders():
    q = get_text("q")
    stype = get_text("type")
    rows = db.query_all("""
        SELECT s.stakeholder_id, s.stakeholder_name, s.stakeholder_type,
               s.contact_no, r.region_name
        FROM stakeholder s
        JOIN region r ON r.region_id = s.region_id
        WHERE (%(q)s IS NULL OR s.stakeholder_name ILIKE %(like)s OR r.region_name ILIKE %(like)s
               OR s.contact_no ILIKE %(like)s)
          AND (%(type)s IS NULL OR s.stakeholder_type = %(type)s)
        ORDER BY s.stakeholder_id
    """, {"q": q, "like": like(q), "type": stype})

    # Second query: every advisory-stakeholder link. Python then groups them
    # by stakeholder so the template can list them next to each person.
    links = db.query_all("""
        SELECT x.stakeholder_id, a.advisory_id, a.alert_level
        FROM advisory_stakeholder x
        JOIN heatwave_advisory a ON a.advisory_id = x.advisory_id
        ORDER BY a.advisory_id
    """)
    by_stakeholder = {}
    for link in links:
        by_stakeholder.setdefault(link["stakeholder_id"], []).append(link)

    types = db.query_all("SELECT DISTINCT stakeholder_type FROM stakeholder ORDER BY 1")
    return render_template("stakeholders.html", stakeholders=rows, links=by_stakeholder,
                           types=types, q=q, stype=stype)


# ----------------------------------------------------------------- search
@app.route("/search")
def search():
    q = get_text("q")
    results = {"regions": [], "stations": [], "advisories": [], "stakeholders": []}
    if q:
        p = {"like": like(q)}
        results["regions"] = db.query_all("""
            SELECT region_id, region_name, state, climate_zone FROM region
            WHERE region_name ILIKE %(like)s OR state ILIKE %(like)s OR climate_zone ILIKE %(like)s
        """, p)
        results["stations"] = db.query_all("""
            SELECT s.station_id, s.station_name, s.status, r.region_name
            FROM weather_station s JOIN region r ON r.region_id = s.region_id
            WHERE s.station_name ILIKE %(like)s OR s.status ILIKE %(like)s
        """, p)
        results["advisories"] = db.query_all(ADVISORY_LIST_SQL + """
            WHERE a.message ILIKE %(like)s OR a.alert_level ILIKE %(like)s
                  OR r.region_name ILIKE %(like)s
            ORDER BY advisory_date DESC
        """, p)
        results["stakeholders"] = db.query_all("""
            SELECT s.stakeholder_id, s.stakeholder_name, s.stakeholder_type, r.region_name
            FROM stakeholder s JOIN region r ON r.region_id = s.region_id
            WHERE s.stakeholder_name ILIKE %(like)s OR s.stakeholder_type ILIKE %(like)s
                  OR s.contact_no ILIKE %(like)s
        """, p)
    total = sum(len(v) for v in results.values())
    return render_template("search_results.html", q=q, results=results, total=total)


if __name__ == "__main__":
    app.run(debug=True)