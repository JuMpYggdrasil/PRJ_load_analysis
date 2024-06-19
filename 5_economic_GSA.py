import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.colors as mcolors
import pandas as pd
import json
import math
import statistics
import os

# Inputs
#### param_for_economic.json
# installed_capacity_set = 10  # kW
# capacity_factor_set = 14.5   # %
## annual energy = installed_capacity x 24 x 365 x capacity_factor/100

## tariff_rate_average = (tariff_rate_on_peak*242+tariff_rate_off_peak*123)/365 (add more 0.6 for FT)
tariff_rate = 4.19109 # THB/units     <==    ##### edit #####
# >=69kV -> 4.19109, 22,33kV -> 4.25139,<22kV -> 4.36 (adready add FT 0.6THB, exclude VAT)


# Inputs config
project_time_years = 25 # years
cost_per_kw = 24800     # THB/kW  <==    ##### from contractor ##### Roof 28400-30000, carport 42000
margin = 10 # % approx 10%-12%
sale_price_per_kw = cost_per_kw*(1+margin/100) # THB/kW
solar_degradation_first_year = 2    # %  https://poweramr.in/blog/performance-ratio
solar_degradation_after_first_year = 0.55  # %
inverter_replacement_cost = 4200 # THB/kW
o_and_m_percentage = 2   # %
o_and_m_escalation = 0   # Escalation rate
o_and_m_start_at_year = 1 #

tariff_discount = 15 # % include FT, exclude VAT
tariff_escalation = 0 # %
contract_year = 15

## EGAT_operation_cost
# from excel 2 person 3 day approx  59,000 +(27*km) -- minimum
# from excel 2 person 5 day approx  81,000 +(27*km) 
# from excel 2 person 7 day approx 104,000 +(27*km)
# from excel 3 person 5 day approx  97,000 +(27*km)
# from excel 3 person 7 day approx 127,000 +(27*km) -- default
# from excel 7 person 7 day approx 223,000 +(27*km)
general_work_cost = 127000
distance_from_EGAT_km = 160      # <<----- input distance from EGAT HQ (km)
EGAT_operation_cost = general_work_cost+(27*distance_from_EGAT_km)
print("EGAT_operation_cost= ",EGAT_operation_cost)


df_load = pd.read_csv('analyse_electric_load_data.csv', parse_dates=['timestamp'])
df_load.set_index('timestamp', inplace=True)


first_row_timestamp = df_load.index[0]
year_of_first_row = first_row_timestamp.year


# Path to the JSON file
file_path = 'anual_electricity_base_price.json'

# Load JSON data from the file
with open(file_path, 'r') as file:
    json_data = json.load(file)

# Extract total_price
anual_electricity_base_price = json_data["total_price"]
# print(f"anual_electricity_base_price: {anual_electricity_base_price:,.2f}")

# Create the folder if it doesn't exist
folder_name = f"result_{year_of_first_row}/GSA"
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

tariff discount: {tariff_discount} % (include FT, exclude VAT)
contract year = {contract_year} year

