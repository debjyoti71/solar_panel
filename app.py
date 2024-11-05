from flask import Flask, request, render_template
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry

app = Flask(__name__)

# Setup Open-Meteo API client with cache and retry
cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # Get latitude, longitude, and energy consumption from the form
            latitude = float(request.form['latitude'])
            longitude = float(request.form['longitude'])
            energy_consumption = float(request.form['energy_consumption'])

            # Set up weather API parameters
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": "2023-10-27",
                "end_date": "2024-10-27",
                "hourly": ["temperature_2m", "precipitation", "rain", "cloud_cover", "wind_speed_10m", "direct_radiation"],
                "daily": ["sunrise", "sunset", "daylight_duration"],
                "timezone": "Asia/Kolkata",
                "tilt": 30
            }
            responses = openmeteo.weather_api(url, params=params)

            # Process response
            response = responses[0]
            hourly = response.Hourly()
            hourly_data = {
                "date": pd.date_range(
                    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=hourly.Interval()),
                    inclusive="left"
                ),
                "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
                "precipitation": hourly.Variables(1).ValuesAsNumpy(),
                "rain": hourly.Variables(2).ValuesAsNumpy(),
                "cloud_cover": hourly.Variables(3).ValuesAsNumpy(),
                "wind_speed_10m": hourly.Variables(4).ValuesAsNumpy(),
                "direct_radiation": hourly.Variables(5).ValuesAsNumpy()
            }
            hourly_dataframe = pd.DataFrame(hourly_data)

            # Efficiency and correction factors
            base_efficiency = 0.21
            hourly_dataframe["temperature_correction_factor"] = 1 - (hourly_dataframe["temperature_2m"] - 25).clip(lower=0) * 0.005
            hourly_dataframe["cloud_cover_correction_factor"] = 1 - (hourly_dataframe["cloud_cover"] / 100 * 0.75)
            hourly_dataframe["wind_speed_correction_factor"] = 1 + (hourly_dataframe["wind_speed_10m"] * 0.001)
            hourly_dataframe["total_correction_factor"] = (
                hourly_dataframe["temperature_correction_factor"] *
                hourly_dataframe["cloud_cover_correction_factor"] *
                hourly_dataframe["wind_speed_correction_factor"]
            )
            hourly_dataframe["adjusted_efficiency"] = base_efficiency * hourly_dataframe["total_correction_factor"]

            # Energy calculation per hour and total
            panel_size_kw = 1
            hourly_dataframe["energy_kwh"] = hourly_dataframe["direct_radiation"] * hourly_dataframe["adjusted_efficiency"] * panel_size_kw / 1000
            correction_factor = 8.3847
            total_energy_kwh = hourly_dataframe["energy_kwh"].sum() * correction_factor

            # Average daily energy production
            unique_days = len(hourly_dataframe['date'].dt.date.unique())
            average_daily_energy_kwh = (total_energy_kwh / unique_days)//1

            # Calculate required panels
            panels_needed = (energy_consumption / average_daily_energy_kwh)//1

            return render_template(
                'index.html',
                total_energy_kwh=total_energy_kwh,
                average_daily_energy_kwh=average_daily_energy_kwh,
                panels_needed=panels_needed
            )
        except Exception as e:
            return f"Error: {e}"

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)