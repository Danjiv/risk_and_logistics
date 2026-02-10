import pandas as pd
import xpress as xp
import os
import zipfile
import preprocessing 

data_dir = "CaseStudyDataPY"

# -----------------------------------------------------------------------------
# Read supplier data
# The first column is used as the supplier index
# -----------------------------------------------------------------------------
Suppliers_df = pd.read_csv(f"{data_dir}/Suppliers.csv", index_col=0)
# Maximum supplier index (assumed to be integer-indexed)
nbSuppliers = Suppliers_df.index.max()



# -----------------------------------------------------------------------------
# Read postcode district data (used to define customers)
# Group postcode demand data by westminster parliamentary constituency
PostcodeDistricts = pd.read_csv(f"{data_dir}/PostcodeDistricts.csv")

PostcodeDistricts_constituency, con_index_dict  = preprocessing.get_constituency(PostcodeDistricts)

# Read demand data with time periods
# Creates a dictionary keyed by (Customer, Product, Period)

DemandPeriods_df = pd.read_csv(f"{data_dir}/DemandPeriods.csv")

DemandPeriodsGrouped, DemandPeriodsProportion = preprocessing.get_clustered_demand(DemandPeriods_df, PostcodeDistricts_constituency)


# -----------------------------------------------------------------------------
# Read candidate facility data
# -----------------------------------------------------------------------------
Candidates_df = pd.read_csv(f"{data_dir}/Candidates.csv", index_col=0)
# Maximum candidate index
nbCandidates = Candidates_df.index.max()

# -----------------------------------------------------------------------------
# Read distance matrices
# Supplier → District distances
# District → District distances
# -----------------------------------------------------------------------------

DistanceSupplierDistrict_df = pd.read_csv(
    f"{data_dir}/Distance Supplier-District.csv", index_col=0
)
DistanceSupplierDistrict_df.columns = DistanceSupplierDistrict_df.columns.astype(int)

#Adjust distance based on grouping by parliamentary constituency,
#weighted by proportion of total demand in each constituency by demand in each
# individual postcode district, for each period

DistanceDistrictDistrict_df = pd.read_csv(
    f"{data_dir}/Distance District-District.csv", index_col=0
)
DistanceDistrictDistrict_df.columns = DistanceDistrictDistrict_df.columns.astype(int)

DistanceDistrictPeriod_df_dict = preprocessing.get_clustered_distance_weighted_by_demand(DistanceDistrictDistrict_df,
                                                                                         DemandPeriodsProportion,
                                                                                         con_index_dict)

# Number of time periods
nbPeriods = DemandPeriods_df["Period"].max()


# -----------------------------------------------------------------------------
# Read demand data with time periods and scenarios
# Creates a dictionary keyed by (Customer, Product, Period, Scenario)
# -----------------------------------------------------------------------------
DemandPeriodsScenarios_df = pd.read_csv(f"{data_dir}/DemandPeriodScenarios.csv")
DemandPeriodsScenarios = (
    DemandPeriodsScenarios_df
        .set_index(["Customer", "Product", "Period", "Scenario"])["Demand"]
        .to_dict()
)

# Number of scenarios
nbScenarios = DemandPeriodsScenarios_df["Scenario"].max()

#print(list(DistanceDistrictPeriod_df_dict.keys())[0:3])
#print(DistanceDistrictPeriod_df_dict[("Aberdeen South", 1)].head())
#print(DistanceDistrictPeriod_df_dict[("Aberdeen South", 2)].head())

#DistanceDistrictPeriod_df_list[0]["Aberdeen South"].to_csv("check_distances.csv")

#PostcodeDistricts[PostcodeDistricts["Constituency"]=="Aberdeen South"].to_csv("working.csv")
#PostcodeDistricts.to_csv("working.csv")
#print(constituency_index_dict["Aberdeen North"])
#in each constituency, just take the postcode district with min distance to all other postcode districts!!

# =============================================================================
# Index sets
# =============================================================================
Customers  = list[con_index_dict.keys()]
Candidates = Candidates_df.index
Suppliers  = Suppliers_df.index


# =============================================================================
# Vehicle-related data
# Vehicles are indexed as:
#   1 = 18t trucks
#   2 = 7.5t lorries
#   3 = 3.5t vans
# =============================================================================

# Vehicle capacity in tonnes
VehicleCapacity = {
    1: 9.0,
    2: 2.4,
    3: 1.5
}

# Cost in pounds per mile travelled (fixed cost)
VehicleCostPerMileOverall = {
    1: 1.666,
    2: 1.727,
    3: 1.285
}

# Cost in pounds per mile and tonne transported (variable cost)
VehicleCostPerMileAndTonneOverall = {
    1: 0.185,
    2: 0.720,
    3: 0.857
}

# CO₂ emissions in kg per mile and tonne transported
VehicleCO2PerMileAndTonne = {
    1: 0.11,
    2: 0.31,
    3: 0.30
}


# -----------------------------------------------------------------------------
# Time periods and scenarios
# -----------------------------------------------------------------------------
Times = range(1, nbPeriods + 1)
Scenarios = range(1, nbScenarios + 1)


# =============================================================================
# Transport cost calculations
# =============================================================================

# Cost from suppliers to candidate facilities
# Round-trip distance (factor 2)
# Cost depends on supplier vehicle type
# Division by 1000 converts from kg to tonnes
CostSupplierCandidate = {
    (k, j): 2
    * DistanceSupplierDistrict_df.loc[k, j]
    * VehicleCostPerMileAndTonneOverall[
        Suppliers_df.loc[k, "Vehicle type"]
    ]
    / 1000
    for j in Candidates
    for k in Suppliers
}

# Cost from candidate facilities to customers
# All transports use 3.5t vans (vehicle type 3)
CostCandidateCustomers = {
    (j, i, t): 2
    * DistanceDistrictPeriod_df_dict[(i, t)][j]
    * VehicleCostPerMileAndTonneOverall[3]
    / 1000
    for j in Candidates
    for i in Customers
    for t in Times
}

# =============================================================================
# Build optimization model
# =============================================================================
prob = xp.problem("Assignment 1")

# To turn on and off the solver log
xp.setOutputEnabled(True)


xp.setOutputEnabled(True)
prob.solve()

# =============================================================================
# Post-processing and data visualisation
# =============================================================================

sol_status = prob.attributes.solstatus

if sol_status == xp.SolStatus.OPTIMAL:
    print("Optimal solution found")
    best_obj = prob.attributes.objval
    best_bound = prob.attributes.bestbound
    mip_gap = abs(best_obj - best_bound) / (1e-10 +abs(best_obj))
    print(f"MIP Gap: {mip_gap*100:.2f}%")
    
elif sol_status == xp.SolStatus.FEASIBLE:
    print("Feasible solution (not proven optimal)")
    best_obj = prob.attributes.objval
    best_bound = prob.attributes.bestbound
    mip_gap = abs(best_obj - best_bound) / (1e-10 +abs(best_obj))
    print(f"MIP Gap: {mip_gap*100:.2f}%")
elif sol_status == xp.SolStatus.INFEASIBLE:
    print("Model is infeasible")
elif sol_status == xp.SolStatus.UNBOUNDED:
    print("Model is unbounded")
else:
    print("No solution available")


print("ok!")