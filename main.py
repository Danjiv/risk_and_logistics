import pandas as pd
import numpy as np
import xpress as xp
import os
import zipfile
import preprocessing 
import postprocessing

data_dir = "CaseStudyDataPY"

# -----------------------------------------------------------------------------
# Read supplier data
# The first column is used as the supplier index
# -----------------------------------------------------------------------------
Suppliers_df = pd.read_csv(f"{data_dir}/Suppliers.csv", index_col=0)
Vehicle_df = pd.read_csv(f"{data_dir}/vehicleType.csv", index_col=0)
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
# Read candidate capacity and setup operating costs data

Capacity_df = pd.read_csv(f"{data_dir}/Capacity.csv")
Setup_df = pd.read_csv(f"{data_dir}/Setup.csv")
Operating_df = pd.read_csv(f"{data_dir}/Operating.csv")

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

# =============================================================================
# Index sets
# =============================================================================
Customers  = list(con_index_dict.keys())
Candidates = Candidates_df.index
Suppliers  = Suppliers_df.index
Products = range(1, DemandPeriods_df["Product"].max() + 1)


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
    * DistanceDistrictPeriod_df_dict.get((i, t))[j-1]
    * VehicleCostPerMileAndTonneOverall[3]
    / 1000
    for j in Candidates
    for i in Customers
    for t in Times
}

# =============================================================================
# Build optimization model
# =============================================================================
prob = xp.problem("MECWLP")

prob.controls.maxtime = -300

# =============================================================================
# Declarations
# =============================================================================

build = np.array([prob.addVariable(name='build_{0}_{1}'.format(c, t), vartype=xp.binary)
                  for c in Candidates for t in Times], dtype=xp.npvar).reshape(len(Candidates), len(Times))

open = np.array([prob.addVariable(name='open_{0}_{1}'.format(c, t), vartype=xp.binary)
                  for c in Candidates for t in Times], dtype=xp.npvar).reshape(len(Candidates), len(Times))

supply = np.array([prob.addVariable(name='supply_{0}_{1}_{2}'.format(c, s, t), vartype=xp.integer)
                   for c in Candidates for s in Suppliers for t in Times], dtype=xp.npvar).reshape(
                       len(Candidates), len(Suppliers), len(Times))

warehoused = np.array([prob.addVariable(name='warehoused_{0}_{1}_{2}'.format(c, p, t), vartype=xp.integer)
                       for c in Candidates for p in Products for t in Times],dtype=xp.npvar).reshape(
                           len(Candidates), len(Products), len(Times)
                       )
delivered = np.array([prob.addVariable(name='delivered_{0}_{1}_{2}_{3}'.format(c, Customers[k], p, t), vartype=xp.integer)
                       for c in Candidates for k in range(len(Customers)) for p in Products for t in Times],dtype=xp.npvar).reshape(
                           len(Candidates), len(Customers), len(Products), len(Times)
                       )

#=========================================================================================================
# Objective function
# ========================================================================================================
# Need to factor in the fixed costs related to the number of vans you have to send!!!!!
prob.setObjective(xp.Sum(open[c-1,t-1]*Operating_df["Operating cost"][c-1] for c in Candidates for t in Times) +
                  xp.Sum(build[c-1, t-1]*Setup_df["Setup cost"][c-1] for c in Candidates for t in Times) +
                  xp.Sum(supply[c-1, s-1, t-1]*CostSupplierCandidate[(s, c)] for c in Candidates for s in Suppliers for t in Times) +
                  xp.Sum(delivered[c-1, k, p-1, t-1]*CostCandidateCustomers[(c, Customers[k], t)] 
                         for c in Candidates for k in range(len(Customers)) for p in Products for t in Times), 
                  sense = xp.minimize)

# ========================================================================================================
# Constraints
# ========================================================================================================
# warehouses can only be built in one time period
prob.addConstraint(xp.Sum(build[c-1, t-1] for t in Times) <= 1 for c in Candidates)
# warehouse cannot be open if it's not been built
prob.addConstraint(open[c-1, t-1] <= xp.Sum(build[c-1, t2] for t2 in range(t-1)) for c in Candidates for t in Times if t != 1)
# Warehouse remains open from the year it's built onwards
prob.addConstraint(open[c-1, t-1] >= build[c-1, t-1] for c in Candidates for t in Times)
prob.addConstraint(open[c-1, t-1] >= open[c-1, t-2] for c in Candidates for t in Times if t != 1)
prob.addConstraint(open[c-1, 0] == build[c-1, 0] for c in Candidates)
# supplier constraints - can't supply more than total capacity
prob.addConstraint(xp.Sum(supply[c-1, s-1, t-1] for c in Candidates) <= Suppliers_df["Capacity"][s] for s in Suppliers for t in Times)
# update warehouse stock
prob.addConstraint(warehoused[c-1, p-1, t-1] == xp.Sum(supply[c-1, s-1, t-1] 
                          for s in Suppliers if Suppliers_df["Product group"][s] == p)
                          for c in Candidates for p in Products for t in Times)
# Can't carry more stock than max capacity
prob.addConstraint(xp.Sum(warehoused[c-1, p-1, t-1] for p in Products) <= Candidates_df["Capacity"][c] for c in Candidates for t in Times)
# Can't carry any stock in a warehouse that isn't open
prob.addConstraint(xp.Sum(warehoused[c-1, p-1, t-1] for p in Products) <= Candidates_df["Capacity"][c]*open[c-1, t-1]
                   for c in Candidates for t in Times)
#delivery constraints
#ensure we meed customer demand
prob.addConstraint(xp.Sum(delivered[c-1, k, p-1, t-1] for c in Candidates) >= DemandPeriodsGrouped[Customers[k], p, t]
                   for k in range(len(Customers)) for p in Products for t in Times)
#can't deliver more than the warehouses hold
prob.addConstraint(xp.Sum(delivered[c-1, k, p-1, t-1] for k in range(len(Customers))) <= warehoused[c-1, p-1, t-1]
                   for c in Candidates for p in Products for t in Times)


xp.setOutputEnabled(False)
prob.solve()
print(f'The objective function value is {prob.attributes.objval}')


#print and save some summary stats
#the period when warehouses get built/opened is saved off into
#the csv's build.csv and open.csv, respectively.

operating_costs = 0
building_costs = 0
supply_costs = 0
delivery_costs = 0
open = prob.getSolution(open)
build = prob.getSolution(build)
supply = prob.getSolution(supply)
delivery = prob.getSolution(delivered)
for c in Candidates:
    for t in Times:
        operating_costs = operating_costs + open[c-1,t-1]*Operating_df["Operating cost"][c-1]
        building_costs = building_costs + build[c-1, t-1]*Setup_df["Setup cost"][c-1]

build_df = pd.DataFrame(data = build, index = Candidates, columns = Times)
build_df = build_df[build_df.sum(axis=1) > 0]
open_df = pd.DataFrame(data = open, index = Candidates, columns = Times)
open_df = open_df[open_df.sum(axis=1)>0]


build_df.to_csv("build.csv")
open_df.to_csv("open.csv")

print(f"operating costs: {operating_costs}")
print(f"building costs: {building_costs}")

postprocessing.postprocessing(prob)


print("ok!")