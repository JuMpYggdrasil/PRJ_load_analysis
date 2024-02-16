import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta

# Assuming you've already read the CSV file into a DataFrame with proper parsing
dataframe = pd.read_csv('prepared_electric_load_data.csv', parse_dates=['timestamp'])

# Count unique days
unique_days = dataframe['timestamp'].dt.date.nunique()

# Dictionary to store results
results = {}

# Iterate over unique dates
for i in range(unique_days):
    current_date = dataframe['timestamp'].dt.date.unique()[i]
    previous_dates = [current_date - timedelta(days=x) for x in range(1, 11)]
    
    # Sum load for previous 10 days
    sum_loads = []
    sum_loads_date = []
    for previous_date in previous_dates:
        sum_load = dataframe[dataframe['timestamp'].dt.date == previous_date]['load'].sum()
        sum_loads.append(sum_load)
        sum_loads_date.append(previous_date)
        
    # Create DataFrame
    df_local = pd.DataFrame({'Date': sum_loads_date, 'Sum_Load': sum_loads})
    df_local['Date'] = pd.to_datetime(df_local['Date'])
    df_local = df_local.sort_values(by='Sum_Load')
    # Delete 2 rows with minimum 'Sum_Load'
    df_local = df_local.drop(df_local.nsmallest(2, 'Sum_Load').index)
    df_local = df_local.sort_values(by='Date')
    
    
    # Store result
    # results[current_date] = df_local
    # selected_data = data[data.dt.date.isin(df_local['Date'])]
    # print("selected_data",selected_data)
    dataframe['timestamp'] = pd.to_datetime(dataframe['timestamp'])

    # Filter dataframe based on dates in df_local['Date']
    filtered_df = dataframe[dataframe['timestamp'].dt.date.isin(df_local['Date'].dt.date)]
    print(df_local['Date'],filtered_df)
    
    filtered_df['hour'] = filtered_df['timestamp'].dt.hour
    hourly_average_load = filtered_df.groupby('hour')['load'].mean()
    
    # # Copy hourly_average_load to dataframe['baseline']
    # dataframe.loc[dataframe['timestamp'].dt.date == current_date, 'baseline'] = \
    #     dataframe.loc[dataframe['timestamp'].dt.date == current_date, 'timestamp'].dt.hour.map(hourly_average_load)


    print(hourly_average_load)
# print(dataframe)
    

