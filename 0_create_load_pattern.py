# create load pattern from electricity bill
import pandas as pd
import matplotlib.pyplot as plt
import os

on_peak_demand = 1544077.352 # kWh, units per year
off_peak_demand = 1366903.763 # kWh, units per year
holiday_demand = 1561699.456 # kWh, units per year

# Create a DatetimeIndex for the year 2023 with hourly frequency
hourly_index = pd.date_range(start='2023-01-01', end='2023-12-31 23:59:00', freq='15T')

df = pd.DataFrame(index=hourly_index)

# Rename the index column to 'Date'
df = df.rename_axis('Date')


# Create a list of day labels for the legend
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

weekday_mask = (df.index.dayofweek >= 0) & (df.index.dayofweek < 5)
weekend_mask = (df.index.dayofweek >= 5)
on_peak_mask = (df.index.hour >= 9) & (df.index.hour < 22)
off_peak_mask = ~on_peak_mask
# PEA off-peak date @(MON-FRI) special
specific_dates = ['2021-01-01', '2021-02-12', '2021-02-26', '2021-04-06', '2021-04-12', '2021-04-13', '2021-04-14', '2021-04-15', '2021-05-04', '2021-05-26', '2021-06-03', '2021-07-27', '2021-07-28', '2021-08-12', '2021-09-24', '2021-10-13', '2021-12-10', '2021-12-31',
                  '2022-02-16', '2022-04-06', '2022-04-13', '2022-04-14', '2022-04-15', '2022-05-04', '2022-06-03', '2022-07-13', '2022-07-14', '2022-07-15', '2022-07-28', '2022-07-29', '2022-08-12', '2022-10-13', '2022-10-14', '2022-12-05', '2022-12-30',
                  '2023-03-06', '2023-04-06', '2023-04-13', '2023-04-14', '2023-05-01', '2023-05-04', '2023-07-28', '2023-08-01', '2023-08-02', '2023-10-13', '2023-10-23', '2023-12-05',
                  '2024-01-01', '2024-04-15', '2024-05-01', '2024-05-22', '2024-06-03', '2024-08-12', '2024-10-23', '2024-12-05', '2024-12-10', '2024-12-31']
specific_dates = pd.to_datetime(specific_dates, format='%Y-%m-%d')
specific_dates_mask = df.index.isin(specific_dates)


# selected_month_mask = (df.index.month == 2) # for view specific month
selected_month_mask = True # for all month

# Apply the masks to create the "On Peak", "Off Peak" and "Holiday" groups
on_peak_data = df[weekday_mask & ~specific_dates_mask & on_peak_mask & selected_month_mask]
off_peak_data = df[weekday_mask & ~specific_dates_mask & off_peak_mask & selected_month_mask]
holiday_data = df[(specific_dates_mask | weekend_mask) & selected_month_mask]

# on_peak_hours_count = len(on_peak_data)*15/60
# off_peak_hours_count = len(off_peak_data)*15/60
# holiday_hours_count = len(holiday_data)*15/60
on_peak_hours_count = len(on_peak_data)*15/60
off_peak_hours_count = len(off_peak_data)*15/60
holiday_hours_count = len(holiday_data)*15/60

print(on_peak_hours_count,off_peak_hours_count,holiday_hours_count)
print(on_peak_hours_count+off_peak_hours_count+holiday_hours_count)

# Set all values in _data to the demand per hour
df.loc[on_peak_data.index, 'Load'] = on_peak_demand / on_peak_hours_count
df.loc[off_peak_data.index, 'Load'] = off_peak_demand / off_peak_hours_count
df.loc[holiday_data.index, 'Load'] = holiday_demand / holiday_hours_count



# ******* need to change format before use *******
file_name = 'source/created_load_pattern.csv'
from_format = '%Y-%m-%d %H:%M:%S'
to_format = '%d/%m/%Y %H.%M' # (standard)

# Log DataFrame to CSV
df.to_csv(file_name)
# Read the CSV file into a DataFrame
df = pd.read_csv(file_name)

# Reformat the 'Date' column to the desired format
df['Date'] = pd.to_datetime(df['Date'], format=from_format).dt.strftime(to_format)

# Save the modified DataFrame back to a CSV file
file_name_without_extension, _ = os.path.splitext(file_name)
homer_file_name = file_name_without_extension + "_edit.csv"
df.to_csv(homer_file_name, index=False)


# Plot the data
plt.figure(figsize=(10, 6))
plt.plot(df.index, df['Load'], color='blue', linewidth=1)
plt.title('Electricity Load for the Year 2023')
plt.xlabel('Date')
plt.ylabel('Load (kWh)')
plt.ylim(bottom=0)  # Ensure y-axis starts at 0
plt.grid(True)
plt.show()

