import requests
import pandas as pd

def PVGIS_TMY(latitude,longitude,output_format='csv',use_horizon=1):
    # PVGIS TMY endpoint URL
    url = f"https://re.jrc.ec.europa.eu/api/v5_2/tmy?lat={latitude}&lon={longitude}&outputformat={output_format}&usehorizon={use_horizon}"

    # Make a GET request to the API
    response = requests.get(url)

    # Save the response content to a CSV file
    filename = 'tmy_data.csv'
    with open(filename, 'wb') as file:
        file.write(response.content)

    # Read the CSV file into a pandas DataFrame
    tmy_data = pd.read_csv(filename, skiprows=16)

    # # Display the first few rows of the data
    # print(tmy_data.head())


    # Calculate the total GHI for the year
    total_ghi = tmy_data['G(h)'].sum()
    # print(total_ghi Wh/m^2)

    # Convert total GHI to kWh/m^2
    total_ghi_kwh = total_ghi / 1000
    # print(total_ghi_kwh)

    Energy_per_year_per_kWp = total_ghi_kwh*1441.9/1868.9

    return total_ghi_kwh, [Energy_per_year_per_kWp]

if __name__ == '__main__':
    # Define the location (latitude, longitude) and parameters
    latitude = 13.811739286586437   # Replace with your latitude
    longitude = 100.50565968620579  # Replace with your longitude

    PVSyst_GlobInc, E = PVGIS_TMY(latitude, longitude)
    print(f"{PVSyst_GlobInc} kWh/m2/year, {E} kWh/kWp/year")


