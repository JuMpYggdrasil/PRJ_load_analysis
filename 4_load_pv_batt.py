import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import json
# from deap import base, creator, tools, algorithms

# Online section for weather database TMY
from PVGIS_TMY import PVGIS_TMY
latitude, longitude = 13.811739286586437, 100.50565968620579

CONFIG_PATH = "config.json"

def load_config(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as config_file:
        config = json.load(config_file)

    required_sections = ["solar_pv", "battery", "tariff", "optimizer", "analysis"]
    missing_sections = [section for section in required_sections if section not in config]
    if missing_sections:
        raise KeyError(f"Missing config sections: {', '.join(missing_sections)}")

    solar_cfg = config["solar_pv"]
    if len(solar_cfg["install_capacities_kwp"]) != len(solar_cfg["pvsyst_yield_kwh_per_kwp_year"]):
        raise ValueError(
            "solar_pv.install_capacities_kwp and solar_pv.pvsyst_yield_kwh_per_kwp_year "
            "must have the same length"
        )

    return config

config = load_config()
solar_cfg = config["solar_pv"]
battery_cfg = config["battery"]
tariff_cfg = config["tariff"]
optimizer_cfg = config["optimizer"]
analysis_cfg = config["analysis"]

PV_Install_Capacity = solar_cfg["install_capacities_kwp"] # kW
PVSyst_GlobInc = solar_cfg["pvsyst_globinc_kwh_per_m2_year"] # (PVSyst: GlobInc kWh/m2/year)
PVSyst_Energy_per_year_per_kWp = solar_cfg["pvsyst_yield_kwh_per_kwp_year"] # (PVSyst kWh/year/kWp)
SOLAR_REFERENCE_YIELD = solar_cfg["reference_yield_kwh_per_kwp_year"]
PV_Energy_Adjust_Factor = [x/SOLAR_REFERENCE_YIELD for x in PVSyst_Energy_per_year_per_kWp]
print(PV_Energy_Adjust_Factor)

unit_price_on_peak = tariff_cfg["on_peak_thb_per_kwh"]
unit_price_off_peak = tariff_cfg["off_peak_thb_per_kwh"]
unit_price_demand_charge = tariff_cfg["demand_charge_thb_per_kw"]
unit_price_service_charge = tariff_cfg["service_charge_thb_per_month"]

kg_CO2_per_kWh = solar_cfg["co2_kg_per_kwh"]
hours_per_year = analysis_cfg["hours_per_year"]

battery_capacity_kwh = battery_cfg["capacity_kwh"]
battery_power_limit_kw = battery_cfg["power_limit_kw"]
battery_depth_of_discharge = battery_cfg["depth_of_discharge"]
battery_charge_efficiency = battery_cfg["charge_efficiency"]
battery_discharge_efficiency = battery_cfg["discharge_efficiency"]

df_load = pd.read_csv('temporary/analyse_electric_load_data.csv', parse_dates=['timestamp'])
df_load.set_index('timestamp', inplace=True)


first_row_timestamp = df_load.index[0]
year_of_first_row = first_row_timestamp.year
# Create the folder if it doesn't exist
folder_name = f"result_{year_of_first_row}"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"Folder '{folder_name}' created.")




# === tracking or fixed === #
solar_profile_template = (
    solar_cfg["tracking_profile_template"]
    if solar_cfg["use_tracking"]
    else solar_cfg["profile_template"]
)
solar_profile_path = solar_profile_template.format(year=year_of_first_row)
df_pv = pd.read_csv(
    solar_profile_path,
    parse_dates=['timestamp'],
    date_format=solar_cfg["timestamp_format"],
)
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
df_pv_data.to_csv('temporary/pv_data_for_train_model.csv')



# Create a list of hours (0 to 23) for the x-axis
hours = list(range(24))

# selected_month_mask = (df.index.month == 2) # for view specific month
selected_month_mask = True # for all month


# check must be "datetime64[ns]"
print(df_load.index.dtype)
print(df_pv.index.dtype)

