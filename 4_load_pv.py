import pandas as pd
import matplotlib.pyplot as plt

df_load = pd.read_csv('analyse_electric_load_data.csv', parse_dates=['timestamp'])
df_load.set_index('timestamp', inplace=True)

df_pv = pd.read_csv('solar_1kW_2023 copy.csv', parse_dates=['timestamp'],date_format='%d/%m/%Y %H:%M')
df_pv.set_index('timestamp', inplace=True)

# check must be "datetime64[ns]"
print(df_load.index.dtype)
print(df_pv.index.dtype)

df_load["pv"] = df_pv["pv"]
df_load.to_csv('dummy.csv')