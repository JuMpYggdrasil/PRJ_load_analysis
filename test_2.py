import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

file_path = 'combined_data.csv'
date_format = '%d/%m/%Y %H.%M'  # Ensure this matches the format in your CSV
data = pd.read_csv(file_path, parse_dates=['Date'], date_format=date_format)

# data.rename(columns={'Date': 'timestamp', 'Load': 'load'}, inplace=True)
data.set_index('Date', inplace=True)

# Interpolate missing values (you may choose a different method if more appropriate)
if data.isnull().any().any():
    data.interpolate(inplace=True)

# Aggregate data to hourly intervals
df = data.resample('H').mean() 

# Feature Engineering
df['day_of_week'] = df.index.dayofweek
df['month'] = df.index.month
df['hour'] = df.index.hour
df['rolling_mean'] = df['Load'].rolling(window=24).mean()

# Drop NaN values from rolling mean calculation if needed
df.dropna(inplace=True)

# Select features for clustering
features = df[['Load', 'hour', 'day_of_week', 'rolling_mean']]

# Apply K-means clustering
kmeans = KMeans(n_clusters=4, n_init=10, random_state=0)
df['cluster'] = kmeans.fit_predict(features)

# Plot the clusters
for cluster in sorted(df['cluster'].unique()):
    plt.figure(figsize=(10, 6))
    plt.title(f"Cluster {cluster}")
    cluster_data = df[df['cluster'] == cluster]
    
    # Plotting
    plt.plot(cluster_data.index, cluster_data['Load'], label=f"Cluster {cluster}", linestyle='', marker='o')
    plt.legend()
    plt.show()

    # Save to CSV
    output_file = f'cluster_{cluster}_data.csv'
    
    # Convert index to a column with the specified format
    formatted_cluster_data = cluster_data.copy()
    formatted_cluster_data['Date'] = formatted_cluster_data.index.strftime('%d/%m/%Y %H.%M')
    formatted_cluster_data.reset_index(drop=True, inplace=True)
    
    # Save the DataFrame with the formatted timestamp
    formatted_cluster_data.to_csv(output_file, index=False)
    print(f"Cluster {cluster} data saved to {output_file}")