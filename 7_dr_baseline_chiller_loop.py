import pandas as pd
import matplotlib.pyplot as plt
import math

# Loop through each day in the year (yyyy-mm-dd)
start_date = pd.Timestamp('2022-02-15')
end_date = pd.Timestamp('2022-12-31')

# Function to calculate demand pattern for a specific day
def calculate_demand_pattern_for_day(data, day, Xday=7, Yday=12):
    # Get the dates 10 days before the given day
    interested_dates = pd.date_range(end=day - pd.Timedelta(days=1), periods=Yday)

    # Filter data for the range of interested_dates
    interested_data = data[data['timestamp'].dt.date.isin(interested_dates.date)]



    # Calculate the sum of load for each day in the interested dates
    sum_load_per_day = interested_data.groupby(interested_data['timestamp'].dt.date)['load'].sum()
    
    
    sum_load_sorted = sum_load_per_day.sort_values(ascending=False)
    sum_load_sorted_X = sum_load_sorted[:Xday]
    sum_load_sorted_X_check = sum_load_sorted_X.iloc[Xday-1]
    # if sum_load_sorted_X_check < 0.1:
    #     print("sum_load_sorted_X",sum_load_sorted_X,"->",sum_load_sorted_X_check)
    
    i=1
    while sum_load_sorted_X_check < 0.1:
        # Get the dates 10 days before the given day
        interested_dates = pd.date_range(end=day - pd.Timedelta(days=1), periods=Yday+i)

        # Filter data for the range of interested_dates
        interested_data = data[data['timestamp'].dt.date.isin(interested_dates.date)]



        # Calculate the sum of load for each day in the interested dates
        sum_load_per_day = interested_data.groupby(interested_data['timestamp'].dt.date)['load'].sum()
        
        
        sum_load_sorted = sum_load_per_day.sort_values(ascending=False)
        sum_load_sorted_X = sum_load_sorted[:Xday]
        sum_load_sorted_X_check = sum_load_sorted_X.iloc[Xday-1]
        # print("sum_load_sorted_X",sum_load_sorted_X,"->",sum_load_sorted_X_check)
        
        i+=1
        if i>10:
             break
        
    
    
    
    # Sort interested dates by sum of load from max to min
    sorted_dates = sum_load_per_day.sort_values(ascending=False).index
    
    # Keep only the maximum X dates
    top_X_dates = sorted_dates[:Xday]
    
    # Filter data for top X dates
    top_X_data = interested_data[interested_data['timestamp'].dt.date.isin(top_X_dates)]

    # count_top_X_data = len(top_X_data)
    # min_load_value = top_X_data['load'].min()
    # lowest_5_load_values = top_X_data['load'].nsmallest(5)
    # highest_5_load_values = top_X_data['load'].nlargest(5)


    
    
    # Calculate average load pattern for top X dates
    average_load_pattern = top_X_data.groupby(top_X_data['timestamp'].dt.hour)['load'].mean()
    
    return average_load_pattern

# Read the CSV file into a DataFrame with proper parsing
dataframe = pd.read_csv('prepared_electric_load_data.csv', parse_dates=['timestamp'])




def run_baseline_calculation(Xday_setpoint,Yday_setpoint):
    combined_baseline_values = []
    combined_real_values = []

    # plt.figure(figsize=(10, 6))
    
    
    for day in pd.date_range(start=start_date, end=end_date):
        # Calculate demand pattern for the current day
        baseline_pattern = calculate_demand_pattern_for_day(dataframe, day,Xday=Xday_setpoint,Yday=Yday_setpoint)
        
        # Extend the list of combined baseline values with the values of the current baseline pattern
        combined_baseline_values.extend(baseline_pattern.values)
        
        # Filter data for the specific day
        real_pattern = dataframe[dataframe['timestamp'].dt.date == day.date()]
        
        combined_real_values.extend(real_pattern['load'])
        
        # # Plot baseline pattern
        # plt.plot(baseline_pattern, linestyle='--', label=f'Baseline (Day: {day})')
        
        # # Plot real pattern
        # plt.plot(real_pattern['timestamp'].dt.hour, real_pattern['load'], label=f'Real Value (Day: {day})')
        

    # # Plot the demand pattern
    # plt.title('Hourly Average Load Patterns')
    # plt.xlabel('Hour of the day')
    # plt.ylabel('Average load')
    # plt.legend()
    # plt.grid(True)
    # plt.show()



    combined_baseline_values = []
    combined_real_values = []

    # plt.figure(figsize=(10, 6))
        
    for day in pd.date_range(start=start_date, end=end_date):
        # Filter data for the specific day
        real_pattern = dataframe[dataframe['timestamp'].dt.date == day.date()]
        real_energy = real_pattern['load'].sum()
        
        
        
        # Calculate demand pattern for the current day
        baseline_pattern = calculate_demand_pattern_for_day(dataframe, day,Xday=Xday_setpoint,Yday=Yday_setpoint)
        if (real_energy < 1):
            i=0
            while i < len(baseline_pattern.values):
                baseline_pattern.values[i] = 0
                i+=1

        
        # Extend the list of combined baseline values with the values of the current baseline pattern
        combined_baseline_values.extend(baseline_pattern.values)
        
        
        
        combined_real_values.extend(real_pattern['load'])
        
        # # Plot baseline pattern
        # plt.plot(baseline_pattern, linestyle='--', label=f'Baseline (Day: {day})')
        
        # # Plot real pattern
        # plt.plot(real_pattern['timestamp'].dt.hour, real_pattern['load'], label=f'Real Value (Day: {day})')


    # # Plot the combined baseline values
    # plt.figure(figsize=(10, 6))
    # plt.plot(combined_baseline_values, linestyle='--', label='Combined Baseline Values')
    # plt.plot(combined_real_values, linestyle='-', label='Combined Real Values')
    # plt.title('Combined Hourly Average Load Patterns')
    # plt.legend()
    # plt.grid(True)
    # plt.show()


    error_list=[xi - yi for xi, yi in zip(combined_real_values, combined_baseline_values)]
    for i, v in enumerate(error_list):
        error_list[i] = v**2
    
    sum_error = sum(error_list)
    RMSE = math.sqrt(sum_error)
    sum_value = sum(combined_real_values)
    RRMSE = RMSE/sum_value*100
    # print(f'RRMSE= {RRMSE} %')


    baseline_energy = sum(combined_baseline_values)
    # print("baseline energy = {:,.2f} kWh/year".format(baseline_energy))
    real_energy = sum(combined_real_values)
    # print("real energy = {:,.2f} kWh/year".format(real_energy))
    # print("% = {:,.2f} kWh/year".format((real_energy-baseline_energy)/real_energy*100))
    # print("X",Xday_setpoint,"Y",Yday_setpoint)
    # print("")
    print(Xday_setpoint,Yday_setpoint,abs(real_energy-baseline_energy)/real_energy*100)
    


for Xday_setpoint in range(2, 9):
    # Loop through Yday_setpoint from Xday_setpoint + 1 to 15
    for Yday_setpoint in range(Xday_setpoint + 1, 16):
        run_baseline_calculation(Xday_setpoint, Yday_setpoint)