import pandas as pd
import matplotlib.pyplot as plt

# Load your electrical load data into a Pandas DataFrame
df = pd.read_csv('analyse_electric_load_data.csv', parse_dates=['timestamp'])
# df.rename(columns={'Date': 'timestamp','Load': 'load'}, inplace=True)

# Assuming your DataFrame has a 'timestamp' column, you can set it as the index
df.set_index('timestamp', inplace=True)

#df = df[df.index.month==10]

weekday_mask = (df.index.dayofweek >= 0) & (df.index.dayofweek < 5)
weekend_mask = (df.index.dayofweek >= 5)
on_peak_mask = (df.index.hour >= 9) & (df.index.hour < 22)
off_peak_mask = ~on_peak_mask
specific_dates = ['2022-01-01', '2022-02-16', '2022-02-26', '2022-04-06', '2022-04-13', '2022-04-14', '2022-04-15', '2022-05-01', '2022-05-04', '2022-05-15', '2022-06-03', '2022-07-13', '2022-07-14', '2022-07-15', '2022-07-28', '2022-07-29', '2022-08-12', '2022-10-13', '2022-10-14', '2022-10-23', '2022-10-30', '2022-12-05', '2022-12-25', '2022-12-30']
specific_dates = pd.to_datetime(specific_dates, format='%Y-%m-%d')
specific_dates_mask = df.index.isin(specific_dates)

# Extract data for weekdays (Monday to Friday)
weekdays = df[weekday_mask & ~specific_dates_mask]
# Apply the masks to create the "On Peak" and "Off Peak" groups
on_peak_data = df[weekday_mask & ~specific_dates_mask & on_peak_mask]
off_peak_data = df[weekday_mask & ~specific_dates_mask & off_peak_mask]

sum_on_peak_data = on_peak_data['load'].sum()
print(f"Sum of On Peak Data: {sum_on_peak_data:.2f}")

sum_off_peak_data = off_peak_data['load'].sum()
print(f"Sum of Off Peak Data: {sum_off_peak_data:.2f}")

# Extract data for weekends (Saturday and Sunday)
weekends = df[weekend_mask | specific_dates_mask]
sum_weekend = weekends['load'].sum()
print(f"Sum of weekends Data: {sum_weekend:.2f}")
print(f"Total: {(sum_on_peak_data+sum_off_peak_data+sum_weekend):.2f}")

sorted_weekdays_loads = sorted(weekdays['load'], reverse=True)
sorted_weekends_loads = sorted(weekends['load'], reverse=True)

# Create a list of percentiles (from 0 to 99)
percentiles = list(range(100))

# Calculate hourly averages for each hour of the day for all 7 days of the week
day_patterns = [[] for _ in range(7)]
day_patterns_ldc = [[] for _ in range(7)]
for day in range(7):
    day_data = df[df.index.dayofweek == day]
    sorted_loads = sorted(day_data['load'], reverse=True)
    day_patterns_ldc[day] = sorted_loads# for load duration curve
    for hour in range(24):
        day_patterns[day].append(day_data['load'][day_data.index.hour == hour].mean())
        
month_patterns = [[] for _ in range(12)]
month_patterns_ldc = [[] for _ in range(12)]

for month in range(1, 13):  # Loop through months (assuming data spans a whole year)
    month_data = df[df.index.month == month]
    sorted_loads = sorted(month_data['load'], reverse=True)
    month_patterns_ldc[month - 1] = sorted_loads  # for load duration curve
    for hour in range(24):
        month_patterns[month - 1].append(month_data['load'][month_data.index.hour == hour].mean())

        
# Create a list of day labels for the legend
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

# Calculate hourly averages for each hour of the day
weekdays_pattern = []
weekends_pattern = []
for hour in range(24):
    weekdays_pattern.append(weekdays['load'][weekdays.index.hour == hour].mean())
    weekends_pattern.append(weekends['load'][weekends.index.hour == hour].mean())
    


# Create a list of hours (0 to 23) for the x-axis
hours = list(range(24))