# Specify the file path
file_path = "temporary/param_for_economic.json"

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
        PV_Energy_Adjust_Factor_gain = sum(PV_Energy_Adjust_Factor)/len(PV_Energy_Adjust_Factor)
    
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
    capacity_factor = (sum_pv_produce/pv_install_capacity/hours_per_year*100)
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
    
    # Save hourly average load & PV profiles to CSV
    avg_df = pd.DataFrame({
        'hour': hours,
        'average_load_kW': pd.Series(average_load_patterns, dtype=float),
        'average_pv_kW': pd.Series(average_pv_patterns, dtype=float)
    })
    avg_df.to_csv(f"result_{year_of_first_row}/average_load_pv_profile_{pv_install_capacity:,.0f}kWp.csv", index=False)
    print(f"Saved hourly averages -> result_{year_of_first_row}/average_load_pv_profile_{pv_install_capacity:,.0f}kWp.csv")

    

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
    on_peak_mask = (
        (df.index.hour >= tariff_cfg["on_peak_start_hour"])
        & (df.index.hour < tariff_cfg["on_peak_end_hour_exclusive"])
    )
    off_peak_mask = ~on_peak_mask
    # PEA off-peak date @(MON-FRI) special
    specific_dates = pd.to_datetime(tariff_cfg["holidays"], format='%Y-%m-%d')
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
    charge_time_start = battery_cfg["charge_window_hours"]["start"] # charge
    charge_time_finish = battery_cfg["charge_window_hours"]["end"]
    charge_time_mask = (df.index.hour >= charge_time_start) & (df.index.hour <= charge_time_finish)

    extra_time_start = battery_cfg["discharge_window_hours"]["start"] # discharge
    extra_time_finish = battery_cfg["discharge_window_hours"]["end"]
    extra_time_mask = (df.index.hour >= extra_time_start) & (df.index.hour <= extra_time_finish)

    post_extra_time_start = battery_cfg["curtailment_charge_window_hours"]["start"] # charge
    post_extra_time_finish = battery_cfg["curtailment_charge_window_hours"]["end"]
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

    # Calculate percentile-based battery recommendations
    battery_sizing_percentile = battery_cfg["sizing_percentile"]
    battery_plot_percentiles = battery_cfg["plot_percentiles"]
    percentile_values = {
        percentile: pv_curtailed_kWh_df.quantile(percentile)
        for percentile in battery_plot_percentiles
    }
    suggested_battery_kwh = pv_curtailed_kWh_df.quantile(battery_sizing_percentile)
    print(f"max battery from PV curtailed: {max_pv_curtailed_kWh:,.2f} kWh")
    print(f"  -- suggest Battery Capacity: {suggested_battery_kwh:,.0f} kWh\n\r")

    

    if ENplot:
        # Create a plot
        plt.figure(figsize=(10, 6))

        # Plotting the data
        plt.plot(pv_curtailed_kWh_df, marker='o', label='PV Curtailed')

        plot_styles = ['lime', 'g', 'lightgreen']
        for percentile, color in zip(
            sorted(battery_plot_percentiles, reverse=True), plot_styles
        ):
            plt.axhline(
                y=percentile_values[percentile],
                color=color,
                linestyle='--' if percentile != battery_sizing_percentile else '-',
                label=f'{percentile*100:.0f}th Percentile ({percentile_values[percentile]})',
            )

        # Adding title and labels
        plt.title(
            f'PV Curtailed with {battery_sizing_percentile*100:.0f}th Percentile Line '
            f'({pv_install_capacity:,.0f} kWp)'
        )
        plt.xlabel('Index')
        plt.ylabel('Values')

        # Adding a legend
        plt.legend()

        plt.savefig(f"result_{year_of_first_row}/pv_curtailed_60_percentile_{pv_install_capacity:,.0f}kWp.png", format="png")
        # Show the plot
        plt.show()
    


        
    


    df.to_csv('temporary/load_pv_profile.csv')

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

def find_optimal_pv_capacity(
    df_pv,
    df_load,
    target_percent=10,
    tolerance=0.1,
    max_iterations=100,
    min_capacity_kw=0,
    max_capacity_kw=100000,
):
    """
    Finds the optimal PV installation capacity using a binary search method to meet a target percentage of curtailed PV energy.

    Parameters:
    df_pv (DataFrame): DataFrame containing the PV generation data.
    df_load (DataFrame): DataFrame containing the load data.
    target_percent (float): The target percentage of PV energy curtailment. Default is 10%.
    tolerance (float): The acceptable tolerance around the target percentage. Default is 0.1%.
    max_iterations (int): The maximum number of iterations for the binary search. Default is 100.
    min_capacity_kw (float): Minimum capacity for the search range. Default is 0.
    max_capacity_kw (float): Maximum capacity for the search range. Default is 100,000.

    Returns:
    float: The optimal PV installation capacity that best meets the target percentage of curtailed PV energy.
    str: A summary string showing the percentage of PV curtailed for the best-found capacity.

    The function performs a binary search between the configured minimum and maximum PV installation capacity.
    In each iteration, it calculates the percentage of PV energy curtailed using the `cal_pv_serve_load` function.
    If the calculated curtailment is within the specified tolerance of the target percentage, it returns the current capacity.
    Otherwise, it adjusts the search range by comparing the calculated curtailment to the target.
    If the maximum number of iterations is reached, the function returns the best-found capacity and its corresponding curtailment.
    """
    low = min_capacity_kw
    high = max_capacity_kw
    iterations = 0
    sum_pv_curtailed_percent_txt = ""
    mid = (low + high) / 2

    while iterations < max_iterations:
        mid = (low + high) / 2
        sum_pv_curtailed_percent, _ = cal_pv_serve_load(df_pv, df_load, mid)
        sum_pv_curtailed_percent_txt = f" PV curtailed {sum_pv_curtailed_percent:,.2f}"

        if abs(sum_pv_curtailed_percent - target_percent) <= tolerance:
            return mid, sum_pv_curtailed_percent_txt

        if sum_pv_curtailed_percent < target_percent:
            low = mid
        else:
            high = mid

        iterations += 1

    return mid, sum_pv_curtailed_percent_txt  # Return the best found value if max_iterations is reached


optimal_capacity, curtailed_percent_txt = find_optimal_pv_capacity(
    df_pv,
    df_load,
    target_percent=optimizer_cfg["target_curtailment_percent"],
    tolerance=optimizer_cfg["tolerance_percent"],
    max_iterations=optimizer_cfg["max_iterations"],
    min_capacity_kw=optimizer_cfg["min_capacity_kw"],
    max_capacity_kw=optimizer_cfg["max_capacity_kw"],
)
print(f"The optimal PV installation capacity is {optimal_capacity:,.2f} kW,{curtailed_percent_txt}%")