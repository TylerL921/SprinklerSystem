# Imports
import psycopg2
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

# User Information - Adjust Accordingly
latLong = 44.099, -79.133 # Latitude and Longitude
hourlyD = ["temperature_2m", "precipitation"]
dailyD = ["precipitation_sum", "temperature_2m_max"]
timezone = "America/New_York"

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



# Process hourly data.
hourly = response.Hourly()

# Time - Database Key
dataH = {"date": pd.date_range(
	start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
	end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = hourly.Interval()),
	inclusive = "left"
)}

# Other Data
for i in range(len(hourlyD)):
    dataH[hourlyD[i]] = hourly.Variables(i).ValuesAsNumpy()
    

# Create Dataframe
hourly_dataframe = pd.DataFrame(data = dataH)
hourly_long = hourly_dataframe.melt(id_vars="date", var_name="tag", value_name="value")
print(hourly_long)




# Process daily data. The order of variables needs to be the same as requested.
daily = response.Daily()

# Date
dataD = {"date": pd.date_range(
	start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
	end = pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = daily.Interval()),
	inclusive = "left"
)}

# Other Data
for i in range(len(dailyD)):
    dataD[dailyD[i]] = daily.Variables(i).ValuesAsNumpy()

daily_dataframe = pd.DataFrame(data = dataD)
daily_long = daily_dataframe.melt(id_vars="date", var_name="tag", value_name="value")
print(daily_long)


# Connect to Postgres
