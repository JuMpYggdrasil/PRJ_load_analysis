import pandas as pd

def split_excel_sheets(input_file):
    # Read the Excel file
    xls = pd.ExcelFile(input_file)
    
    # Get the list of sheet names
    sheet_names = xls.sheet_names
    
    # Iterate over each sheet and save it to a separate file
    for sheet_name in sheet_names:
        # Read each sheet into a DataFrame
        df = pd.read_excel(xls, sheet_name)
        
        # Define the output file name
        output_file = f"{sheet_name}.xlsx"
        
        # Write the DataFrame to a new Excel file
        df.to_excel(output_file, index=False)

# Example usage:
input_file = "source\RAJBURI_COGEN\Load Profile 115 kV ปี 2023.xlsx"
split_excel_sheets(input_file)
