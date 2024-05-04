import pandas as pd

# Define the start and end timestamps
start_date = "2022-01-01 00:00"
end_date = "2022-12-31 23:59"

# Create a date range with hourly frequency
date_range = pd.date_range(start=start_date, end=end_date, freq="15T")

# Create an initial DataFrame with the timestamp index
df = pd.DataFrame(index=date_range)

# Set the desired timestamp format
timestamp_format = '%d.%m.%Y %H:%M'

# Format the timestamp index with the specified format
df.index = df.index.strftime(timestamp_format)

# Set the column header to 'Date'
df.index.name = 'Date'

# Convert the index to a DatetimeIndex to access dayofweek, hour, etc.
df.index = pd.to_datetime(df.index, format=timestamp_format)

# Define masks for weekdays, weekends, high hours, and low hours
weekday_mask = (df.index.dayofweek >= 0) & (df.index.dayofweek < 5)
weekend_mask = (df.index.dayofweek >= 5)
high_mask = (df.index.hour >= 9) & (df.index.hour < 22)
low_mask = ~high_mask

# Set 'Load' values based on the defined masks
df.loc[weekday_mask & high_mask, 'Load'] = 100
df.loc[weekday_mask & low_mask, 'Load'] = 20
df.loc[weekend_mask & high_mask, 'Load'] = 80
df.loc[weekend_mask & low_mask, 'Load'] = 20

# Check for missing values and handle them if necessary
if df.isnull().any().any():
    df = df.interpolate()  # Interpolate missing values
    # or
    # df = df.fillna(method='ffill')  # Forward fill missing values
    # df = df.fillna(method='bfill')  # Backward fill missing values


# Save the DataFrame to a CSV file
# df.to_csv('template_24_7.csv')# all day all night 100 100 100 100
# df.to_csv('template_24_6.csv')# 6 days flat 100 100 0 0
# df.to_csv('template_24_5.csv')# weekday only 100 100 0 0
df.to_csv('template_16_7.csv')# 6am-10pm 100 0 100 0
# df.to_csv('template_16_5.csv')# 6am-10pm weekday only 100 0 0 0
# df.to_csv('template_8_7.csv')# 9am-5pm 100 0 100 0
# df.to_csv('template_8_5.csv')# 9am-5pm weekday only 100 0 0 0
