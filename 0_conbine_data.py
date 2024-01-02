import pandas as pd
import os
from datetime import timedelta

def dumb_AMR_format_to_datetime(date_str):
    try:
        date_str = date_str.strip()
        if date_str[11:13] != '24':
            date_obj = pd.to_datetime(date_str, format='%d/%m/%Y %H.%M') - timedelta(minutes=15)
        else:
            date_str = date_str[0:11] + '00' + date_str[13:]
            date_obj = pd.to_datetime(date_str, format='%d/%m/%Y %H.%M') + timedelta(days=1) - timedelta(minutes=15)
        return date_obj.strftime('%d/%m/%Y %H.%M')
    except ValueError:
        return None

def clean_dataframe(df, datetime_col=0):
    df_cleaned = df.copy()
    for index, row in df.iterrows():
        datetime_value = dumb_AMR_format_to_datetime(str(row.iat[datetime_col]))
        if datetime_value:
            df_cleaned.at[index, df.columns[datetime_col]] = datetime_value
        else:
            # Skip or remove the row, depending on your requirement
            df_cleaned.drop(index, inplace=True)
    return df_cleaned


# Set the directory where your Excel files are located
excel_files_dir = r'C:\Users\Egat\Documents\GitHub\PRJ_load_analysis\source'
output_files_dir = r'C:\Users\Egat\Documents\GitHub\PRJ_load_analysis'

# Create an empty list to store individual dataframes
all_dataframes = []

# List all the Excel files in the directory
excel_files = [file for file in os.listdir(excel_files_dir) if file.endswith(('.xlsx', '.xls'))]

# Sort the files to ensure they are processed in the correct order
excel_files.sort()

# Loop through the Excel files and add them to the list
for file in excel_files:
    file_path = os.path.join(excel_files_dir, file)
    try:
        # Attempt to read the Excel file
        df = pd.read_excel(file_path, header=0, skiprows=5)
        print(f"Header for {file}: {df.columns.tolist()}")  # Print the header
        df = clean_dataframe(df)  # Clean the dataframe to remove non-datetime starting rows
        df = df.iloc[:, :5]  # Select the first 5 columns
        df = df.fillna(0)
        all_dataframes.append(df)
    except Exception as e:
        # If there is an error, print the error and file name, then continue
        print(f"Error reading {file}: {e}")

# Check if the list of dataframes is not empty before concatenating
if all_dataframes:
    # Concatenate all dataframes
    combined_data = pd.concat(all_dataframes, ignore_index=True)
    combined_data.rename(columns={'Unnamed: 0': 'Date','ผลรวม': 'Load'}, inplace=True)

    # Save the combined data to a new CSV file
    combined_data.to_csv(os.path.join(output_files_dir, 'combined_data.csv'), index=False)
else:
    print("No data to concatenate. Check if the files are available and correctly formatted.")
