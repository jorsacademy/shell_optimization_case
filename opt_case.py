import pandas as pd
from pulp import LpMinimize, LpProblem, LpVariable, lpSum, value

# Load datasets
demand_df = pd.read_csv('/mnt/data/demand.csv')
vehicles_df = pd.read_csv('/mnt/data/vehicles.csv')
vehicles_fuels_df = pd.read_csv('/mnt/data/vehicles_fuels.csv')
fuels_df = pd.read_csv('/mnt/data/fuels.csv')
carbon_emissions_df = pd.read_csv('/mnt/data/carbon_emissions.csv')
cost_profiles_df = pd.read_csv('/mnt/data/cost_profiles.csv')

# Initialize the problem
problem = LpProblem("Fleet_Transition_Optimization", LpMinimize)

# Define decision variables
purchase = {}
use = {}
sell = {}

years = list(range(2023, 2039))
for year in years:
 for _, vehicle in vehicles_df.iterrows():
 vehicle_id = vehicle['ID']
 purchase[vehicle_id, year] = LpVariable(f'purchase_{vehicle_id}_{year}', 0, cat='Integer')
 use[vehicle_id, year] = LpVariable(f'use_{vehicle_id}_{year}', 0, cat='Integer')
 sell[vehicle_id, year] = LpVariable(f'sell_{vehicle_id}_{year}', 0, cat='Integer')

# Define constraints
for year in years:
 for _, demand in demand_df.iterrows():
 size_bucket = demand['Size']
 distance_bucket = demand['Distance']
 yearly_demand = demand['Demand (km)']
 
 problem += lpSum([use[vehicle_id, year] for vehicle_id in vehicles_df['ID']
 if vehicles_df.loc[vehicles_df['ID'] == vehicle_id, 'Size'].values[0] == size_bucket and
 vehicles_df.loc[vehicles_df['ID'] == vehicle_id, 'Distance'].values[0] <= distance_bucket]) >= yearly_demand

# Emissions constraint
for year in years:
 total_emissions = lpSum([use[vehicle_id, year] * vehicles_fuels_df.loc[vehicles_fuels_df['ID'] == vehicle_id, 'Consumption (unit_fuel/km)'].values[0]
 for vehicle_id in vehicles_df['ID']])
 problem += total_emissions <= carbon_emissions_df.loc[carbon_emissions_df['Year'] == year, 'Carbon emission CO2/kg'].values[0]

# Objective function
total_cost = lpSum([purchase[vehicle_id, year] * vehicles_df.loc[vehicles_df['ID'] == vehicle_id, 'Cost ($)'].values[0] +
 use[vehicle_id, year] * vehicles_fuels_df.loc[vehicles_fuels_df['ID'] == vehicle_id, 'Consumption (unit_fuel/km)'].values[0]
 for year in years for vehicle_id in vehicles_df['ID']])
problem += total_cost

# Solve the problem
problem.solve()

# Create the output dataframe
output = []
for year in years:
 for vehicle_id in vehicles_df['ID']:
 if purchase[vehicle_id, year].varValue is not None and purchase[vehicle_id, year].varValue > 0:
 output.append([year, vehicle_id, int(purchase[vehicle_id, year].varValue), 'Buy', '', '', ''])
 if use[vehicle_id, year].varValue is not None and use[vehicle_id, year].varValue > 0:
 fuel = vehicles_fuels_df.loc[vehicles_fuels_df['ID'] == vehicle_id, 'Fuel'].values[0]
 distance_bucket = vehicles_df.loc[vehicles_df['ID'] == vehicle_id, 'Distance'].values[0]
 yearly_range = vehicles_df.loc[vehicles_df['ID'] == vehicle_id, 'Yearly range (km)'].values[0]
 output.append([year, vehicle_id, int(use[vehicle_id, year].varValue), 'Use', fuel, distance_bucket, yearly_range])
 if sell[vehicle_id, year].varValue is not None and sell[vehicle_id, year].varValue > 0:
 output.append([year, vehicle_id, int(sell[vehicle_id, year].varValue), 'Sell', '', '', ''])

output_df = pd.DataFrame(output, columns=['Year', 'ID', 'Num_Vehicles', 'Type', 'Fuel', 'Distance_bucket', 'Distance_per_vehicle(km)'])
output_df.to_csv('optimized_submission.csv', index=False)

print("Optimization complete and CSV file generated.")
