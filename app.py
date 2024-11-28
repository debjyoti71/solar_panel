import sqlite3
from flask import Flask, request, render_template, session, redirect, url_for
from datetime import datetime, timedelta
import pandas as pd
import openmeteo_requests
import requests_cache
from retry_requests import retry
import requests
import json

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key

# Set up Open-Meteo API client with caching and retries
cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Function to calculate required panels
def calculate_panels_needed(energy_consumption, average_daily_energy_kwh):
    panels_needed = energy_consumption / average_daily_energy_kwh
    return round(panels_needed * 2) / 2  # Round to the nearest 0.5

# Function to get address from coordinates
def get_address_from_coordinates(lat, lon):
    try:
        headers = {'User-Agent': 'SolarPanelApp/1.0'}
        response = requests.get(
            f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('display_name', 'Address not found')
        else:
            return 'Unable to retrieve address'
    except Exception as e:
        print(f"Error in address lookup: {e}")
        return 'Unable to retrieve address'

@app.route('/', methods=['GET', 'POST'])
def index():
    location_address = None
    if request.method == 'POST':
        try:
            # Get form data
            energy_consumption = float(request.form['energy_consumption'])
            latitude = float(request.form['latitude'])
            longitude = float(request.form['longitude'])

            # Save to session
            session['latitude'] = latitude
            session['longitude'] = longitude
            session['energy_consumption'] = energy_consumption

            # Get address from coordinates
            location_address = get_address_from_coordinates(latitude, longitude)

            # Date range for API (last year)
            end_date = datetime.today().strftime("%Y-%m-%d")
            start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")

            # Weather API request parameters
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "hourly": ["temperature_2m", "cloud_cover", "wind_speed_10m", "direct_radiation"],
                "timezone": "Asia/Kolkata"
            }
            response = requests.get(url, params=params)
            if response.status_code != 200:
                raise Exception(f"Weather API error: {response.status_code}")

            weather_data = response.json()
            if 'hourly' not in weather_data:
                raise Exception("Invalid weather data format")

            hourly_data = weather_data['hourly']
            df = pd.DataFrame(hourly_data)

            # Calculate efficiency correction factors
            df["temperature_correction"] = 1 - (df["temperature_2m"] - 25).clip(lower=0) * 0.005
            df["cloud_cover_correction"] = 1 - (df["cloud_cover"] / 100 * 0.75)
            df["wind_speed_correction"] = 1 + (df["wind_speed_10m"] * 0.001)
            df["total_correction"] = (
                df["temperature_correction"] * df["cloud_cover_correction"] * df["wind_speed_correction"]
            )
            df["efficiency"] = 0.21 * df["total_correction"]
            correction_factor = 8.3847

            # Calculate energy production
            df["energy_kwh"] = df["direct_radiation"] * df["efficiency"] / 1000
            total_energy_kwh = df["energy_kwh"].sum() * correction_factor
            average_daily_energy_kwh = total_energy_kwh / len(df['time'].str[:10].unique())

            # Calculate required panels
            panels_needed = calculate_panels_needed(energy_consumption, average_daily_energy_kwh)

            # Save results to session
            session['panels_needed'] = panels_needed
            session['total_energy_kwh'] = total_energy_kwh
            session['average_daily_energy_kwh'] = average_daily_energy_kwh

            # Debug logs
            location_address = get_address_from_coordinates(latitude, longitude)
            print(f"Location Address: {location_address}")  # Debug print
            session['location_address'] = location_address
            print(f"Total Energy: {total_energy_kwh} kWh, Avg Daily: {average_daily_energy_kwh} kWh")
            print(f"Panels Needed: {panels_needed}")

            return redirect(url_for('index'))

        except Exception as e:
            print(f"Error: {e}")
            return f"An error occurred: {e}"
        
    print(f"Session Data: {dict(session)}") 

    # Load session data for rendering
    return render_template(
        'home.html',
        latitude=session.get('latitude'),
        longitude=session.get('longitude'),
        energy_consumption=session.get('energy_consumption'),
        location_address=session.get('location_address'),
        panels_needed=session.get('panels_needed'),
        total_energy_kwh=session.get('total_energy_kwh'),
        average_daily_energy_kwh=session.get('average_daily_energy_kwh')
    )


# Route to show stored data
@app.route('/data')
def data():
    records = get_all_data()
    return render_template('energy_data.html', records=records)

# Function to store or update data in the SQLite database
def store_data(location_address, energy_consumption, average_daily_energy_kwh, panels_needed):
    print(f"Storing data: {location_address}, {energy_consumption}, {average_daily_energy_kwh}, {panels_needed}")
    conn = sqlite3.connect('solar_data.db')
    c = conn.cursor()
    
    # Check if the data already exists for the same location
    c.execute("SELECT * FROM energy_data WHERE location_address = ?", (location_address,))
    existing_record = c.fetchone()
    print(f"Existing record: {existing_record}")
    
    if existing_record:
        # Update existing record with the latest data
        c.execute("""
            UPDATE energy_data
            SET energy_consumption = ?, average_daily_energy_kwh = ?, panels_needed = ?, date_updated = ?
            WHERE location_address = ?
        """, (energy_consumption, average_daily_energy_kwh, panels_needed, datetime.now(), location_address))
        print(f"Updated record for {location_address}")
    else:
        # Insert new record
        c.execute("""
            INSERT INTO energy_data (location_address, energy_consumption, average_daily_energy_kwh, panels_needed, date_created)
            VALUES (?, ?, ?, ?, ?)
        """, (location_address, energy_consumption, average_daily_energy_kwh, panels_needed, datetime.now()))
        print(f"Inserted new record for {location_address}")

    conn.commit()
    conn.close()

# Function to retrieve all stored data from the SQLite database
from datetime import datetime

def get_all_data():
    conn = sqlite3.connect('solar_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM energy_data")
    records = c.fetchall()
    
    formatted_records = []
    for record in records:
        # Assuming the date is in the last two columns (index 5 and 6)
        record = list(record)
        
        # Check if the date value is not None before parsing
        if record[5] is not None:
            try:
                record[5] = datetime.strptime(record[5], "%Y-%m-%d %H:%M:%S.%f").strftime("%d-%m-%Y %H:%M:%S")
            except ValueError as e:
                print(f"Date parsing error: {e}")
                record[5] = record[5]  # Keep the original format if there's an error
        else:
            record[5] = "No Date Provided"  # Set a default value if the date is None

        # Repeat for the second date column (if it exists)
        if record[6] is not None:
            try:
                record[6] = datetime.strptime(record[6], "%Y-%m-%d %H:%M:%S.%f").strftime("%d-%m-%Y %H:%M:%S")
            except ValueError as e:
                print(f"Date parsing error: {e}")
                record[6] = record[6]  # Keep the original value if there's an error
        else:
            record[6] = "No Date Provided"  # Set a default value if the date is None
        
        formatted_records.append(tuple(record))
    
    conn.close()
    return formatted_records



# Create the SQLite database and table on startup
def create_db():
    conn = sqlite3.connect('solar_data.db')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS energy_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_address TEXT,
            energy_consumption REAL,
            average_daily_energy_kwh REAL,
            panels_needed REAL,
            date_created TEXT,
            date_updated TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("Database and table created (or already exists).")


# Run the app and create the database if not already present
if __name__ == '__main__':
    create_db()
    app.run(debug=True)
