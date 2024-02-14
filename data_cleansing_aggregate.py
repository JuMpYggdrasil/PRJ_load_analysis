import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os


# Create a function to load and process the selected .csv file
def load_and_process_data(file_path):
        
    # Load the historical data with the specified timestamp format
    # date_format = '%d.%m.%Y %H:%M'
    # date_format = '%d.%m.%Y %H.%M'
    # date_format = '%d/%m/%Y %H:%M'
    date_format = '%d/%m/%Y %H.%M' # default
    # date_format = '%m/%d/%Y %H:%M'
    # date_format = '%m/%d/%Y %H.%M'
    # date_format ='ISO8601'
    data = pd.read_csv(file_path, parse_dates=['Date'], date_format=date_format)
    data = data.sort_index()
    

    data.rename(columns={'Date': 'timestamp','Load': 'load'}, inplace=True)

    

    # data['load'].fillna(method='ffill', inplace=True)  # Forward fill
    # data['load'].fillna(method='bfill', inplace=True)  # Backward fill

    # Ensure the timestamp column is set as the index
    data.set_index('timestamp', inplace=True)
    if data.index.dtype == np.dtype('datetime64[ns]'):
        print("Index is of type datetime64[ns]")
    else:
        print("ERROR: Wrong Index Format")
        return
    
    first_row_timestamp = data.index[0]
    year_of_first_row = first_row_timestamp.year
    # Create the folder if it doesn't exist
    folder_name = f"result_{year_of_first_row}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"Folder '{folder_name}' created.")
    
    

    # Check for missing values and handle them if necessary
    if data.isnull().any().any():
        data = data.interpolate()  # Interpolate missing values
        # or
        # data = data.fillna(method='ffill')  # Forward fill missing values
        # data = data.fillna(method='bfill')  # Backward fill missing values
    data.to_csv('dummy.csv')
    
    print(data.head())

    if data is None:
        print("ERROR: no data")
        return

    # Aggregate data to hourly intervals
    hourly_data = data.resample('H').mean()

    # Optionally, add additional features like day of the week
    hourly_data['day_of_week'] = hourly_data.index.dayofweek

    # Add a 'month' column
    hourly_data['month'] = hourly_data.index.month

    # Save the prepared data to a CSV file
    hourly_data.to_csv('prepared_electric_load_data.csv')


    # Aggregate data to hourly intervals
    daily_peak_data = data.resample('D').max()  # You can use 'D' for daily aggregation

    # Optionally, add additional features like day of the week
    daily_peak_data['day_of_week'] = daily_peak_data.index.dayofweek

    # Add a 'month' column
    daily_peak_data['month'] = daily_peak_data.index.month

    # Save the prepared data to a CSV file
    daily_peak_data.to_csv('daily_peak_load_data.csv')

    # Find the day with the maximum and minimum
    max_peak_day = daily_peak_data['load'].idxmax().date()
    min_peak_day = daily_peak_data['load'].idxmin().date()
    # min_peak_day = daily_peak_data[daily_peak_data['load'] > 0]['load'].idxmin().date()

    # Filter the data for the day with maximum daily peak load
    max_peak_day_data = hourly_data[hourly_data.index.date == max_peak_day]

    # Filter the data for the day with minimum daily peak load
    min_peak_day_data = hourly_data[hourly_data.index.date == min_peak_day]

    # Calculate the average load for each hour across the entire year
    average_pattern = []
    for hour in range(24):
        average_pattern.append(hourly_data['load'][hourly_data.index.hour == hour].mean())

    print(average_pattern.index)
    # Plot the max_load_day_data and average_pattern
    plt.figure(figsize=(12, 6))
    plt.plot(max_peak_day_data.index.hour, max_peak_day_data['load'], marker='o', linestyle='-', color='blue', label=f'Max Load ({max_peak_day})')
    plt.plot(min_peak_day_data.index.hour, min_peak_day_data['load'], marker='o', linestyle='-', color='green', label=f'Min Load ({min_peak_day})')
    plt.plot(range(24), average_pattern, linestyle='-', color='grey', label='Average Load Pattern (Yearly)')
    plt.title(f'Hourly Electric Load Peaks (Max: {max_peak_day}, Min: {min_peak_day}) vs. Average Load Pattern')
    plt.xlabel('Hour of the Day')
    plt.ylabel('Load')
    plt.grid(True)
    plt.legend()
    plt.savefig(f"result_{year_of_first_row}/peak_day.png", format="png")
    plt.show()

    # on_peak_hours_price = 2 # Rate A
    # off_peak_hours_price = 2 # Rate B
    # holiday_peak_price = 2 # Rate C

    # # Calculate cost during peak hours
    # peak_hours = hourly_data.between_time('08:00', '18:00')  # Example peak hours
    # total_cost_peak = (peak_hours['load'] * peak_hours_price).sum()

    # # Implementing a demand response strategy (load shifting)
    # # Shift load from peak hours to non-peak hours
    # non_peak_hours = data.between_time('22:00', '06:00')  # Example non-peak hours
    # # Implement your load shifting strategy here

    # print(f'Total cost during peak hours: ${total_cost_peak:.2f}')

    # Aggregate data to hourly intervals
    montly_peak_data = data.resample('M').max()

    # Save the prepared data to a CSV file
    montly_peak_data.to_csv('montly_peak_load_data.csv')

if __name__ == '__main__':
    # file_path = 'combined_data.csv'
    file_path = 'EnergyDayChartAll2022_edit.csv'
    load_and_process_data(file_path)
    