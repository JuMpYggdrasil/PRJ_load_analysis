import pandas as pd
import os

file_name = "EnergyDayChartAll2023.csv"
from_format = '%m/%d/%Y %H:%M'
to_format = '%d/%m/%Y %H.%M' # (standard)

# Read the CSV file into a DataFrame
df = pd.read_csv(file_name)

# Reformat the 'Date' column to the desired format
df['Date'] = pd.to_datetime(df['Date'], format=from_format).dt.strftime(to_format)

# Save the modified DataFrame back to a CSV file
file_name_without_extension, _ = os.path.splitext(file_name)
homer_file_name = file_name_without_extension + "_edit.csv"
df.to_csv(homer_file_name, index=False)
