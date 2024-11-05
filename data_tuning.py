import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": 22.737195,
    "longitude": 88.190791,
    "start_date": "2024-07-15",
    "end_date": "2024-10-27",
    "hourly": ["temperature_2m", "precipitation", "rain", "cloud_cover", "wind_speed_10m", "direct_radiation"],
    "daily": ["sunrise", "sunset", "daylight_duration"],
    "timezone": "Asia/Singapore",
    "tilt": 30
}
responses = openmeteo.weather_api(url, params=params)

# Process first location
response = responses[0]
print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
print(f"Elevation {response.Elevation()} m asl")
print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

# Process hourly data
hourly = response.Hourly()
hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
hourly_precipitation = hourly.Variables(1).ValuesAsNumpy()
hourly_cloud_cover = hourly.Variables(3).ValuesAsNumpy()
hourly_wind_speed_10m = hourly.Variables(4).ValuesAsNumpy()
hourly_direct_radiation = hourly.Variables(5).ValuesAsNumpy()

hourly_data = {
    "date": pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    )
}
hourly_data["temperature_2m"] = hourly_temperature_2m
hourly_data["precipitation"] = hourly_precipitation
hourly_data["cloud_cover"] = hourly_cloud_cover
hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
hourly_data["direct_radiation"] = hourly_direct_radiation

hourly_dataframe = pd.DataFrame(data=hourly_data)
print(hourly_dataframe)

# Process daily data
daily = response.Daily()
daily_sunrise = daily.Variables(0).ValuesAsNumpy()
daily_sunset = daily.Variables(1).ValuesAsNumpy()
daily_daylight_duration = daily.Variables(2).ValuesAsNumpy()

daily_data = {
    "date": pd.date_range(
        start=pd.to_datetime(daily.Time(), unit="s", utc=True),
        end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=daily.Interval()),
        inclusive="left"
    )
}

daily_data["daylight_duration"] = daily_daylight_duration

daily_dataframe = pd.DataFrame(data=daily_data)
print(daily_dataframe)
# Assuming base efficiency of solar panel
base_efficiency = 0.21  # 17% base efficiency

# Temperature correction: Reduce efficiency by 0.5% per degree Celsius above 25°C
hourly_dataframe["temperature_correction_factor"] = 1 - (hourly_dataframe["temperature_2m"] - 25).clip(lower=0) * 0.005

# Cloud cover adjustment: Reduce direct radiation by 75% of cloud cover percentage
hourly_dataframe["cloud_cover_correction_factor"] = 1 - (hourly_dataframe["cloud_cover"] / 100 * 0.75)

# Wind speed correction: Slightly increase efficiency by 0.1% per m/s of wind speed
hourly_dataframe["wind_speed_correction_factor"] = 1 + (hourly_dataframe["wind_speed_10m"] * 0.001)

# Calculate total correction factor
hourly_dataframe["total_correction_factor"] = (
    hourly_dataframe["temperature_correction_factor"] *
    hourly_dataframe["cloud_cover_correction_factor"] *
    hourly_dataframe["wind_speed_correction_factor"]
)

# Apply the total correction factor to base efficiency
hourly_dataframe["adjusted_efficiency"] = base_efficiency * hourly_dataframe["total_correction_factor"]

# Calculate hourly energy production (in kWh) considering panel size (2 kW panel assumed for this example)
correction_factor = 1
panel_size_kw = 2  # 2 kW panel
hourly_dataframe["energy_kwh"] = hourly_dataframe["direct_radiation"] * hourly_dataframe["adjusted_efficiency"] * panel_size_kw / 1000

# Total energy produced in a day (kWh)
total_energy_kwh_per_day = hourly_dataframe["energy_kwh"].sum()

# Fine-tuning the correction factor
actual_energy_produced = 520  # Actual energy produced in kWh
predicted_energy_kwh = total_energy_kwh_per_day  # Initial predicted energy from the model
correction_factor = 1.0  # Start with a correction factor of 1.0
tolerance = 0.01  # Acceptable tolerance for error
max_iterations = 1000  # Maximum number of iterations to avoid infinite loop
iteration = 0  # Initialize iteration counter

# Fine-tuning loop
while abs(predicted_energy_kwh - actual_energy_produced) > tolerance and iteration < max_iterations:
    # Adjust the correction factor based on the ratio of actual to predicted energy
    correction_factor *= (actual_energy_produced / predicted_energy_kwh)
    
    # Update the predicted energy based on the new correction factor
    predicted_energy_kwh = total_energy_kwh_per_day * correction_factor
    
    iteration += 1  # Increment the iteration counter

# Output the results
print(f"Final Correction Factor: {correction_factor:.4f}")
print(f"Adjusted Predicted Energy Production: {predicted_energy_kwh:.2f} kWh")
