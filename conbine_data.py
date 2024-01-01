import pandas as pd
import os
import xlrd

# Get the current working directory
current_directory = os.getcwd()

# Set the directory where your Excel files are located
excel_files_dir = r'C:\\Users\\thitinun\\Desktop\\test_proj\\'
# excel_files_dir = current_directory


# Create an empty list to store individual dataframes
all_dataframes = []

# Create an empty DataFrame to store the combined data
combined_data = pd.DataFrame()

# List all the Excel files in the directory
excel_files = [file for file in os.listdir(excel_files_dir) if (file.endswith('.xlsx') or file.endswith('.xls'))]

# Sort the files to ensure they are processed in the correct order
excel_files.sort()

# Loop through the Excel files and concatenate them
for file in excel_files:
    file_path = os.path.join(excel_files_dir, file)
    df = pd.read_excel(file_path, header=4)
    df = df.iloc[:, :3]
    all_dataframes.append(df)
    # print(df.columns)
    combined_data = pd.concat([combined_data, df], ignore_index=True)
    
# # Concatenate all dataframes vertically
combined_data = pd.concat(all_dataframes)

# # Save the combined data to a new CSV file
combined_data.to_csv(excel_files_dir+'combined_data.csv', index=False)
