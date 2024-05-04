import pandas as pd

# Define the original timestamp format and the desired format
timestamp_format_standard = "%Y-%m-%d %H:%M:%S"
timestamp_format_homer = "%Y-{m:d}-{d:d} %H:%M"
timestamp_format_AMR = '%d/%m/%Y %H.%M' # PEA

output_file_name = r'combined_data.csv'
df = pd.read_csv(output_file_name)
# Assuming df is your DataFrame and 'Date' column needs reformatting
df['Date'] = pd.to_datetime(df['Date'], format=timestamp_format_AMR)

# Define a function to reformat the date
def reformat_date(date):
    return date.strftime(timestamp_format_homer).format(m=date.month, d=date.day)

# Apply the function to the 'Date' column
df['Date'] = df['Date'].apply(reformat_date)

print(df)
