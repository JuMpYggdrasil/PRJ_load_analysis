import pandas as pd
import matplotlib.pyplot as plt

# Electricity demand data
on_peak_demand = 2780 * 12  # kWh, units per year
off_peak_demand = 2030 * 12  # kWh, units per year
holiday_demand = 1980 * 12  # kWh, units per year

# Create a DatetimeIndex for the year 2023 with hourly frequency
hourly_index = pd.date_range(start='2023-01-01', end='2023-12-31 23:59:00', freq='15T')

# Create a DataFrame with the hourly timestamp as index
df = pd.DataFrame(index=hourly_index)

# Rename the index column to 'Date'
df = df.rename_axis('Date')

# Masks for weekdays, weekends, on-peak, off-peak, and holidays
weekday_mask = (df.index.dayofweek >= 0) & (df.index.dayofweek < 5)
weekend_mask = (df.index.dayofweek >= 5)
on_peak_mask = (df.index.hour >= 9) & (df.index.hour < 22)
off_peak_mask = ~on_peak_mask

# Special dates mask
specific_dates = ['2023-01-01', '2023-07-04']  # Example dates, you can add more
specific_dates = pd.to_datetime(specific_dates, format='%Y-%m-%d')
specific_dates_mask = df.index.isin(specific_dates)

# Apply the masks to create the "On Peak", "Off Peak" and "Holiday" groups
on_peak_data = df[weekday_mask & ~specific_dates_mask & on_peak_mask]
off_peak_data = df[weekday_mask & ~specific_dates_mask & off_peak_mask]
holiday_data = df[(specific_dates_mask | weekend_mask)]

# Calculate the hours count for each group
on_peak_hours_count = len(on_peak_data) * 15 / 60
off_peak_hours_count = len(off_peak_data) * 15 / 60
holiday_hours_count = len(holiday_data) * 15 / 60

# Set all values in _data to the demand per hour
df.loc[on_peak_data.index, 'Load'] = on_peak_demand / on_peak_hours_count
df.loc[off_peak_data.index, 'Load'] = off_peak_demand / off_peak_hours_count
df.loc[holiday_data.index, 'Load'] = holiday_demand / holiday_hours_count

# Reformat the 'Date' column to the desired format
df.index = df.index.strftime('%d/%m/%Y %H.%M')

# Log DataFrame to CSV
df.to_csv('created_load_pattern.csv')

# Plot the data
plt.figure(figsize=(10, 6))
plt.plot(df.index, df['Load'], color='blue', linewidth=1)
plt.title('Electricity Load for the Year 2023')
plt.xlabel('Date')
plt.ylabel('Load (kWh)')
plt.grid(True)
plt.show()