# Plot the hourly data for weekdays and weekends
plt.figure(figsize=(12, 6))
plt.plot(hours, weekdays_pattern, label='weekdays_pattern', marker='o')
plt.plot(hours, weekends_pattern, label='weekends_pattern', marker='o')
plt.title('Hourly Electrical Load Profile')
plt.xlabel('Hour of the Day')
plt.ylabel('Average Load (kW)')
plt.legend()
plt.grid(True)
plt.xticks(hours)
plt.savefig("average_weekday_weekend.png", format="png")
plt.show()

# Plot the hourly data for all 7 days of the week on the same page
plt.figure(figsize=(12, 6))
for day in range(7):
    plt.plot(hours, day_patterns[day], label=days[day], marker='o')

plt.title('Hourly Electrical Load Profile for All Days of the Week')
plt.xlabel('Hour of the Day')
plt.ylabel('Average Load (kW)')
plt.legend()
plt.grid(True)
plt.xticks(hours)
plt.savefig("average_load.png", format="png")
plt.show()


# Reset the index if you want to keep the 'timestamp' column
weekdays.reset_index(inplace=True)
weekends.reset_index(inplace=True)

# Save the DataFrames to separate CSV files
weekdays.to_csv('weekdays_data.csv', index=False)
weekends.to_csv('weekends_data.csv', index=False)

# Plot the load duration curves for all 7 days of the week
plt.figure(figsize=(12, 6))
for day in range(7):
    day_data_ldc = day_patterns_ldc[day]
    if len(day_data_ldc) > 0:  # Check if the list is not empty
        print(f"Day {day + 1} length: {len(day_data_ldc)}")
        plt.plot(percentiles, [day_data_ldc[int(p * len(day_data_ldc) / 100)] for p in percentiles], label=days[day])
        
plt.title('Load Duration Curve for All Days of the Week')
plt.xlabel('Percentile')
plt.ylabel('Load (kW)')
plt.legend()
plt.grid(True)

# Set x-axis ticks at 10 percentile intervals
plt.xticks(range(0, 101, 10))
#plt.xticks(percentiles)

plt.savefig("load_duration_curve_all_days.png", format="png")
plt.show()



plt.figure(figsize=(12, 6)) 

for month in range(12):
    month_data_ldc = month_patterns_ldc[month]
    if len(month_data_ldc) > 0:  # Check if the list is not empty
        print(f"Month {month + 1} length: {len(month_data_ldc)}")
        plt.plot(percentiles, [month_data_ldc[int(p * len(month_data_ldc) / 100)] for p in percentiles], label=f'Month {month + 1}')

plt.title('Load Duration Curve for All Months')
plt.xlabel('Percentile')
plt.ylabel('Load (kW)')
plt.legend()
plt.grid(True)
plt.axhline(y=1850, color='gray', linestyle='--', label='Load = 1850 kW')

plt.savefig("load_duration_curve_all_months.png", format="png")
plt.show()
# 1 month = 720 hours




# Plot the load duration curves for weekdays and weekends
plt.figure(figsize=(12, 6))
plt.plot(percentiles, [sorted_weekdays_loads[int(p * len(sorted_weekdays_loads) / 100)] for p in percentiles], label='Weekdays')
plt.plot(percentiles, [sorted_weekends_loads[int(p * len(sorted_weekends_loads) / 100)] for p in percentiles], label='Weekends')

plt.title('Load Duration Curve for Weekdays and Weekends')
plt.xlabel('Percentile')
plt.ylabel('Load (kW)')
plt.legend()
plt.grid(True)

# Set x-axis ticks at 10 percentile intervals
plt.xticks(range(0, 101, 10))
#plt.xticks(percentiles)

plt.savefig("load_duration_curve_weekdays_weekends.png", format="png")
plt.show()

plt.figure(figsize=(12, 6))
plt.subplot(1, 2, 1)
plt.hist(weekdays['load'], bins=30, color='b', alpha=0.7)
plt.title('Weekday Load Distribution')
plt.xlabel('Load')
plt.ylabel('Frequency')

plt.subplot(1, 2, 2)
plt.hist(weekends['load'], bins=30, color='g', alpha=0.7)
plt.title('Weekend Load Distribution')
plt.xlabel('Load')
plt.ylabel('Frequency')

plt.tight_layout()
plt.savefig("load_distributiom.png", format="png")
plt.show()
