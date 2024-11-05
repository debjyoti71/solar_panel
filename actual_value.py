import requests

# Use your Polygon.io API key
url = 'https://api.polygon.io/v3/reference/tickers?apiKey=pVRpwGkbyVr28GAuYVr0alz1dv4gZRER'
r = requests.get(url)
data = r.json()

# This will give a list of all stock symbols
print(data)
