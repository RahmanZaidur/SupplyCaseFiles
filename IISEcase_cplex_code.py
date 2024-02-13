#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from docplex.mp.model import Model
import pandas as pd

path_to = "/Users/zaidur/Documents/IISE_case"

# Read data from CSV files
suppliers_df = pd.read_csv(path_to + '/TX_suppliers.csv')
roads_df = pd.read_csv(path_to +'/TX_roads.csv')
railroads_df = pd.read_csv(path_to +'/TX_railroads.csv')
plants_df = pd.read_csv(path_to +'/TX_plants.csv')
hubs_df = pd.read_csv(path_to +'/TX_hubs.csv')

# Create a model
mdl = Model('BioethanolSupplyChain')

# Parameters
conversion_yield = 232  # Conversion yield in liters per mg
D = 1476310602 #liters

# Decision variables
Q = mdl.continuous_var_matrix(suppliers_df['county'], hubs_df["hub"], lb=0, name='Q')
L = mdl.continuous_var_matrix(hubs_df["hub"], plants_df["plant"], lb=0, name='L')
H = mdl.binary_var_dict(hubs_df["hub"], name='H')
P = mdl.binary_var_dict(plants_df["plant"], name='P')
Y = mdl.binary_var_matrix(hubs_df["hub"], plants_df["plant"], name='Y')

# Variable for third-party supplier amount to meet demand
TP = mdl.continuous_var(name='TP', lb=0)

third_party_price = 369 #to be changed in each trial



# Objective function
total_cost = mdl.sum(
    roads_df[(roads_df['county']==i) & (roads_df['hub']==j)]['cost'].item() * Q[i, j]
    for i in suppliers_df['county'] for j in hubs_df["hub"]
)

total_cost += mdl.sum(
    railroads_df[ (railroads_df['hub']==j) & (railroads_df['plant']==k) ]['cost'].item() * L[j, k]
    + railroads_df[ (railroads_df['hub']==j) & (railroads_df['plant']==k) ]['loading'].item() * Y[j, k]
    for j in hubs_df['hub'] for k in plants_df["plant"]
)

total_cost += mdl.sum(
    hubs_df[hubs_df['hub']==j]['invest'].item() * H[j]
    for j in hubs_df["hub"]
)

total_cost += mdl.sum(
    plants_df[plants_df['plant']==k]['invest'].item() * P[k]
    for k in plants_df["plant"]
)

total_cost += third_party_price * TP   #total cost for third party biofuel

mdl.minimize(total_cost)

# Constraints
for i in suppliers_df['county']:  #costraint 2
    mdl.add_constraint(mdl.sum(Q[i, j] for j in hubs_df["hub"]) <= suppliers_df[suppliers_df["county"]==i]['supply'].item())
    
for j in hubs_df["hub"]:
    mdl.add_constraint(mdl.sum(Q[i, j] for i in suppliers_df["county"]) <= hubs_df[hubs_df['hub']==j]['capacity'].item() * H[j]) #constraint 3
    mdl.add_constraint(mdl.sum(Q[i, j] for i in suppliers_df["county"]) == mdl.sum(L[j, k] for k in plants_df["plant"]))  #constraint 5



for k in plants_df["plant"]: #constraint 4
    mdl.add_constraint(mdl.sum(L[j, k] for j in hubs_df["hub"]) <= (plants_df[plants_df['plant']==k]['capacity'].item())/conversion_yield)


for j in hubs_df["hub"]:
    for k in plants_df["plant"]: # constraint 6
        mdl.add_constraint(L[j, k] <= railroads_df[ (railroads_df['hub']==j) & (railroads_df['plant']==k) ]['capacity'].item() * Y[j,k])


#constraint 7
mdl.add_constraint(mdl.sum(L[j, k] for j in hubs_df["hub"] for k in plants_df["plant"]) + TP >= D/conversion_yield)
    
    
# constraint 9        
for k in plants_df["plant"]:
    mdl.add_constraint(mdl.sum(Y[j, k] for j in hubs_df["hub"]) <= P[k] * 400)

# constraint 12        
for j in hubs_df["hub"]:
    mdl.add_constraint(mdl.sum(Y[j, k] for k in plants_df["plant"]) <= H[j] * 400)

# Solve the model
# Set a time limit (in seconds)
mdl.parameters.timelimit.set(10800) # Sets a time limit of 1.5 hour

mdl.parameters.mip.tolerances.mipgap = 0.00050

solution = mdl.solve(log_output=True)

# Print the solution
if solution:
    print("Solution found:\n")
    mdl.print_solution()
else:
    print("No solution found")
    

# Assuming the model has been solved and mdl contains the solution
solution_df = pd.DataFrame([(var.name, var.solution_value) for var in mdl.iter_variables()], columns=['Variable', 'Value'])

# Add the objective value, best bound, and gap percentage
objective_value = mdl.objective_value
best_bound = mdl.solve_details.best_bound
gap_percentage = mdl.solve_details.mip_relative_gap * 100  # Convert to percentage

# Append this information to the DataFrame
additional_info = pd.DataFrame([
    ("Objective Value", objective_value),
    ("Best Bound", best_bound),
    ("Gap Percentage", gap_percentage)
], columns=['Variable', 'Value'])

# Combine the variable solutions and additional information
combined_df = pd.concat([solution_df, additional_info], ignore_index=True)

# Export to CSV
combined_df.to_csv("/Users/zaidur/Documents/IISE_case/solutions/solution_at_price_"+str(third_party_price/232)+".csv", index=False)


# In[ ]:




