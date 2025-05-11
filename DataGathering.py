# Imports
import psycopg2
import openmeteo_requests
import pandas as pd
import requests_cache
import pytz
from io import StringIO
from retry_requests import retry
from datetime import datetime

# User Information - Adjust Accordingly
latLong = 44.099, -79.133 # Latitude and Longitude
hourlyD = ["temperature_2m", "precipitation_probability", "precipitation", "relative_humidity_2m"] # Data you want for hourly table
dailyD = ["temperature_2m_min", "temperature_2m_max", "sunshine_duration", "daylight_duration", "precipitation_sum"] # Data you want for daily table
timezone = "America/New_York"

# Postgres Information
db = "SprinklerWeatherData" # Name of Database
h = "localhost" # Host
u = "postgres" # User
p = "postgres" # Password
pt = 5432 # Port

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
url = "https://api.open-meteo.com/v1/forecast"
params = {
	"latitude": latLong[0],
	"longitude": latLong[1],
    "daily": dailyD,
	"hourly": hourlyD,
    "timezone": timezone,
    "forecast_days": 3
}

# Gather the data from open meteo
responses = openmeteo.weather_api(url, params=params)
response = responses[0] # Note: Must change if querying for multiple locations

# Get current time in America/New_York timezone
now = datetime.now(pytz.timezone(timezone)).replace(minute=0, second=0, microsecond=0)


# Process hourly data.
hourly = response.Hourly()

# Time Column
dataH = {"time": pd.date_range(
	start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
	end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = hourly.Interval()),
	inclusive = "left"
)}

# Other Columns
for i in range(len(hourlyD)):
    dataH[hourlyD[i]] = hourly.Variables(i).ValuesAsNumpy()
    

# Create Hourly Dataframe
hourly_dataframe = pd.DataFrame(data = dataH)
hourly_dataframe["time"] = hourly_dataframe["time"].dt.tz_convert(timezone)
hourly_long = hourly_dataframe.melt(id_vars="time", var_name="tag", value_name="value")

# Keep only future rows (i.e., where time > now)
hourly_long = hourly_long[hourly_long["time"] >= now].reset_index(drop=True)
print(hourly_long)




# Process daily data.
daily = response.Daily()

# Date
dataD = {"time": pd.date_range(
	start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
	end = pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = daily.Interval()),
	inclusive = "left"
)}

# Other Columns
for i in range(len(dailyD)):
    dataD[dailyD[i]] = daily.Variables(i).ValuesAsNumpy()

# Create Daily Dataframe
daily_dataframe = pd.DataFrame(data = dataD)
daily_dataframe["time"] = daily_dataframe["time"].dt.tz_convert(timezone)
daily_long = daily_dataframe.melt(id_vars="time", var_name="tag", value_name="value")
print(daily_long)



# PostGres
# Connect to Postgres
conn = psycopg2.connect(database = db, user = u, host= h, password = p, port = pt)
cur = conn.cursor()

# Delete the predicted values in the tables
def clearFuture():
	# Delete data to be re-written
	cur.execute("DELETE FROM \"dailyFloat\" WHERE time >= date_trunc('day', now());")
	conn.commit()

	cur.execute("DELETE FROM \"hourlyFloat\" WHERE time >= date_trunc('hour', now());")
	conn.commit()
     
# Adds Dataframe to Postgres table
def updateTable(table, df):
    # Convert DataFrame to CSV-like format in memory
	buffer = StringIO()
	df.to_csv(buffer, index=False, header=False)
	buffer.seek(0)

	try:
		cur.copy_expert(
			f"COPY {table} (time, tag, value) FROM STDIN WITH CSV",
			buffer
		)
		conn.commit()
		print("Data inserted successfully.")
	except Exception as e:
		conn.rollback()
		print("Error inserting data:", e)

# Update Tables
clearFuture()
updateTable("\"dailyFloat\"", daily_long)
updateTable("\"hourlyFloat\"", hourly_long)

