import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.colors as mcolors
import pandas as pd
import json
import math
import os

# Inputs
#### param_for_economic.json
# installed_capacity_set = 10  # kW
# capacity_factor_set = 14.5   # %
## annual energy = installed_capacity x 24 x 365 x capacity_factor/100

## tariff_rate_average = (tariff_rate_on_peak*242+tariff_rate_off_peak*123)/365 (add more 0.6 for vat)
tariff_rate = 5.5/1.07 # THB/units     <==    ##### edit #####
# >=69kV -> 4.19109, 22,33kV -> 4.25139,<22kV -> 4.36 (adready add 0.6THB)


# Inputs config
project_time_years = 25 # years
cost_per_kw =  8555000/380      # THB/kW  <==    ##### from contractor ##### Roof 28400-30000, carport 42000, float 30500
margin = 10 # % approx 10%-12%
sale_price_per_kw = cost_per_kw*(1+margin/100) # THB/kW
solar_degradation_first_year = 2    # %  https://poweramr.in/blog/performance-ratio
solar_degradation_after_first_year = 0.55  # %
inverter_replacement_cost = 4200  # THB/kW
o_and_m_percentage = 2   # %
o_and_m_escalation = 0   # Escalation rate
o_and_m_start_at_year = 5 #

## EGAT_operation_cost
# from excel 2 person 3 day approx  59,000 +(27*km) -- minimum
# from excel 2 person 5 day approx  81,000 +(27*km) 
# from excel 2 person 7 day approx 104,000 +(27*km)
# from excel 3 person 5 day approx  97,000 +(27*km)
# from excel 3 person 7 day approx 127,000 +(27*km) -- default
# from excel 7 person 7 day approx 223,000 +(27*km)
general_work_cost = 468538#127000
distance_from_EGAT_km = 0      # <<----- input distance from EGAT HQ (km)
EGAT_operation_cost = general_work_cost+(27*distance_from_EGAT_km)
print("EGAT_operation_cost= ",EGAT_operation_cost)


df_load = pd.read_csv('analyse_electric_load_data.csv', parse_dates=['timestamp'])
df_load.set_index('timestamp', inplace=True)


first_row_timestamp = df_load.index[0]
year_of_first_row = first_row_timestamp.year
# Create the folder if it doesn't exist
folder_name = f"result_{year_of_first_row}/EPC"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"Folder '{folder_name}' created.")
    
# Assumptions and values to save
assumptions_values = f"""
Assumption:
Tariff Rate Average (with VAT): {tariff_rate:.5f} THB/units

Inputs Configuration:
Project Time (Years): {project_time_years} years
Cost per kW: {cost_per_kw} THB/kW
Margin: {margin} %
Sale Price per kW: {sale_price_per_kw:.2f} THB/kW
Solar Degradation First Year: {solar_degradation_first_year} %
Solar Degradation After First Year: {solar_degradation_after_first_year} %
Inverter Replacement Cost: {inverter_replacement_cost} THB/kW
O&M Percentage: {o_and_m_percentage} %
O&M Escalation Rate: {o_and_m_escalation} %
O&M Starts at Year: {o_and_m_start_at_year}

EGAT Operation Cost:
General Work Cost: {general_work_cost} THB
Distance from EGAT HQ: {distance_from_EGAT_km} km
EGAT Operation Cost: {EGAT_operation_cost} THB
"""
# Save assumptions and values to text file
file_path = os.path.join(folder_name, 'assumptions.txt')
with open(file_path, 'w') as file:
    file.write(assumptions_values)
    

