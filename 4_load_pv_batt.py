import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

PV_Install_Capacity = [0.000001,150] # kW

unit_price_on_peak = 4.1839
unit_price_off_peak = 2.6037
# unit_price_holiday = unit_price_off_peak
unit_price_demand_charge = 132.93
unit_price_service_charge = 312.24
# *** ignore FT 5-10% and vat 7%

df_load = pd.read_csv('analyse_electric_load_data.csv', parse_dates=['timestamp'])
df_load.set_index('timestamp', inplace=True)

first_row_timestamp = df_load.index[0]
year_of_first_row = first_row_timestamp.year
# Create the folder if it doesn't exist
folder_name = f"result_{year_of_first_row}"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"Folder '{folder_name}' created.")

df_pv = pd.read_csv(f'solar_1kW_{year_of_first_row}.csv', parse_dates=['timestamp'],date_format='%d/%m/%Y %H:%M')
df_pv.set_index('timestamp', inplace=True)


# Calculate hourly averages for each hour of the day
solar_pattern = []
for hour in range(24):
    solar_pattern.append(df_pv['pv'][df_pv.index.hour == hour].mean())
    
print(solar_pattern)

df_pv_day = df_pv.resample('D').max()
df_pv_data = pd.DataFrame(index=df_pv_day.index)

df_pv_data['pv_max'] = df_pv_day['pv']
df_pv_data['pv_6']=df_pv[df_pv.index.hour == 6].resample('D').mean()['pv']
df_pv_data['pv_7']=df_pv[df_pv.index.hour == 7].resample('D').mean()['pv']
df_pv_data['pv_8']=df_pv[df_pv.index.hour == 8].resample('D').mean()['pv']
df_pv_data.to_csv('tempo.csv')
    


# Create a list of hours (0 to 23) for the x-axis
hours = list(range(24))

# selected_month_mask = (df.index.month == 2) # for view specific month
selected_month_mask = True # for all month


# check must be "datetime64[ns]"
print(df_load.index.dtype)
print(df_pv.index.dtype)



