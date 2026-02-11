import pandas as pd
import numpy as np
import xpress as xp
import os
import zipfile
import preprocessing 
import postprocessing
import MECWLP_model
import SCENARIOS_model
import constants
import transforms

#read in input data and group customer demand and adjust distances between candidates and customers accordingly
(Suppliers_df, Candidates_df, DemandPeriods_df, DemandPeriodsScenarios_df, DistanceSupplierDistrict_df,
  DistanceDistrictPeriod_df_dict, DemandPeriodsGrouped, con_index_dict, Operating_df,
    Setup_df, DemandPeriodsGrouped_scenarios, DistanceDistrictPeriod_df_scenarios_dict_list
    ) = preprocessing.read_input_data_and_preprocess()

# Maximum supplier index (assumed to be integer-indexed)
nbSuppliers = Suppliers_df.index.max()
# Maximum candidate index
nbCandidates = Candidates_df.index.max()
# Number of time periods
nbPeriods = DemandPeriods_df["Period"].max()
# Number of scenarios
nbScenarios = DemandPeriodsScenarios_df["Scenario"].max()
# =============================================================================
# Index sets
# =============================================================================
Customers  = list(con_index_dict.keys())
Candidates = Candidates_df.index
Suppliers  = Suppliers_df.index
Products = range(1, DemandPeriods_df["Product"].max() + 1)
# -----------------------------------------------------------------------------
# Time periods and scenarios
# -----------------------------------------------------------------------------
Times = range(1, nbPeriods + 1)
Scenarios = range(1, nbScenarios + 1)
# =============================================================================
# Transport cost calculations
# =============================================================================
CostSupplierCandidate = transforms.get_CostSupplierCandidate(DistanceSupplierDistrict_df,Suppliers_df,
                                                             constants.VehicleCostPerMileAndTonneOverall,
                                                             Candidates, Suppliers)
CostCandidateCustomers = transforms.get_CostCandidateCustomers(DistanceDistrictPeriod_df_dict,
                                                               constants.VehicleCostPerMileAndTonneOverall,
                                                               Candidates, Customers, Times)
CostCandidateCustomers_scenarios = []
for i in range(constants.number_of_scenarios_to_use()):
    CostCandidateCustomers_scenarios.append(transforms.get_CostCandidateCustomers(DistanceDistrictPeriod_df_scenarios_dict_list[i],
                                                               constants.VehicleCostPerMileAndTonneOverall,
                                                               Candidates, Customers, Times))

#Formulate & solve the MECWLP model
#MECWLP_model.MECWLP_model(Candidates, Times, Suppliers, Products,Customers,
#                          Operating_df, Setup_df, CostSupplierCandidate,
#                          DemandPeriodsGrouped, CostCandidateCustomers,
#                          Suppliers_df, Candidates_df)

SCENARIOS_model.SCENARIOS_model(Candidates, Times, Suppliers, Products,Customers, Scenarios,
                                Operating_df, Setup_df, CostSupplierCandidate,
                                DemandPeriodsGrouped_scenarios, CostCandidateCustomers_scenarios,
                                Suppliers_df, Candidates_df)



print("ok!")