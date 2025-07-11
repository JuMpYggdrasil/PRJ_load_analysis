import re
import pandas as pd

file_path = 'ammr.xlsx'

def find_first_last_date_idx(df, datetime_col=0):
    """
    Returns the index of the first and last row where the first column matches DD/MM/YYYY.
    """
    date_regex = re.compile(r'^\d{2}/\d{2}/\d{4}')
    first_idx = None
    last_idx = None
    for idx, val in df.iloc[:, datetime_col].items():
        if isinstance(val, str) and date_regex.match(val.strip()):
            if first_idx is None:
                first_idx = idx
            last_idx = idx
    return first_idx, last_idx

try:
    df = pd.read_excel(file_path)
    print("File read successfully.")

    first_idx, last_idx = find_first_last_date_idx(df)
    print(f"First row index with date: {first_idx}")
    if first_idx is not None:
        print(f"First row value: {df.iloc[first_idx].tolist()}")

    print(f"Last row index with date: {last_idx}")
    if last_idx is not None:
        print(f"Last row value: {df.iloc[last_idx].tolist()}")

    # Get only the rows in the range [first_idx, last_idx]
    if first_idx is not None and last_idx is not None:
        df_range = df.iloc[first_idx:last_idx+1]
        print("DataFrame with only date rows:")
        print(df_range)

except FileNotFoundError:
    print(f"File not found: {file_path}")
except ValueError as ve:
    print(f"Value error while reading {file_path}: {ve}")
except Exception as e:
    print(f"Error reading {file_path}: {e}")