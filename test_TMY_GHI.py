import requests
import pandas as pd

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

# Example usage:
lat = 52.52  # Latitude for Berlin, Germany
lon = 13.405  # Longitude for Berlin, Germany
startyear = 2005  # Year with available data
endyear = 2015
hourly_data = get_pvgis_hourly(lat, lon, startyear, endyear)

# Inspect the structure of the JSON response
if isinstance(hourly_data, dict):
    print("Keys in JSON response:", hourly_data.keys())
    print("Sample hourly data:", hourly_data['outputs']['hourly'][:5])
    # Extracting GHI data from JSON response
    ghi_data = [hour['Gb(i)'] + hour['Gd(i)'] for hour in hourly_data['outputs']['hourly']]
    print("GHI data:", ghi_data[:10])  # Print first 10 entries for brevity
    # Save to CSV
    df = pd.DataFrame(hourly_data['outputs']['hourly'])
    df['GHI'] = df['Gb(i)'] + df['Gd(i)']
    df.to_csv('ghi_data_2005_2015.csv', index=False)
elif isinstance(hourly_data, pd.DataFrame):
    print("Dataframe columns:", hourly_data.columns)
    hourly_data['GHI'] = hourly_data['Gb(i)'] + hourly_data['Gd(i)']
    ghi_data = hourly_data['GHI']
    print("GHI data:", ghi_data[:10])  # Print first 10 entries for brevity
    # Save to CSV
    hourly_data.to_csv('ghi_data_2015.csv', index=False)