def calculate_economic(installed_capacity,capacity_factor,energy_of_pv_serve_load,tariff_rate,ENplot=False):
    # Initialize lists to store data
    years = []
    solar_degradation_list = []
    annual_energy_year_list = []
    revenue_of_energy_list = []
    o_and_m_cost_list = []
    cash_flow_list = []
    inverter_replacement = 0

    # Calculate Initial Investment
    initial_investment = installed_capacity * sale_price_per_kw + EGAT_operation_cost
    
    ## Calculate Annual Electricity Generation
    # annual_generation = installed_capacity * 24 * 365 * capacity_factor/100 # focus only PV production
    annual_generation = energy_of_pv_serve_load # focus PV meet load
    print("energy per year",annual_generation/1000,"MWh")

    # Calculate payback period
    def calculate_payback_period(cash_flow_list):
        cumulative_cash_flow = 0
        payback_period = -1

        for cash_flow in cash_flow_list:
            cumulative_cash_flow += cash_flow
            payback_period += 1
            if cumulative_cash_flow > 0:
                break
            
        # Calculate the fraction of the last incomplete month
        last_cash_flow = cash_flow_list[payback_period-1]
        if last_cash_flow != 0:
            last_fraction = abs(abs(cumulative_cash_flow) - abs(last_cash_flow)) / abs(last_cash_flow)
        else:
            last_fraction = 0

        # Convert fraction to months
        payback_period_fraction = payback_period - 1 + last_fraction

        # Convert fraction to years and months
        years = int(payback_period_fraction)
        months = math.ceil((payback_period_fraction - years) * 12)
        # print(payback_period, years, months, payback_period_fraction)

        return payback_period, years, months, payback_period_fraction

    print("")
    # Calculate cash flows for each year
    for year in range(0, project_time_years + 1):
        # Calculate Solar Degradation for the year
        if year == 0:
            solar_degradation = 1
        elif year == 1:
            solar_degradation = solar_degradation_list[-1]-solar_degradation_first_year/100
            # solar_degradation = solar_degradation_list[-1]*(1-solar_degradation_first_year/100)
        else:
            solar_degradation = solar_degradation_list[-1]-solar_degradation_after_first_year/100
            # solar_degradation = solar_degradation_list[-1]*(1-solar_degradation_after_first_year/100)
        
        # Append Solar Degradation to list
        solar_degradation_list.append(solar_degradation)
        
        # Calculate Annual Generation for the year considering degradation
        annual_energy_year = annual_generation * solar_degradation
        
        # Append Annual Generation to list
        annual_energy_year_list.append(annual_energy_year)
        
        # Calculate O&M Cost for the year starting from year o_and_m_start_at_year
        if year >= o_and_m_start_at_year:
            o_and_m_cost = initial_investment * o_and_m_percentage/100 * ((1 + o_and_m_escalation/100) ** (year - 3))
            # Add Inverter Replacement Cost in the 10th year
            if year == 10:
                inverter_replacement = inverter_replacement_cost * installed_capacity
                o_and_m_cost += inverter_replacement
        else:
            o_and_m_cost = 0
        
        # Append O&M Cost to list
        o_and_m_cost_list.append(o_and_m_cost)
        
        if year == 0:
            # Calculate Annual Revenue for the year
            revenue_of_energy = 0
        else:
            revenue_of_energy = annual_energy_year * tariff_rate
        
        # Append Annual Revenue to list
        revenue_of_energy_list.append(revenue_of_energy)
        
        if year == 0:
            # Calculate Net Savings for the year
            cash_flow = -initial_investment
        else:
            cash_flow = revenue_of_energy - o_and_m_cost
        
        
        # Append Net Savings to list
        cash_flow_list.append(cash_flow)
        
        # Append year
        years.append(year)

    # Calculate IRR and Payback Period
    irr = npf.irr(cash_flow_list)
    irr_percent = round(irr*100, 2)
    print("IRR:", irr_percent, "%")
    cumulative_cash_flow = np.cumsum(cash_flow_list)
    payback_period, pbp_yr,pbp_mo,pbp_frac = calculate_payback_period(cash_flow_list)
    # print(payback_period, pbp_yr,pbp_mo)
    

    if ENplot:
        # Width of the bars
        bar_width = 0.3

        # Plotting
        plt.figure(figsize=(10, 6))
        plt.bar(np.array(years) - bar_width/2, revenue_of_energy_list, bar_width, color='green', alpha=0.9, label='Cash Flow')
        plt.bar(np.array(years) + bar_width/2, o_and_m_cost_list, bar_width, color='red', alpha=0.9, label='O&M Cost')
        plt.xlabel('Year')
        plt.ylabel('Amount (THB)')
        plt.title(f'Annual Revenue and O&M Cost ({installed_capacity:,.0f} kWp)')
        plt.xticks(years)
        formatter = ticker.StrMethodFormatter('{x:,.0f}')
        plt.gca().yaxis.set_major_formatter(formatter)
        plt.legend()
        plt.grid(True)
        plt.savefig(f"result_{year_of_first_row}/EPC/anual_revenue_{installed_capacity}kW.png", format="png")
        plt.show()

        # Plotting
        plt.figure(figsize=(10, 6))
        plt.bar(years, cumulative_cash_flow, color='blue', alpha=0.9)
        plt.xlabel('Year')
        plt.ylabel('Amount (THB)')
        plt.title(f'Cumulative Cash Flow ({installed_capacity:,.0f} kWp)')
        formatter = ticker.StrMethodFormatter('{x:,.0f}')
        plt.gca().yaxis.set_major_formatter(formatter)
        plt.legend()
        plt.grid(True)

        # Add payback period annotation
        plt.annotate("Payback Period {:,.0f} years {:,.0f} months".format(pbp_yr,pbp_mo), xy=(payback_period-1, 0), xytext=(payback_period + 3, -cumulative_cash_flow[payback_period+1]), arrowprops=dict(facecolor='red', arrowstyle='->'))
        
        plt.savefig(f"result_{year_of_first_row}/EPC/cumulative_cashflow_{installed_capacity}kW.png", format="png")
        plt.show()

    print("Installed Capacity: {:,.2f} kWp".format(installed_capacity))
    total_energy = sum(annual_energy_year_list)
    print("Total Energy ({}-yr): {:,.2f} MWh".format(project_time_years,total_energy/1000))
    print("Capital Investment: {:,.2f} THB".format(initial_investment))
    average_saving_pv = sum(revenue_of_energy_list[1:])/len(revenue_of_energy_list[1:])
    print("Average Savings: {:,.2f} THB/Year".format(average_saving_pv))
    O_M_average_cost = (sum(o_and_m_cost_list)-inverter_replacement)/len(o_and_m_cost_list[o_and_m_start_at_year:])
    print("O&M Cost: {:,.2f} THB/Year (*Warrantee 2 years)".format(O_M_average_cost))
    average_net_saving = average_saving_pv-O_M_average_cost
    print("Average Net Savings: {:,.2f} THB/Year".format(average_net_saving))
    inverter_replacement_at_first_year = inverter_replacement/((1+o_and_m_escalation/100)**10)
    print("Inverter Replacement: {:,.2f} THB".format(inverter_replacement_at_first_year))
    total_25_year_saving = sum(revenue_of_energy_list)-sum(o_and_m_cost_list)
    print("Total {:,.0f}-Year Savings: {:,.2f} THB".format(project_time_years,total_25_year_saving))

    print("IRR: {:.2f}%".format(irr_percent))
    ROI = (total_25_year_saving-initial_investment)/initial_investment*100
    print("ROI: {:.2f}%".format(ROI))
    print("Payback Period: {:.2f} years ({:.2f})".format(payback_period,pbp_frac))
    lifetime_year_saving = "Total "+str(project_time_years)+"-Year Savings"
    
    data = {
        "Metric": ["Installed Capacity", "Total Energy ({}-yr)".format(project_time_years), "Capital Investment", "Average Savings", "O&M Cost", "Average Net Savings", "Inverter Replacement", lifetime_year_saving, "ROI", "IRR", "Payback Period"],
        "Value": ["{:,.2f}".format(installed_capacity),"{:,.2f}".format(total_energy/1000), "{:,.2f}".format(initial_investment), "{:,.2f}".format(average_saving_pv), "{:,.2f}".format(O_M_average_cost), "{:,.2f}".format(average_net_saving), "{:,.2f}".format(inverter_replacement_at_first_year), "{:,.2f}".format(total_25_year_saving), "{:,.2f}".format(ROI), "{:,.2f}".format(irr_percent), "{:,.0f} years {:,.0f} months".format(pbp_yr,pbp_mo)],
        "Unit": ["kWp","MWh", "THB", "THB/Year", "THB/Year", "THB/Year", "THB", "THB", "%", "%", ""]
    }

    if ENplot:
        # Create a DataFrame from the data
        df = pd.DataFrame(data)

        # Set the metric column as the index
        df.set_index("Metric", inplace=True)

        # Plot the table
        plt.figure(figsize=(9, 6))

        # Define colors for each column
        colors = [mcolors.to_rgba('lightgreen', alpha=0.8)] * len(df.columns)
        row_colors = [mcolors.to_rgba('lightblue', alpha=0.8)] * len(df)

        table = plt.table(cellText=df.values,rowColours=row_colors, colLabels=df.columns, rowLabels=df.index, loc='center', cellLoc='right', colColours=colors, colWidths=[0.2, 0.2, 0.15])
        plt.axis('off')  # Hide the axis
        plt.title(f'Economic Indicators for Solar PV Project ({installed_capacity:,.0f} kWp)', fontsize=16, pad=20, loc='center')  # Set pad to adjust the distance between the title and the table
        table.scale(1, 1.8)  # Adjust the scale of the table
        plt.tight_layout(rect=[0, 0.1, 1, 0.9])  # Adjust the layout to make room for the title
        plt.savefig(f"result_{year_of_first_row}/EPC/economic_indicators_{installed_capacity}kW.png", format="png")
        df.to_csv(f"result_{year_of_first_row}/EPC/economic_indicators_{installed_capacity}kW.csv", index=True)
        plt.show()

        # ## for debuging
        # print(f"years: {years}")
        # print(f"solar_degradation_list: {solar_degradation_list}")
        # annual_energy_year_MW_list = [x / 1000 for x in annual_energy_year_list]
        # print(f"annual_energy_year_list: {annual_energy_year_MW_list}")
        # print(f"o_and_m_cost_list: {o_and_m_cost_list}")
        # print(f"revenue_of_energy_list: {revenue_of_energy_list}")
        # print(f"cash_flow_list: {cash_flow_list}")
        
        # Creating DataFrame
        df = pd.DataFrame({
            "Years": years,
            "Solar Degradation": solar_degradation_list,
            "Annual Energy (MW)": [x / 1000 for x in annual_energy_year_list],
            "O&M Cost": o_and_m_cost_list,
            "Revenue of Energy": revenue_of_energy_list,
            "Cash Flow": cash_flow_list
        })

        # Display DataFrame
        print(df)

        # Save DataFrame to CSV
        csv_file_path = f"result_{year_of_first_row}/EPC/energy_data.csv"
        df.to_csv(csv_file_path, index=False)
        
    return irr_percent, pbp_frac
    
    
    
    
    
    


