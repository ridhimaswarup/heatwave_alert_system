from database import get_connection
import config

TABLES = [
    "region",
    "weather_station",
    "weather_observation",
    "heatwave_forecast",
    "heatwave_advisory",
    "stakeholder",
    "advisory_stakeholder",
]

print("Trying to connect with these settings:")
print("  host     =", config.DB_HOST)
print("  port     =", config.DB_PORT)
print("  database =", config.DB_NAME)
print("  user     =", config.DB_USER)
print()

try:
    conn = get_connection()
except Exception as e:
    print("Database connection FAILED.")
    print("Error:", e)
    raise SystemExit(1)

print("Database connected successfully!")
print()

cur = conn.cursor()
for table in TABLES:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f"  {table}: {count} rows")

cur.close()
conn.close()