EGAT Operation Cost:
General Work Cost: {general_work_cost} THB
Distance from EGAT HQ: {distance_from_EGAT_km} km
EGAT Operation Cost: {EGAT_operation_cost} THB
"""
# Save assumptions and values to text file
file_path = os.path.join(folder_name, 'assumptions.txt')
with open(file_path, 'w') as file:
    file.write(assumptions_values)
    
def roundup(number, digits):
    factor = 10 ** digits
    return math.ceil(number * factor) / factor

def Average(lst): 
    return sum(lst) / len(lst) 

def calculate_economic(installed_capacity,capacity_factor,energy_of_pv_serve_load,tariff_rate,ENplot=False):
    # Initialize lists to store data
    years = []
    solar_degradation_list = []
    annual_energy_year_list = []
    o_and_m_cost_list = []
    solar_saving_list = []
    service_price_to_EGAT_list = []
    discount_saving_list = []
    inverter_replacement = 0

    # Calculate Initial Investment
    initial_investment = 0
    EGAT_init_investment = installed_capacity * sale_price_per_kw + EGAT_operation_cost
    
    ## Calculate Annual Electricity Generation
    # annual_generation = installed_capacity * 24 * 365 * capacity_factor/100 # focus only PV production
    annual_generation = energy_of_pv_serve_load # focus PV meet load
    # print("energy per year",annual_generation/1000,"MWh")

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
            o_and_m_cost = EGAT_init_investment * o_and_m_percentage/100 * ((1 + o_and_m_escalation/100) ** (year - o_and_m_start_at_year))
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
            solar_saving = 0
        elif year == 1:
            solar_saving = annual_energy_year * tariff_rate
        else:
            solar_saving = annual_energy_year * tariff_rate * ((1 + tariff_escalation/100) ** (year-1))
            
        # Append Annual Revenue to list
        solar_saving_list.append(solar_saving)
        
        if year == 0:
            # Calculate Annual Revenue for the year
            service_price_to_EGAT = 0
        elif year == 1:
            service_price_to_EGAT = annual_energy_year * tariff_rate * (1-tariff_discount/100)
        else:
            if year <= contract_year:
                service_price_to_EGAT = annual_energy_year * tariff_rate * (1-tariff_discount/100) * ((1 + tariff_escalation/100) ** (year-1))
            else:
                service_price_to_EGAT = 0
        
        service_price_to_EGAT_list.append(service_price_to_EGAT)
        
        # Append year
        years.append(year)
        
    service_price_average = roundup(service_price_to_EGAT_list[1],-3) # 1st-yr concept
    # service_price_average = roundup(Average(service_price_to_EGAT_list[1:contract_year+1]),-3) # average concept
    service_price_average_list = [0] + [service_price_average]*contract_year+[0]*(project_time_years-contract_year)
    # print("service_price_average_list",service_price_average_list)
    
    discount_saving_list = [x - y for x, y in zip(solar_saving_list, service_price_average_list)]
    # print("discount_saving_list",discount_saving_list)
    solar_saving_average_1 = Average(solar_saving_list[1:contract_year+1])
    solar_saving_average_2 = Average(solar_saving_list[contract_year+1:project_time_years+1])


    # print("Installed Capacity: {:,.2f} kWp".format(installed_capacity))
    total_energy = sum(annual_energy_year_list)
    # print("Total Energy: {:,.2f} MW".format(total_energy/1000))
    # print("Capital Investment: {:,.2f} THB".format(initial_investment))
    # print("Tariff Discount: {} %".format(tariff_discount))
    # print("During Contract: 1st-{}th Year".format(contract_year))
    average_saving_1 = sum(discount_saving_list[1:contract_year+1])/len(discount_saving_list[1:contract_year+1])
    # print("Average Savings: {:,.2f} THB/Year".format(average_saving_1))
    O_M_average_cost_1 = (sum(o_and_m_cost_list[o_and_m_start_at_year:contract_year+1])-inverter_replacement)/len(o_and_m_cost_list[o_and_m_start_at_year:contract_year+1])
    # print("O&M Cost: {:,.2f} THB/Year".format(O_M_average_cost_1))
    inverter_replacement_at_first_year = inverter_replacement/((1+o_and_m_escalation/100)**10)
    # print("Inverter Replacement: {:,.2f} THB".format(inverter_replacement_at_first_year))
    average_net_saving_1 = average_saving_1
    # print("Average Net Savings: {:,.2f} THB/Year".format(average_net_saving_1))
    total_net_saving_1 = average_net_saving_1*contract_year
    # print("{}-years Net Savings: {:,.2f} THB".format(contract_year,total_net_saving_1))
    
    # print("After Contract: {}st-{}th Year".format(contract_year+1,project_time_years))
    average_saving_2 = sum(discount_saving_list[contract_year+1:project_time_years+1])/len(discount_saving_list[contract_year+1:project_time_years+1])
    # print("Average Savings: {:,.2f} THB/Year".format(average_saving_2))
    O_M_average_cost_2 = (sum(o_and_m_cost_list[contract_year+1:project_time_years+1]))/len(o_and_m_cost_list[contract_year+1:project_time_years+1])
    # print("O&M Cost: {:,.2f} THB/Year".format(O_M_average_cost_2))
    
    average_net_saving_2 = average_saving_2-O_M_average_cost_2
    # print("Average Net Savings: {:,.2f} THB/Year".format(average_net_saving_2))
    total_net_saving_2 = average_net_saving_2*(project_time_years-contract_year)
    # print("{}-years Net Savings: {:,.2f} THB".format(project_time_years-contract_year,total_net_saving_2))
    
    
    total_life_year_saving = total_net_saving_1 + total_net_saving_2
    # print("Total {}-Year Savings: {:,.2f} THB".format(project_time_years,total_life_year_saving))
    
    if ENplot:
        # Data for the table
        data = [
            ["Installed Capacity", "{:,.2f}".format(installed_capacity), "kWp"],
            ["Total Energy", "{:,.2f}".format(total_energy/1000), "MW"],
            ["Capital Investment", "{:,.2f}".format(initial_investment), "THB"],
            ["Tariff Discount", "{}".format(tariff_discount), "%"],
            ["During Contract", "1st-{}th".format(contract_year), "Year"],
            ["Average Savings", "{:,.2f}".format(average_saving_1), "THB/Year"],
            ["O&M Cost", "{:,.2f}".format(O_M_average_cost_1), "THB/Year"],
            ["Inverter Replacement", "{:,.2f}".format(inverter_replacement_at_first_year), "THB"],
            ["Average Net Savings", "{:,.2f}".format(average_net_saving_1), "THB/Year"],
            ["{}-years Net Savings".format(contract_year), "{:,.2f}".format(total_net_saving_1), "THB"],
            ["After Contract", "{}st-{}th".format(contract_year+1, project_time_years), "Year"],
            ["Average Savings", "{:,.2f}".format(average_saving_2), "THB/Year"],
            ["O&M Cost", "{:,.2f}".format(O_M_average_cost_2), "THB/Year"],
            ["Average Net Savings", "{:,.2f}".format(average_net_saving_2), "THB/Year"],
            ["{}-years Net Savings".format(project_time_years-contract_year), "{:,.2f}".format(total_net_saving_2),"THB"],
            ["Total {}-Year Savings".format(project_time_years),"{:,.2f}".format(total_life_year_saving),"THB"]
        ]

        # Create a DataFrame
        df = pd.DataFrame(data, columns=["Description", "Value", "Duration"])

        # Plotting the table
        fig, ax = plt.subplots(figsize=(10, len(data)*0.5))  # Adjust the height as per the number of rows

        # Hide axes
        ax.xaxis.set_visible(False)
        ax.yaxis.set_visible(False)
        ax.set_frame_on(False)

        # Create the table
        table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')

        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.auto_set_column_width(col=list(range(len(df.columns))))

        # Set header color to lightgrey
        header_color = 'lightblue'
        for key, cell in table.get_celld().items():
            if key[0] == 0:
                cell.set_facecolor(header_color)
                cell.set_text_props(weight='bold')

                
        # Blue for rows 1, 10, 12, lightgreen for rows 0, 2, 3, ..., 8, 13, 14, 15 and lightblue for the rest
        row_colors = ['lightgrey' if i in [4, 10] else 'lightgreen' if i in [0, 3, 15] else 'azure' for i in range(len(data))]
        for i, key in enumerate(table.get_celld().keys()):
            cell = table.get_celld()[key]
            if key[0] > 0:  # Skip header
                cell.set_facecolor(row_colors[key[0]-1])

        # Save the table as an image
        plt.savefig(f"result_{year_of_first_row}/GSA/table_image_{installed_capacity:,.0f}kWp_{tariff_discount}_{contract_year}yr.png", bbox_inches='tight', dpi=400)
        df.to_csv(f"result_{year_of_first_row}/GSA/table_image_{installed_capacity:,.0f}kWp_{tariff_discount}_{contract_year}yr.csv", index=False)

        # Show the plot
        plt.show()
        
    
        
    species = (
        "Before",
        "After (1st-{}th)".format(contract_year),
        "After ({}th-{})".format(contract_year+1, project_time_years),
    )
    weight_counts = {
        "Electricity Cost": np.array([anual_electricity_base_price, anual_electricity_base_price-solar_saving_average_1, anual_electricity_base_price-solar_saving_average_2]),
        "Service Price to EGAT": np.array([0, service_price_average, 0]),
        "Average Savings": np.array([0,  solar_saving_average_1-service_price_average, solar_saving_average_2]),
    }
    width = 0.5

    fig, ax = plt.subplots()
    bottom = np.zeros(3)

    bar_colors = ['darkmagenta', 'orange', 'green'] # define the colors

    for i, (boolean, weight_count) in enumerate(weight_counts.items()):
        p = ax.bar(species, weight_count, width, color=bar_colors[i], label=boolean, bottom=bottom)
        bottom += weight_count
    
    # Adding text labels to the top of each stack with formatted text
    for index, species_name in enumerate(species):
        total_height = 0
        for boolean, weight_count in weight_counts.items():
            label_text = '{:,.0f}'.format(weight_count[index])  # Format text
            if boolean=="Electricity Cost":
                plt.text(index, total_height + weight_count[index]*9.5/10, label_text, ha='center', va='top')
            else:
                plt.text(index, total_height + weight_count[index]/2, label_text, ha='center', va='center')
            total_height += weight_count[index]


    

    ax.yaxis.set_units('THB/Year')
    ax.set_ylabel('Electricity Cost (THB/Year)')
    ax.set_title("Comparison Of Electricity Cost")
    ax.legend(loc="lower left")
    ax.set_ylim(0, roundup(anual_electricity_base_price*1.1,-5))  # set y-axis limit
        
    if ENplot:
        # Save the plot as PNG
        plt.savefig(f"result_{year_of_first_row}/GSA/electricity_cost_comparison_{installed_capacity:,.0f}kWp_{tariff_discount}_{contract_year}yr.png")

    # Create a DataFrame from weight_counts and save it as CSV
    df = pd.DataFrame(weight_counts)
    df.to_csv(f"result_{year_of_first_row}/GSA/electricity_cost_comparison_{installed_capacity:,.0f}kWp_{tariff_discount}_{contract_year}yr.csv", index_label="Species")
    
    
    
    if ENplot:
        plt.show()
    else:
        plt.close(fig)
        plt.cla()


    EGAT_investment = EGAT_init_investment + sum(o_and_m_cost_list[o_and_m_start_at_year:contract_year+1])
    EGAT_total_income = service_price_average * contract_year
    pbp_frac = EGAT_investment/service_price_average
    percent_profit = (EGAT_total_income - EGAT_investment)/EGAT_investment*100
    
    return pbp_frac,percent_profit
    
    


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

        pbp, percent_profit = calculate_economic(installed_capacity, capacity_factor, energy_of_pv_serve_load, tariff_rate, ENplot=True)
        print(f"tariff_discount: {tariff_discount:,.2f} %, EGAT pbp: {pbp:,.2f} yr")
        print(f"EGAT percent profit: {percent_profit:,.2f} %")



# Access specific fields and perform calculations
for data in data_list:
    installed_capacity = data.get("installed_capacity")  # Get installed_capacity field
    capacity_factor = data.get("capacity_factor")  # Get capacity_factor field

    print("\n\rInstalled Capacity:", installed_capacity)
        
    # energy_of_pv_produce = data.get("energy_of_pv_produce")
    energy_of_pv_serve_load = data.get("energy_of_pv_serve_load")   
    tariff_discount_varies = list(range(10, 50, 5))
    for tariff_discount_vary in tariff_discount_varies:
        tariff_discount = tariff_discount_vary # %
        pbp, percent_profit = calculate_economic(installed_capacity, capacity_factor, energy_of_pv_serve_load, tariff_rate, ENplot=False)
        print(f"tariff_discount: {tariff_discount:,.2f} % ({(tariff_rate*(1-tariff_discount/100)):,.2f}), EGAT pbp: {pbp:,.2f} yr, EGAT profit: {percent_profit:,.2f} %")
