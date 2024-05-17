import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

unit_price_on_peak = 4.1839
unit_price_off_peak = 2.6037
# unit_price_holiday = unit_price_off_peak
unit_price_demand_charge = 132.93
unit_price_service_charge = 312.24
# *** ignore FT 5-10% and vat 7%

# Load your electrical load data into a Pandas DataFrame
df = pd.read_csv('analyse_electric_load_data.csv', parse_dates=['timestamp'])
# df.rename(columns={'Date': 'timestamp','Load': 'load'}, inplace=True)

# Assuming your DataFrame has a 'timestamp' column, you can set it as the index
df.set_index('timestamp', inplace=True)

first_row_timestamp = df.index[0]
year_of_first_row = first_row_timestamp.year
# Create the folder if it doesn't exist
folder_name = f"result_{year_of_first_row}"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"Folder '{folder_name}' created.")


# Create a list of day labels for the legend
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

# Define a day color palette
dayColor_palette = ['yellow', 'pink','green', 'orange', 'lightblue', 'purple', 'red']

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

# Open a text file in write mode
with open(f'result_{year_of_first_row}/Energy consumption_result.txt', 'w') as f:
    # Redirect the standard output to the text file
    import sys
    sys.stdout = f
    
    print(f"\n\rEnergy consumption -- Load (kWh)")
    for month in range(1, 13):  # Loop through months (assuming data spans a whole year)
        monthly_energy = df[df.index.month == month]['load'].sum()
        print(f"{month} {months[month-1]} {monthly_energy:,.0f} kWh")
    print("\n\r")
        
    sum_on_peak_data = on_peak_data['load'].sum()
    print(f"Energy of On Peak Data: {sum_on_peak_data:,.2f} kWh")

    sum_off_peak_data = off_peak_data['load'].sum()
    print(f"Energy of Off Peak Data: {sum_off_peak_data:,.2f} kWh")

    sum_holiday_data = holiday_data['load'].sum()
    print(f"Energy of holiday Data: {sum_holiday_data:,.2f} kWh")

    print(f"Total Energy: {(sum_on_peak_data+sum_off_peak_data+sum_holiday_data):,.2f} kWh")

    sum_total_data = df['load'].sum()
    print(f"Sum of all Data: {sum_total_data:,.2f} kWh")

    demand_charge_df = df['load'].resample('M').max()
    sum_demand_charge = demand_charge_df.sum()
    print(f"Sum of demand_charge: {sum_demand_charge:,.2f} kW")
    # print(demand_charge_df)

    print("")
    price_on_peak = unit_price_on_peak * sum_on_peak_data
    print(f"price_on_peak: {price_on_peak:,.2f} THB")

    price_off_peak = unit_price_off_peak * (sum_off_peak_data+sum_holiday_data)
    print(f"price_off_peak: {price_off_peak:,.2f} THB")

    price_demand_charge = unit_price_demand_charge * sum_demand_charge
    print(f"price_demand_charge: {price_demand_charge:,.2f} THB")

    price_service_charge = unit_price_service_charge * 12

    total_price = price_on_peak + price_off_peak + price_demand_charge + price_service_charge
    print(f"Total Base Price: {total_price:,.2f} THB")
    print("\tignore FT & vat\n\r")

    # After exiting the 'with' block, the standard output will be reverted back to the console
    
    
# Extract data for weekdays (Monday to Friday)
weekdays = df[weekday_mask & ~specific_dates_mask]
# sum_weekday = weekdays['load'].sum()
# print(f"Sum of weekends(Holiday) Data: {sum_weekday:.2f} kWh")
# Extract data for weekends (Saturday and Sunday)
weekends = df[weekend_mask | specific_dates_mask]
# sum_weekend = weekends['load'].sum()
# print(f"Sum of weekends(Holiday) Data: {sum_weekend:.2f} kWh")


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
plt.savefig(f"result_{year_of_first_row}/average_weekday_weekend.png", format="png")
plt.show()


# Define a day color palette
dayColor_palette = ['yellow', 'pink','green', 'orange', 'lightblue', 'purple', 'red']

# Plot the hourly data for all 7 days of the week on the same page
plt.figure(figsize=(12, 6))
for day in range(7):
    plt.plot(hours, day_patterns[day], label=days[day], marker='o', color=dayColor_palette[day])

plt.title('Hourly Electrical Load Profile for All Days of the Week')
plt.xlabel('Hour of the Day')
plt.ylabel('Average Load (kW)')
plt.legend()
plt.grid(True)
plt.xticks(hours)
plt.savefig(f"result_{year_of_first_row}/average_load_every_day.png", format="png")
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
        # print(f"Day {day + 1} length: {len(day_data_ldc)}")
        plt.plot(percentiles, [day_data_ldc[int(p * len(day_data_ldc) / 100)] for p in percentiles], label=days[day], color=dayColor_palette[day])
        
plt.title('Load Duration Curve for All Days of the Week')
plt.xlabel('Percentile')
plt.ylabel('Load (kW)')
plt.legend()
plt.grid(True)

# Set x-axis ticks at 10 percentile intervals
plt.xticks(range(0, 101, 10))
#plt.xticks(percentiles)

plt.savefig(f"result_{year_of_first_row}/load_duration_curve_all_days.png", format="png")
plt.show()



plt.figure(figsize=(12, 6)) 

for month in range(12):
    month_data_ldc = month_patterns_ldc[month]
    if len(month_data_ldc) > 0:  # Check if the list is not empty
        # print(f"Month {month + 1} length: {len(month_data_ldc)}")
        plt.plot(percentiles, [month_data_ldc[int(p * len(month_data_ldc) / 100)] for p in percentiles], label=f'Month {month + 1}')

plt.title('Load Duration Curve for All Months')
plt.xlabel('Percentile')
plt.ylabel('Load (kW)')
plt.legend()
plt.grid(True)
mark_line_val = 00
plt.axhline(y=mark_line_val, color='gray', linestyle='--', label=f'Load = {mark_line_val:.1f} kW')

plt.savefig(f"result_{year_of_first_row}/load_duration_curve_all_months.png", format="png")
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

plt.savefig(f"result_{year_of_first_row}/load_duration_curve_weekdays_weekends.png", format="png")
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
plt.savefig(f"result_{year_of_first_row}/load_distribution.png", format="png")
plt.show()





####################################
### test section =========== not use
df_load_with_pv = df


# Define the time range (6:00 AM to 6:00 PM)
time_range = pd.to_datetime(['06:00:00', '18:00:00'], format='%H:%M:%S').time


# Replace values in the specified time range with NaN
df_load_with_pv['load_wo_pv'] = df_load_with_pv.apply(lambda row: np.nan if time_range[0] <= row.name.time() <= time_range[1] else row['load'], axis=1)

# Forward fill to replace empty values with the nearest non-empty value
df_load_with_pv.ffill(inplace=True)

# Display the resulting DataFrame
# print(df_load_with_pv)

df_load_with_pv.to_csv('load_without_pv.csv', index=True)