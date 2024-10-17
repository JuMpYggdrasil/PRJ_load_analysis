import pandas as pd
import os
from datetime import timedelta
import openpyxl
import xlrd,xlwt
import tkinter as tk
from tkinter import filedialog

# create 1 year data (.csv) from 12 excel (.xlsx) files

output_file_name = r'combined_data.csv'

## PEA AMR format setting
skiprows_count = 5 #DEFAULT 5, 8
peak_string = "RATE A"
off_peak_string = "RATE B"
holiday_string = "RATE C"
header_column_index = [0, 1, 3, 5]

# ## Robinson AMR format setting
# skiprows_count = 1 #DEFAULT 5
# peak_string = "RATE A"
# off_peak_string = "RATE B"
# holiday_string = "RATE C"
# header_column_index = [0, 1, 3, 5]

# ### PEA kWh AMR format setting (don't forget to scale load x4)
# skiprows_count = 8 #DEFAULT 8
# peak_string = "RATE A"
# off_peak_string = "RATE B"
# holiday_string = "RATE C"
# header_column_index = [0, 1, 2, 3]

# ## RAJBURI_COGEN AMR format setting
# skiprows_count = 7
# peak_string = "RATE A"
# off_peak_string = "RATE B"
# holiday_string = "RATE C"
# header_column_index = [0, 1, 3, 5]


# ## egat dimond AMR format setting
# skiprows_count = 3
# peak_string = "Peak (kW)"
# off_peak_string = "Offpeak (kW)"
# holiday_string = "Offpeak-Holiday (kW)"
# header_column_index = [0, 1, 2, 3]

timestamp_format_AMR = '%d/%m/%Y %H.%M' # PEA
# timestamp_format_AMR = '%d/%m/%Y %H:%M' # RAJBURI_COGEN
# timestamp_format_AMR = '%d %b %Y %H:%M' # EGAT_DIAMOND

timestamp_format_standard = '%d/%m/%Y %H.%M'
timestamp_format_homer = '%d.%m.%Y %H:%M'

def dumb_AMR_format_to_datetime(date_str):
    try:
        date_str = date_str.strip()
        if date_str[11:13] != '24':
            date_obj = pd.to_datetime(date_str, format=timestamp_format_AMR) - timedelta(minutes=15)
        else:
            date_str = date_str[0:11] + '00' + date_str[13:]
            date_obj = pd.to_datetime(date_str, format=timestamp_format_AMR) + timedelta(days=1) - timedelta(minutes=15)
        return date_obj.strftime(timestamp_format_standard)
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

# Define a function to reformat the date
def reformat_date(date):
    return date.strftime("{d:d}.{m:d}.%Y %H:%M").format(m=date.month, d=date.day)

def select_directory(files_dir):
    directory_path = filedialog.askdirectory(initialdir=os.getcwd(), title="Select Directory")
    if directory_path:
        files_dir.set(directory_path)

def check_xlsx_files_exist(directory):
    """
    Check if the directory contains at least one .xlsx file.
    
    Args:
    - directory: The path to the directory to be checked.
    
    Returns:
    - True if at least one .xlsx file exists in the directory, False otherwise.
    """
    # List all the files in the directory
    files = os.listdir(directory)
    
    # Check if any file has .xlsx extension
    for file in files:
        if file.endswith('.xlsx'):
            return True
        elif file.endswith('.csv'):
            return False
    
    # No .xlsx file found
    return False

