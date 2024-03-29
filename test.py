import pandas as pd
import matplotlib.pyplot as plt

# Function to check if a given day is a weekday
def is_weekday(day):
    # Get the weekday value (0 represents Monday, 1 represents Tuesday, ..., 6 represents Sunday)
    weekday_value = day.weekday()
    # Return True if the weekday value is between 0 and 4 (inclusive), indicating a weekday
    return weekday_value >= 0 and weekday_value <= 4

# Function to calculate demand pattern for a specific day
def calculate_demand_pattern_for_day(data, day):
    if is_weekday(day):
        Xday = 4
        Yday = 5
        # business day (weekday) date ranges
        interested_dates = pd.bdate_range(end=day - pd.Timedelta(days=1), periods=Yday)
    else:
        Xday = 2
        Yday = 3
        # Get the dates 30 days before the given day, including weekends
        all_dates = pd.date_range(end=day - pd.Timedelta(days=1), periods=30)
        weekend_dates = [date for date in all_dates if not is_weekday(date)]
        # If there are more than 3 weekend dates, trim the list
        interested_dates = weekend_dates[:Yday]
    
    # Filter data for the range of interested_dates
    interested_data = data[data['timestamp'].dt.date.isin([d.date() for d in interested_dates])]

    # Calculate the sum of load for each day in the interested dates
    sum_load_per_day = interested_data.groupby(interested_data['timestamp'].dt.date)['load'].sum()
    
    # Sort interested dates by sum of load from max to min
    sorted_dates = sum_load_per_day.sort_values(ascending=False).index
    
    # Keep only the maximum X dates
    top_X_dates = sorted_dates[:Xday]
    
    # Filter data for top X dates
    top_X_data = interested_data[interested_data['timestamp'].dt.date.isin(top_X_dates)]
    
    # Calculate average load pattern for top X dates
    average_load_pattern = top_X_data.groupby(top_X_data['timestamp'].dt.hour)['load'].mean()
    
    return average_load_pattern

# Read the CSV file into a DataFrame with proper parsing
dataframe = pd.read_csv('prepared_electric_load_data_ref.csv', parse_dates=['timestamp'])

# Lists to store baseline and real patterns
baseline_patterns = []
real_patterns = []

# Loop through each day in the year (yyyy-mm-dd)
start_date = pd.Timestamp('2022-01-01')
end_date = pd.Timestamp('2022-12-31')

for month in range(1, 13):
    # Filter data for the specific month
    month_data = dataframe[dataframe['timestamp'].dt.month == month]
    
    # Calculate demand pattern for each day in the month
    baseline_month_patterns = []
    real_month_patterns = []
    for day in pd.date_range(start=start_date, end=end_date):
        # Calculate demand pattern for the current day
        baseline_pattern = calculate_demand_pattern_for_day(month_data, day)
        
        # Filter data for the specific day
        real_pattern = month_data[month_data['timestamp'].dt.date == day.date()]
        
        # Append baseline pattern and real pattern to the lists
        baseline_month_patterns.append(baseline_pattern)
        real_month_patterns.append(real_pattern['load'].tolist())
    
    # Append monthly patterns to the lists
    baseline_patterns.append(baseline_month_patterns)
    real_patterns.append(real_month_patterns)

# Plot monthly baseline and real patterns
plt.figure(figsize=(12, 8))
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
for month, baseline_month, real_month in zip(months, baseline_patterns, real_patterns):
    plt.plot(baseline_month, label=f'Baseline - {month}')
    plt.plot(real_month, label=f'Real - {month}')

plt.title('Monthly Average Load Patterns')
plt.xlabel('Hour of the day')
plt.ylabel('Average load')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
