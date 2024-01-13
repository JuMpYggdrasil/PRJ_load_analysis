import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

file_path = 'combined_data.csv'
# Load the historical data with the specified timestamp format
# date_format = '%d.%m.%Y %H:%M'
date_format = '%d/%m/%Y %H.%M'
#date_format ='ISO8601'
data = pd.read_csv(file_path, parse_dates=['Date'], date_format=date_format)

#data['Date'] = pd.to_datetime(data['Date'])
data.rename(columns={'Date': 'timestamp','Load': 'load'}, inplace=True)

# Ensure the timestamp column is set as the index
data.set_index('timestamp', inplace=True)

# Check for missing values and handle them if necessary
if data.isnull().any().any():
    data = data.interpolate()  # Interpolate missing values
    # or
    # data = data.fillna(method='ffill')  # Forward fill missing values
    # data = data.fillna(method='bfill')  # Backward fill missing values
    



# Aggregate data to hourly intervals
df = data.resample('H').mean()  # You can use 'D' for daily aggregation

# Optionally, add additional features like day of the week
df['day_of_week'] = df.index.dayofweek

# Add a 'month' column
df['month'] = df.index.month

# # Generate a datetime index for an entire year with hourly frequency
# date_rng = pd.date_range(start='2023-01-01', end='2023-12-31 23:00:00', freq='H')

# # Generate synthetic data
# np.random.seed(0)
# data = np.random.randn(len(date_rng))

# # Create a DataFrame
# df = pd.DataFrame(data, index=date_rng, columns=['Load'])

# # Extract features
df['hour'] = df.index.hour
# df['day_of_week'] = df.index.dayofweek
df['rolling_mean'] = df['load'].rolling(window=24).mean()

# # Drop NaN values from rolling mean calculation
# df.dropna(inplace=True)

# Select features for clustering
features = df[['load', 'hour', 'day_of_week', 'rolling_mean']]

# # Apply K-means clustering
# kmeans = KMeans(n_clusters=4, random_state=0)
# df['cluster'] = kmeans.fit_predict(features)
# Apply K-means clustering
# Explicitly setting n_init to 10, which is the current default
kmeans = KMeans(n_clusters=4, n_init=10, random_state=0)
df['cluster'] = kmeans.fit_predict(features)

# Plot the clusters
for cluster in sorted(df['cluster'].unique()):
    plt.figure(figsize=(10, 6))
    plt.title(f"Cluster {cluster}")
    cluster_data = df[df['cluster'] == cluster]
    plt.plot(cluster_data['load'], label=f"Cluster {cluster}", linestyle='', marker='o')
    plt.legend()
    plt.show()