def combine_xlsx_data(excel_files_dir,output_files_dir):

    # Create an empty list to store individual dataframes
    all_dataframes = []

    # List all the Excel files in the directory
    excel_files = [file for file in os.listdir(excel_files_dir) if file.endswith(('.xlsx', '.xls', '.csv'))]

    # Sort the files to ensure they are processed in the correct order
    excel_files.sort()

    # Loop through the Excel files and add them to the list
    for file in excel_files:
        file_path = os.path.join(excel_files_dir, file)
        try:
            # Open the workbook and unmerge cells
            if check_xlsx_files_exist(excel_files_dir):
                ### for .xlsx
                workbook = openpyxl.load_workbook(file_path)
                for sheet in workbook.worksheets:
                    # Create a list of all merged cells
                    merged_cells = [mc for mc in sheet.merged_cells.ranges]
                    # Unmerge all merged cells
                    for merged_cell in merged_cells:
                        sheet.unmerge_cells(str(merged_cell))
                        
                # Save the unmerged workbook to a temporary file
                temp_file_path = os.path.join(excel_files_dir, 'temp_unmerged.xlsx')
                workbook.save(temp_file_path)
            else:
                print("folder not contain .xlsx")
            
            # Attempt to read the Excel file
            # Now read the unmerged Excel file into a Pandas DataFrame
            df = pd.read_excel(temp_file_path, header=0, skiprows=skiprows_count)
            os.remove(temp_file_path)  # Clean up the temporary file

            
            df = clean_dataframe(df)  # Clean the dataframe to remove non-datetime starting rows
            # df = df.iloc[:, :5]  # Select the first 5 columns
            # df = df.iloc[:, [0, 1, 3, 5]]  # Select the index, 2nd, 4th, and 6th columns
            df = df.iloc[:, header_column_index]
            df = df.fillna(0)
            df["ผลรวม"] = df[peak_string]+df[off_peak_string]+df[holiday_string]
            # incase excel file is energy kWh -> need to scale x4
            # df["ผลรวม"] = df["ผลรวม"]*4

            
            all_dataframes.append(df)

            print(f"Header for {file}: {df.columns.tolist()}")  # Print the header
        except Exception as e:
            # If there is an error, print the error and file name, then continue
            print(f"Error reading {file}: {e}")

    # Check if the list of dataframes is not empty before concatenating
    if all_dataframes:
        # Concatenate all dataframes
        combined_data = pd.concat(all_dataframes, ignore_index=True)
        combined_data.rename(columns={'Unnamed: 0': 'Date','ผลรวม': 'Load'}, inplace=True)
        # Sort by 'Date' : Date is in text format -> not good to sort if it's string(not object)
        

        # Save the combined data to a new CSV file
        combined_data.to_csv(os.path.join(output_files_dir, output_file_name), index=False)
    else:
        print("No data to concatenate. Check if the files are available and correctly formatted.")


    # Read the CSV file into a DataFrame
    df = pd.read_csv(os.path.join(output_files_dir, output_file_name))

    # Reformat the 'Date' column to the desired format
    df['Date'] = pd.to_datetime(df['Date'], format=timestamp_format_standard).dt.strftime(timestamp_format_homer)

    # Drop the 'RATE A', 'RATE B', and 'RATE C' columns
    df.drop([peak_string, off_peak_string, holiday_string], axis=1, inplace=True)
    
    ## convert string to dt object -> sort -> convert back to string
    df['Date'] = pd.to_datetime(df['Date'], format=timestamp_format_homer)
    df = df.sort_values(by='Date')
    # df['Date'] = df['Date'].dt.strftime(timestamp_format_homer)
    
    # Apply the function to the 'Date' column
    df['Date'] = df['Date'].apply(reformat_date)
    

    # Save the modified DataFrame back to a CSV file
    file_name_without_extension, _ = os.path.splitext(output_file_name)
    homer_output_file_name = file_name_without_extension + "_homer.csv"
    df.to_csv(os.path.join(output_files_dir, homer_output_file_name), index=False)

def run_combination():
    combine_xlsx_data(excel_files_dir.get(), output_files_dir.get())

if __name__ == "__main__":
    # Create the main window
    root = tk.Tk()
    root.title("Combine <AMR file>.xlsx in selected directory")

    excel_files_dir = tk.StringVar()
    output_files_dir = tk.StringVar()

    # Entry widgets for selected directories
    tk.Label(root, text="Selected Source Directory:").pack()
    tk.Entry(root, textvariable=excel_files_dir, state='readonly').pack()
    tk.Button(root, text="Select Directory", command=lambda: select_directory(excel_files_dir)).pack()

    tk.Label(root, text="Selected Output Directory:").pack()
    tk.Entry(root, textvariable=output_files_dir, state='readonly').pack()
    tk.Button(root, text="Select Directory", command=lambda: select_directory(output_files_dir)).pack()

    # Button to run combination process
    tk.Button(root, text="Run", command=run_combination).pack()
    tk.Label(root, text=f"result create: {output_file_name}").pack()

    root.mainloop()