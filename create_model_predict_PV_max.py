import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error
import joblib
import math

install_capacityPV_Install_Capacity = 200 # kW

# Load the dataset
df = pd.read_csv('pv_data_for_train_model.csv')

# Define the input features (X) and the target variable (y)
X = df[['pv_5', 'pv_6', 'pv_7']]*install_capacityPV_Install_Capacity
y = df['pv_max']*install_capacityPV_Install_Capacity

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create a linear regression model
# model = LinearRegression()
# model = KNeighborsRegressor(n_neighbors=6)
model = MLPRegressor(hidden_layer_sizes=(100,), max_iter=2000, random_state=42)

# Train the model on the training set
model.fit(X_train, y_train)

# Make predictions on the test set
y_pred = model.predict(X_test)

# Evaluate the model
mse = mean_squared_error(y_test, y_pred)
print(f'Mean Squared Error: {mse}')
print(f'RMSE: {math.sqrt(mse)}')

# Save the model for future use
joblib.dump(model, 'pv_max_prediction_model.joblib')

# Create a DataFrame with y_test and y_pred
results_df = pd.DataFrame({'Actual': y_test, 'Predicted': y_pred})

# Save the DataFrame to a CSV file
results_df.to_csv('prediction_results.csv', index=False)