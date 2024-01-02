import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

# Generate a datetime index for an entire year with hourly frequency
date_rng = pd.date_range(start='2023-01-01', end='2023-12-31 23:00:00', freq='H')

# Generate synthetic data
np.random.seed(0)
data = np.random.randn(len(date_rng))

# Create a DataFrame
df = pd.DataFrame(data, index=date_rng, columns=['Load'])

# Extract features
df['hour'] = df.index.hour
df['day_of_week'] = df.index.dayofweek
df['rolling_mean'] = df['Load'].rolling(window=24).mean()

# Drop NaN values from rolling mean calculation
df.dropna(inplace=True)

# Select features for clustering
features = df[['Load', 'hour', 'day_of_week', 'rolling_mean']]

# Apply K-means clustering
kmeans = KMeans(n_clusters=4, random_state=0)
df['cluster'] = kmeans.fit_predict(features)

# Plot the clusters
for cluster in sorted(df['cluster'].unique()):
    plt.figure(figsize=(10, 6))
    plt.title(f"Cluster {cluster}")
    cluster_data = df[df['cluster'] == cluster]
    plt.plot(cluster_data['Load'], label=f"Cluster {cluster}", linestyle='', marker='o')
    plt.legend()
    plt.show()
