import pandas as pd
import matplotlib.pyplot as plt
import math

# Loop through each day in the year (yyyy-mm-dd)
start_date = pd.Timestamp('2022-01-11')
end_date = pd.Timestamp('2022-01-15')

# PJM: High4of5 for weekdays; High2of3 for weekends.
# PJM: Pennsylvania, Jersey, Maryland Interconnection
# PJM is a regional transmission organization (RTO) that coordinates the movement of wholesale electricity in all or parts of 13 states and the District of Columbia in the United States.

# NYISO: High5of10 for weekdays; High2of3 for weekends.
# NYISO: New York Independent System Operator
# NYISO is a nonprofit organization that operates the power grid and wholesale electricity market in New York State.

# CAISO: High10of10 for weekdays; High4of4 for weekends
# CAISO: California Independent System Operator
# CAISO is a nonprofit organization that operates the power grid and wholesale electricity market in California.


# Function to check if a given day is a weekday
def is_weekday(day):
    # Get the weekday value (0 represents Monday, 1 represents Tuesday, ..., 6 represents Sunday)
    weekday_value = day.weekday()
    
    # Return True if the weekday value is between 0 and 4 (inclusive), indicating a weekday
    return weekday_value >= 0 and weekday_value <= 4

# Function to calculate demand pattern for a specific day
def calculate_demand_pattern_for_day(data, day):
    # Get the dates 10 days before the given day
    # interested_dates = pd.date_range(end=day - pd.Timedelta(days=1), periods=Yday)
    if is_weekday(day):
        Xday = 4
        Yday = 5
        # Business day (weekday) date ranges
        interested_dates = pd.bdate_range(end=day - pd.Timedelta(days=1), periods=Yday)

        # Filter data for the range of interested_dates
        interested_data = data[data['timestamp'].dt.date.isin(interested_dates.date)]
    else:
        Xday = 2
        Yday = 3
        # Get the dates 30 days before the given day, including weekends
        all_dates = pd.date_range(end=day - pd.Timedelta(days=1), periods=30)
        weekend_dates = [date for date in all_dates if not is_weekday(date)]
        # Sort the list of timestamps in descending order
        sorted_dates = sorted(weekend_dates, reverse=True)

        # Select the first three maximum dates
        interested_dates = sorted_dates[:Yday]

        # If there are more than 3 weekend dates, trim the list
        interested_dates = pd.to_datetime(interested_dates)
        # [:Yday]
        # print(interested_dates)
        
        # Filter data for the range of interested_dates
        interested_data = data[data['timestamp'].dt.date.isin(interested_dates.date)]


    # Calculate the sum of load for each day in the interested dates
    sum_load_per_day = interested_data.groupby(interested_data['timestamp'].dt.date)['load'].sum()
    
    # Sort interested dates by sum of load from max to min
    sorted_dates = sum_load_per_day.sort_values(ascending=False).index
    
    # Keep only the maximum X dates
    top_X_dates = sorted_dates[:Xday]
    
    # Filter data for top X dates
    top_X_data = interested_data[interested_data['timestamp'].dt.date.isin(top_X_dates)]
    # print(top_X_data)
    
    # Calculate average load pattern for top X dates
    average_load_pattern = top_X_data.groupby(top_X_data['timestamp'].dt.hour)['load'].mean()
    
    return average_load_pattern

# Read the CSV file into a DataFrame with proper parsing
dataframe = pd.read_csv('prepared_electric_load_data.csv', parse_dates=['timestamp'])




combined_baseline_values = []
combined_real_values = []

plt.figure(figsize=(10, 6))

for day in pd.date_range(start=start_date, end=end_date):
    # Calculate demand pattern for the current day
    baseline_pattern = calculate_demand_pattern_for_day(dataframe, day)
    
    # Extend the list of combined baseline values with the values of the current baseline pattern
    combined_baseline_values.extend(baseline_pattern.values)
    
    # Filter data for the specific day
    real_pattern = dataframe[dataframe['timestamp'].dt.date == day.date()]
    
    combined_real_values.extend(real_pattern['load'])
    
    # Plot baseline pattern
    plt.plot(baseline_pattern, linestyle='--', label=f'Baseline (Day: {day})')
    
    # Plot real pattern
    plt.plot(real_pattern['timestamp'].dt.hour, real_pattern['load'], label=f'Real Value (Day: {day})')

# Plot the demand pattern
plt.title('Hourly Average Load Patterns')
plt.xlabel('Hour of the day')
plt.ylabel('Average load')
plt.legend()
plt.grid(True)
plt.show()


# Plot the combined baseline values
plt.figure(figsize=(10, 6))
plt.plot(combined_baseline_values, linestyle='--', label='Combined Baseline Values')
plt.plot(combined_real_values, linestyle='-', label='Combined Real Values')
plt.title('Combined Hourly Average Load Patterns')
plt.legend()
plt.grid(True)
plt.show()


error_list=[xi - yi for xi, yi in zip(combined_real_values, combined_baseline_values)]
for i, v in enumerate(error_list):
   error_list[i] = v**2
   
sum_error = sum(error_list)
RMSE = math.sqrt(sum_error)
sum_value = sum(combined_real_values)
RRMSE = RMSE/sum_value*100
print(f'RRMSE= {RRMSE} %')