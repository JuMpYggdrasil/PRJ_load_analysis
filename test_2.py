import numpy_financial as npf

# Example cash_flow_list
cash_flow_list = [-1815000.0, 278493.94243439997, 276930.96622686, 229992.99001932004, 228430.01381178002, 226867.03760424, 225304.0613967001, 223741.08518916008, 222178.10898162005, 220615.13277408015, -11947.843433459871, 217489.1803590001, 215926.20415146012, 214363.22794392018, 212800.2517363802, 211237.27552884017, 209674.29932130018, 208111.32311376024, 206548.34690622022, 204985.37069868023, 203422.39449114027, 201859.4182836003, 200296.44207606028, 198733.46586852032, 197170.48966098033, 195607.51345344033]

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

payback_period = calculate_payback_period(cash_flow_list)
print("Payback Period:", payback_period, "years")
