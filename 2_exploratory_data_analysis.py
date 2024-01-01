import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load the prepared data
data = pd.read_csv('prepared_electric_load_data.csv', parse_dates=['timestamp'], index_col='timestamp')

specific_1_day_mask = (data.index.dayofweek == 0) 
specific_2_day_mask = (data.index.dayofweek >= 0) & (data.index.dayofweek < 6)
specific_3_day_mask = (data.index.dayofweek == 6) 

specific_1_day = data[specific_1_day_mask]
specific_2_day = data[specific_2_day_mask]
specific_3_day = data[specific_3_day_mask]

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

# Explore seasonality with a box plot
sns.boxplot(x='month', y='load', data=data, showfliers = False)
plt.title('Seasonal Variation in Load')
plt.xlabel('Month')
plt.ylabel('Load')
plt.savefig("Seasonal.png", format="png")
plt.show()

# Explore seasonality with a box plot
sns.boxplot(x='month', y='load', data=specific_1_day, showfliers = False)
plt.title('Seasonal Variation in Load of MON Day')
plt.xlabel('Month')
plt.ylabel('Load')
plt.savefig("Seasonal_specific_1.png", format="png")
plt.show()

# Explore seasonality with a box plot
sns.boxplot(x='month', y='load', data=specific_2_day, showfliers = False)
plt.title('Seasonal Variation in Load of MON-SAT Day')
plt.xlabel('Month')
plt.ylabel('Load')
plt.savefig("Seasonal_specific_2.png", format="png")
plt.show()

# Explore seasonality with a box plot
sns.boxplot(x='month', y='load', data=specific_3_day, showfliers = False)
plt.title('Seasonal Variation in Load of SUN Day')
plt.xlabel('Month')
plt.ylabel('Load')
plt.savefig("Seasonal_specific_3.png", format="png")
plt.show()

# Explore trends with a rolling mean
rolling_mean = data['load'].rolling(window=30).mean()  # 30-day rolling mean
plt.figure(figsize=(12, 6))
plt.plot(data.index, data['load'], label='Load Data')
plt.plot(data.index, rolling_mean, label='30-Day Rolling Mean', color='orange')
plt.xlabel('Timestamp')
plt.ylabel('Load')
plt.title('Electrical Load Time Series with Rolling Mean')
plt.legend()
plt.grid(True)
plt.show()

# Explore day of the week patterns
sns.boxplot(x='day_of_week', y='load', data=data, showfliers = False)
plt.title('Load Variation by Day of the Week')
plt.xlabel('Day of the Week')
plt.ylabel('Load')
plt.xticks(range(7), ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])  # Optional: Label days of the week
plt.savefig("LoadVariation.png", format="png")
plt.show()



data.to_csv('analyse_electric_load_data.csv')