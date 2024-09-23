import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import json
# from deap import base, creator, tools, algorithms

# Online section for weather database TMY
from PVGIS_TMY import PVGIS_TMY
latitude, longitude = 13.811739286586437, 100.50565968620579


PV_Install_Capacity = [700] # kW1350
## -- Offline
PVSyst_GlobInc = 2045.3 # (PVSyst: GlobInc kWh/m2/year) 
PVSyst_Energy_per_year_per_kWp = [1580*0.8/0.75] # (PVSyst kWh/year/kWp) or https://globalsolaratlas.info/ tracking +20%
# ## -- Online (roughly)
# PVSyst_GlobInc, PVSyst_Energy_per_year_per_kWp = PVGIS_TMY(latitude, longitude) # -- Online



## >69 kV
unit_price_on_peak = 4.1025
unit_price_off_peak = 2.5849
# unit_price_holiday = unit_price_off_peak
unit_price_demand_charge = 74.14
unit_price_service_charge = 312.24
# *** ignore FT 5-10% and vat 7%

# ## 22-33 kV
# unit_price_on_peak = 4.1839
# unit_price_off_peak = 2.6037
# # unit_price_holiday = unit_price_off_peak
# unit_price_demand_charge = 132.93
# unit_price_service_charge = 312.24
# # *** ignore FT 5-10% and vat 7%


# PV_Energy_Adjust_Factor_1_6 = PVSyst_Energy_per_year_per_kWp/737.41945*737.41945
# PV_Energy_Adjust_Factor_7_12 = PVSyst_Energy_per_year_per_kWp/665.39245*665.39245
PV_Energy_Adjust_Factor = [x/1402.8119 for x in PVSyst_Energy_per_year_per_kWp] # (PVSyst kWh/year/kWp)/1402.8119 change this factory to match PvSyst Energy per year
print(PV_Energy_Adjust_Factor)

kg_CO2_per_kWh = 0.4857

df_load = pd.read_csv('analyse_electric_load_data.csv', parse_dates=['timestamp'])
df_load.set_index('timestamp', inplace=True)


first_row_timestamp = df_load.index[0]
year_of_first_row = first_row_timestamp.year
# Create the folder if it doesn't exist
folder_name = f"result_{year_of_first_row}"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"Folder '{folder_name}' created.")




# === tracking or fixed === #
df_pv = pd.read_csv(f'solar_1kW_{year_of_first_row}.csv', parse_dates=['timestamp'],date_format='%d/%m/%Y %H:%M')
# df_pv = pd.read_csv(f'solar_1kW_{year_of_first_row}_tracking.csv', parse_dates=['timestamp'],date_format='%d/%m/%Y %H:%M')

df_pv.set_index('timestamp', inplace=True)


# Calculate hourly averages for each hour of the day
solar_pattern = []
for hour in range(24):
    solar_pattern.append(df_pv['pv'][df_pv.index.hour == hour].mean())
    
print(solar_pattern)
df_solar_pattern = pd.DataFrame(solar_pattern)
df_solar_pattern.to_csv("solar_pattern.csv")

df_pv_day = df_pv.resample('D').max()
df_pv_data = pd.DataFrame(index=df_pv_day.index)

df_pv_data['pv_max'] = df_pv_day['pv']
df_pv_data['pv_5']=df_pv[df_pv.index.hour == 5].resample('D').mean()['pv']
df_pv_data['pv_6']=df_pv[df_pv.index.hour == 6].resample('D').mean()['pv']
df_pv_data['pv_7']=df_pv[df_pv.index.hour == 7].resample('D').mean()['pv']
df_pv_data.to_csv('pv_data_for_train_model.csv')



# Create a list of hours (0 to 23) for the x-axis
hours = list(range(24))

# selected_month_mask = (df.index.month == 2) # for view specific month
selected_month_mask = True # for all month


# check must be "datetime64[ns]"
print(df_load.index.dtype)
print(df_pv.index.dtype)

# Specify the file path
file_path = "param_for_economic.json"

# Check if the file exists
if os.path.exists(file_path):
    # Delete the file
    os.remove(file_path)

def cal_pv_serve_load(df_pv,df_load,pv_install_capacity,ENplot=False):
    def safe_index(lst, item):
        try:
            return lst.index(item)
        except ValueError:
            return -1

    # first_six_month_mask = (df_pv.index.month >= 1) & (df_pv.index.month <= 6)
    # last_six_month_mask = (df_pv.index.month >= 7) & (df_pv.index.month <= 12)
    # first_six_month_data = df_pv["pv"][first_six_month_mask] * pv_install_capacity * PV_Energy_Adjust_Factor_1_6
    # last_six_month_data = df_pv["pv"][last_six_month_mask] * pv_install_capacity * PV_Energy_Adjust_Factor_7_12
    
    # df_load["pv_produce"] = pd.concat([first_six_month_data, last_six_month_data])
    
    l_index = safe_index(PV_Install_Capacity,pv_install_capacity)
    if l_index != -1:
        PV_Energy_Adjust_Factor_gain= PV_Energy_Adjust_Factor[l_index]
    else:
        PV_Energy_Adjust_Factor_gain = sum(PVSyst_Energy_per_year_per_kWp)/len(PVSyst_Energy_per_year_per_kWp)
    
    df_load["pv_produce"] = df_pv["pv"] * pv_install_capacity * PV_Energy_Adjust_Factor_gain
    df_load["pv_serve_load"] = np.where(df_load['pv_produce'] > df_load['load'], df_load['load'], df_load['pv_produce'])
    df_load['pv_curtailed'] = np.maximum(0, df_load['pv_produce'] - df_load['pv_serve_load'])
    df_load['load_existing'] = df_load['load'] - df_load['pv_serve_load']

    target_month = [1,2,3,4,5,6,7,8,9,10,11,12]
    target_month_show = [3,8]
    month_name = ['','January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December', 'None']

    if ENplot:
        for month in target_month:
            plt.figure(figsize=(14, 6))
            # Plotting 'load' and 'pv_serve_load' columns against the timestamp index
            plt.plot(df_load.index, df_load['load'], label='Load')
            plt.plot(df_load.index, df_load['pv_produce'], label='PV Produce')

            # Adding labels and title
            plt.xlabel('Timestamp')
            plt.ylabel('Load')
            plt.title(f"Load and PV({pv_install_capacity:,.0f} kWp) {month_name[month]}")

            # Adding legend
            plt.legend()

            
            ## Set x-axis limits to the current target month
            # Get the first date in the DataFrame's index
            start_date = df_load.index[0]
            start_of_target_month = start_date.replace(month=month, day=1)
            start_of_next_month = (start_of_target_month + pd.DateOffset(months=1)).replace(day=1)
            # Set the x-axis limits to span from the start of the target month to the start of the next month
            plt.xlim((start_of_target_month, start_of_next_month))

            plt.savefig(f"result_{year_of_first_row}/Load_and_PV({pv_install_capacity:,.0f}_kWp)_{month}_{month_name[month]}.png", format="png")
            if month in target_month_show:
                # Display the plot
                plt.show()
            else:
                plt.close()  # Close the plot to free up memory
        
    

    sum_pv_produce = df_load['pv_produce'].sum()
    capacity_factor = (sum_pv_produce/pv_install_capacity/8760*100)
    # print(f"pv_install_capacity: {pv_install_capacity:,.2f} kW")
    print(f"Energy of pv_produce: {sum_pv_produce:,.2f} kWh/year (Verify with PVSyst)")
    # Initialize list to store monthly average PV energy
    pv_energy_monthly = []
    # Calculate the average PV energy for each month
    for mth in range(1, 13):  # Use 13 to include December
        monthly_mean = df_load['pv_produce'][df_load.index.month == mth].mean()
        pv_energy_monthly.append(monthly_mean)
    # Print the monthly averages in a formatted way
    formatted_pv_energy = ','.join([f"{value:,.0f}" for value in pv_energy_monthly])
    print(f"  Monthly average PV energy production (kWh/month): {formatted_pv_energy}")
    
    print(f"Energy of pv_produce: {(sum_pv_produce/pv_install_capacity):,.2f} kWh/kWp/year")
    print(f"Energy of pv_produce: {(sum_pv_produce/pv_install_capacity/365):,.2f} kWh/kWp/day")
    print(f"Capacity Factor: {capacity_factor:,.2f} %")
    

    sum_pv_curtailed = df_load['pv_curtailed'].sum()
    sum_pv_curtailed_percent = (sum_pv_curtailed/sum_pv_produce*100)
    print(f"Energy of pv_curtailed: {sum_pv_curtailed:,.2f} kWh  ({sum_pv_curtailed_percent:.2f} %)")
    sum_pv_serve_load = df_load['pv_serve_load'].sum()
    print(f"Energy of pv_serve_load: {sum_pv_serve_load:,.2f} kWh")
    print(f"PR ratio (PV): {(sum_pv_produce/PVSyst_GlobInc/pv_install_capacity):,.2f}")
    print(f"PR ratio (Load): {(sum_pv_serve_load/PVSyst_GlobInc/pv_install_capacity):,.2f}")

    param_econ = {
        "installed_capacity": pv_install_capacity,
        "capacity_factor": capacity_factor,
        "energy_of_pv_produce": sum_pv_produce,
        "energy_of_pv_serve_load": sum_pv_serve_load
    }
    
    if ENplot:
        # Append the data to the JSON file
        with open(file_path, "a") as json_file:
            json.dump(param_econ, json_file)
            json_file.write("\n")
    

    
    
    df = df_load
    
    # Calculate hourly averages for each hour of the day for all 7 days of the week
    average_load_patterns = []
    average_pv_patterns = []
    day_data = df
    for hour in range(24):
        average_load_patterns.append(day_data['load'][day_data.index.hour == hour].mean())
        average_pv_patterns.append(day_data['pv_produce'][day_data.index.hour == hour].mean())
        
    # Create a list of hours (0 to 23) for the x-axis
    hours = list(range(24))

    if ENplot:
        # Plot the hourly data for weekdays and weekends
        plt.figure(figsize=(12, 6))
        plt.plot(hours, average_load_patterns, label='average_load_patterns', marker='o')
        plt.plot(hours, average_pv_patterns, label='average_pv_patterns', marker='o')
        # Highlight the area where average_pv_patterns > average_load_patterns
        # Highlight the area where average_pv_patterns > average_load_patterns
        plt.fill_between(hours, average_load_patterns, average_pv_patterns, 
                    where=[pv > load for pv, load in zip(average_pv_patterns, average_load_patterns)], 
                    color='darkviolet', alpha=0.5)

        # Add a hatched pattern using an additional fill_between
        plt.fill_between(hours, average_load_patterns, average_pv_patterns, 
                        where=[pv > load for pv, load in zip(average_pv_patterns, average_load_patterns)], 
                        color='none', hatch='///', edgecolor='purple')

        plt.title(f'Hourly Electrical Load  & PV Profile({pv_install_capacity:,.0f}_kWp)')
        plt.xlabel('Hour of the Day')
        plt.ylabel('Average Load & PV (kW)')
        plt.legend()
        plt.grid(True)
        plt.xticks(hours)
        plt.savefig(f"result_{year_of_first_row}/load_pv({pv_install_capacity:,.0f}_kWp).png", format="png")
        plt.show()
        
        

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
    
    print(f"  CO2 Emission Reduction: {(sum_pv_serve_load*kg_CO2_per_kWh):,.0f} kg-CO2")
    
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

    
    # Define the time ranges and masks
    charge_time_start = 6 # charge
    charge_time_finish = 8
    charge_time_mask = (df.index.hour >= charge_time_start) & (df.index.hour <= charge_time_finish)

    extra_time_start = 9 # discharge
    extra_time_finish = 10
    extra_time_mask = (df.index.hour >= extra_time_start) & (df.index.hour <= extra_time_finish)

    post_extra_time_start = 11 # charge
    post_extra_time_finish = 13
    post_extra_time_mask = (df.index.hour >= post_extra_time_start) & (df.index.hour <= post_extra_time_finish)

    # Calculate load_existing_charge_kWh_df during charge time
    load_existing_charge_kWh_df = df[charge_time_mask]['load_existing'].resample('D').sum()

    # Calculate load_existing_extra_discharge_kWh_df during extra time
    load_existing_extra_discharge_kWh_df = df[extra_time_mask]['load_existing'].resample('D').sum()

    # Calculate pv_curtailed_charge_kWh_df during post-extra time
    pv_curtailed_charge_kWh_df = df[post_extra_time_mask]['pv_curtailed'].resample('D').sum()

    # Create the initial intermediate DataFrame
    initial_intermediate_df = pd.DataFrame({
        'load_existing_charge_kWh': load_existing_charge_kWh_df,
        'load_existing_extra_discharge_kWh': load_existing_extra_discharge_kWh_df,
        'pv_curtailed_charge_kWh': pv_curtailed_charge_kWh_df
    })

    # Create masks for days where load_existing_extra_discharge_kWh_df > 0 and pv_curtailed_charge_kWh_df > 0
    extra_discharge_mask = load_existing_extra_discharge_kWh_df > 0
    post_extra_time_mask = pv_curtailed_charge_kWh_df > 0

    extra_condition_mask = extra_discharge_mask & post_extra_time_mask

    # # Apply masks to filter the DataFrame
    # filtered_intermediate_df = initial_intermediate_df[extra_condition_mask]

    
    pv_curtailed_kWh_df = df['pv_curtailed'].resample('D').sum()
    pv_curtailed_kWh_df = pv_curtailed_kWh_df[pv_curtailed_kWh_df > 1]
    # Filter pv_curtailed_kWh_df for dates where pv_curtailed sum is greater than 1
    pv_curtailed_filtered_dates = pv_curtailed_kWh_df[pv_curtailed_kWh_df > 1].index
    max_pv_curtailed_kWh = pv_curtailed_kWh_df.max()

    

    # Invert the filter to get dates where pv_curtailed sum is not greater than 1
    load_existing_charge_kWh_df_1 = load_existing_charge_kWh_df[~load_existing_charge_kWh_df.index.isin(pv_curtailed_filtered_dates)]
    load_existing_charge_kWh_df_2 = load_existing_charge_kWh_df[extra_condition_mask]

    # Combine load_existing_charge_kWh_df_1 and load_existing_charge_kWh_df_2
    load_existing_charge_kWh_df = pd.concat([load_existing_charge_kWh_df_1, load_existing_charge_kWh_df_2]).sort_index()

    count_curtailed_day = pv_curtailed_kWh_df.index.nunique()
    count_arbitrage_day = load_existing_charge_kWh_df_1.index.nunique()
    count_double_cycle_day = load_existing_charge_kWh_df_2.index.nunique()

    # Print the count
    print(f"Number of dates can do Double Cycles: {count_double_cycle_day} days")
    print(f"Number of count_curtailed_day       : {count_curtailed_day} days")
    print(f"Number of count_arbitrage_day       : {count_arbitrage_day} days")
    print(f"                                365 ? {(count_curtailed_day+count_arbitrage_day)}")



    count_both_case_day = count_double_cycle_day + count_curtailed_day + count_arbitrage_day
    print(f"Cycle/year {count_both_case_day} cycles")
    print(f"5000 Cycle = {(5000/count_both_case_day):,.1f} year")
    print(f"6000 Cycle = {(6000/count_both_case_day):,.1f} year")
    print(f"8000 Cycle = {(8000/count_both_case_day):,.1f} year")

    # Calculate the 40th percentile -> mean almost use full capacity
    percentile_40_pv_curtailed_kWh = pv_curtailed_kWh_df.quantile(0.40)
    percentile_60_pv_curtailed_kWh = pv_curtailed_kWh_df.quantile(0.60)
    percentile_80_pv_curtailed_kWh = pv_curtailed_kWh_df.quantile(0.80)
    print(f"max battery from PV curtailed: {max_pv_curtailed_kWh:,.2f} kWh")
    print(f"  -- suggest Battery Capacity: {percentile_60_pv_curtailed_kWh:,.0f} kWh\n\r")

    

    if ENplot:
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
        battery_capacities = [400000,450000,500000,]  # example capacities in kWh
        for batt_capacity_selected in battery_capacities:
            batt_cap_selected = batt_capacity_selected * 0.8 * 0.95 *0.95 # batt depth 80%, performance 95%

            # arbitrage only (discharge) in case load > PV
            batt_arbitrage_kWh_df = np.where(load_existing_charge_kWh_df > batt_cap_selected, batt_cap_selected, load_existing_charge_kWh_df)
            sum_batt_arbitrage_kWh = batt_arbitrage_kWh_df.sum() * 0.7
            price_batt_arbitrage = sum_batt_arbitrage_kWh * (unit_price_on_peak-unit_price_off_peak)
            # price_batt_arbitrage = batt_cap_selected*365*0.70*2 # 2 (4.1-2.1) THB/unit, arbitrage chance 70%

            batt_store_curtailed_kWh_df = np.where(pv_curtailed_kWh_df > batt_cap_selected, batt_cap_selected, pv_curtailed_kWh_df)
            sum_batt_store_curtailed_kWh = batt_store_curtailed_kWh_df.sum() * 0.9
            price_batt_store_curtailed = (sum_batt_store_curtailed_kWh * unit_price_on_peak)
            Average_load_factor = 0.42
            demand_charge_saving = (count_double_cycle_day+count_arbitrage_day)/365 * batt_cap_selected / 3 * unit_price_demand_charge * (1-Average_load_factor) # interval discharge time= 3 hours, can reduce 10 mth/yr
            
            total_price_saving_batt = price_batt_store_curtailed + price_batt_arbitrage + demand_charge_saving
            print(f"  -- installed Battery       : {batt_capacity_selected:,.0f} kWh")
            print(f"  -- suggest Battery Saving  : {total_price_saving_batt:,.0f} THB  ({(total_price_saving_batt*10/batt_capacity_selected):,.0f} THB/kWh/10years)")
            print(f"         - curtailed saving  : {price_batt_store_curtailed:,.0f} THB")
            print(f"         - arbitrage saving  : {price_batt_arbitrage:,.0f} THB")
            print(f"         - demand charge sav : {demand_charge_saving:,.0f} THB")
            print(f"         - curtailed energy  : {sum_batt_store_curtailed_kWh:,.0f} kWh (Curtail {(sum_pv_curtailed/sum_pv_produce*100):.2f} % -> {((sum_pv_curtailed-sum_batt_store_curtailed_kWh)/sum_pv_produce*100):.2f} %)")
            print(f"")
    
    
    
    


    df.to_csv('load_pv_profile.csv')

    return sum_pv_curtailed_percent,total_price



for install_cap in PV_Install_Capacity:
    import sys
    original_stdout = sys.stdout
    # Open a text file in write mode
    with open(f'result_{year_of_first_row}/load_pv_batt_result_{install_cap}.txt', 'w') as f:
        # Redirect the standard output to the text file
        sys.stdout = f
        
        print(f"\n\rPV Install_cap: {install_cap:,.2f} kW")
        cal_pv_serve_load(df_pv,df_load,install_cap,ENplot=True)
    
    sys.stdout = original_stdout       

    # After exiting the 'with' block, the standard output will be reverted back to the console

def find_optimal_pv_capacity(df_pv, df_load, target_percent=10, tolerance=0.1, max_iterations=100):
    """
    Finds the optimal PV installation capacity using a binary search method to meet a target percentage of curtailed PV energy.

    Parameters:
    df_pv (DataFrame): DataFrame containing the PV generation data.
    df_load (DataFrame): DataFrame containing the load data.
    target_percent (float): The target percentage of PV energy curtailment. Default is 10%.
    tolerance (float): The acceptable tolerance around the target percentage. Default is 0.1%.
    max_iterations (int): The maximum number of iterations for the binary search. Default is 100.

    Returns:
    float: The optimal PV installation capacity that best meets the target percentage of curtailed PV energy.
    str: A summary string showing the percentage of PV curtailed for the best-found capacity.

    The function performs a binary search between a predefined minimum (0) and maximum (100,000) PV installation capacity.
    In each iteration, it calculates the percentage of PV energy curtailed using the `cal_pv_serve_load` function. 
    If the calculated curtailment is within the specified tolerance of the target percentage, it returns the current capacity.
    Otherwise, it adjusts the search range by comparing the calculated curtailment to the target.
    If the maximum number of iterations is reached, the function returns the best-found capacity and its corresponding curtailment.
    """
    low = 0  # Minimum possible pv_install_capacity
    high = 100000  # Set a reasonable high boundary based on your data context
    iterations = 0
    sum_pv_curtailed_percent_txt = ""

    while iterations < max_iterations:
        mid = (low + high) / 2
        sum_pv_curtailed_percent, _ = cal_pv_serve_load(df_pv, df_load, mid)

        if abs(sum_pv_curtailed_percent - target_percent) <= tolerance:
            return mid,sum_pv_curtailed_percent_txt

        if sum_pv_curtailed_percent < target_percent:
            low = mid
        else:
            high = mid

        iterations += 1
        sum_pv_curtailed_percent_txt=f" PV curtailed {sum_pv_curtailed_percent:,.2f}"

    return mid,sum_pv_curtailed_percent_txt  # Return the best found value if max_iterations is reached

optimal_capacity,curtailed_percent_txt = find_optimal_pv_capacity(df_pv, df_load, target_percent=20)
print(f"The optimal PV installation capacity is {optimal_capacity:,.2f} kW, {curtailed_percent_txt}%")