def cal_pv_serve_load(df_pv,df_load,pv_install_capacity):
    
    df_load["pv_produce"] = df_pv["pv"] * pv_install_capacity * 1.05
    df_load["pv_serve_load"] = np.where(df_load['pv_produce'] > df_load['load'], df_load['load'], df_load['pv_produce'])
    df_load['pv_curtailed'] = np.maximum(0, df_load['pv_produce'] - df_load['pv_serve_load'])
    df_load['load_existing'] = df_load['load'] - df_load['pv_serve_load']

    target_month = [1, 6]

    for month in target_month:

        # Plotting 'load' and 'pv_serve_load' columns against the timestamp index
        plt.plot(df_load.index, df_load['load'], label='Load')
        plt.plot(df_load.index, df_load['pv_produce'], label='PV Produce')

        # Adding labels and title
        plt.xlabel('Timestamp')
        plt.ylabel('Load')
        plt.title('Load and PV Produce Over Time')

        # Adding legend
        plt.legend()

        
        # Set x-axis limits to the current target month
        plt.xlim((df_load.index[0].replace(month=month), df_load.index[0].replace(month=month + 1)))


        # Display the plot
        plt.show()

    sum_pv_produce = df_load['pv_produce'].sum()
    print(f"Energy of pv_produce: {sum_pv_produce:,.2f} kWh/year")
    print(f"Energy of pv_produce: {(sum_pv_produce/pv_install_capacity):,.2f} kWh/kWp/year")
    print(f"Energy of pv_produce: {(sum_pv_produce/pv_install_capacity/365):,.2f} kWh/kWp/day")

    sum_pv_curtailed = df_load['pv_curtailed'].sum()
    print(f"Energy of pv_curtailed: {sum_pv_curtailed:,.2f} kWh  ({(sum_pv_curtailed/sum_pv_produce*100):.2f} %)")

    sum_pv_serve_load = df_load['pv_serve_load'].sum()
    print(f"Energy of pv_serve_load: {sum_pv_serve_load:,.2f} kWh")



    df = df_load

    weekday_mask = (df.index.dayofweek >= 0) & (df.index.dayofweek < 5)
    weekend_mask = (df.index.dayofweek >= 5)
    on_peak_mask = (df.index.hour >= 9) & (df.index.hour < 22)
    off_peak_mask = ~on_peak_mask
    # PEA off-peak date @(MON-FRI) special
    specific_dates = ['2021-01-01', '2021-02-12', '2021-02-26', '2021-04-06', '2021-04-12', '2021-04-13', '2021-04-14', '2021-04-15', '2021-05-04', '2021-05-26', '2021-06-03', '2021-07-27', '2021-07-28', '2021-08-12', '2021-09-24', '2021-10-13', '2021-12-10', '2021-12-31',
                    '2022-02-16', '2022-04-06', '2022-04-13', '2022-04-14', '2022-04-15', '2022-05-04', '2022-06-03', '2022-07-13', '2022-07-14', '2022-07-15', '2022-07-28', '2022-07-29', '2022-08-12', '2022-10-13', '2022-10-14', '2022-12-05', '2022-12-30',
                    '2023-03-06', '2023-04-06', '2023-04-13', '2023-04-14', '2023-05-01', '2023-05-04', '2023-07-28', '2023-08-01', '2023-08-02', '2023-10-13', '2023-10-23', '2023-12-05',
                    '2024-01-01', '2024-04-15', '2024-05-01', '2024-05-22', '2024-06-03', '2024-08-12', '2024-10-23', '2024-12-05', '2024-12-10', '2024-12-31']
    specific_dates = pd.to_datetime(specific_dates, format='%Y-%m-%d')
    specific_dates_mask = df.index.isin(specific_dates)


    # Apply the masks to create the "On Peak", "Off Peak" and "Holiday" groups
    on_peak_data = df[weekday_mask & ~specific_dates_mask & on_peak_mask & selected_month_mask]
    off_peak_data = df[weekday_mask & ~specific_dates_mask & off_peak_mask & selected_month_mask]
    holiday_data = df[(specific_dates_mask | weekend_mask) & selected_month_mask]


    sum_on_peak_data = on_peak_data['pv_serve_load'].sum()
    print(f"  pv_serve_load -- On Peak: {sum_on_peak_data:,.2f} kWh")

    sum_off_peak_data = off_peak_data['pv_serve_load'].sum()
    print(f"  pv_serve_load -- Off Peak: {sum_off_peak_data:,.2f} kWh")

    sum_holiday_data = holiday_data['pv_serve_load'].sum()
    print(f"  pv_serve_load -- holiday: {sum_holiday_data:,.2f} kWh")
    
    demand_charge_df = df['pv_serve_load'].resample('M').max()
    sum_demand_charge = demand_charge_df.sum()
    # print(f"Sum of demand_charge: {sum_demand_charge:.2f} kW")
    

    price_on_peak = unit_price_on_peak * sum_on_peak_data
    # print(f"price_on_peak: {price_on_peak:,.2f} THB")

    price_off_peak = unit_price_off_peak * (sum_off_peak_data+sum_holiday_data)
    # print(f"price_off_peak: {price_off_peak:,.2f} THB")

    price_demand_charge = unit_price_demand_charge * sum_demand_charge
    # print(f"price_demand_charge: {price_demand_charge:,.2f} THB")

    price_service_charge = unit_price_service_charge * 12

    total_price = price_on_peak + price_off_peak + price_demand_charge + price_service_charge
    print(f"Total Base Price: {total_price:,.2f} THB")
    print("\tignore FT & vat\n\r")
        
    discharge_time_mask = (df.index.hour >= 9) & (df.index.hour < 11)
    load_existing_kWh_df = df[discharge_time_mask]['load_existing'].resample('D').sum() # forward euler
    # Count values greater than zero
    count_arbitrage_day = (df[discharge_time_mask]['load_existing'] > 0).sum()/2

    # Count values less than zero
    count_curtailed_day = (df[discharge_time_mask]['pv_curtailed'] > 0).sum()/2
    print(f"PV < load @9.00 {count_arbitrage_day} days")
    print(f"PV > load @9.00 {count_curtailed_day} days")


    pv_curtailed_kWh_df = df['pv_curtailed'].resample('D').sum()
    pv_curtailed_kWh_df = pv_curtailed_kWh_df[pv_curtailed_kWh_df > 1]
    max_pv_curtailed_kWh = pv_curtailed_kWh_df.max()

    # Calculate the 40th percentile -> mean almost use full capacity
    percentile_40_pv_curtailed_kWh = pv_curtailed_kWh_df.quantile(0.40)
    percentile_60_pv_curtailed_kWh = pv_curtailed_kWh_df.quantile(0.60)
    percentile_80_pv_curtailed_kWh = pv_curtailed_kWh_df.quantile(0.80)
    print(f"max battery from PV curtailed: {max_pv_curtailed_kWh:,.2f} kWh")
    print(f"  -- suggest Battery Capacity: {percentile_60_pv_curtailed_kWh:,.0f} kWh\n\r")

    

    
    # Create a plot
    plt.figure(figsize=(10, 6))

    # Plotting the data
    plt.plot(pv_curtailed_kWh_df, marker='o', label='PV Curtailed')

    # Adding a horizontal line for the 40th percentile
    plt.axhline(y=percentile_80_pv_curtailed_kWh, color='lime', linestyle='--', label=f'80th Percentile ({percentile_80_pv_curtailed_kWh})')
    plt.axhline(y=percentile_60_pv_curtailed_kWh, color='g', linestyle='-', label=f'60th Percentile ({percentile_60_pv_curtailed_kWh})')
    plt.axhline(y=percentile_40_pv_curtailed_kWh, color='lightgreen', linestyle='--', label=f'40th Percentile ({percentile_40_pv_curtailed_kWh})')
 
    # Adding title and labels
    plt.title(f'PV Curtailed with 60th Percentile Line ({pv_install_capacity:,.0f} kWp)')
    plt.xlabel('Index')
    plt.ylabel('Values')

    # Adding a legend
    plt.legend()

    plt.savefig(f"result_{year_of_first_row}/pv_curtailed_60_percentile_{pv_install_capacity:,.0f}kWp.png", format="png")
    # Show the plot
    plt.show()
    


    # =============================================== #
    # ============= SELECT BATTERY SIZE ============= #
    # =============================================== #
    # batt_cap_selected = percentile_60_pv_curtailed_kWh
    batt_capacity_selected = 900 # kWh
    batt_cap_selected = batt_capacity_selected * 0.8 # batt performance 80%

    # arbitrage only (discharge) 9.00-11.00 in case load > PV
    batt_arbitrage_kWh_df = np.where(load_existing_kWh_df > batt_cap_selected, batt_cap_selected, load_existing_kWh_df)
    sum_batt_arbitrage_kWh = batt_arbitrage_kWh_df.sum() * 0.9
    price_batt_arbitrage = sum_batt_arbitrage_kWh * 2
    # price_batt_arbitrage = batt_cap_selected*365*0.75*2 # 2 (4.1-2.1) THB/unit, arbitrage chance 75%

    batt_store_curtailed_kWh_df = np.where(pv_curtailed_kWh_df > batt_cap_selected, batt_cap_selected, pv_curtailed_kWh_df)
    sum_batt_store_curtailed_kWh = batt_store_curtailed_kWh_df.sum() * 0.9
    price_batt_store_curtailed = (sum_batt_store_curtailed_kWh * 4.1)
    
    total_price_batt = price_batt_store_curtailed + price_batt_arbitrage
    print(f"  -- installed Battery       : {batt_capacity_selected:,.0f} kWh")
    print(f"  -- suggest Battery Saving  : {total_price_batt:,.0f} THB  ({(total_price_batt*10/batt_capacity_selected):,.0f} THB/kWh/10years)")
    print(f"                             : {sum_batt_store_curtailed_kWh:,.0f} kWh (Curtail {(sum_pv_curtailed/sum_pv_produce*100):.2f} % -> {((sum_pv_curtailed-sum_batt_store_curtailed_kWh)/sum_pv_produce*100):.2f} %)")
    print(f"")

    batt_capacity_selected = 200 # kWh
    batt_cap_selected = batt_capacity_selected * 0.8 # batt performance 80%

    # arbitrage only (discharge) 9.00-11.00 in case load > PV
    batt_arbitrage_kWh_df = np.where(load_existing_kWh_df > batt_cap_selected, batt_cap_selected, load_existing_kWh_df)
    sum_batt_arbitrage_kWh = batt_arbitrage_kWh_df.sum() * 0.9
    price_batt_arbitrage = sum_batt_arbitrage_kWh * 2
    # price_batt_arbitrage = batt_cap_selected*365*0.75*2 # 2 (4.1-2.1) THB/unit, arbitrage chance 75%

    batt_store_curtailed_kWh_df = np.where(pv_curtailed_kWh_df > batt_cap_selected, batt_cap_selected, pv_curtailed_kWh_df)
    sum_batt_store_curtailed_kWh = batt_store_curtailed_kWh_df.sum() * 0.9
    price_batt_store_curtailed = (sum_batt_store_curtailed_kWh * 4.1)
    
    total_price_batt = price_batt_store_curtailed + price_batt_arbitrage
    print(f"  -- installed Battery       : {batt_capacity_selected:,.0f} kWh")
    print(f"  -- suggest Battery Saving  : {total_price_batt:,.0f} THB  ({(total_price_batt*10/batt_capacity_selected):,.0f} THB/kWh/10years)")
    print(f"                             : {sum_batt_store_curtailed_kWh:,.0f} kWh (Curtail {(sum_pv_curtailed/sum_pv_produce*100):.2f} % -> {((sum_pv_curtailed-sum_batt_store_curtailed_kWh)/sum_pv_produce*100):.2f} %)")
    print(f"")


    batt_capacity_selected = 150 # kWh
    batt_cap_selected = batt_capacity_selected * 0.8 # batt performance 80%

    # arbitrage only (discharge) 9.00-11.00 in case load > PV
    batt_arbitrage_kWh_df = np.where(load_existing_kWh_df > batt_cap_selected, batt_cap_selected, load_existing_kWh_df)
    sum_batt_arbitrage_kWh = batt_arbitrage_kWh_df.sum() * 0.9
    price_batt_arbitrage = sum_batt_arbitrage_kWh * 2
    # price_batt_arbitrage = batt_cap_selected*365*0.75*2 # 2 (4.1-2.1) THB/unit, arbitrage chance 75%

    batt_store_curtailed_kWh_df = np.where(pv_curtailed_kWh_df > batt_cap_selected, batt_cap_selected, pv_curtailed_kWh_df)
    sum_batt_store_curtailed_kWh = batt_store_curtailed_kWh_df.sum() * 0.9
    price_batt_store_curtailed = (sum_batt_store_curtailed_kWh * 4.1)
    
    total_price_batt = price_batt_store_curtailed + price_batt_arbitrage
    print(f"  -- installed Battery       : {batt_capacity_selected:,.0f} kWh")
    print(f"  -- suggest Battery Saving  : {total_price_batt:,.0f} THB  ({(total_price_batt*10/batt_capacity_selected):,.0f} THB/kWh/10years)")
    print(f"                             : {sum_batt_store_curtailed_kWh:,.0f} kWh (Curtail {(sum_pv_curtailed/sum_pv_produce*100):.2f} % -> {((sum_pv_curtailed-sum_batt_store_curtailed_kWh)/sum_pv_produce*100):.2f} %)")
    print(f"")
    

    batt_capacity_selected = 100 # kWh
    batt_cap_selected = batt_capacity_selected * 0.8 # batt performance 80%

    # arbitrage only (discharge) 9.00-11.00 in case load > PV
    batt_arbitrage_kWh_df = np.where(load_existing_kWh_df > batt_cap_selected, batt_cap_selected, load_existing_kWh_df)
    sum_batt_arbitrage_kWh = batt_arbitrage_kWh_df.sum() * 0.9
    price_batt_arbitrage = sum_batt_arbitrage_kWh * 2
    # price_batt_arbitrage = batt_cap_selected*365*0.75*2 # 2 (4.1-2.1) THB/unit, arbitrage chance 75%

    batt_store_curtailed_kWh_df = np.where(pv_curtailed_kWh_df > batt_cap_selected, batt_cap_selected, pv_curtailed_kWh_df)
    sum_batt_store_curtailed_kWh = batt_store_curtailed_kWh_df.sum() * 0.9
    price_batt_store_curtailed = (sum_batt_store_curtailed_kWh * 4.1)
    
    total_price_batt = price_batt_store_curtailed + price_batt_arbitrage
    print(f"  -- installed Battery       : {batt_capacity_selected:,.0f} kWh")
    print(f"  -- suggest Battery Saving  : {total_price_batt:,.0f} THB  ({(total_price_batt*10/batt_capacity_selected):,.0f} THB/kWh/10years)")
    print(f"                             : {sum_batt_store_curtailed_kWh:,.0f} kWh (Curtail {(sum_pv_curtailed/sum_pv_produce*100):.2f} % -> {((sum_pv_curtailed-sum_batt_store_curtailed_kWh)/sum_pv_produce*100):.2f} %)")
    print(f"")
    
    


    df.to_csv('load_pv_profile.csv')

for install_cap in PV_Install_Capacity:
    print(f"\n\rPV Install_cap: {install_cap:.2f} kW")
    cal_pv_serve_load(df_pv,df_load,install_cap)


 