# Specify the file path
file_path = "param_for_economic.json"

# List to store parsed JSON objects
data_list = []

# Read the JSON data from the file
with open(file_path, "r") as json_file:
    for line in json_file:
        data = json.loads(line)
        data_list.append(data)

# Access specific fields and perform calculations
for data in data_list:
    installed_capacity = data.get("installed_capacity")  # Get installed_capacity field
    capacity_factor = data.get("capacity_factor")  # Get capacity_factor field
        
    # energy_of_pv_produce = data.get("energy_of_pv_produce")
    energy_of_pv_serve_load = data.get("energy_of_pv_serve_load")
    
    # Do something with the fields
    if installed_capacity is not None and capacity_factor is not None:
        print("Installed Capacity:", installed_capacity)
        print("Capacity Factor:", capacity_factor)
        gen_sensitivity = [-10, -5, 0, 5, 10]
        # gen_sensitivity = [0]
        irr_results = []
        pbp_results = []

        for sensitivity in gen_sensitivity:
            if sensitivity == 0:
                irr, pbp = calculate_economic(installed_capacity, capacity_factor*(1 + sensitivity/100), energy_of_pv_serve_load*(1 + sensitivity/100), tariff_rate,ENplot=True)
            else:
                irr, pbp = calculate_economic(installed_capacity, capacity_factor*(1 + sensitivity/100), energy_of_pv_serve_load*(1 + sensitivity/100), tariff_rate)
            irr_results.append(irr)
            pbp_results.append(pbp)
            
        print('irr',irr_results)
        print('pbp',pbp_results)

        # Plotting IRR
        plt.plot(gen_sensitivity, irr_results, marker='o')
        plt.xlabel('Energy Production Sensitivity (%)')
        plt.ylabel('IRR (%)')
        plt.title('IRR vs Energy Production Sensitivity')
        plt.grid(True)
        plt.ylim(0, max(irr_results) + 1)
        plt.show()

        # Plotting PBP
        plt.plot(gen_sensitivity, pbp_results, marker='o')
        plt.xlabel('Energy Production Sensitivity (%)')
        plt.ylabel('PBP (year)')
        plt.title('PBP vs Energy Production Sensitivity')
        plt.grid(True)
        plt.ylim(0, max(pbp_results) + 1)
        plt.show()

        
        
        # price_sensitivity = [-15, -10, -5, 0, 5, 10, 15]
        # irr_results = []
        # pbp_results = []

        # for sensitivity in price_sensitivity:
        #     tariff_adjusted = tariff_rate * (1 + sensitivity / 100)
        #     irr, pbp = calculate_economic(installed_capacity, capacity_factor, energy_of_pv_serve_load, tariff_adjusted)
        #     irr_results.append(irr)
        #     pbp_results.append(pbp)

        # # Define colors based on sign of sensitivity
        # colors = ['lightgreen' if sensitivity < 0 else 'darkgreen' for sensitivity in price_sensitivity]

        # # Plotting IRR
        # plt.plot(price_sensitivity, irr_results, marker='o', color=colors)
        # plt.xlabel('Energy Price Sensitivity (%)')
        # plt.ylabel('IRR (%)')
        # plt.title('IRR vs Energy Price Sensitivity')
        # plt.grid(True)
        # plt.ylim(0, max(irr_results) + 1)
        # plt.show()

        # # Plotting PBP
        # plt.plot(price_sensitivity, pbp_results, marker='o', color=colors)
        # plt.xlabel('Energy Price Sensitivity (%)')
        # plt.ylabel('PBP (year)')
        # plt.title('PBP vs Energy Price Sensitivity')
        # plt.grid(True)
        # plt.ylim(0, max(pbp_results) + 1)
        # plt.show()
        
        price_sensitivity = [-15, -10, -5, 0, 5, 10, 15]
        irr_results = []
        pbp_results = []

        for sensitivity in price_sensitivity:
            tariff_adjusted = tariff_rate * (1 + sensitivity / 100)
            irr, pbp = calculate_economic(installed_capacity, capacity_factor, energy_of_pv_serve_load, tariff_adjusted)
            irr_results.append(irr)
            pbp_results.append(pbp)

        # Define colors based on sign of sensitivity
        colors = ['lightgreen' if sensitivity < 0 else 'darkgreen' for sensitivity in price_sensitivity]

        # Plotting IRR points
        for sensitivity, irr, color in zip(price_sensitivity, irr_results, colors):
            plt.plot(sensitivity, irr, marker='o', color=color)

        # Plotting lines connecting IRR points
        plt.plot(price_sensitivity, irr_results, color='green', linestyle='-', linewidth=1)

        plt.xlabel('Energy Price Sensitivity (%)')
        plt.ylabel('IRR (%)')
        plt.title('IRR vs Energy Price Sensitivity')
        plt.grid(True)
        plt.ylim(0, max(irr_results) + 1)
        plt.show()

        # Plotting PBP points
        for sensitivity, pbp, color in zip(price_sensitivity, pbp_results, colors):
            plt.plot(sensitivity, pbp, marker='o', color=color)

        # Plotting lines connecting PBP points
        plt.plot(price_sensitivity, pbp_results, color='green', linestyle='-', linewidth=1)

        plt.xlabel('Energy Price Sensitivity (%)')
        plt.ylabel('PBP (year)')
        plt.title('PBP vs Energy Price Sensitivity')
        plt.grid(True)
        plt.ylim(0, max(pbp_results) + 1)
        plt.show()
