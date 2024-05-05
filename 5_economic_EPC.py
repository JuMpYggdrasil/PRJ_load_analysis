import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.colors as mcolors
import pandas as pd
import json

# Inputs
# installed_capacity = 55  # kW
# capacity_factor = 15.5217   # %
tariff_rate = 3.8 # THB/units

# Inputs config
project_time_years = 25 # years
solar_degradation_first_year = 2    # %
solar_degradation_after_first_year = 0.55  # %
cost_per_kw = 30000         # THB/kW
margin = 10               # %
sale_price_per_kw =  cost_per_kw*(1+margin/100) # THB/kW
inverter_replacement_cost = 4200  # THB/kW
o_and_m_percentage = 2.5   # %
o_and_m_escalation = 0.0   # Escalation rate
o_and_m_start_at_year = 3 #

def calculate_economic(installed_capacity,capacity_factor,energy_of_pv_serve_load):
    # Initialize lists to store data
    years = []
    solar_degradation_list = []
    annual_energy_year_list = []
    annual_revenue_year_list = []
    o_and_m_cost_list = []
    cash_flow_list = []
    inverter_replacement = 0

    # Calculate Initial Investment
    initial_investment = installed_capacity * sale_price_per_kw
    # Calculate Annual Electricity Generation
    # annual_generation = installed_capacity * 24 * 365 * capacity_factor/100
    annual_generation = energy_of_pv_serve_load

    # Calculate payback period
    def calculate_payback_period(cash_flow_list):
        cumulative_cash_flow = 0
        payback_period = 0

        for cash_flow in cash_flow_list:
            cumulative_cash_flow += cash_flow
            if cumulative_cash_flow >= 0:
                break
            payback_period += 1

        return payback_period

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
            o_and_m_cost = initial_investment * o_and_m_percentage/100 * (1 + o_and_m_escalation/100) ** (year - 2)
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
            annual_revenue_year = 0
        else:
            annual_revenue_year = annual_energy_year * tariff_rate
        
        # Append Annual Revenue to list
        annual_revenue_year_list.append(annual_revenue_year)
        
        if year == 0:
            # Calculate Net Savings for the year
            cash_flow = -initial_investment
        else:
            cash_flow = annual_revenue_year - o_and_m_cost
        
        
        # Append Net Savings to list
        cash_flow_list.append(cash_flow)
        
        # Append year
        years.append(year)

    # Calculate IRR and Payback Period
    irr = npf.irr(cash_flow_list)
    irr_percent = round(irr*100, 2)
    print("IRR:", irr_percent, "%")
    payback_period = calculate_payback_period(cash_flow_list)
    cumulative_cash_flow = np.cumsum(cash_flow_list)


    # Width of the bars
    bar_width = 0.3

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.bar(np.array(years) - bar_width/2, annual_revenue_year_list, bar_width, color='green', alpha=0.9, label='Cash Flow')
    plt.bar(np.array(years) + bar_width/2, o_and_m_cost_list, bar_width, color='red', alpha=0.9, label='O&M Cost')
    plt.xlabel('Year')
    plt.ylabel('Amount (THB)')
    plt.title(f'Annual Revenue and O&M Cost ({installed_capacity:,.0f} kWp)')
    plt.xticks(years)
    formatter = ticker.StrMethodFormatter('{x:,.0f}')
    plt.gca().yaxis.set_major_formatter(formatter)
    plt.legend()
    plt.grid(True)
    plt.show()

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.bar(years, cumulative_cash_flow, color='blue', alpha=0.9)
    plt.xlabel('Year')
    plt.ylabel('Amount (THB)')
    plt.title(f'Cash Flow ({installed_capacity:,.0f} kWp)')
    formatter = ticker.StrMethodFormatter('{x:,.0f}')
    plt.gca().yaxis.set_major_formatter(formatter)
    plt.legend()
    plt.grid(True)

    # Add payback period annotation
    plt.annotate(f"Payback Period {payback_period} yrs", xy=(payback_period, 0), xytext=(payback_period + 3, -cumulative_cash_flow[payback_period+1]), arrowprops=dict(facecolor='red', arrowstyle='->'))

    plt.show()

    print("Installed Capacity: {:,.2f} kWp".format(installed_capacity))
    print("Initial Investment: {:,.2f} THB".format(initial_investment))
    average_saving_pv = sum(annual_revenue_year_list[1:])/len(annual_revenue_year_list[1:])
    print("Average Savings: {:,.2f} THB/Year".format(average_saving_pv))
    O_M_cost = (sum(o_and_m_cost_list)-inverter_replacement)/len(o_and_m_cost_list[o_and_m_start_at_year:])
    print("O&M Cost: {:,.2f} THB/Year (*Warrantee 2 years)".format(O_M_cost))
    average_net_saving = average_saving_pv-O_M_cost
    print("Average Net Savings: {:,.2f} THB/Year".format(average_net_saving))
    print("Inverter Replacement: {:,.2f} THB".format(inverter_replacement))
    total_25_year_saving = sum(annual_revenue_year_list)-sum(o_and_m_cost_list)
    print("Total 25-Year Savings: {:,.2f} THB".format(total_25_year_saving))

    print("IRR: {:.2f}%".format(irr_percent))
    print("Payback Period: {:.2f} years".format(payback_period))
    
    data = {
        "Metric": ["Installed Capacity", "Initial Investment", "Average Savings", "O&M Cost", "Average Net Savings", "Inverter Replacement", "Total 25-Year Savings", "IRR", "Payback Period"],
        "Value": ["{:,.2f}".format(installed_capacity), "{:,.2f}".format(initial_investment), "{:,.2f}".format(average_saving_pv), "{:,.2f}".format(O_M_cost), "{:,.2f}".format(average_net_saving), "{:,.2f}".format(inverter_replacement), "{:,.2f}".format(total_25_year_saving), "{:,.2f}".format(irr_percent), "{:,.2f}".format(payback_period)],
        "Unit": ["kWp", "THB", "THB/Year", "THB/Year", "THB/Year", "THB", "THB", "%", "years"]
    }

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
    plt.title('Financial Metrics for Solar PV Project', fontsize=16, pad=20, loc='center')  # Set pad to adjust the distance between the title and the table
    table.scale(1, 1.8)  # Adjust the scale of the table
    plt.tight_layout(rect=[0, 0.1, 1, 0.9])  # Adjust the layout to make room for the title
    plt.show()

    # for debug
    # print(f"years: {years}")
    # print(f"solar_degradation_list: {solar_degradation_list}")
    # annual_energy_year_MW_list = [x / 1000 for x in annual_energy_year_list]
    # print(f"annual_energy_year_list: {annual_energy_year_MW_list}")
    # print(f"o_and_m_cost_list: {o_and_m_cost_list}")
    # print(f"annual_revenue_year_list: {annual_revenue_year_list}")
    # print(f"cash_flow_list: {cash_flow_list}")


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
        # Perform calculations or other operations here
        calculate_economic(installed_capacity,capacity_factor,energy_of_pv_serve_load)