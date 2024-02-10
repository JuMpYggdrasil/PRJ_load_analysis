import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Load the prepared data
data = pd.read_csv('prepared_electric_load_data.csv', parse_dates=['timestamp'], index_col='timestamp')

first_row_timestamp = data.index[0]
year_of_first_row = first_row_timestamp.year
# Create the folder if it doesn't exist
folder_name = f"result_{year_of_first_row}"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"Folder '{folder_name}' created.")

specific_1_day_mask = (data.index.dayofweek == 0) # MON
specific_2_day_mask = (data.index.dayofweek >= 0) & (data.index.dayofweek < 5) # MON-FRI
specific_3_day_mask = (data.index.dayofweek == 5) # SAT
specific_4_day_mask = (data.index.dayofweek == 6) # SUN
specific_5_day_mask = (data.index.dayofweek >= 5) # SAT-SUN

specific_1_day = data[specific_1_day_mask]
specific_2_day = data[specific_2_day_mask]
specific_3_day = data[specific_3_day_mask]
specific_4_day = data[specific_4_day_mask]
specific_5_day = data[specific_5_day_mask]

# Feature Engineering: Adding lag features (previous hour's load)
data['load_lag1'] = data['load'].shift(1)  # Lag of 1 hour
data['load_lag2'] = data['load'].shift(2)  # Lag of 2 hours

data['load_lag1'] = data['load_lag1'].fillna(0)
data['load_lag2'] = data['load_lag2'].fillna(0)

# Display basic statistics of the data
print(data.describe())



# Check for correlation between variables
correlation_matrix = data.corr()
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm')
plt.title('Correlation Matrix')
plt.show()

# Visualize the time series data
plt.figure(figsize=(12, 6))
plt.plot(data.index, data['load'], label='Load Data')
plt.xlabel('Timestamp')
plt.ylabel('Load')
plt.title('Electrical Load Time Series')
plt.legend()
plt.grid(True)
plt.show()
# plt.clf()



# Create a figure and axes for subplots
fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(12, 6))

# Plot seasonal variation for every day
sns.boxplot(x='month', y='load', data=data, showfliers=False, palette='bright', ax=axes[0,0])
axes[0,0].set_title('Seasonal Variation in Load of MON-SUN Day')
axes[0,0].set_xlabel('Month')
axes[0,0].set_ylabel('Load')

# Plot seasonal variation for MON-FRI day
sns.boxplot(x='month', y='load', data=specific_2_day, showfliers=False, palette='bright', ax=axes[0,1])
axes[0,1].set_title('Seasonal Variation in Load of MON-FRI Day')
axes[0,1].set_xlabel('Month')
axes[0,1].set_ylabel('Load')

# Plot seasonal variation for SAT day
sns.boxplot(x='month', y='load', data=specific_3_day, showfliers=False, palette='bright', ax=axes[1,0])
axes[1,0].set_title('Seasonal Variation in Load of SAT Day')
axes[1,0].set_xlabel('Month')
axes[1,0].set_ylabel('Load')

# Plot seasonal variation for SUN day
sns.boxplot(x='month', y='load', data=specific_4_day, showfliers=False, palette='bright', ax=axes[1,1])
axes[1,1].set_title('Seasonal Variation in Load of SUN Day')
axes[1,1].set_xlabel('Month')
axes[1,1].set_ylabel('Load')

# Adjust layout
plt.tight_layout()

# Save or show the plot
plt.savefig(f"result_{year_of_first_row}/Seasonal_comparison.png", format="png")
plt.show()

sns.set_palette("bright")
# Explore seasonality with a box plot
sns.boxplot(x='month', y='load', data=data, showfliers = False, palette='bright')
plt.title('Seasonal Variation in Load')
plt.xlabel('Month')
plt.ylabel('Load')
plt.savefig(f"result_{year_of_first_row}/Seasonal.png", format="png")
# plt.show()
plt.clf()  # Clear the current figure

# Explore seasonality with a box plot
sns.boxplot(x='month', y='load', data=specific_1_day, showfliers = False, palette='bright')
plt.title('Seasonal Variation in Load of MON Day')
plt.xlabel('Month')
plt.ylabel('Load')
plt.savefig(f"result_{year_of_first_row}/Seasonal_specific_1.png", format="png")
# plt.show()
plt.clf()

# Explore seasonality with a box plot
sns.boxplot(x='month', y='load', data=specific_2_day, showfliers = False, palette='bright')
plt.title('Seasonal Variation in Load of MON-FRI Day')
plt.xlabel('Month')
plt.ylabel('Load')
plt.savefig(f"result_{year_of_first_row}/Seasonal_specific_2.png", format="png")
# plt.show()
plt.clf()


# Explore seasonality with a box plot
sns.boxplot(x='month', y='load', data=specific_3_day, showfliers = False, palette='bright')
plt.title('Seasonal Variation in Load of SAT Day')
plt.xlabel('Month')
plt.ylabel('Load')
plt.savefig(f"result_{year_of_first_row}/Seasonal_specific_3.png", format="png")
# plt.show()
plt.clf()

# Explore seasonality with a box plot
sns.boxplot(x='month', y='load', data=specific_4_day, showfliers = False, palette='bright')
plt.title('Seasonal Variation in Load of SUN Day')
plt.xlabel('Month')
plt.ylabel('Load')
plt.savefig(f"result_{year_of_first_row}/Seasonal_specific_4.png", format="png")
# plt.show()
plt.clf()

# Explore seasonality with a box plot
sns.boxplot(x='month', y='load', data=specific_5_day, showfliers = False, palette='bright')
plt.title('Seasonal Variation in Load of SAT-SUN Day')
plt.xlabel('Month')
plt.ylabel('Load')
plt.savefig(f"result_{year_of_first_row}/Seasonal_specific_5.png", format="png")
# plt.show()
plt.clf()

# Explore day of the week patterns
sns.boxplot(x='day_of_week', y='load', data=data, showfliers = False, palette='bright', hue='day_of_week')
plt.title('Load Variation by Day of the Week')
plt.xlabel('Day of the Week')
plt.ylabel('Load')
plt.xticks(range(7), ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])  # Optional: Label days of the week
plt.savefig(f"result_{year_of_first_row}/LoadVariation.png", format="png")
plt.show()



rolling_mean = data['load'].rolling(window=30).mean()  # 30-day rolling mean

# Create a new figure before plotting
plt.figure(figsize=(12, 6))

# Add labels, title, legend, and grid
plt.xlabel('Timestamp')
plt.ylabel('Load')
plt.title('Electrical Load Time Series with Rolling Mean')
plt.legend()
plt.grid(True)

# Plot load data and rolling mean
plt.plot(data.index, data['load'], label='Load Data')
plt.plot(data.index, rolling_mean, label='30-Day Rolling Mean', color='orange')
plt.show()




data.to_csv('analyse_electric_load_data.csv')