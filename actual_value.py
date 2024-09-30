import requests
import pandas as pd

# Replace with your actual API endpoint and parameters
api_url = "https://api.solarprovider.com/production"  # Hypothetical endpoint
locations = [
    {"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639},
    {"name": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
    {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777},
    {"name": "Chennai", "latitude": 13.0827, "longitude": 80.2707}
]

# Collect data for each location
all_data = []

for location in locations:
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "start_date": "2024-08-01",
        "end_date": "2024-08-31"
    }
    response = requests.get(api_url, params=params)
    
    if response.status_code == 200:
        solar_data = response.json()  # Assuming the response is in JSON format
        df = pd.DataFrame(solar_data)
        df['location'] = location['name']  # Add location name
        all_data.append(df)
    else:
        print(f"Failed to retrieve data for {location['name']}: {response.status_code}")

# Combine all data into a single DataFrame
combined_data = pd.concat(all_data, ignore_index=True)

# Save to CSV
combined_data.to_csv('C:/Users/HP/Desktop/csv_files/actual_solar_production_last_month.csv', index=False)
print("Actual solar production data for last month saved to 'actual_solar_production_last_month.csv'")
