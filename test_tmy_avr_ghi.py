import requests
import pandas as pd
from collections import defaultdict

def get_pvgis_hourly(lat, lon, startyear, endyear, output_format='json'):
    """
    Fetch hourly data from PVGIS for the given latitude, longitude, and year range.

    Parameters:
    lat (float): Latitude of the location.
    lon (float): Longitude of the location.
    startyear (int): Starting year of the data.
    endyear (int): Ending year of the data.
    output_format (str): Format of the output ('json' or 'csv').

    Returns:
    dict or DataFrame: Hourly data including GHI.
    """
    base_url = "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"
    params = {
        'lat': lat,
        'lon': lon,
        'startyear': startyear,
        'endyear': endyear,
        'outputformat': output_format,
        'pvcalculation': 0,  # Only meteorological data, no PV calculations
        'browser': 0,
        'components': 1  # Ensure we get the individual components
    }

    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        print("Error:", response.status_code)
        print("Response content:", response.content)
        response.raise_for_status()

    if output_format == 'json':
        return response.json()
    elif output_format == 'csv':
        csv_data = response.text
        data = pd.read_csv(pd.compat.StringIO(csv_data))
        return data

def calculate_average_ghi(hourly_data):
    """
    Calculate average GHI for each hour of the day across multiple years.

    Parameters:
    hourly_data (list): List of dictionaries containing hourly data.

    Returns:
    dict: Dictionary with hour as key and average GHI as value.
    """
    hour_ghi = defaultdict(list)

    for hour_entry in hourly_data:
        time_str = hour_entry['time']
        hour = int(time_str[-4:-2])  # Extract hour from time string
        ghi = hour_entry['Gb(i)'] + hour_entry['Gd(i)']
        hour_ghi[hour].append(ghi)

    average_ghi = {hour: sum(ghi_list) / len(ghi_list) for hour, ghi_list in hour_ghi.items()}
    return average_ghi

# Example usage:
lat = 13.7563  # Latitude for Bangkok, Thailand
lon = 100.5018  # Longitude for Bangkok, Thailand
startyear = 2005  # Starting year for data retrieval
endyear = 2015  # Ending year for data retrieval (adjust as needed)
hourly_data = []

# Fetch data for each year from startyear to endyear
for year in range(startyear, endyear + 1):
    print(f"Fetching data for year {year}...")
    data = get_pvgis_hourly(lat, lon, year, year)
    if isinstance(data, dict) and 'outputs' in data:
        hourly_data.extend(data['outputs']['hourly'])

# Calculate average GHI for each hour of the day
average_ghi = calculate_average_ghi(hourly_data)
print("PVGIS API is typically in UTC")
# Display or store the results
for hour, avg_ghi in sorted(average_ghi.items()):
    print(f"Hour {hour:02}:00 - Average GHI: {avg_ghi:.2f} W/m²")
